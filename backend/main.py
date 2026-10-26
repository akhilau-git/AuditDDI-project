"""FastAPI service for the research-only AuditDDI model."""

from pathlib import Path
from typing import List, Optional
import hmac
import hashlib
import logging
import os
import re
import sys
import threading
import time
import uuid
import numpy as np
import requests
from urllib.parse import urlparse
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import torch
from torch_geometric.data import Batch


BACKEND_DIR = Path(__file__).resolve().parent
SRC_PATH = BACKEND_DIR.parent / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from models.ddi_model import (
    MODEL_ARCHITECTURE_EDGE_AWARE,
    MODEL_ARCHITECTURE_CROSS_ATTENTION_EDGE_AWARE,
    MODEL_ARCHITECTURE_MOTIF_EDGE_AWARE,
    MODEL_ARCHITECTURE_GRAPH_FP_FUSION,
    MODEL_ARCHITECTURE_AUDITDDI_MEMORY,
    MODEL_ARCHITECTURE_MULTIMODAL,
    MODEL_ARCHITECTURE_SEVEN_BRANCH,
    architecture_uses_edge_features,
    architecture_requires_motif_features,
    architecture_requires_fingerprint_features,
    model_from_checkpoint,
)
from models.neighbor_memory import AuditableNeighborMemory
from models.calibration import apply_calibrator
from models.applicability_domain import APPLICABILITY_DOMAIN_METHOD
from models.uncertainty import conformal_prediction_sets
from models.explainability import full_explanation_pipeline
if __package__:
    from .auth import AuthStore, SESSION_TTL_SECONDS
    from .compound_registry import CompoundRegistry
    from src.data_prep.polypharmacy_engine import analyze_polypharmacy_regimen
else:
    from auth import AuthStore, SESSION_TTL_SECONDS
    from compound_registry import CompoundRegistry
    from data_prep.polypharmacy_engine import analyze_polypharmacy_regimen
from data_prep.prepare_twosides import (
    FEATURE_SCHEMA_LEGACY,
    FEATURE_SCHEMA_RICH,
    smiles_to_graph,
)
from data_prep.pubchem_bridge import canonicalize as canonicalize_pubchem_smiles
from models.seven_branch_ddi import SEVEN_BRANCH_NAMES


LOGGER = logging.getLogger('auditddi.api')
REQUEST_ID_PATTERN = re.compile(r'^[A-Za-z0-9._-]{8,128}$')

if __package__:
    from .toxicity_lookup import (
        KNOWN_TOXICITY_SMILES,
        TOXICITY_BRIDGE_ERROR,
        TOXICITY_BRIDGE_SUMMARY,
        is_toxicity_known,
    )
else:
    from toxicity_lookup import (
        KNOWN_TOXICITY_SMILES,
        TOXICITY_BRIDGE_ERROR,
        TOXICITY_BRIDGE_SUMMARY,
        is_toxicity_known,
    )


def positive_integer_from_environment(name: str, default: int) -> int:
    """Read a positive integer setting and fail early on an invalid config."""
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError) as error:
        raise RuntimeError(f'{name} must be a positive integer') from error
    if value <= 0:
        raise RuntimeError(f'{name} must be a positive integer')
    return value


def non_negative_integer_from_environment(name: str, default: int) -> int:
    """Read an optional non-negative integer deployment setting."""
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError) as error:
        raise RuntimeError(f'{name} must be a non-negative integer') from error
    if value < 0:
        raise RuntimeError(f'{name} must be a non-negative integer')
    return value


