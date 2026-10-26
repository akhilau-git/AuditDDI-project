#!/usr/bin/env python3
"""Build restartable per-drug ligand-bound pocket features from verified RCSB matches.

Input is the full-panel report produced by the exact stereochemical ligand
audit.  For each verified CCD component, this script queries RCSB Search API,
downloads and caches a small candidate set of mmCIF structures, confirms the
ligand coordinates and protein contacts, then keeps the best-quality usable
complex for that drug.  Drugs without a usable exact-match complex are omitted
from the feature CSV; the seven-branch bundle builder then marks their PDB
branch unavailable with its explicit row mask.

The output is a compact pocket-contact descriptor, not a claim to predict
binding affinity or mechanism.  No DDI pair labels or outcomes are read.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from Bio.PDB import MMCIFParser
from Bio.PDB.Polypeptide import is_aa
from scipy.spatial.distance import cdist

SEARCH_URL = 'https://search.rcsb.org/rcsbsearch/v2/query'
CIF_URL = 'https://files.rcsb.org/download/{pdb_id}.cif.gz'
UA = {'User-Agent': 'AuditDDI-seven-branch-feature-builder/1.0 (research)'}
AA_TYPES = (
    'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'GLY', 'HIS', 'ILE',
    'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER', 'THR', 'TRP', 'TYR', 'VAL',
)
ATOM_TYPES = ('C', 'N', 'O', 'S', 'P', 'OTHER')
MAX_HITS_PER_COMPONENT = 10
MAX_COMPONENTS_PER_DRUG = 8


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def components(value: Any) -> list[str]:
    if pd.isna(value):
        return []
    vals = re.split(r'[,;|\s]+', str(value).strip().upper())
    return list(dict.fromkeys(v for v in vals if re.fullmatch(r'[A-Z0-9]{1,5}', v)))


def request_json(session: requests.Session, url: str, *, method: str = 'GET',
                 payload: dict[str, Any] | None = None, attempts: int = 5) -> Any:
    last = 'no response'
    for attempt in range(attempts):
        try:
            if method == 'POST':
                response = session.post(url, json=payload, timeout=(20, 120))
            else:
                response = session.get(url, timeout=(20, 120))
            if response.status_code == 204:
                return {'_empty_result': True}
            if response.status_code in (429, 500, 502, 503, 504):
                last = f'HTTP {response.status_code}: {response.text[:240]}'
                time.sleep(min(2 ** attempt, 20))
                continue
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last = f'{type(exc).__name__}: {exc}'
            time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(last)


def search_component(session: requests.Session, comp_id: str, max_hits: int) -> tuple[str, list[str], str | None]:
    query = {
        'query': {'type': 'terminal', 'service': 'text_chem', 'parameters': {
            'attribute': 'rcsb_chem_comp_container_identifiers.comp_id',
            'operator': 'exact_match', 'value': comp_id,
        }},
        'return_type': 'entry',
            'request_options': {'paginate': {'start': 0, 'rows': max_hits}},
    }
    try:
        result = request_json(session, SEARCH_URL, method='POST', payload=query)
        if result.get('_empty_result'):
            return comp_id, [], None
        hits = [str(x.get('identifier', '')).upper() for x in result.get('result_set', [])]
        return comp_id, list(dict.fromkeys(x for x in hits if re.fullmatch(r'[0-9A-Z]{4}', x))), None
    except Exception as exc:
        return comp_id, [], f'{type(exc).__name__}: {exc}'


def fetch_cif(session: requests.Session, pdb_id: str, cache: Path) -> tuple[Path | None, str | None]:
    path = cache / f'{pdb_id.lower()}.cif'
    if path.is_file() and path.stat().st_size > 0:
        return path, None
    try:
        response = session.get(CIF_URL.format(pdb_id=pdb_id.upper()), timeout=(20, 180))
        response.raise_for_status()
        content = gzip.decompress(response.content) if response.content[:2] == b'\x1f\x8b' else response.content
        if not content.strip():
            raise ValueError('empty mmCIF response')
        tmp = path.with_suffix('.cif.tmp')
        tmp.write_bytes(content)
        tmp.replace(path)
        return path, None
    except Exception as exc:
        return None, f'{type(exc).__name__}: {exc}'


def atom_element(atom: Any) -> str:
    el = (atom.element or '').strip().upper()
    if not el:
        el = re.sub(r'[^A-Z]', '', atom.get_name().upper())[:1]
    return el if el in ATOM_TYPES[:-1] else 'OTHER'


def pocket_features(cif_path: Path, pdb_id: str, comp_id: str) -> tuple[dict[str, float] | None, dict[str, Any]]:
    # Keep author residue numbering so non-polymer ligand residues are parsed.
    # With auth_residues=False Bio.PDB uses label_seq_id and silently omits
    # non-polymers (including the bound small-molecule ligand) that have no
    # label_seq_id, causing valid ligand-bound structures to look empty.
    parser = MMCIFParser(QUIET=True, auth_chains=False, auth_residues=True)
    structure = parser.get_structure(pdb_id, str(cif_path))
    ligand_atoms = []
    protein_atoms = []
    protein_residues: dict[tuple[str, str, str, str], Any] = {}
    # Use the first deposited model consistently for NMR/multi-model entries;
    # concatenating conformers would inflate atom-contact counts.
    for model in list(structure)[:1]:
        for chain in model:
            for residue in chain:
                hetflag, seqnum, icode = residue.id
                resname = residue.resname.strip().upper()
                atoms = [a for a in residue.get_atoms() if atom_element(a) != 'OTHER' or
                         (a.element or '').strip()]
                if hetflag.strip() and resname == comp_id:
                    ligand_atoms.extend(a for a in atoms if atom_element(a) != 'OTHER' or
                                        (a.element or '').strip())
                elif is_aa(residue, standard=False):
                    key = (str(model.id), str(chain.id), f'{seqnum}{icode}'.strip(), resname)
                    for atom in atoms:
                        element = atom_element(atom)
                        if element != 'OTHER':
                            protein_atoms.append((atom, residue, key, element))
                            protein_residues[key] = residue
    ligand_atoms = [a for a in ligand_atoms if atom_element(a) != 'OTHER']
    if not ligand_atoms or not protein_atoms:
        return None, {'pdb_id': pdb_id, 'component_id': comp_id,
                      'ligand_atoms': len(ligand_atoms), 'protein_atoms': len(protein_atoms),
                      'reason': 'missing ligand coordinates or polymer protein atoms'}

    lig_xyz = np.asarray([a.coord for a in ligand_atoms], dtype=np.float64)
    prot_xyz = np.asarray([x[0].coord for x in protein_atoms], dtype=np.float64)
    dist = cdist(lig_xyz, prot_xyz)
    if not np.isfinite(dist).all():
        return None, {'pdb_id': pdb_id, 'component_id': comp_id, 'reason': 'nonfinite coordinates'}
    nearest = float(dist.min())
    if nearest > 4.5:
        return None, {'pdb_id': pdb_id, 'component_id': comp_id, 'nearest_protein_distance_A': nearest,
                      'reason': 'no protein contact within 4.5 A'}

    feature: dict[str, float] = {}
    for cutoff in (4.0, 6.0):
        residues = {
            key for j, (_, _, key, _) in enumerate(protein_atoms)
            if np.any(dist[:, j] <= cutoff)
        }
        for aa in AA_TYPES:
            feature[f'residue_{aa.lower()}_within_{cutoff:g}A'] = float(
                sum(1 for key in residues if key[3] == aa)
            )
    atom_to_idx = {name: i for i, name in enumerate(ATOM_TYPES)}
    for la in ATOM_TYPES:
        for pa in ATOM_TYPES:
            mask = (dist <= 4.5)
            lsel = np.asarray([atom_to_idx[atom_element(a)] == atom_to_idx[la] for a in ligand_atoms])
            psel = np.asarray([x[3] == pa for x in protein_atoms])
            feature[f'atom_contacts_{la.lower()}_{pa.lower()}_4_5A'] = float(
                np.count_nonzero(mask & lsel[:, None] & psel[None, :]) / max(len(ligand_atoms), 1)
            )
    for cutoff in (3.5, 4.0, 4.5, 6.0):
        feature[f'atom_pair_contacts_within_{cutoff:g}A_per_ligand_atom'] = float(
            np.count_nonzero(dist <= cutoff) / max(len(ligand_atoms), 1)
        )
    close_res = set()
    for j, (_, _, key, _) in enumerate(protein_atoms):
        if np.any(dist[:, j] <= 4.5):
            close_res.add(key)
    feature['ligand_heavy_atom_count'] = float(len(ligand_atoms))
    feature['protein_residues_within_4_5A'] = float(len(close_res))
    feature['nearest_protein_distance_A'] = nearest
    audit = {'pdb_id': pdb_id, 'component_id': comp_id, 'ligand_heavy_atom_count': len(ligand_atoms),
             'protein_residue_count': len(protein_residues), 'protein_residues_within_4_5A': len(close_res),
             'nearest_protein_distance_A': nearest, 'pocket_contact_confirmed': True}
    return feature, audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verified-matches', type=Path, required=True,
                        help='rcsb_full_panel_verified_after_retry.csv or equivalent exact-match report')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--max-hits-per-component', type=int, default=MAX_HITS_PER_COMPONENT)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--resume', action='store_true', help='Reuse component search and CIF caches')
    args = parser.parse_args()
    if not args.verified_matches.is_file():
        raise FileNotFoundError(args.verified_matches)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache = args.output_dir / 'pdb_cache'
    cache.mkdir(parents=True, exist_ok=True)
    search_cache = cache / 'component_search_cache.json'
    identity = pd.read_csv(args.verified_matches, low_memory=False)
    if not {'drug_idx', 'canonical_smiles'}.issubset(identity.columns):
        raise ValueError(f'Expected drug_idx and canonical_smiles columns; found {identity.columns.tolist()}')
    comp_col = next((c for c in ('exact_component_ids', 'exact_component_id', 'component_ids')
                     if c in identity.columns), None)
    if comp_col is None:
        raise ValueError(f'No exact component ID column found in {args.verified_matches}')
    identity['drug_idx'] = identity['drug_idx'].astype(str).str.strip()
    identity['canonical_smiles'] = identity['canonical_smiles'].astype(str).str.strip()
    if identity['drug_idx'].duplicated().any():
        raise ValueError('Verified report has duplicate drug_idx rows; select one audited identity row per drug first.')
    if identity['canonical_smiles'].duplicated().any():
        raise ValueError('Verified report has duplicate canonical_smiles rows; resolve identity duplicates first.')
    if 'exact_ligand_entities' in identity:
        identity = identity[pd.to_numeric(identity['exact_ligand_entities'], errors='coerce').fillna(0) > 0]
    identity['components'] = identity[comp_col].map(components)
    identity = identity[identity['components'].map(bool)].copy()
    if identity.empty:
        raise ValueError('The verified report contains no exact-matched component IDs.')
    print(f'Exact-match drugs: {identity.drug_idx.nunique()} / {pd.read_csv(args.verified_matches).drug_idx.nunique()}')
    unique_components = sorted(set(c for row in identity['components'] for c in row))
    if identity['components'].map(len).max() > MAX_COMPONENTS_PER_DRUG:
        raise ValueError('A drug has an unexpected number of component IDs; inspect the report delimiter.')

    cached: dict[str, list[str]] = {}
    if args.resume and search_cache.is_file():
        try:
            cached = json.loads(search_cache.read_text(encoding='utf-8'))
        except Exception:
            cached = {}
    missing = [c for c in unique_components if c not in cached]
    print(f'Unique verified components: {len(unique_components)}; cached searches: {len(unique_components)-len(missing)}')
    session = requests.Session()
    session.headers.update(UA)
    search_results: dict[str, list[str]] = {k: v for k, v in cached.items() if k in unique_components}
    search_errors: list[dict[str, str]] = []
    for comp_id, hits, error in map(lambda c: search_component(session, c, args.max_hits_per_component), missing):
        if error:
            search_errors.append({'component_id': comp_id, 'error': error})
        else:
            search_results[comp_id] = hits[:args.max_hits_per_component]
        search_cache.write_text(json.dumps(search_results, indent=2), encoding='utf-8')
        print(f'Searched CCD {comp_id}: {len(hits)} PDB entries' + (f' [ERROR: {error}]' if error else ''), flush=True)

    # Queue candidate structures and cache each mmCIF as soon as it arrives.
    component_to_entries = {c: search_results.get(c, [])[:args.max_hits_per_component] for c in unique_components}
    all_entries = sorted(set(e for vals in component_to_entries.values() for e in vals))
    print(f'Unique candidate PDB entries to inspect: {len(all_entries)}', flush=True)
    entry_cifs: dict[str, Path] = {}
    fetch_errors: list[dict[str, str]] = []
    def fetch_one(entry: str) -> tuple[str, Path | None, str | None]:
        local = requests.Session(); local.headers.update(UA)
        path, err = fetch_cif(local, entry, cache / 'cif')
        return entry, path, err
    (cache / 'cif').mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch_one, entry): entry for entry in all_entries}
        for i, future in enumerate(as_completed(futures), 1):
            entry, path, err = future.result()
            if path:
                entry_cifs[entry] = path
            elif err:
                fetch_errors.append({'pdb_id': entry, 'error': err})
            if i % 50 == 0 or i == len(futures):
                print(f'Downloaded/cached {i}/{len(futures)} candidate structures', flush=True)

    records: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    pocket_cache: dict[tuple[str, str], tuple[dict[str, float] | None, dict[str, Any], str, float]] = {}
    seen: set[str] = set()
    total = len(identity)
    for row_num, row in enumerate(identity.itertuples(index=False), 1):
        drug_idx = getattr(row, 'drug_idx')
        smiles = str(getattr(row, 'canonical_smiles')).strip()
        comps = getattr(row, 'components')
        candidates = [(c, entry) for c in comps for entry in component_to_entries.get(c, []) if entry in entry_cifs]
        valid: list[tuple[tuple[float, int, str], str, str, dict[str, float], dict[str, Any]]] = []
        for comp_id, entry in candidates:
            try:
                cache_key = (entry, comp_id)
                if cache_key not in pocket_cache:
                    feats0, audit0 = pocket_features(entry_cifs[entry], entry, comp_id)
                    text0 = entry_cifs[entry].read_text(encoding='utf-8', errors='ignore')
                    method0 = ' '.join(re.findall(r'(?m)^_exptl\.method\s+(.+)$', text0)[:1]).strip('"\' ')
                    # mmCIF uses '.' and '?' for unknown numeric values.  Do
                    # not treat the bare missing-value token '.' as a float.
                    resvals0 = re.findall(
                        r'(?m)^_refine\.ls_d_res_high\s+([0-9]+(?:\.[0-9]*)?)\s*$',
                        text0,
                    )
                    if not resvals0:
                        resvals0 = re.findall(
                            r'(?m)^_reflns\.d_resolution_high\s+([0-9]+(?:\.[0-9]*)?)\s*$',
                            text0,
                        )
                    resolution0 = float(resvals0[0]) if resvals0 else 99.0
                    pocket_cache[cache_key] = (feats0, audit0, method0, resolution0)
                feats, audit, method, resolution = pocket_cache[cache_key]
                if feats is None:
                    audit_rows.append({'drug_idx': drug_idx, 'canonical_smiles': smiles, **audit})
                    continue
                # Rank by X-ray before other methods; use crystallographic
                # resolution parsed from mmCIF when available, then stable ID.
                rank = (0.0 if 'X-RAY' in method.upper() else 1.0, resolution, entry)
                valid.append((rank, comp_id, entry, feats, {**audit, 'method': method, 'resolution_A': resolution}))
            except Exception as exc:
                audit_rows.append({'drug_idx': drug_idx, 'canonical_smiles': smiles, 'pdb_id': entry,
                                   'component_id': comp_id, 'reason': f'{type(exc).__name__}: {exc}'})
        if valid:
            _, comp_id, entry, feats, audit = min(valid, key=lambda x: x[0])
            if smiles in seen:
                raise ValueError(f'Duplicate canonical_smiles in verified report: {smiles}')
            seen.add(smiles)
            records.append({'canonical_smiles': smiles, **feats})
            audit_rows.append({'drug_idx': drug_idx, 'canonical_smiles': smiles, **audit, 'selected': True})
        else:
            audit_rows.append({'drug_idx': drug_idx, 'canonical_smiles': smiles,
                               'pocket_contact_confirmed': False, 'reason': 'no usable candidate structure'})
        if row_num % 25 == 0 or row_num == total:
            print(f'Validated PDB pockets: {row_num}/{total}; usable drugs: {len(records)}', flush=True)

    table = pd.DataFrame(records)
    if table.empty:
        raise RuntimeError('No valid ligand-bound pockets were produced; see the audit report.')
    feature_cols = [c for c in table.columns if c not in {'drug_idx', 'canonical_smiles'}]
    if table['canonical_smiles'].duplicated().any() or not np.isfinite(table[feature_cols].to_numpy(float)).all():
        raise ValueError('PDB feature table failed duplicate or finite-value validation.')
    out_csv = args.output_dir / 'pdb_structure.csv'
    audit_csv = args.output_dir / 'pdb_structure_audit.csv'
    errors_csv = args.output_dir / 'pdb_structure_errors.csv'
    table.to_csv(out_csv, index=False)
    pd.DataFrame(audit_rows).to_csv(audit_csv, index=False)
    pd.DataFrame(
        search_errors + fetch_errors,
        columns=['component_id', 'pdb_id', 'error'],
    ).to_csv(errors_csv, index=False)
    manifest = {
        'dataset': 'RCSB Protein Data Bank exact stereochemical ligand matches',
        'release': 'RCSB PDB search/data services queried at extraction time',
        'feature_definition': '20 amino-acid pocket residue counts at 4A and 6A; 36 ligand/protein atom-type contact counts at 4.5A normalized by ligand heavy atoms; contact totals at 3.5/4/4.5/6A; ligand/pocket geometry summary',
        'drug_identity_mapping': 'verified exact stereochemical SMILES-to-RCSB chemical component mapping from supplied report',
        'structure_to_drug_mapping': 'verified exact ligand component IDs; selected mmCIF entry must contain ligand coordinates and protein contacts <=4.5A',
        'selection_policy': 'among cached exact-component hits, prefer X-ray diffraction, then lower parsed resolution, then PDB ID; one entry per drug',
        'missingness_policy': 'drugs without usable exact-match protein-bound structure are omitted; downstream bundle stores zero plus explicit observed-row mask',
        'source_report': str(args.verified_matches),
        'source_report_sha256': sha256(args.verified_matches),
        'component_search_cache': str(search_cache),
        'structure_cache': str(cache / 'cif'),
        'candidate_entries_inspected': len(all_entries),
        'matched_drugs_in_report': int(identity['drug_idx'].nunique()),
        # The model-facing table is keyed by canonical SMILES only.  Drug IDs
        # are retained in the audit CSV, not copied into the numeric feature
        # matrix, so count the successfully selected records here.
        'drugs_with_usable_pocket_features': int(len(records)),
        'feature_dimension': len(feature_cols),
        'feature_columns': feature_cols,
        'output_csv': str(out_csv),
        'output_sha256': sha256(out_csv),
        'audit_csv': str(audit_csv),
        'search_or_download_errors_csv': str(errors_csv),
    }
    (args.output_dir / 'pdb_structure.manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Feature table: {out_csv}')
    print(f'Audit: {audit_csv}')
    print(f'Manifest: {args.output_dir / "pdb_structure.manifest.json"}')
    print(f'Usable structures: {len(records)}/{identity.drug_idx.nunique()} exact-match drugs')
    print(f'Feature columns: {len(feature_cols)}')


if __name__ == '__main__':
    main()
