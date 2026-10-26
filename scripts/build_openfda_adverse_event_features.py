"""Build a compact drug-level adverse-event table from openFDA label ZIPs.

The extractor streams ZIP members and attributes only unambiguous,
single-ingredient labels through the audited TWOSIDES/PubChem CID crosswalk.
It uses ``adverse_reactions`` text only; pairwise ``drug_interactions`` text
is intentionally never read. Output is suitable for the seven-branch feature
bundle builder and includes an audit manifest with source hashes and coverage.

Example (Colab):
    python scripts/build_openfda_adverse_event_features.py \
      --data-root /content/drive/MyDrive/Projects/auditddi \
      --output-dir /content/drive/MyDrive/Projects/auditddi/processed/seven_branch
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.evidence.openfda_labels import (
    attribute_label,
    build_name_map,
    iter_zip_records,
)


TOKEN_RE = re.compile(r"[a-z][a-z0-9'-]{2,}")
STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'were', 'was',
    'are', 'has', 'have', 'had', 'may', 'can', 'not', 'than', 'then',
    'into', 'during', 'after', 'before', 'among', 'following', 'including',
    'due', 'use', 'used', 'using', 'patient', 'patients', 'drug', 'drugs',
    'treatment', 'study', 'studies', 'clinical', 'trial', 'trials', 'data',
    'reported', 'report', 'reports', 'incidence', 'adverse', 'reaction',
    'reactions', 'event', 'events', 'placebo', 'percent', 'including',
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def as_text(value: Any) -> str:
    if value is None:
        return ''
    values = value if isinstance(value, list) else [value]
    return ' '.join(str(item) for item in values if item is not None)


def cid_key(value: Any) -> str | None:
    if pd.isna(value):
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if number <= 0 or not number.is_integer():
        return None
    return str(int(number))


def load_identity_map(data_root: Path) -> tuple[pd.DataFrame, dict[str, int], int]:
    audit = data_root / 'processed' / 'auditddi_v1'
    resolution_path = audit / 'twosides_drug_cid_resolution.csv'
    aliases_path = audit / 'twosides_pubchem_aliases.csv'
    if not resolution_path.is_file():
        raise FileNotFoundError(f'Audited CID resolution table not found: {resolution_path}')
    resolution = pd.read_csv(resolution_path, low_memory=False)
    cid_column = next(
        (column for column in ('cid', 'selected_pubchem_cid', 'pubchem_cid')
         if column in resolution.columns),
        None,
    )
    required = {'drug_idx', 'canonical_smiles'}
    if not required.issubset(resolution.columns) or cid_column is None:
        raise ValueError(
            f'{resolution_path} needs columns {sorted(required)} and a CID column '
            "named 'cid', 'selected_pubchem_cid', or 'pubchem_cid'; "
            f'found {list(resolution.columns)}'
        )
    resolution['drug_idx'] = pd.to_numeric(resolution['drug_idx'], errors='coerce')
    resolution = resolution.dropna(subset=['drug_idx', 'canonical_smiles']).copy()
    resolution['drug_idx'] = resolution['drug_idx'].astype(int)
    resolution['canonical_smiles'] = resolution['canonical_smiles'].astype(str).str.strip()
    resolution = resolution[resolution['canonical_smiles'].ne('')]
    resolution = resolution.drop_duplicates('drug_idx', keep='first')

    name_parts: list[pd.DataFrame] = []
    if 'names' in resolution:
        name_parts.append(
            resolution[['drug_idx', 'names']].rename(columns={'names': 'name'})
        )
    if aliases_path.is_file():
        header = pd.read_csv(aliases_path, nrows=0).columns.tolist()
        cid_col = next((c for c in ('cid', 'pubchem_cid', 'selected_pubchem_cid') if c in header), None)
        name_col = next((c for c in ('synonym', 'alias', 'name', 'title', 'drug_name') if c in header), None)
        if cid_col and name_col:
            aliases = pd.read_csv(aliases_path, usecols=[cid_col, name_col], low_memory=False)
            cid_to_idx = {
                key: int(idx)
                for cid, idx in zip(resolution[cid_column], resolution['drug_idx'])
                if (key := cid_key(cid)) is not None
            }
            aliases['drug_idx'] = aliases[cid_col].map(cid_key).map(cid_to_idx)
            aliases = aliases.dropna(subset=['drug_idx']).rename(columns={name_col: 'name'})
            aliases['drug_idx'] = aliases['drug_idx'].astype(int)
            name_parts.append(aliases[['drug_idx', 'name']])
    if not name_parts:
        raise ValueError('No drug names/aliases are available for label attribution.')
    names = pd.concat(name_parts, ignore_index=True).dropna(subset=['name']).drop_duplicates()
    name_map, ambiguous = build_name_map(names)
    return resolution, name_map, ambiguous


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--labels-dir', type=Path, default=None)
    parser.add_argument('--output-dir', type=Path, default=None)
    parser.add_argument('--top-features', type=int, default=256)
    parser.add_argument('--min-document-frequency', type=int, default=2)
    parser.add_argument('--max-chars-per-drug', type=int, default=250_000)
    args = parser.parse_args()
    if args.top_features < 1 or args.min_document_frequency < 1 or args.max_chars_per_drug < 1:
        parser.error('feature count, document frequency, and character limit must be positive')

    data_root = args.data_root
    labels_dir = args.labels_dir or data_root / 'openfda'
    output_dir = args.output_dir or data_root / 'processed' / 'seven_branch'
    output_dir.mkdir(parents=True, exist_ok=True)
    resolution, name_map, ambiguous_names = load_identity_map(data_root)
    idx_to_smiles = dict(zip(resolution['drug_idx'], resolution['canonical_smiles']))
    archives = sorted(labels_dir.rglob('*.zip'))
    if not archives:
        raise FileNotFoundError(f'No openFDA label ZIP files found under {labels_dir}')

    text_by_drug: dict[int, list[str]] = {}
    chars_by_drug: Counter[int] = Counter()
    records_seen = attributed = labels_with_adverse_text = 0
    for archive in archives:
        part_seen = part_attributed = 0
        for record in iter_zip_records(archive):
            records_seen += 1
            part_seen += 1
            drug_idx = attribute_label(record, name_map)
            if drug_idx is None or drug_idx not in idx_to_smiles:
                continue
            attributed += 1
            part_attributed += 1
            text = as_text(record.get('adverse_reactions'))
            if not text:
                continue
            labels_with_adverse_text += 1
            remaining = args.max_chars_per_drug - chars_by_drug[drug_idx]
            if remaining > 0:
                text_by_drug.setdefault(drug_idx, []).append(text[:remaining])
                chars_by_drug[drug_idx] += min(len(text), remaining)
        print(f'{archive.name}: {part_seen:,} labels scanned; {part_attributed:,} attributed')

    token_counts: dict[int, Counter[str]] = {}
    document_frequency: Counter[str] = Counter()
    for drug_idx, chunks in text_by_drug.items():
        tokens = [token for token in TOKEN_RE.findall(' '.join(chunks).lower()) if token not in STOPWORDS]
        counts = Counter(tokens)
        if counts:
            token_counts[drug_idx] = counts
            document_frequency.update(counts.keys())
    features = [
        token for token, count in document_frequency.most_common()
        if count >= args.min_document_frequency
    ][:args.top_features]
    if not features:
        raise RuntimeError(
            'No adverse-reaction terms passed the document-frequency threshold; '
            'inspect label attribution and lower --min-document-frequency only if justified.'
        )
    feature_index = {term: i for i, term in enumerate(features)}
    n_docs = max(1, len(token_counts))
    idf = {
        term: float(np.log((1 + n_docs) / (1 + document_frequency[term])) + 1)
        for term in features
    }

    output_rows: list[dict[str, Any]] = []
    for drug_idx, counts in sorted(token_counts.items()):
        tfidf = np.zeros(len(features), dtype=np.float32)
        for term, count in counts.items():
            column = feature_index.get(term)
            if column is not None:
                tfidf[column] = (1.0 + np.log(count)) * idf[term]
        norm = float(np.linalg.norm(tfidf))
        if norm > 0:
            tfidf /= norm
            row: dict[str, Any] = {'canonical_smiles': idx_to_smiles[drug_idx]}
            row.update({f'ae_tfidf_{i:04d}': float(value) for i, value in enumerate(tfidf)})
            output_rows.append(row)

    if not output_rows:
        raise RuntimeError('No drug received a non-empty adverse-event feature vector.')
    output_path = output_dir / 'adverse_event.csv'
    pd.DataFrame(output_rows).drop_duplicates('canonical_smiles').to_csv(output_path, index=False)
    resolution_hash = sha256(data_root / 'processed' / 'auditddi_v1' / 'twosides_drug_cid_resolution.csv')
    alias_path = data_root / 'processed' / 'auditddi_v1' / 'twosides_pubchem_aliases.csv'
    manifest = {
        'schema': 'auditddi_openfda_adverse_event_features_v1',
        'feature_definition': 'L2-normalized TF-IDF over adverse_reactions section tokens, one aggregated document per drug',
        'identity_mapping': 'unambiguous single-ingredient openFDA generic/substance names matched to audited PubChem CID aliases; canonical SMILES emitted',
        'pairwise_ddi_signals_excluded': True,
        'excluded_fields': ['drug_interactions', 'clinical_pharmacology', 'pharmacokinetics'],
        'source': 'openFDA bulk drug-label files',
        'labels_dir': str(labels_dir),
        'archives': [{'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha256(path)} for path in archives],
        'drug_identity_resolution_sha256': resolution_hash,
        'drug_aliases_sha256': sha256(alias_path) if alias_path.is_file() else None,
        'records_seen': records_seen,
        'single_ingredient_labels_attributed': attributed,
        'attributed_labels_with_adverse_reaction_text': labels_with_adverse_text,
        'drugs_in_twosides_identity_table': int(resolution['drug_idx'].nunique()),
        'drugs_with_observed_adverse_event_features': len(output_rows),
        'feature_count': len(features),
        'min_document_frequency': args.min_document_frequency,
        'max_chars_per_drug': args.max_chars_per_drug,
        'ambiguous_names_discarded': ambiguous_names,
        'feature_names': features,
        'output_csv': str(output_path),
        'output_sha256': sha256(output_path),
        'limitations': [
            'Label-derived adverse reactions are not incidence estimates or causal adverse-event rates.',
            'Coverage is limited to drugs with an unambiguous single-ingredient label match.',
            'Review source overlap and label dates before interpreting held-out metrics.',
        ],
    }
    manifest_path = output_dir / 'adverse_event.manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Feature table:', output_path)
    print('Manifest:', manifest_path)
    print(f"Coverage: {len(output_rows)}/{resolution['drug_idx'].nunique()} TWOSIDES-mapped drugs")
    print('Features:', len(features))


if __name__ == '__main__':
    main()