def boolean_from_environment(name: str, default: bool) -> bool:
    """Read an explicit boolean deployment setting without silent coercion."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise RuntimeError(f'{name} must be true or false')


def configured_origins():
    default_origins = 'http://localhost:3000,http://127.0.0.1:3000'
    raw_origins = os.environ.get('PXDDI_ALLOWED_ORIGINS', default_origins)
    origins = [origin.strip() for origin in raw_origins.split(',') if origin.strip()]
    if not origins:
        raise RuntimeError('PXDDI_ALLOWED_ORIGINS must contain at least one origin')
    for origin in origins:
        parsed = urlparse(origin)
        if (
            origin == '*'
            or parsed.scheme not in {'http', 'https'}
            or not parsed.netloc
            or parsed.path
            or parsed.params
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise RuntimeError(
                'PXDDI_ALLOWED_ORIGINS must contain explicit HTTP(S) origins without paths.'
            )
    return origins


def configured_trusted_hosts() -> list[str]:
    """Return an explicit Host-header allowlist for the HTTP service.

    This protects the local/container service against Host-header attacks. A
    public deployment must replace the development defaults with its actual
    API domain through ``PXDDI_TRUSTED_HOSTS``; TLS, authentication, and a
    global rate limit still belong at the deployment gateway.
    """
    default_hosts = 'localhost,127.0.0.1,testserver'
    raw_hosts = os.environ.get('PXDDI_TRUSTED_HOSTS', default_hosts)
    hosts = [host.strip() for host in raw_hosts.split(',') if host.strip()]
    if not hosts:
        raise RuntimeError('PXDDI_TRUSTED_HOSTS must contain at least one host.')
    if any('*' in host or '://' in host or '/' in host for host in hosts):
        raise RuntimeError(
            'PXDDI_TRUSTED_HOSTS must contain explicit bare host names, not URLs, paths, or *.'
        )
    return hosts


def configured_deployment_mode() -> str:
    """Return the explicitly constrained API operating mode."""
    mode = os.environ.get('PXDDI_DEPLOYMENT_MODE', 'development').strip().lower()
    if mode not in {'development', 'production'}:
        raise RuntimeError('PXDDI_DEPLOYMENT_MODE must be development or production.')
    return mode


def configured_api_key(deployment_mode: str) -> str | None:
    """Read an optional local API key, mandatory in production mode."""
    value = os.environ.get('PXDDI_API_KEY')
    if value is not None:
        value = value.strip()
    if deployment_mode == 'production' and not value:
        raise RuntimeError('PXDDI_API_KEY must be set in production mode.')
    if value and len(value) < 32:
        raise RuntimeError('PXDDI_API_KEY must contain at least 32 characters.')
    return value or None


def validate_production_configuration(
    deployment_mode: str,
    api_key: str | None,
    allowed_origins: list[str],
    trusted_hosts: list[str],
    enable_docs: bool,
    rate_limit_per_minute: int,
) -> None:
    """Fail closed when someone tries to expose the local service publicly."""
    if deployment_mode != 'production':
        return
    if not api_key:
        raise RuntimeError('PXDDI_API_KEY must be set in production mode.')
    if enable_docs:
        raise RuntimeError('PXDDI_ENABLE_DOCS must be false in production mode.')
    if any(urlparse(origin).scheme != 'https' for origin in allowed_origins):
        raise RuntimeError('PXDDI_ALLOWED_ORIGINS must use HTTPS in production mode.')
    if any(host in {'localhost', '127.0.0.1', 'testserver'} for host in trusted_hosts):
        raise RuntimeError('PXDDI_TRUSTED_HOSTS must contain public API hosts in production mode.')
    if rate_limit_per_minute <= 0:
        raise RuntimeError(
            'PXDDI_RATE_LIMIT_PER_MINUTE must be positive in production mode.'
        )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as checkpoint_file:
        for block in iter(lambda: checkpoint_file.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def resolve_checkpoint_path(configured_path: str | None = None, *, allow_missing: bool = False) -> Path:
    """Resolve the selected model within the configured artifact directory.

    The default is the repository's ignored ``demo_artifacts`` folder. A
    checkpoint can be selected by its actual run filename; it need not be
    renamed to a legacy model filename. Absolute paths are accepted only when
    they remain inside the explicitly configured artifact directory.
    """
    artifact_dir = Path(os.environ.get(
        'AUDITDDI_CHECKPOINT_DIR', str(BACKEND_DIR.parent / 'demo_artifacts')
    )).resolve()
    raw_path = configured_path or os.environ.get(
        'PXDDI_CHECKPOINT_PATH', 'auditddi_seven_branch_candidate.pt'
    )
    requested_path = Path(raw_path)
    selected_path = requested_path if requested_path.is_absolute() else artifact_dir / requested_path
    selected_path = selected_path.resolve()
    try:
        selected_path.relative_to(artifact_dir)
    except ValueError as error:
        raise RuntimeError(
            'PXDDI_CHECKPOINT_PATH must point inside AUDITDDI_CHECKPOINT_DIR.'
        ) from error
    if not selected_path.is_file() and not allow_missing:
        raise RuntimeError(f'Configured checkpoint does not exist: {selected_path}')
    return selected_path


def checkpoint_feature_schema(checkpoint_metadata: dict) -> str:
    """Read and validate the graph schema required by a versioned checkpoint."""
    architecture = checkpoint_metadata.get('architecture_version', 'legacy_gat_v1')
    feature_schema = checkpoint_metadata.get('feature_schema', FEATURE_SCHEMA_LEGACY)
    if feature_schema not in {FEATURE_SCHEMA_LEGACY, FEATURE_SCHEMA_RICH}:
        raise RuntimeError(f'Unsupported checkpoint feature schema: {feature_schema!r}.')
    if architecture_uses_edge_features(architecture) and feature_schema != FEATURE_SCHEMA_RICH:
        raise RuntimeError(
            'An edge-aware checkpoint must declare the rich molecular feature schema.'
        )
    if architecture == 'legacy_gat_v1' and feature_schema != FEATURE_SCHEMA_LEGACY:
        raise RuntimeError(
            'A legacy GAT checkpoint must declare the legacy molecular feature schema.'
        )
    return feature_schema


MAX_SMILES_LENGTH = positive_integer_from_environment('PXDDI_MAX_SMILES_LENGTH', 1000)
MAX_MOLECULE_ATOMS = positive_integer_from_environment('PXDDI_MAX_MOLECULE_ATOMS', 200)
MAX_MOLECULE_BONDS = positive_integer_from_environment('PXDDI_MAX_MOLECULE_BONDS', 250)
MAX_REQUEST_BYTES = positive_integer_from_environment('PXDDI_MAX_REQUEST_BYTES', 16 * 1024)
MAX_CONCURRENT_PREDICTIONS = positive_integer_from_environment(
    'PXDDI_MAX_CONCURRENT_PREDICTIONS', 2
)
MAX_CONCURRENT_EXPLANATIONS = positive_integer_from_environment(
    'PXDDI_MAX_CONCURRENT_EXPLANATIONS', 1
)
ENABLE_API_DOCUMENTATION = boolean_from_environment('PXDDI_ENABLE_DOCS', True)
ALLOWED_ORIGINS = configured_origins()
TRUSTED_HOSTS = configured_trusted_hosts()
DEPLOYMENT_MODE = configured_deployment_mode()
API_KEY = configured_api_key(DEPLOYMENT_MODE)
RATE_LIMIT_PER_MINUTE = non_negative_integer_from_environment(
    'PXDDI_RATE_LIMIT_PER_MINUTE', 60 if DEPLOYMENT_MODE == 'production' else 0
)
AUTH_ENABLED = boolean_from_environment('PXDDI_AUTH_ENABLED', False)
AUTH_STATE_DIR = Path(os.environ.get('PXDDI_AUTH_STATE_DIR', BACKEND_DIR / 'state'))
AUTH_BOOTSTRAP_TOKEN = os.environ.get('PXDDI_AUTH_BOOTSTRAP_TOKEN', '').strip()
AUTH_COOKIE_NAME = 'auditddi_session'
AUTH_COOKIE_SECURE = DEPLOYMENT_MODE == 'production'
AUTH_STORE = AuthStore(AUTH_STATE_DIR) if AUTH_ENABLED else None
COMPOUND_REGISTRY = CompoundRegistry(AUTH_STATE_DIR)
validate_production_configuration(
    DEPLOYMENT_MODE,
    API_KEY,
    ALLOWED_ORIGINS,
    TRUSTED_HOSTS,
    ENABLE_API_DOCUMENTATION,
    RATE_LIMIT_PER_MINUTE,
)
if DEPLOYMENT_MODE == 'production' and not AUTH_ENABLED:
    raise RuntimeError('PXDDI_AUTH_ENABLED must be true in production mode.')

app = FastAPI(
    title='AuditDDI API',
    docs_url='/docs' if ENABLE_API_DOCUMENTATION else None,
    redoc_url=None,
    openapi_url='/openapi.json' if ENABLE_API_DOCUMENTATION else None,
)

# The default permits only the local frontend. Deployments must explicitly set
# PXDDI_ALLOWED_ORIGINS to their own comma-separated frontend origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=['GET', 'POST', 'PATCH', 'OPTIONS'],
    allow_headers=['Content-Type', 'X-Request-ID', 'X-API-Key'],
    expose_headers=['X-Request-ID'],
    allow_credentials=True,
)


class MaxRequestBodyMiddleware:
    """Enforce a small buffered JSON body limit, including chunked requests."""

    def __init__(self, app):
        self.app = app

    @staticmethod
    async def _reject(scope, receive, send, status_code: int, detail: str) -> None:
        await JSONResponse(status_code=status_code, content={'detail': detail})(
            scope, receive, send
        )

    async def __call__(self, scope, receive, send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get('headers', [])}
        content_length = headers.get(b'content-length')
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                await self._reject(
                    scope, receive, send, 400, 'Content-Length must be a valid integer.'
                )
                return
            if declared_size < 0 or declared_size > MAX_REQUEST_BYTES:
                await self._reject(
                    scope,
                    receive,
                    send,
                    413,
                    f'Request body exceeds the {MAX_REQUEST_BYTES}-byte API limit.',
                )
                return

        messages = []
        received_bytes = 0
        while True:
            message = await receive()
            messages.append(message)
            if message['type'] == 'http.request':
                received_bytes += len(message.get('body', b''))
                if received_bytes > MAX_REQUEST_BYTES:
                    await self._reject(
                        scope,
                        receive,
                        send,
                        413,
                        f'Request body exceeds the {MAX_REQUEST_BYTES}-byte API limit.',
                    )
                    return
                if not message.get('more_body', False):
                    break
            elif message['type'] == 'http.disconnect':
                break

        async def replay_body():
            if messages:
                return messages.pop(0)
            return {'type': 'http.disconnect'}

        await self.app(scope, replay_body, send)


class PerClientFixedWindowRateLimiter:
    """Small in-process rate limiter for the protected inference endpoints.

    This limits an accidentally exposed single worker. A production gateway
    must still enforce a shared, durable rate limit across all workers and
    instances; this class intentionally makes no global-distribution claim.
    """

    def __init__(self, requests_per_minute: int) -> None:
        self.requests_per_minute = requests_per_minute
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, int]] = {}

    def retry_after_seconds(self, client_key: str) -> int | None:
        if self.requests_per_minute <= 0:
            return None
        now = time.monotonic()
        current_window = int(now // 60)
        with self._lock:
            # Bound the local bookkeeping even if an attacker rotates source
            # addresses. This is not a replacement for gateway protection.
            self._windows = {
                key: value
                for key, value in self._windows.items()
                if value[0] == current_window
            }
            window, count = self._windows.get(client_key, (current_window, 0))
            if window != current_window:
                count = 0
            if count >= self.requests_per_minute:
                return max(1, int(60 - (now % 60)))
            self._windows[client_key] = (current_window, count + 1)
        return None


PER_CLIENT_RATE_LIMITER = PerClientFixedWindowRateLimiter(RATE_LIMIT_PER_MINUTE)
AUTH_RATE_LIMITER = PerClientFixedWindowRateLimiter(10)
PROTECTED_API_PATHS = frozenset({'/predict', '/explain'})

ROLE_WORKSPACES = {
    'research': 'research.html',
    'prescriber_review': 'prescriber.html',
    'medication_safety': 'pharmacy.html',
    'governance': 'governance.html',
    'portfolio_screening': 'pharma.html',
    'public_information': 'medication-information.html',
    'admin': 'admin.html',
}
VALID_ACCOUNT_ROLES = frozenset(ROLE_WORKSPACES) - {'admin'}


def session_user_from_request(request: Request) -> dict | None:
    if not AUTH_ENABLED or AUTH_STORE is None:
        return None
    return AUTH_STORE.session_user(request.cookies.get(AUTH_COOKIE_NAME))


def required_roles_for_path(path: str) -> set[str] | None:
    """Return the least-privilege roles for each application API path."""
    if path.startswith('/auth/users'):
        return {'admin'}
    if path == '/compounds':
        return {'research', 'portfolio_screening'}
    if path in {'/drugs/lookup', '/drugs/structure', '/evidence/labels'} or path.startswith('/drugs/conformer/'):
        return {'research', 'prescriber_review', 'governance', 'portfolio_screening'}
    if path == '/polypharmacy/analyze':
        return {'research', 'medication_safety', 'portfolio_screening'}
    if path in {'/predict', '/explain'}:
        return {'research', 'prescriber_review', 'governance', 'portfolio_screening'}
    if path in {'/audit/dossier', '/api/audit/dossier'}:
        return {
            'research', 'prescriber_review', 'medication_safety',
            'governance', 'portfolio_screening',
        }
    return None


class RequestGuardMiddleware(BaseHTTPMiddleware):
    """Guard request availability and log non-sensitive request metadata.

    This deliberately never logs a request body, SMILES string, or secret. It
    applies optional local API-key authentication and a per-process rate limit
    to inference routes, but is not a substitute for a gateway rate limit,
    durable audit log, TLS termination, or clinical audit trail.
    """

    @staticmethod
    def _finalize_response(
        request: Request,
        response,
        request_id: str,
        started_at: float,
    ):
        """Attach stable response metadata and log no request-body content."""
        response.headers['X-Request-ID'] = request_id
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        LOGGER.info(
            'api_request request_id=%s method=%s path=%s status=%s duration_ms=%.2f',
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started_at) * 1000,
        )
        return response

    async def dispatch(self, request: Request, call_next):
        supplied_request_id = request.headers.get('x-request-id', '')
        request_id = (
            supplied_request_id
            if REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else uuid.uuid4().hex
        )
        started_at = time.perf_counter()
        auth_exempt_paths = {
            '/health', '/ready', '/auth/session', '/auth/login',
            '/auth/bootstrap', '/auth/logout', '/workspaces',
        }
        required_roles = required_roles_for_path(request.url.path)
        if (
            AUTH_ENABLED
            and request.method != 'OPTIONS'
            and request.url.path not in auth_exempt_paths
        ):
            user = session_user_from_request(request)
            if user is None:
                response = JSONResponse(
                    status_code=401,
                    content={'detail': 'Sign in is required to access this resource.'},
                )
                return self._finalize_response(request, response, request_id, started_at)
            if required_roles is not None and user['role'] not in required_roles:
                response = JSONResponse(
                    status_code=403,
                    content={'detail': 'Your account role cannot access this resource.'},
                )
                return self._finalize_response(request, response, request_id, started_at)
        if request.method == 'POST' and request.url.path in PROTECTED_API_PATHS:
            if API_KEY is not None and session_user_from_request(request) is None:
                supplied_key = request.headers.get('x-api-key', '')
                if not hmac.compare_digest(supplied_key, API_KEY):
                    response = JSONResponse(
                        status_code=401,
                        content={'detail': 'Valid API credentials are required.'},
                    )
                    return self._finalize_response(request, response, request_id, started_at)
            client_key = request.client.host if request.client else 'unknown_client'
            retry_after_seconds = PER_CLIENT_RATE_LIMITER.retry_after_seconds(client_key)
            if retry_after_seconds is not None:
                response = JSONResponse(
                    status_code=429,
                    content={'detail': 'Rate limit exceeded. Please retry later.'},
                    headers={'Retry-After': str(retry_after_seconds)},
                )
                return self._finalize_response(request, response, request_id, started_at)
        if request.method == 'POST' and request.url.path in {'/auth/login', '/auth/bootstrap'}:
            client_key = request.client.host if request.client else 'unknown_client'
            retry_after_seconds = AUTH_RATE_LIMITER.retry_after_seconds(client_key)
            if retry_after_seconds is not None:
                response = JSONResponse(
                    status_code=429,
                    content={'detail': 'Authentication rate limit exceeded. Please retry later.'},
                    headers={'Retry-After': str(retry_after_seconds)},
                )
                return self._finalize_response(request, response, request_id, started_at)
        try:
            response = await call_next(request)
        except Exception:
            LOGGER.exception(
                'api_request_failed request_id=%s method=%s path=%s',
                request_id,
                request.method,
                request.url.path,
            )
            raise

        return self._finalize_response(request, response, request_id, started_at)


# Middleware is added in reverse wrapping order. This gives the request path
# TrustedHost -> RequestGuard -> MaxRequestBody -> CORS -> application.
app.add_middleware(MaxRequestBodyMiddleware)
app.add_middleware(RequestGuardMiddleware)
# Add this after CORS so it is the outermost middleware, including for CORS
# preflight requests. Otherwise a malicious Host header could bypass the check.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)

CHECKPOINT_PATH = resolve_checkpoint_path(allow_missing=True)
CHECKPOINT_LOAD_ERROR = None
if not CHECKPOINT_PATH.is_file():
    checkpoint = {}
    CHECKPOINT_LOAD_ERROR = f'Configured checkpoint does not exist: {CHECKPOINT_PATH}'
    LOGGER.warning('%s; starting API in lookup-only mode.', CHECKPOINT_LOAD_ERROR)
else:
    try:
        checkpoint = torch.load(CHECKPOINT_PATH, map_location='cpu', weights_only=True)
    except Exception as safe_load_err:
        allow_unsafe = os.environ.get('PXDDI_ALLOW_UNSAFE_PICKLE', '0').strip().lower() in {'1', 'true', 'yes'}
        if not allow_unsafe:
            LOGGER.error(
                "Security Policy Violation: Checkpoint '%s' failed weights_only=True load: %s. "
                "To permit unsafe pickle deserialization for trusted local development, set PXDDI_ALLOW_UNSAFE_PICKLE=1.",
                CHECKPOINT_PATH,
                safe_load_err,
            )
            raise RuntimeError(
                f"Checkpoint at {CHECKPOINT_PATH} cannot be safely deserialized with weights_only=True. "
                f"Arbitrary code execution via pickle is blocked. "
                f"Set environment variable PXDDI_ALLOW_UNSAFE_PICKLE=1 to override for trusted files."
            ) from safe_load_err
        LOGGER.warning(
            "AUDIT WARNING: Deserializing checkpoint with weights_only=False. "
            "Do not run this path in production or on untrusted checkpoint files."
        )
        checkpoint = torch.load(CHECKPOINT_PATH, map_location='cpu', weights_only=False)

if checkpoint.get('use_chemberta', False):
    try:
        import transformers  # noqa: F401
    except ImportError:
        LOGGER.error("The selected checkpoint requires 'transformers', which is not installed.")
        raise RuntimeError(
            "The selected checkpoint requires the 'transformers' package for ChemBERTa embeddings. "
            "Please install it via: pip install transformers"
        )
model = None
if checkpoint:
    model = model_from_checkpoint(checkpoint)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
MODEL_FEATURE_SCHEMA = checkpoint_feature_schema(checkpoint)
MODEL_REQUIRES_MOTIF_FEATURES = architecture_requires_motif_features(
    checkpoint.get('architecture_version', 'legacy_gat_v1')
)
MODEL_REQUIRES_FP_FEATURES = architecture_requires_fingerprint_features(
    checkpoint.get('architecture_version', 'legacy_gat_v1')
)
SOURCE_FEATURE_LOOKUP = checkpoint.get('source_feature_lookup', {})
SOURCE_FEATURE_DIM = int(checkpoint.get('gene_feature_dim', 51))
SEVEN_BRANCH_FEATURE_LOOKUP: dict[str, dict[str, tuple[list[float], float]]] = {}
SEVEN_BRANCH_BUNDLE_SHA256 = None
SEVEN_BRANCH_BUNDLE_DRUG_COUNT = 0
SEVEN_BRANCH_BUNDLE_COVERAGE: dict[str, float] = {}
if checkpoint.get('architecture_version') == MODEL_ARCHITECTURE_SEVEN_BRANCH:
    bundle_value = os.environ.get(
        'AUDITDDI_SEVEN_BRANCH_FEATURE_BUNDLE',
        checkpoint.get('seven_branch_bundle_path', ''),
    )
    bundle_path = Path(bundle_value) if bundle_value else None
    if bundle_path is None or not bundle_path.is_file():
        raise RuntimeError(
            'This checkpoint requires the seven-branch feature bundle. Set '
            'AUDITDDI_SEVEN_BRANCH_FEATURE_BUNDLE to the matching .npz file.'
        )
    expected_bundle_hash = checkpoint.get('seven_branch_bundle_sha256')
    if not expected_bundle_hash:
        raise RuntimeError(
            'Seven-branch checkpoint has no feature-bundle SHA-256 provenance; '
            'refusing to load an unverified bundle.'
        )
    SEVEN_BRANCH_BUNDLE_SHA256 = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    if not hmac.compare_digest(SEVEN_BRANCH_BUNDLE_SHA256, expected_bundle_hash):
        raise RuntimeError('Seven-branch feature bundle hash does not match the checkpoint.')
    with np.load(bundle_path, allow_pickle=False) as bundle:
        if 'canonical_smiles' not in bundle:
            raise RuntimeError('Seven-branch feature bundle is missing canonical_smiles.')
        keys = bundle['canonical_smiles'].astype(str)
        if keys.ndim != 1 or not len(keys):
            raise RuntimeError('Seven-branch bundle canonical_smiles must be a non-empty vector.')
        branch_dimensions = checkpoint.get('seven_branch_dimensions', {})
        branch_arrays = {}
        for branch in SEVEN_BRANCH_NAMES:
            if f'{branch}_features' not in bundle or f'{branch}_mask' not in bundle:
                raise RuntimeError(f'Seven-branch feature bundle is missing {branch}.')
            if branch not in branch_dimensions:
                raise RuntimeError(f'Seven-branch checkpoint is missing the {branch} dimension.')
            expected_dim = int(branch_dimensions[branch])
            features = np.asarray(bundle[f'{branch}_features'], dtype=np.float32)
            masks = np.asarray(bundle[f'{branch}_mask'], dtype=np.float32)
            if features.shape != (len(keys), expected_dim):
                raise RuntimeError(
                    f'Seven-branch {branch} feature shape {features.shape} does not match '
                    f'({len(keys)}, {expected_dim}) from the checkpoint.'
                )
            if masks.shape != (len(keys),):
                raise RuntimeError(
                    f'Seven-branch {branch} mask shape {masks.shape} does not match '
                    f'({len(keys)},).'
                )
            if not np.isfinite(features).all() or not np.isfinite(masks).all():
                raise RuntimeError(f'Seven-branch {branch} contains non-finite values.')
            if not np.isin(masks, (0.0, 1.0)).all():
                raise RuntimeError(f'Seven-branch {branch} masks must contain only 0 or 1.')
            branch_arrays[branch] = (features, masks)
        for index, raw_key in enumerate(keys):
            canonical_key = canonicalize_pubchem_smiles(raw_key)
            if not canonical_key:
                raise RuntimeError(
                    f'Seven-branch feature bundle contains invalid SMILES at row {index}.'
                )
            if canonical_key in SEVEN_BRANCH_FEATURE_LOOKUP:
                raise RuntimeError(
                    'Seven-branch feature bundle contains duplicate canonical drug '
                    f'identities at row {index}.'
                )
            SEVEN_BRANCH_FEATURE_LOOKUP[canonical_key] = {
                branch: (
                    branch_arrays[branch][0][index].astype(float).tolist(),
                    float(branch_arrays[branch][1][index]),
                )
                for branch in SEVEN_BRANCH_NAMES
            }
    if not SEVEN_BRANCH_FEATURE_LOOKUP:
        raise RuntimeError('Seven-branch feature bundle has no canonical drug records.')
    SEVEN_BRANCH_BUNDLE_DRUG_COUNT = len(SEVEN_BRANCH_FEATURE_LOOKUP)
    SEVEN_BRANCH_BUNDLE_COVERAGE = {
        branch: float(np.mean([
            SEVEN_BRANCH_FEATURE_LOOKUP[key][branch][1]
            for key in SEVEN_BRANCH_FEATURE_LOOKUP
        ]))
        for branch in SEVEN_BRANCH_NAMES
    }

NEIGHBOR_MEMORY = None
if checkpoint.get('use_neighbor_memory') and checkpoint.get('neighbor_memory_state'):
    try:
        NEIGHBOR_MEMORY = AuditableNeighborMemory.from_state(checkpoint['neighbor_memory_state'])
        LOGGER.info('AuditableNeighborMemory successfully restored into API.')
    except Exception as exc:
        LOGGER.warning('Could not restore AuditableNeighborMemory: %s', exc)


def compute_ecfp_tensor(smiles: str, radius: int = 2, n_bits: int = 1024) -> torch.Tensor:
    """Compute normalized 1024-bit Morgan fingerprint tensor for candidate models."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return torch.zeros((1, n_bits), dtype=torch.float)
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits)
    fp = gen.GetFingerprint(mol)
    import numpy as np
    arr = np.zeros((n_bits,), dtype=np.float32)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return torch.from_numpy(arr).unsqueeze(0)

DECISION_THRESHOLD = float(checkpoint.get('optimal_threshold', checkpoint.get('s1_opt_thresh', checkpoint.get('threshold', 0.5))))
CALIBRATION = checkpoint.get('calibration')
CHECKPOINT_SHA256 = file_sha256(CHECKPOINT_PATH) if CHECKPOINT_PATH.is_file() else None
EXPLANATION_SEMAPHORE = threading.BoundedSemaphore(MAX_CONCURRENT_EXPLANATIONS)
PREDICTION_SEMAPHORE = threading.BoundedSemaphore(MAX_CONCURRENT_PREDICTIONS)


def _optional_float(value) -> float | None:
    """Convert checkpoint scalar metadata without making health checks fragile."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if 0 <= numeric <= 1 else None


def stored_validation_evidence(checkpoint_metadata: dict) -> dict:
    """Describe stored validation metadata without presenting it as test evidence."""
    auroc = _optional_float(
        checkpoint_metadata.get('validation_auroc', checkpoint_metadata.get('auroc'))
    )
    epoch_value = checkpoint_metadata.get('epoch')
    epoch = int(epoch_value) if isinstance(epoch_value, (int, float)) else None
    selection_split = checkpoint_metadata.get(
        'model_selection_split',
        'internal validation; exact historical split manifest is unavailable',
    )
    return {
        'status': 'available' if auroc is not None else 'unavailable',
        'auroc': auroc,
        'epoch': epoch,
        'selection_metric': checkpoint_metadata.get('model_selection_metric', 'AUROC'),
        'selection_split': selection_split,
        'note': (
            'This is stored internal model-selection metadata. It is not '
            'transductive test, cold-start, external, or clinical performance.'
        ),
    }


def auxiliary_toxicity_head_status(checkpoint_metadata: dict) -> dict:
    """State whether auxiliary-head training uses the recorded logits contract.

    The interaction forward path remains loadable for legacy checkpoints.  But
    a checkpoint that predates the explicit logits-vs-probability record cannot
    be used as evidence for an auxiliary toxicity-training claim.
    """
    if float(checkpoint_metadata.get('toxicity_loss_weight', 0.0) or 0.0) <= 0.0:
        return {
            'status': 'not_trained',
            'note': 'This checkpoint was trained for DDI prediction only; toxicity-head scores are suppressed.',
        }
    if checkpoint_metadata.get('toxicity_head_output') == 'logits_v1':
        return {
            'status': 'current_logits_training_contract_recorded',
            'note': (
                'The candidate records raw toxicity logits for the auxiliary '
                'BCE-with-logits training objective. Its toxicity output remains '
                'an auxiliary research score, not a clinical probability.'
            ),
        }
    return {
        'status': 'historical_contract_not_recorded',
        'note': (
            'This checkpoint predates the recorded auxiliary-toxicity logits '
            'training contract. It remains a loadable research DDI reference, but '
            'it must not support an auxiliary-toxicity performance claim; retrain '
            'a candidate with the current pipeline before making one.'
        ),
    }


class CheckpointStructuralDomain:
    """Optional checkpoint-backed nearest-training-structure diagnostic.

    Candidate checkpoints produced by a future audited run may carry the
    canonical training-structure reference list. The API can then flag a query
    whose drug structure is far from every training drug. The diagnostic is a
    review guardrail, never a reliability or safety guarantee.
    """

    REQUIRED_METHOD = APPLICABILITY_DOMAIN_METHOD

    def __init__(self, metadata: dict) -> None:
        if metadata.get('method') != self.REQUIRED_METHOD:
            raise ValueError('unsupported applicability-domain method')
        reference_smiles = metadata.get('reference_canonical_smiles')
        if not isinstance(reference_smiles, list) or not reference_smiles:
            raise ValueError('missing canonical training-structure references')
        if len(reference_smiles) > 50_000:
            raise ValueError('too many structural-domain reference structures')
        radius = int(metadata.get('radius', 2))
        num_bits = int(metadata.get('num_bits', 1024))
        minimum_similarity = float(metadata.get('minimum_tanimoto_similarity', 0.4))
        if radius <= 0 or num_bits < 128 or not 0 <= minimum_similarity <= 1:
            raise ValueError('invalid applicability-domain parameters')
        if metadata.get('include_chirality', True) is not True:
            raise ValueError('only chirality-aware ECFP checkpoint domain state is supported')

        canonical_references = []
        for smiles in reference_smiles:
            molecule = Chem.MolFromSmiles(str(smiles).strip())
            if molecule is None:
                raise ValueError('invalid canonical training structure in checkpoint metadata')
            canonical_references.append(
                Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
            )
        self.method = self.REQUIRED_METHOD
        self.radius = radius
        self.num_bits = num_bits
        self.minimum_similarity = minimum_similarity
        self.generator = rdFingerprintGenerator.GetMorganGenerator(
            radius=radius,
            fpSize=num_bits,
            includeChirality=True,
        )
        self.reference_smiles = frozenset(canonical_references)
        self.reference_fingerprints = tuple(
            self.generator.GetFingerprint(Chem.MolFromSmiles(smiles))
            for smiles in sorted(self.reference_smiles)
        )

    def score_smiles(self, smiles: str) -> dict:
        molecule = Chem.MolFromSmiles(smiles.strip())
        if molecule is None:
            raise ValueError('SMILES could not be parsed for structural-domain scoring')
        canonical = Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
        fingerprint = self.generator.GetFingerprint(molecule)
        similarity = max(DataStructs.BulkTanimotoSimilarity(
            fingerprint, self.reference_fingerprints
        ))
        return {
            'canonical_smiles': canonical,
            'nearest_train_tanimoto': float(similarity),
            'exactly_seen_in_training': canonical in self.reference_smiles,
            'outside_structural_domain': bool(similarity < self.minimum_similarity),
        }


def checkpoint_structural_domain(
    checkpoint_metadata: dict,
) -> tuple[CheckpointStructuralDomain | None, str | None]:
    """Load optional domain state while keeping legacy checkpoints loadable."""
    metadata = checkpoint_metadata.get('applicability_domain')
    if metadata is None:
        return None, 'checkpoint_has_no_structural_domain_reference_set'
    if not isinstance(metadata, dict):
        return None, 'checkpoint_structural_domain_metadata_is_invalid'
    try:
        return CheckpointStructuralDomain(metadata), None
    except (TypeError, ValueError) as error:
        return None, f'checkpoint_structural_domain_unavailable: {error}'


STRUCTURAL_DOMAIN, STRUCTURAL_DOMAIN_ERROR = checkpoint_structural_domain(checkpoint)

if model is not None:
    LOGGER.info(
        'Loaded DDI model architecture=%s threshold=%s checkpoint_sha256=%s',
        checkpoint.get('architecture_version', 'legacy_gat_v1'),
        DECISION_THRESHOLD,
        CHECKPOINT_SHA256,
    )
else:
    LOGGER.warning('DDI prediction is disabled until a trained checkpoint is installed.')


class DDIRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    smiles_a: str = Field(min_length=1, max_length=MAX_SMILES_LENGTH)
    smiles_b: str = Field(min_length=1, max_length=MAX_SMILES_LENGTH)
    age_band: Optional[StrictInt] = None
    sex: Optional[StrictInt] = None
    comorbidities: Optional[List[StrictInt]] = None

    @field_validator('smiles_a', 'smiles_b', mode='before')
    @classmethod
    def strip_smiles(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('age_band')
    @classmethod
    def validate_age_band(cls, value):
        if value is not None:
            raise ValueError('Patient context is not supported by this model.')
        return value

    @field_validator('sex')
    @classmethod
    def validate_sex(cls, value):
        if value is not None:
            raise ValueError('Patient context is not supported by this model.')
        return value

    @field_validator('comorbidities')
    @classmethod
    def validate_comorbidities(cls, value):
        if value is not None:
            raise ValueError('Patient context is not supported by this model.')
        return value


class DrugLookupRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=120)

    @field_validator('query', mode='before')
    @classmethod
    def strip_query(cls, value):
        return value.strip() if isinstance(value, str) else value


class DrugStructureRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    smiles: str = Field(min_length=1, max_length=MAX_SMILES_LENGTH)

    @field_validator('smiles', mode='before')
    @classmethod
    def strip_smiles(cls, value):
        return value.strip() if isinstance(value, str) else value


class PairLabelEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    drug_a_name: str = Field(min_length=1, max_length=120)
    drug_b_name: str = Field(min_length=1, max_length=120)

    @field_validator('drug_a_name', 'drug_b_name', mode='before')
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class BootstrapRequest(LoginRequest):
    bootstrap_token: str = Field(min_length=1, max_length=512)


class AccountCreateRequest(LoginRequest):
    role: str = Field(min_length=1, max_length=64)


class AccountStatusRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    is_active: bool


class AccountPasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    password: str = Field(min_length=12, max_length=1024)


class CompoundCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=160)
    external_id: Optional[str] = Field(default=None, max_length=160)
    smiles: str = Field(min_length=1, max_length=MAX_SMILES_LENGTH)
    evidence_notes: Optional[str] = Field(default=None, max_length=4000)

    @field_validator('name', 'smiles', mode='before')
    @classmethod
    def strip_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class RegimenDrug(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=160)
    smiles: str = Field(min_length=1, max_length=MAX_SMILES_LENGTH)

    @field_validator('name', 'smiles', mode='before')
    @classmethod
    def strip_regimen_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class PolypharmacyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    drugs: list[RegimenDrug] = Field(min_length=2, max_length=12)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, error: RequestValidationError
):
    """Return stable validation errors without echoing submitted structures."""
    safe_errors = [
        {
            'loc': list(item['loc']),
            'msg': item['msg'],
            'type': item['type'],
        }
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={'detail': safe_errors})


def build_drug_batches(req: DDIRequest):
    """Build bounded molecular batches shared by prediction and explanation."""
    graph_a = smiles_to_graph(
        req.smiles_a,
        feature_schema=MODEL_FEATURE_SCHEMA,
        include_motif_features=MODEL_REQUIRES_MOTIF_FEATURES,
    )
    graph_b = smiles_to_graph(
        req.smiles_b,
        feature_schema=MODEL_FEATURE_SCHEMA,
        include_motif_features=MODEL_REQUIRES_MOTIF_FEATURES,
    )
    if graph_a is None or graph_b is None:
        raise HTTPException(
            status_code=422,
            detail='Invalid, unsupported, or single-atom SMILES string for one or both drugs.',
        )

    for name, graph in (('drug A', graph_a), ('drug B', graph_b)):
        atom_count = int(graph.num_nodes) if graph.num_nodes is not None else 0
        bond_count = int(graph.edge_index.size(1) // 2) if graph.edge_index is not None else 0
        if atom_count > MAX_MOLECULE_ATOMS:
            raise HTTPException(
                status_code=422,
                detail=f'{name} has {atom_count} atoms; the limit is {MAX_MOLECULE_ATOMS}.',
            )
        if bond_count > MAX_MOLECULE_BONDS:
            raise HTTPException(
                status_code=422,
                detail=f'{name} has {bond_count} bonds; the limit is {MAX_MOLECULE_BONDS}.',
            )

    if MODEL_REQUIRES_FP_FEATURES:
        graph_a.fingerprint_features = compute_ecfp_tensor(req.smiles_a)
        graph_b.fingerprint_features = compute_ecfp_tensor(req.smiles_b)

    if checkpoint.get('source_feature_schema') == 'auditddi_seven_source_profile_51_v1':
        for raw_smiles, graph in ((req.smiles_a, graph_a), (req.smiles_b, graph_b)):
            canonical_smiles = canonicalize_pubchem_smiles(raw_smiles)
            profile = SOURCE_FEATURE_LOOKUP.get(canonical_smiles) if canonical_smiles else None
            if profile is None:
                profile = [0.0] * SOURCE_FEATURE_DIM
            if len(profile) != SOURCE_FEATURE_DIM:
                raise RuntimeError('Checkpoint source-feature profile has an incompatible dimension.')
            graph.source_features = torch.tensor(profile, dtype=torch.float32)
            graph.source_profile_mask = torch.tensor(
                float(any(profile[-3:])), dtype=torch.float32
            )

    if checkpoint.get('architecture_version') == MODEL_ARCHITECTURE_SEVEN_BRANCH:
        branch_dimensions = checkpoint.get('seven_branch_dimensions', {})
        for raw_smiles, graph in ((req.smiles_a, graph_a), (req.smiles_b, graph_b)):
            canonical_smiles = canonicalize_pubchem_smiles(raw_smiles)
            profile = SEVEN_BRANCH_FEATURE_LOOKUP.get(canonical_smiles, {})
            for branch in SEVEN_BRANCH_NAMES:
                expected_dim = int(branch_dimensions[branch])
                values, available = profile.get(
                    branch, ([0.0] * expected_dim, 0.0)
                )
                if len(values) != expected_dim:
                    raise RuntimeError(
                        f'Seven-branch feature width mismatch for {branch}; '
                        'the API bundle and checkpoint are incompatible.'
                    )
                setattr(graph, f'{branch}_features', torch.tensor(values, dtype=torch.float32))
                setattr(graph, f'{branch}_mask', torch.tensor([available], dtype=torch.float32))

    return Batch.from_data_list([graph_a]), Batch.from_data_list([graph_b])


def source_feature_coverage_response(batch_a, batch_b) -> dict | None:
    """Describe which archived drug profiles were found for this prediction."""
    if checkpoint.get('source_feature_schema') != 'auditddi_seven_source_profile_51_v1':
        return None
    availability_names = ('PharmGKB', 'openFDA')
    def available(batch, offset: int) -> bool:
        profile = getattr(batch, 'source_features', None)
        if profile is None:
            return False
        values = profile.float().reshape(-1, SOURCE_FEATURE_DIM)
        return bool(values[0, SOURCE_FEATURE_DIM - 3 + offset].item() > 0)
    return {
        'drug_a': {name: available(batch_a, i) for i, name in enumerate(availability_names)},
        'drug_b': {name: available(batch_b, i) for i, name in enumerate(availability_names)},
        'FAERS': {
            'used_as_predictor': False,
            'reason': 'Report counts are withheld pending temporal-overlap and reporting-bias evaluation.',
        },
        'note': 'A false PharmGKB/openFDA value means no matched profile was available for the submitted structure.',
    }


def seven_branch_coverage_response(batch_a, batch_b) -> dict | None:
    if checkpoint.get('architecture_version') != MODEL_ARCHITECTURE_SEVEN_BRANCH:
        return None
    coverage = {}
    for branch in SEVEN_BRANCH_NAMES:
        coverage[branch] = {
            'drug_a': bool(getattr(batch_a, f'{branch}_mask')[0].item() > 0),
            'drug_b': bool(getattr(batch_b, f'{branch}_mask')[0].item() > 0),
        }
    return coverage


def toxicity_response(smiles: str, score: float):
    """Separate an auxiliary model score from FAERS-label coverage."""
    if float(checkpoint.get('toxicity_loss_weight', 0.0) or 0.0) <= 0.0:
        return {
            'score': None,
            'status': 'not_trained',
            'known': False,
            'training_label_available': False,
            'coverage_note': 'This checkpoint was trained for DDI prediction only; it has no supervised toxicity head.',
        }
    training_label_available = is_toxicity_known(smiles)
    coverage_note = (
        'A matched FAERS-derived toxicity training label is available for this structure.'
        if training_label_available
        else 'No matched FAERS-derived toxicity training label is available for this structure.'
    )
    return {
        'score': score,
        'model_score_note': (
            'This is an auxiliary research-model score, not a clinical toxicity '
            'probability. FAERS coverage describes supervision availability only.'
        ),
        'known': training_label_available,
        'training_label_available': training_label_available,
        'coverage_note': coverage_note,
    }


def risk_calibration_response() -> dict:
    """Describe whether the loaded checkpoint supplies a saved calibration map."""
    if CALIBRATION and CALIBRATION.get('status') == 'fitted':
        return {
            'status': 'internally_calibrated',
            'method': CALIBRATION.get('method'),
            'fitted_on': CALIBRATION.get('fitted_on'),
            'note': (
                'Calibration was fitted on the internal validation split only. It is not '
                'evidence of calibrated cold-start, external, or clinical performance.'
            ),
        }
    return {
        'status': 'uncalibrated',
        'method': None,
        'fitted_on': None,
        'note': 'This checkpoint is uncalibrated; no saved calibration map is available.',
    }


def uncertainty_response(probability: float) -> dict:
    """Return a saved conformal set only when the checkpoint carries its state."""
    conformal = checkpoint.get('conformal')
    if not isinstance(conformal, dict) or conformal.get('status') != 'fitted':
        return {
            'status': 'not_available',
            'method': None,
            'abstain': None,
            'prediction_set': None,
            'note': (
                'This checkpoint has no saved validation-only conformal state. '
                'Do not infer uncertainty from the score alone.'
            ),
        }
    try:
        prediction_sets = conformal_prediction_sets([probability], conformal)
    except (KeyError, TypeError, ValueError) as error:
        return {
            'status': 'not_available_invalid_checkpoint_state',
            'method': conformal.get('method'),
            'abstain': None,
            'prediction_set': None,
            'note': f'Checkpoint conformal state is incomplete: {error}',
        }
    return {
        'status': 'available_internal_validation_only',
        'method': conformal.get('method'),
        'alpha': conformal.get('alpha'),
        'fitted_on': conformal.get('fitted_on'),
        'prediction_set': str(prediction_sets['prediction_set'][0]),
        'abstain': bool(prediction_sets['abstain'][0]),
        'no_interaction_p_value': float(prediction_sets['no_interaction_p_value'][0]),
        'interaction_p_value': float(prediction_sets['interaction_p_value'][0]),
        'note': conformal.get(
            'interpretation_warning',
            'This is internal validation uncertainty only, not clinical confidence.',
        ),
    }


def checkpoint_uncertainty_status() -> str:
    """Expose availability in health without representing it as a prediction."""
    return uncertainty_response(0.5)['status']


def structural_domain_response(smiles_a: str, smiles_b: str) -> dict:
    """Return a checkpoint-backed OOD flag without treating it as safety evidence."""
    if STRUCTURAL_DOMAIN is None:
        return {
            'status': 'not_available',
            'method': None,
            'outside_structural_domain': None,
            'note': (
                'This checkpoint has no saved training-structure reference set, so '
                'the API cannot assess structural out-of-domain status. '
                f'Reason: {STRUCTURAL_DOMAIN_ERROR}.'
            ),
        }
    try:
        drug_a = STRUCTURAL_DOMAIN.score_smiles(smiles_a)
        drug_b = STRUCTURAL_DOMAIN.score_smiles(smiles_b)
    except ValueError as error:
        return {
            'status': 'not_available_invalid_query',
            'method': STRUCTURAL_DOMAIN.method,
            'outside_structural_domain': None,
            'note': f'Could not assess the supplied structures: {error}',
        }
    pair_minimum = min(
        drug_a['nearest_train_tanimoto'], drug_b['nearest_train_tanimoto']
    )
    outside = bool(pair_minimum < STRUCTURAL_DOMAIN.minimum_similarity)
    return {
        'status': 'available_structure_similarity_diagnostic',
        'method': STRUCTURAL_DOMAIN.method,
        'minimum_tanimoto_similarity': STRUCTURAL_DOMAIN.minimum_similarity,
        'drug_a': drug_a,
        'drug_b': drug_b,
        'pair_minimum_nearest_train_tanimoto': pair_minimum,
        'outside_structural_domain': outside,
        'note': (
            'This is a nearest-training-drug structural similarity diagnostic only. '
            'It does not measure pair novelty, prove prediction reliability, or make '
            'an unreported pair safe.'
        ),
    }


def explanation_response() -> dict:
    """Describe whether this architecture has a compatible explanation path."""
    if getattr(model, 'architecture_version', None) != 'legacy_gat_v1':
        return {
            'available': False,
            'endpoint': None,
            'note': (
                'This non-legacy candidate has no validated API explanation method yet. '
                'Do not interpret an embedding attribution from the legacy method as an '
                'edge-aware or motif-aware pair-risk explanation.'
            ),
        }
    return {
        'available': True,
        'endpoint': '/explain (separate, slower endpoint)',
        'note': (
            'Available only as a legacy embedding attribution. It is not a validated '
            'pair-risk explanation.'
        ),
    }


def readiness_error() -> str | None:
    """Return a readiness failure when required toxicity-coverage data is unavailable."""
    if float(checkpoint.get('toxicity_loss_weight', 0.0) or 0.0) <= 0.0:
        return None
    if KNOWN_TOXICITY_SMILES:
        return None
    return TOXICITY_BRIDGE_ERROR or (
        'Toxicity bridge loaded without any usable canonical SMILES entries.'
    )


def seven_branch_bundle_status() -> dict | None:
    """Expose the validated bundle identity and per-branch coverage."""
    if SEVEN_BRANCH_BUNDLE_SHA256 is None:
        return None
    return {
        'sha256': SEVEN_BRANCH_BUNDLE_SHA256,
        'drug_records': SEVEN_BRANCH_BUNDLE_DRUG_COUNT,
        'dimensions': checkpoint.get('seven_branch_dimensions', {}),
        'drug_coverage': SEVEN_BRANCH_BUNDLE_COVERAGE,
    }


@app.post('/predict')
def predict_ddi(req: DDIRequest):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail='No trained DDI checkpoint is installed. Add the trusted checkpoint and matching feature bundle, then restart the backend.',
        )
    if not PREDICTION_SEMAPHORE.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail='The prediction service is busy. Please retry shortly.',
        )
    try:
        batch_a, batch_b = build_drug_batches(req)

        # Patient context is rejected at request validation because this model
        # has not been trained with linked patient, exposure, and outcome data.
        patient_context_note = (
            'Patient-specific fields are not accepted. The patient-conditioning '
            'module is not trained on linked patient-outcome data.'
        )

        memory_features = None
        auditable_evidence = None
        if NEIGHBOR_MEMORY is not None:
            mem_res = NEIGHBOR_MEMORY.score_pair_memory(req.smiles_a, req.smiles_b)
            memory_features = torch.tensor([[
                mem_res['neighbor_density'],
                mem_res['max_support'],
                mem_res['structural_confidence'],
            ]], dtype=torch.float)
            auditable_evidence = {
                'status': 'available',
                'method': 'tanimoto_knn_training_memory_v1',
                'neighbor_interaction_density': round(float(mem_res['neighbor_density']), 4),
                'max_supported_interaction': round(float(mem_res['max_support']), 4),
                'structural_confidence': round(float(mem_res['structural_confidence']), 4),
                'audit_trail': mem_res['audit_trail'],
            }
        else:
            auditable_evidence = {
                'status': 'not_available',
                'method': None,
                'note': 'This checkpoint does not carry an active training neighbor memory.',
            }

        with torch.inference_mode():
            if getattr(model, 'use_neighbor_memory', False):
                risk, tox_a, tox_b = model(batch_a, batch_b, patient=None, memory_features=memory_features)
            else:
                risk, tox_a, tox_b = model(batch_a, batch_b, patient=None)

        raw_risk_score = float(torch.sigmoid(risk))
        risk_score = float(apply_calibrator([raw_risk_score], CALIBRATION)[0])
        calibration_response = risk_calibration_response()
        explanation = explanation_response()
        uncertainty = uncertainty_response(risk_score)
        structural_domain = structural_domain_response(req.smiles_a, req.smiles_b)
        source_feature_coverage = source_feature_coverage_response(batch_a, batch_b)
        seven_branch_coverage = seven_branch_coverage_response(batch_a, batch_b)
        return {
            'disclaimer': 'Research prototype output. Not clinical advice. Not FDA/regulatory reviewed.',
            'model_architecture': checkpoint.get('architecture_version', 'legacy_gat_v1'),
            'model_checkpoint_sha256': CHECKPOINT_SHA256,
            'stored_validation_evidence': stored_validation_evidence(checkpoint),
            'interaction_risk_estimate': risk_score,
            'interaction_risk_score_raw': raw_risk_score,
            'interaction_risk_note': (
                'This is a research-model estimate, not a clinical probability. '
                + calibration_response['note']
            ),
            'interaction_label_note': (
                'The research task distinguishes reported TWOSIDES pairs from sampled '
                'unreported pairs. An unreported pair is not evidence that the pair is safe.'
            ),
            'score_calibration': calibration_response,
            'prediction_uncertainty': uncertainty,
            'structural_applicability_domain': structural_domain,
            'source_feature_coverage': source_feature_coverage,
            'seven_branch_input_coverage': seven_branch_coverage,
            'auditable_evidence': auditable_evidence,
            'interaction_predicted': risk_score >= DECISION_THRESHOLD,
            'decision_threshold_used': DECISION_THRESHOLD,
            'patient_context_applied': False,
            'patient_context_note': patient_context_note,
            'drug_a_toxicity': (
                None if checkpoint.get('architecture_version') == MODEL_ARCHITECTURE_SEVEN_BRANCH
                else toxicity_response(req.smiles_a, float(torch.sigmoid(tox_a)))
            ),
            'drug_b_toxicity': (
                None if checkpoint.get('architecture_version') == MODEL_ARCHITECTURE_SEVEN_BRANCH
                else toxicity_response(req.smiles_b, float(torch.sigmoid(tox_b)))
            ),
            'drug_toxicity_note': (
                'The seven-branch model predicts binary DDI association only; '
                'it does not output a drug-toxicity prediction.'
                if checkpoint.get('architecture_version') == MODEL_ARCHITECTURE_SEVEN_BRANCH
                else None
            ),
            'explanation_available_at': explanation['endpoint'],
            'explanation_note': explanation['note'],
        }
    finally:
        PREDICTION_SEMAPHORE.release()


@app.post('/explain')
def explain_ddi(req: DDIRequest):
    if model is None:
        raise HTTPException(status_code=503, detail='No trained DDI checkpoint is installed.')
    """Run the expensive embedding explanation with bounded local concurrency."""
    if not explanation_response()['available']:
        raise HTTPException(
            status_code=501,
            detail=(
                'The edge-aware candidate has no validated API explanation method yet. '
                'This endpoint remains available only for the legacy GAT architecture.'
            ),
        )
    # An explanation performs several model forwards. It must consume the same
    # finite inference capacity as a prediction, otherwise one explanation can
    # still exhaust memory while the prediction semaphore is full.
    if not PREDICTION_SEMAPHORE.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail='The inference service is busy. Please retry shortly.',
        )
    if not EXPLANATION_SEMAPHORE.acquire(blocking=False):
        PREDICTION_SEMAPHORE.release()
        raise HTTPException(
            status_code=429,
            detail='An explanation is already running. Please retry shortly.',
        )

    try:
        batch_a, batch_b = build_drug_batches(req)
        explanation = full_explanation_pipeline(
            model, batch_a, req.smiles_a, batch_b, req.smiles_b
        )
    finally:
        EXPLANATION_SEMAPHORE.release()
        PREDICTION_SEMAPHORE.release()

    return {
        'disclaimer': (
            'Explanation identifies atoms that influenced each molecule embedding and '
            'cross-checks them against a small functional-group heuristic. It is not a '
            'validated literature review or a pair-risk explanation.'
        ),
        'explanation': explanation,
    }


@app.post('/api/audit/dossier')
@app.post('/audit/dossier')
def audit_dossier(req: DDIRequest):
    """Generate complete biophysical, pharmacokinetic, and calibrated audit dossier."""
    from evaluation.clinical_audit_report import generate_clinical_audit_report
    try:
        report = generate_clinical_audit_report(
            drug_a_smiles=req.smiles_a,
            drug_b_smiles=req.smiles_b,
            model=model,
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get('/health')
def health():
    bridge_error = readiness_error()
    return {
        'status': 'ok',
        'ready': model is not None and bridge_error is None,
        'model_loaded': model is not None,
        'model_load_error': CHECKPOINT_LOAD_ERROR,
        'model_type': (
            None if model is None else
            ('GNN' if not checkpoint.get('use_chemberta', False) else 'ChemBERTa')
        ),
        'model_architecture': checkpoint.get('architecture_version'),
        'model_feature_schema': MODEL_FEATURE_SCHEMA if model is not None else None,
        'model_requires_motif_features': MODEL_REQUIRES_MOTIF_FEATURES,
        'score_calibration_status': risk_calibration_response()['status'],
        'conformal_uncertainty_status': checkpoint_uncertainty_status(),
        'structural_applicability_domain_status': (
            'available_structure_similarity_diagnostic'
            if STRUCTURAL_DOMAIN is not None else 'not_available'
        ),
        'structural_applicability_domain_error': STRUCTURAL_DOMAIN_ERROR,
        'explanation_status': 'available' if explanation_response()['available'] else 'not_available',
        'stored_validation_evidence': stored_validation_evidence(checkpoint),
        'auxiliary_toxicity_head_status': auxiliary_toxicity_head_status(checkpoint),
        'model_checkpoint_sha256': CHECKPOINT_SHA256,
        'seven_branch_feature_bundle': seven_branch_bundle_status(),
        'toxicity_bridge_loaded': len(KNOWN_TOXICITY_SMILES) > 0,
        'toxicity_bridge_size': len(KNOWN_TOXICITY_SMILES),
        'toxicity_bridge_error': bridge_error,
        'toxicity_bridge_source_rows': (
            TOXICITY_BRIDGE_SUMMARY['source_rows']
            if TOXICITY_BRIDGE_SUMMARY is not None else None
        ),
        'toxicity_bridge_conflicting_structures_excluded': (
            TOXICITY_BRIDGE_SUMMARY['excluded_conflicting_structures']
            if TOXICITY_BRIDGE_SUMMARY is not None else None
        ),
        'decision_threshold': DECISION_THRESHOLD,
        'patient_context_enabled': False,
        'max_smiles_length': MAX_SMILES_LENGTH,
        'max_molecule_atoms': MAX_MOLECULE_ATOMS,
        'max_molecule_bonds': MAX_MOLECULE_BONDS,
        'max_request_bytes': MAX_REQUEST_BYTES,
        'max_concurrent_predictions': MAX_CONCURRENT_PREDICTIONS,
        'max_concurrent_explanations': MAX_CONCURRENT_EXPLANATIONS,
        'api_documentation_enabled': ENABLE_API_DOCUMENTATION,
        'deployment_mode': DEPLOYMENT_MODE,
        'api_key_protection_enabled': API_KEY is not None,
        'per_client_rate_limit_per_minute': RATE_LIMIT_PER_MINUTE,
    }


@app.get('/ready')
def ready():
    """Readiness endpoint used by deployment health checks."""
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=CHECKPOINT_LOAD_ERROR or 'No trained DDI checkpoint is installed.',
        )
    bridge_error = readiness_error()
    if bridge_error is not None:
        raise HTTPException(status_code=503, detail=bridge_error)
    return {
        'status': 'ready',
        'model_checkpoint_sha256': CHECKPOINT_SHA256,
        'seven_branch_feature_bundle': seven_branch_bundle_status(),
        'toxicity_bridge_size': len(KNOWN_TOXICITY_SMILES),
    }


def _require_auth_store() -> AuthStore:
    if not AUTH_ENABLED or AUTH_STORE is None:
        raise HTTPException(status_code=503, detail='Account authentication is disabled.')
    return AUTH_STORE


def _user_payload(user: dict) -> dict:
    role = user['role']
    return {
        **user,
        'workspace_url': '/' + ROLE_WORKSPACES.get(role, 'research.html'),
    }


def _issue_session(response: Response, user: dict) -> dict:
    store = _require_auth_store()
    token = store.issue_session(int(user['id']))
    response.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite='lax',
        path='/',
    )
    return _user_payload(user)


@app.get('/auth/session')
def auth_session(request: Request):
    if not AUTH_ENABLED or AUTH_STORE is None:
        return {'authentication_enabled': False, 'setup_required': False, 'user': None}
    user = session_user_from_request(request)
    return {
        'authentication_enabled': True,
        'setup_required': not AUTH_STORE.has_users(),
        'user': _user_payload(user) if user else None,
    }


@app.post('/auth/bootstrap')
def bootstrap_admin(req: BootstrapRequest, response: Response):
    store = _require_auth_store()
    if store.has_users():
        raise HTTPException(status_code=409, detail='Administrator setup is already complete.')
    if not AUTH_BOOTSTRAP_TOKEN:
        raise HTTPException(
            status_code=503,
            detail='Administrator bootstrap is not configured on this deployment.',
        )
    if not hmac.compare_digest(req.bootstrap_token, AUTH_BOOTSTRAP_TOKEN):
        raise HTTPException(status_code=401, detail='The bootstrap token is invalid.')
    try:
        user = store.create_user(req.email, req.password, 'admin')
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        if 'UNIQUE constraint failed' in str(error):
            raise HTTPException(status_code=409, detail='That account already exists.') from error
        raise
    return {'user': _issue_session(response, user)}


@app.post('/auth/login')
def login(req: LoginRequest, response: Response):
    store = _require_auth_store()
    user = store.authenticate(req.email, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail='Email or password is incorrect.')
    return {'user': _issue_session(response, user)}


@app.post('/auth/logout')
def logout(request: Request, response: Response):
    if AUTH_ENABLED and AUTH_STORE is not None:
        AUTH_STORE.revoke_session(request.cookies.get(AUTH_COOKIE_NAME))
    response.delete_cookie(
        AUTH_COOKIE_NAME, path='/', secure=AUTH_COOKIE_SECURE,
        httponly=True, samesite='lax',
    )
    return {'status': 'signed_out'}


@app.get('/auth/users')
def list_accounts():
    store = _require_auth_store()
    return {'users': store.list_users()}


@app.post('/auth/users', status_code=201)
def create_account(req: AccountCreateRequest):
    store = _require_auth_store()
    if req.role not in VALID_ACCOUNT_ROLES:
        raise HTTPException(status_code=422, detail='Choose a supported workspace role.')
    try:
        user = store.create_user(req.email, req.password, req.role)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        if 'UNIQUE constraint failed' in str(error):
            raise HTTPException(status_code=409, detail='That account already exists.') from error
        raise
    return {'user': _user_payload(user)}


@app.patch('/auth/users/{user_id}')
def set_account_status(user_id: int, req: AccountStatusRequest, request: Request):
    store = _require_auth_store()
    current_user = session_user_from_request(request)
    if current_user and int(current_user['id']) == user_id and not req.is_active:
        raise HTTPException(status_code=409, detail='Sign in as another administrator before deactivating this account.')
    try:
        store.set_user_active(user_id, req.is_active)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {'user_id': user_id, 'is_active': req.is_active}


@app.put('/auth/users/{user_id}/password')
def reset_account_password(user_id: int, req: AccountPasswordResetRequest, request: Request):
    store = _require_auth_store()
    current_user = session_user_from_request(request)
    if current_user and int(current_user['id']) == user_id:
        raise HTTPException(
            status_code=409,
            detail='Use a separate administrator account to reset your own password.',
        )
    try:
        store.reset_user_password(user_id, req.password)
    except ValueError as error:
        status_code = 404 if str(error) == 'User account was not found.' else 422
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    return {'user_id': user_id, 'status': 'password_reset'}


@app.get('/workspaces')
def list_workspaces():
    details = {
        'research': ('Research & Development', 'researchers and pharmacologists'),
        'prescriber_review': ('Prescriber Review', 'licensed prescribers'),
        'medication_safety': ('Medication Safety Review', 'pharmacists and medication-safety teams'),
        'governance': ('Evidence & Model Governance', 'quality and model-governance reviewers'),
        'portfolio_screening': ('Portfolio Screening', 'pharmaceutical R&D teams'),
        'public_information': ('Medication Information', 'people seeking general medication information'),
    }
    return {
        'workspaces': [
            {
                'id': role,
                'name': values[0],
                'audience': values[1],
                'unavailable_message': 'This workspace does not provide patient-specific medical advice.',
            }
            for role, values in details.items()
        ]
    }


@app.post('/drugs/lookup')
def lookup_drug_name(req: DrugLookupRequest):
    """Resolve a typed name to selectable PubChem structure candidates.

    The lookup is for identity assistance only: every candidate is returned for
    explicit user selection, and the prediction endpoint still receives the
    selected SMILES. Dynamic search results never alter the frozen model bundle.
    """
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail='Enter a drug or compound name.')
    cids_url = (
        'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/'
        f'{quote(query, safe="")}/cids/JSON'
    )
    try:
        cid_response = requests.get(
            cids_url, timeout=(3.05, 12), headers={'User-Agent': 'AuditDDI-local/1.0'}
        )
        if cid_response.status_code == 404:
            raise HTTPException(status_code=404, detail='PubChem found no compound for that name.')
        cid_response.raise_for_status()
        cid_data = cid_response.json()
        cids = cid_data.get('IdentifierList', {}).get('CID', [])
        if not cids:
            raise HTTPException(status_code=404, detail='PubChem returned no compound candidates.')
        selected_cids = [int(cid) for cid in cids[:8]]
        properties_url = (
            'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/'
            f'{",".join(map(str, selected_cids))}/property/Title,SMILES,ConnectivitySMILES,InChIKey/JSON'
        )
        properties_response = requests.get(
            properties_url, timeout=(3.05, 12), headers={'User-Agent': 'AuditDDI-local/1.0'}
        )
        properties_response.raise_for_status()
        properties = properties_response.json().get('PropertyTable', {}).get('Properties', [])
    except HTTPException:
        raise
    except (requests.RequestException, ValueError) as error:
        LOGGER.warning('PubChem lookup failed: %s', type(error).__name__)
        raise HTTPException(
            status_code=502,
            detail='PubChem lookup is temporarily unavailable. Try again or paste SMILES directly.',
        ) from error

    candidates = []
    for item in properties:
        smiles = item.get('SMILES') or item.get('ConnectivitySMILES')
        if not smiles:
            continue
        candidates.append({
            'cid': item.get('CID'),
            'title': item.get('Title') or f"PubChem CID {item.get('CID')}",
            'smiles': smiles,
            'inchikey': item.get('InChIKey'),
            'source_url': f"https://pubchem.ncbi.nlm.nih.gov/compound/{item.get('CID')}",
            'image_url': f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{item.get('CID')}/PNG",
        })
    if not candidates:
        raise HTTPException(status_code=502, detail='PubChem returned no usable structure strings.')
    chembl_url = 'https://www.ebi.ac.uk/chembl/api/data/molecule/search.json'
    chembl_status = 'unavailable'
    chembl_candidates = []
    try:
        chembl_response = requests.get(
            chembl_url,
            params={'q': query, 'limit': 8},
            timeout=(3.05, 12),
            headers={'User-Agent': 'AuditDDI-local/1.0', 'Accept': 'application/json'},
        )
        chembl_response.raise_for_status()
        chembl_data = chembl_response.json()
        chembl_candidates = [
            {
                'chembl_id': item.get('molecule_chembl_id'),
                'name': item.get('pref_name') or item.get('molecule_chembl_id'),
                'max_phase': item.get('max_phase'),
                'source_url': f"https://www.ebi.ac.uk/chembl/explore/compound/{item.get('molecule_chembl_id')}",
            }
            for item in chembl_data.get('molecules', [])
            if item.get('molecule_chembl_id')
        ]
        chembl_status = 'available' if chembl_candidates else 'no_name_match'
    except (requests.RequestException, ValueError):
        LOGGER.info('ChEMBL name lookup unavailable for this request.')
    return {
        'query': query,
        'source': 'PubChem PUG REST',
        'source_api': cids_url,
        'selection_required': len(candidates) > 1,
        'candidate_count_returned': len(candidates),
        'candidates': candidates,
        'chembl': {
            'status': chembl_status,
            'source': 'ChEMBL Web Services',
            'source_api': chembl_url,
            'candidates': chembl_candidates,
            'note': 'Name-search matches are independent records; they are not automatically mapped to the selected PubChem structure or used as pair-specific causal evidence.',
        },
        'note': 'Confirm the intended ingredient and stereochemistry before using a candidate. Name matches do not verify a medication product or clinical identity.',
    }


@app.get('/drugs/conformer/{cid}')
def get_pubchem_3d_conformer(cid: int):
    """Fetch a PubChem 3D conformer SDF for a selected PubChem CID."""
    if cid <= 0:
        raise HTTPException(status_code=422, detail='PubChem CID must be a positive integer.')
    url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/record/SDF'
    try:
        response = requests.get(
            url, params={'record_type': '3d'}, timeout=(3.05, 18),
            headers={'User-Agent': 'AuditDDI-local/1.0'},
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail='PubChem has no 3D conformer for this compound.')
        response.raise_for_status()
        sdf = response.text
        if not sdf.strip() or 'M  END' not in sdf:
            raise HTTPException(status_code=502, detail='PubChem returned no usable 3D structure data.')
    except HTTPException:
        raise
    except requests.RequestException as error:
        LOGGER.warning('PubChem 3D conformer fetch failed: %s', type(error).__name__)
        raise HTTPException(status_code=502, detail='PubChem 3D structure service is temporarily unavailable.') from error
    return {
        'cid': cid,
        'sdf': sdf,
        'source': 'PubChem PUG REST 3D conformer',
        'source_url': url + '?record_type=3d',
        'note': 'This is a standalone compound conformer, not an experimental drug-pair complex or binding pose.',
    }


@app.post('/drugs/structure')
def generate_3d_conformer(req: DrugStructureRequest):
    """Compute a reproducible single-molecule conformer for pasted SMILES."""
    from rdkit.Chem import AllChem

    molecule = Chem.MolFromSmiles(req.smiles)
    if molecule is None:
        raise HTTPException(status_code=422, detail='The submitted SMILES is not a valid molecular structure.')
    molecule = Chem.AddHs(molecule)
    parameters = AllChem.ETKDGv3()
    parameters.randomSeed = 0xA0D17
    if AllChem.EmbedMolecule(molecule, parameters) != 0:
        raise HTTPException(status_code=422, detail='A 3D conformer could not be generated for this structure.')
    force_field = 'MMFF94' if AllChem.MMFFHasAllMoleculeParams(molecule) else 'UFF'
    if force_field == 'MMFF94':
        AllChem.MMFFOptimizeMolecule(molecule, mmffVariant='MMFF94', maxIters=250)
    else:
        AllChem.UFFOptimizeMolecule(molecule, maxIters=250)
    return {
        'sdf': Chem.MolToMolBlock(molecule) + '\n$$$$\n',
        'source': f'RDKit ETKDGv3 conformer optimized with {force_field}',
        'source_url': 'https://www.rdkit.org/docs/RDKit_Book.html#conformer-generation',
        'note': 'Computed isolated-drug geometry for visualization; not an experimental structure, drug-pair complex, docking pose, or interaction mechanism.',
    }


def _openfda_label_excerpt(name: str) -> dict:
    escaped = name.replace('\\', '\\\\').replace('"', '\\"')
    search = f'(openfda.generic_name:"{escaped}" OR openfda.brand_name:"{escaped}")'
    url = 'https://api.fda.gov/drug/label.json'
    try:
        response = requests.get(
            url, params={'search': search, 'limit': 1}, timeout=(3.05, 12),
            headers={'User-Agent': 'AuditDDI-local/1.0'},
        )
        if response.status_code == 404:
            return {'query': name, 'status': 'no_label_match', 'source_url': response.url, 'sections': {}}
        response.raise_for_status()
        results = response.json().get('results', [])
    except (requests.RequestException, ValueError) as error:
        LOGGER.info('openFDA label lookup failed for a query (%s).', type(error).__name__)
        return {'query': name, 'status': 'unavailable', 'source_url': url, 'sections': {}}
    if not results:
        return {'query': name, 'status': 'no_label_match', 'source_url': response.url, 'sections': {}}
    result = results[0]
    sections = {}
    for key, label in (
        ('drug_interactions', 'Drug interactions'),
        ('warnings', 'Warnings'),
        ('adverse_reactions', 'Adverse reactions'),
    ):
        values = result.get(key) or []
        text = ' '.join(str(value).strip() for value in values if value)
        if text:
            sections[label] = text[:2400]
    openfda = result.get('openfda') or {}
    return {
        'query': name,
        'status': 'available',
        'effective_time': result.get('effective_time'),
        'brand_names': (openfda.get('brand_name') or [])[:4],
        'generic_names': (openfda.get('generic_name') or [])[:4],
        'manufacturer_names': (openfda.get('manufacturer_name') or [])[:3],
        'source_url': response.url,
        'sections': sections,
    }


@app.post('/evidence/labels')
def get_live_label_evidence(req: PairLabelEvidenceRequest):
    """Return source excerpts for each drug; never infer pair causality from labels."""
    return {
        'source': 'openFDA Drug Label API',
        'drug_a': _openfda_label_excerpt(req.drug_a_name),
        'drug_b': _openfda_label_excerpt(req.drug_b_name),
        'interpretation': (
            'These are label excerpts for individual products. They may describe drug classes or '
            'general risks and do not prove that this specific pair caused an event or identify a '
            'causal molecular substructure.'
        ),
    }


@app.get('/compounds')
def list_compounds():
    return {'compounds': COMPOUND_REGISTRY.list(limit=100)}


@app.post('/compounds', status_code=201)
def register_compound(req: CompoundCreateRequest):
    molecule = Chem.MolFromSmiles(req.smiles)
    if molecule is None:
        raise HTTPException(status_code=422, detail='The submitted SMILES is not a valid molecular structure.')
    canonical_smiles = Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
    compound = COMPOUND_REGISTRY.add(
        req.name,
        req.external_id,
        canonical_smiles,
        req.evidence_notes,
    )
    compound.pop('evidence_notes', None)
    return {'compound': compound}


@app.post('/polypharmacy/analyze')
def analyze_regimen(req: PolypharmacyRequest):
    drugs = []
    for drug in req.drugs:
        molecule = Chem.MolFromSmiles(drug.smiles)
        if molecule is None:
            raise HTTPException(status_code=422, detail=f'{drug.name}: invalid molecular structure.')
        drugs.append({
            'name': drug.name,
            'smiles': Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True),
        })
    try:
        regimen = analyze_polypharmacy_regimen(drugs)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail='The regimen could not be analyzed.') from error
    return {
        'disclaimer': 'Research prototype output. Not clinical advice or a prescribing recommendation.',
        'regimen': regimen,
    }
