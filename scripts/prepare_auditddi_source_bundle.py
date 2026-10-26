"""Prepare CID-linked, source-audited inputs for the seven-source workflow.

This script consumes the audits already created in Colab. It does not rescan
the 118-million-row PubChem synonym file, infer missing drug identities, or
turn unlisted pairs into negative labels.

Example (Colab):
    python scripts/prepare_auditddi_source_bundle.py \
      --data-root /content/drive/MyDrive/Projects/auditddi

Optional openFDA CYP feature extraction (streams all available label zips):
    python scripts/prepare_auditddi_source_bundle.py \
      --data-root /content/drive/MyDrive/Projects/auditddi --parse-openfda

The output is processed/auditddi_v2/. TWOSIDES is the supervised label
source; DDInter is emitted as a separately tagged positive-evidence source
and a negative-sampling exclusion list. PharmGKB and openFDA supply model
features, FAERS report counts are kept for audit only pending temporal review,
and ChEMBL supplies leakage-filtered encoder pretraining structures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CYP_ISOFORMS = ['1A2', '2B6', '2C8', '2C9', '2C19', '2D6', '2E1', '3A4']
CYP_COLUMNS = [f'cyp{isoform}_{role}' for isoform in CYP_ISOFORMS
               for role in ('substrate', 'inhibitor', 'inducer')]

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for import_root in (REPOSITORY_ROOT, REPOSITORY_ROOT / 'src'):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_required(path: Path, label: str) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f'Missing {label}: {path}')
    return pd.read_csv(path, low_memory=False)


def cid_key(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {'nan', 'none', 'null'}:
        return None
    try:
        number = float(text)
        if number <= 0 or not number.is_integer():
            return None
        return str(int(number))
    except (TypeError, ValueError):
        return None


def join_unique(values: pd.Series) -> str:
    """Keep distinct source annotations without pretending there is one value."""
    items = {
        str(value).strip()
        for value in values
        if pd.notna(value) and str(value).strip() not in {"", "nan", "None"}
    }
    return " ; ".join(sorted(items))


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {'true', '1', 'yes'}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--parse-openfda', action='store_true')
    args = parser.parse_args()

    root = args.data_root
    out = args.output or root / 'processed' / 'auditddi_v2'
    out.mkdir(parents=True, exist_ok=True)
    audit = root / 'processed' / 'auditddi_v1'
    twosides_processed = root / 'processed' / 'twosides_v1'

    resolution_path = audit / 'twosides_drug_cid_resolution.csv'
    ddinter_path = audit / 'ddinter_pubchem_match_audit.csv'
    pharmgkb_path = audit / 'pharmgkb_chemical_gene_match_audit.csv'
    faers_path = audit / 'faers_drug_match_audit.csv'
    twosides_path = twosides_processed / 'twosides_clean.parquet'
    drugs_path = twosides_processed / 'drugs_clean.csv'

    resolution = read_required(resolution_path, 'TWOSIDES CID resolution audit')
    required_resolution = {'drug_idx', 'canonical_smiles', 'selected_pubchem_cid', 'match_status'}
    if not required_resolution.issubset(resolution.columns):
        raise ValueError(f'{resolution_path} needs columns {sorted(required_resolution)}')
    resolution = resolution.copy()
    resolution['cid'] = resolution['selected_pubchem_cid'].map(cid_key)
    resolution['drug_idx'] = pd.to_numeric(resolution['drug_idx'], errors='coerce')
    resolution = resolution.dropna(subset=['drug_idx']).copy()
    resolution['drug_idx'] = resolution['drug_idx'].astype(int)
    resolution['canonical_smiles'] = resolution['canonical_smiles'].fillna('').astype(str).str.strip()
    resolution = resolution[(resolution['cid'].notna()) & (resolution['canonical_smiles'] != '')]
    if resolution['cid'].duplicated().any():
        dup = resolution.loc[resolution['cid'].duplicated(False), 'cid'].head(10).tolist()
        raise ValueError(f'TWOSIDES selected PubChem CIDs are not unique; examples: {dup}')
    if resolution['drug_idx'].duplicated().any():
        raise ValueError('TWOSIDES resolution audit has duplicate drug_idx values.')
    cid_to_idx = dict(zip(resolution['cid'], resolution['drug_idx']))
    idx_to_cid = dict(zip(resolution['drug_idx'], resolution['cid']))
    drug_count = len(resolution)

    # TWOSIDES labels: binary pair association; preserve source and count of
    # pair-event rows without conflating events into additional drug pairs.
    interactions = pd.read_parquet(twosides_path)
    if not {'drug_a', 'drug_b'}.issubset(interactions.columns):
        raise ValueError(f'{twosides_path} must include drug_a and drug_b.')
    interactions['drug_a'] = pd.to_numeric(interactions['drug_a'], errors='coerce')
    interactions['drug_b'] = pd.to_numeric(interactions['drug_b'], errors='coerce')
    interactions = interactions.dropna(subset=['drug_a', 'drug_b']).copy()
    interactions['drug_a'] = interactions['drug_a'].astype(int)
    interactions['drug_b'] = interactions['drug_b'].astype(int)
    valid_ids = set(idx_to_cid)
    interactions = interactions[
        interactions['drug_a'].isin(valid_ids) & interactions['drug_b'].isin(valid_ids)
    ].copy()
    interactions['pair_a'] = interactions[['drug_a', 'drug_b']].min(axis=1)
    interactions['pair_b'] = interactions[['drug_a', 'drug_b']].max(axis=1)
    twosides_pairs = interactions.groupby(['pair_a', 'pair_b'], as_index=False).agg(
        event_rows=('pair_a', 'count')
    )
    twosides_pairs['source'] = 'TWOSIDES'
    twosides_pairs['label'] = 1
    twosides_pairs['label_semantics'] = 'reported_twosides_pair'
    twosides_pairs['drug_a_cid'] = twosides_pairs['pair_a'].map(idx_to_cid)
    twosides_pairs['drug_b_cid'] = twosides_pairs['pair_b'].map(idx_to_cid)
    twosides_pairs.to_csv(out / 'twosides_pairs.csv', index=False)

    # DDInter labels are known interaction evidence, not safe/negative labels.
    ddinter = read_required(ddinter_path, 'DDInter match audit')
    required_ddi = {'drug1_cid', 'drug2_cid', 'both_drugs_match', 'same_cid', 'severity', 'source_file', 'source_row'}
    if not required_ddi.issubset(ddinter.columns):
        raise ValueError(f'{ddinter_path} needs columns {sorted(required_ddi)}')
    ddinter = ddinter[
        ddinter['both_drugs_match'].map(_truthy)
        & ~ddinter['same_cid'].map(_truthy)
    ].copy()
    ddinter['drug_a_cid'] = ddinter['drug1_cid'].map(cid_key)
    ddinter['drug_b_cid'] = ddinter['drug2_cid'].map(cid_key)
    ddinter['drug_a'] = ddinter['drug_a_cid'].map(cid_to_idx)
    ddinter['drug_b'] = ddinter['drug_b_cid'].map(cid_to_idx)
    ddinter = ddinter.dropna(subset=['drug_a', 'drug_b']).copy()
    ddinter['drug_a'] = ddinter['drug_a'].astype(int)
    ddinter['drug_b'] = ddinter['drug_b'].astype(int)
    ddinter['pair_a'] = ddinter[['drug_a', 'drug_b']].min(axis=1)
    ddinter['pair_b'] = ddinter[['drug_a', 'drug_b']].max(axis=1)
    # Re-align identifiers to the canonical pair order (the raw DDInter order
    # is arbitrary and must not be carried into pair_a/pair_b columns).
    ddinter['drug_a_cid'] = ddinter['pair_a'].map(idx_to_cid)
    ddinter['drug_b_cid'] = ddinter['pair_b'].map(idx_to_cid)
    # Aggregate multiple DDInter records for the same unordered pair without
    # discarding their distinct severity/description evidence.
    ddinter_pairs = ddinter.groupby(['pair_a', 'pair_b'], as_index=False).agg(
        drug_a_cid=('drug_a_cid', 'first'),
        drug_b_cid=('drug_b_cid', 'first'),
        ddinter_record_count=('pair_a', 'size'),
        severity=('severity', join_unique),
        description=('description', join_unique),
        source_file=('source_file', join_unique),
        source_row=('source_row', join_unique),
    )
    ddinter_pairs['source'] = 'DDInter'
    ddinter_pairs['label'] = 1
    ddinter_pairs['label_semantics'] = 'curated_ddinter_interaction_record'
    ddinter_pairs[['pair_a', 'pair_b', 'drug_a_cid', 'drug_b_cid', 'source', 'label',
                   'label_semantics', 'ddinter_record_count', 'severity', 'description',
                   'source_file', 'source_row']].to_csv(
        out / 'ddinter_pairs.csv', index=False
    )
    twosides_key_set = set(zip(twosides_pairs['pair_a'], twosides_pairs['pair_b']))
    ddinter_key_set = set(zip(ddinter_pairs['pair_a'], ddinter_pairs['pair_b']))
    ddinter_overlap_summary = {
        'twosides_unique_pairs': len(twosides_key_set),
        'ddinter_unique_pairs': len(ddinter_key_set),
        'pairs_in_both_sources': len(twosides_key_set & ddinter_key_set),
        'ddinter_pairs_not_in_twosides': len(ddinter_key_set - twosides_key_set),
        'absent_from_twosides_means_unknown': True,
        'ddinter_pairwise_rows_used_as_direct_test_labels': False,
    }
    _write_json(out / 'ddinter_pair_overlap_summary.json', ddinter_overlap_summary)

    # Unified evidence table: one row per pair, with one column per source.
    # These are source-presence indicators, not a single merged training label.
    twosides_evidence = twosides_pairs[
        ['pair_a', 'pair_b', 'event_rows']
    ].rename(columns={'event_rows': 'twosides_event_rows'})
    ddinter_evidence = ddinter_pairs[
        ['pair_a', 'pair_b', 'ddinter_record_count', 'severity', 'description']
    ].rename(columns={
        'severity': 'ddinter_severities',
        'description': 'ddinter_descriptions',
    })
    pairwise_evidence = twosides_evidence.merge(
        ddinter_evidence, on=['pair_a', 'pair_b'], how='outer', validate='one_to_one'
    )
    pairwise_evidence['twosides_reported'] = pairwise_evidence['twosides_event_rows'].notna()
    pairwise_evidence['ddinter_reported'] = pairwise_evidence['ddinter_record_count'].notna()
    pairwise_evidence['twosides_event_rows'] = (
        pairwise_evidence['twosides_event_rows'].fillna(0).astype('int64')
    )
    pairwise_evidence['ddinter_record_count'] = (
        pairwise_evidence['ddinter_record_count'].fillna(0).astype('int64')
    )
    pairwise_evidence['evidence_source_set'] = pairwise_evidence.apply(
        lambda row: ';'.join(
            source for source, present in (
                ('TWOSIDES', row['twosides_reported']),
                ('DDInter', row['ddinter_reported']),
            ) if present
        ),
        axis=1,
    )
    pairwise_evidence['evidence_agreement'] = pairwise_evidence.apply(
        lambda row: (
            'both_sources' if row['twosides_reported'] and row['ddinter_reported']
            else 'twosides_only' if row['twosides_reported']
            else 'ddinter_only'
        ),
        axis=1,
    )
    pairwise_evidence['known_pair_evidence'] = 1
    pairwise_evidence['label_semantics'] = (
        'source-specific reported/curated evidence; not a causal claim; '
        'absence from either source is unknown'
    )
    pairwise_evidence['drug_a_cid'] = pairwise_evidence['pair_a'].map(idx_to_cid)
    pairwise_evidence['drug_b_cid'] = pairwise_evidence['pair_b'].map(idx_to_cid)
    idx_to_smiles = dict(zip(resolution['drug_idx'], resolution['canonical_smiles']))
    idx_to_match_status = dict(zip(resolution['drug_idx'], resolution['match_status']))
    pairwise_evidence['canonical_smiles_a'] = pairwise_evidence['pair_a'].map(idx_to_smiles)
    pairwise_evidence['canonical_smiles_b'] = pairwise_evidence['pair_b'].map(idx_to_smiles)
    pairwise_evidence['drug_a_match_status'] = pairwise_evidence['pair_a'].map(idx_to_match_status)
    pairwise_evidence['drug_b_match_status'] = pairwise_evidence['pair_b'].map(idx_to_match_status)
    pairwise_evidence = pairwise_evidence.sort_values(
        ['pair_a', 'pair_b'], kind='stable'
    ).reset_index(drop=True)
    pairwise_evidence.to_csv(out / 'pairwise_evidence_union.csv', index=False)

    # All reported pairs from both sources are blocked from negative sampling.
    # This file does not imply DDInter pairs are automatically training labels.
    forbidden = pd.concat([
        twosides_pairs[['pair_a', 'pair_b', 'source']],
        ddinter_pairs[['pair_a', 'pair_b', 'source']],
    ], ignore_index=True).drop_duplicates(['pair_a', 'pair_b', 'source'])
    forbidden.to_csv(out / 'known_reported_pairs_for_negative_exclusion.csv', index=False)

    # Per-drug PharmGKB annotations keyed through the audit's PubChem CID.
    pg = read_required(pharmgkb_path, 'PharmGKB match audit')
    required_pg = {'gene_name', 'pubchem_cid', 'match_status'}
    if not required_pg.issubset(pg.columns):
        raise ValueError(f'{pharmgkb_path} needs columns {sorted(required_pg)}')
    pg['cid'] = pg['pubchem_cid'].map(cid_key)
    pg['drug_idx'] = pg['cid'].map(cid_to_idx)
    pg['gene_name'] = pg['gene_name'].fillna('').astype(str).str.strip()
    pg = pg.dropna(subset=['drug_idx'])
    pg = pg[pg['gene_name'].ne('')].copy()
    pg['drug_idx'] = pg['drug_idx'].astype(int)
    gene_long = pg[['drug_idx', 'cid', 'gene_name', 'match_status']].drop_duplicates()
    gene_long.to_csv(out / 'pharmgkb_drug_gene_annotations.csv', index=False)
    gene_counts = gene_long.groupby('drug_idx').size().rename('pharmgkb_gene_count')
    genes_per_drug = gene_long.groupby('drug_idx')['gene_name'].agg(lambda values: set(values)).to_dict()
    gene_frequency: dict[str, int] = {}
    for genes in genes_per_drug.values():
        for gene in genes:
            gene_frequency[gene] = gene_frequency.get(gene, 0) + 1
    # A small, deterministic profile fits the existing multimodal model
    # contract. The complete long table is also saved for future vocabularies.
    selected_genes = sorted(gene_frequency, key=lambda gene: (-gene_frequency[gene], gene))[:23]
    gene_feature_names = [f'pharmgkb_gene:{gene}' for gene in selected_genes]
    gene_feature_names.extend(
        f'pharmgkb_gene:unused_{index:02d}'
        for index in range(len(selected_genes), 23)
    )

    # FAERS report volume is retained as an audited, drug-level exposure
    # feature. It must pass temporal/reporting-bias analysis before model use.
    faers = read_required(faers_path, 'FAERS match audit')
    if not {'report_rows', 'pubchem_cid', 'match_status'}.issubset(faers.columns):
        raise ValueError(f'{faers_path} needs report_rows, pubchem_cid, match_status.')
    faers['cid'] = faers['pubchem_cid'].map(cid_key)
    faers['drug_idx'] = faers['cid'].map(cid_to_idx)
    faers['report_rows'] = pd.to_numeric(faers['report_rows'], errors='coerce').fillna(0)
    faers = faers.dropna(subset=['drug_idx']).copy()
    faers['drug_idx'] = faers['drug_idx'].astype(int)
    faers_counts = faers.groupby('drug_idx')['report_rows'].sum().rename('faers_report_rows')

    features = resolution[['drug_idx', 'cid', 'canonical_smiles', 'match_status']].copy()
    features = features.merge(gene_counts, how='left', on='drug_idx')
    features = features.merge(faers_counts, how='left', on='drug_idx')
    features['pharmgkb_gene_count'] = features['pharmgkb_gene_count'].fillna(0).astype(int)
    features['faers_report_rows'] = features['faers_report_rows'].fillna(0).astype(int)
    features['faers_log1p_report_rows'] = np.log1p(features['faers_report_rows'].astype(float))

    # openFDA parsing is optional and label-to-label mentions remain external
    # evidence. Only the drug-level CYP flags are merged into the feature table.
    openfda_summary: dict[str, Any] = {'status': 'not_run'}
    label_features = pd.DataFrame()
    zip_files: list[Path] = []
    if args.parse_openfda:
        from evidence.openfda_labels import build_name_map, iter_zip_records, names_table, process

        names = (
            resolution[['drug_idx', 'names']].rename(columns={'names': 'inn'})
            if 'names' in resolution
            else resolution[['drug_idx']].assign(inn='')
        )[['drug_idx', 'inn']]
        aliases_path = audit / 'twosides_pubchem_aliases.csv'
        aliases_used = False
        if aliases_path.is_file():
            alias_header = pd.read_csv(aliases_path, nrows=0).columns.tolist()
            cid_column = next((column for column in ('cid', 'pubchem_cid', 'selected_pubchem_cid') if column in alias_header), None)
            name_column = next((column for column in ('synonym', 'alias', 'name', 'title', 'drug_name') if column in alias_header), None)
            if cid_column and name_column:
                aliases = pd.read_csv(aliases_path, usecols=[cid_column, name_column], low_memory=False)
                aliases['drug_idx'] = aliases[cid_column].map(cid_key).map(cid_to_idx)
                aliases = aliases.dropna(subset=['drug_idx']).rename(columns={name_column: 'inn'})
                aliases['inn'] = aliases['inn'].fillna('').astype(str)
                names = pd.concat([names, aliases[['drug_idx', 'inn']]], ignore_index=True)
                aliases_used = True
        names['drug_idx'] = pd.to_numeric(names['drug_idx'], errors='coerce')
        names = names.dropna(subset=['drug_idx'])
        names['drug_idx'] = names['drug_idx'].astype(int)
        names = names.drop_duplicates()
        labels_dir = root / 'openfda'
        zip_files = sorted(set(labels_dir.glob('*.zip')) | set(labels_dir.rglob('*.zip')))
        if not zip_files:
            raise FileNotFoundError(f'--parse-openfda was requested but no zip archives were found under {labels_dir}')
        name_map, ambiguous_names = build_name_map(names_table(names))
        label_frames = []
        stats = {'records_seen': 0, 'records_attributed': 0}
        for archive in zip_files:
            frame, _, current = process(iter_zip_records(archive), name_map)
            label_frames.append(frame)
            for key in stats:
                stats[key] += current[key]
            print(f'{archive.name}: {current["records_seen"]} labels scanned; {current["records_attributed"]} attributed')
        label_features = pd.concat(label_frames, ignore_index=True) if label_frames else pd.DataFrame()
        if not label_features.empty:
            aggregate = {column: ('sum' if column in {'n_labels', 'pk_text_chars'} else 'max')
                         for column in label_features.columns if column != 'drug_idx'}
            label_features = label_features.groupby('drug_idx', as_index=False).agg(aggregate)
        else:
            label_features = pd.DataFrame(
                columns=['drug_idx', 'n_labels', 'pk_text_chars', *CYP_COLUMNS]
            )
        label_features.to_csv(out / 'openfda_drug_features.csv', index=False)
        features = features.merge(label_features, how='left', on='drug_idx')
        openfda_summary = {'status': 'parsed', **stats, 'archives': len(zip_files), 'ambiguous_names_discarded': ambiguous_names,
                           'pubchem_aliases_used': aliases_used,
                           'drug_feature_rows': len(label_features),
                           'pairwise_label_mentions_used_as_features': False}

    features.to_csv(out / 'drug_features_by_cid.csv', index=False)

    # Fixed-layout profile consumed by the multimodal graph trainer:
    # 23 PharmGKB gene indicators + 24 openFDA CYP flags + a reserved,
    # always-zero FAERS slot + 3 source-availability flags = 51 values.
    # FAERS report counts remain in the audit CSV but are excluded from model
    # inputs until temporal overlap with TWOSIDES is evaluated.
    n_drugs = int(resolution['drug_idx'].max()) + 1 if len(resolution) else 0
    feature_names = gene_feature_names
    feature_names += [f'openfda:{name}' for name in CYP_COLUMNS]
    feature_names += ['faers:reserved_zero_temporal_audit_only', 'availability:pharmgkb',
                      'availability:openfda', 'availability:faers']
    matrix = np.zeros((n_drugs, len(feature_names)), dtype=np.float32)
    cyp_start = 23
    for drug_idx, genes in genes_per_drug.items():
        if 0 <= int(drug_idx) < n_drugs:
            for offset, gene in enumerate(selected_genes):
                matrix[int(drug_idx), offset] = float(gene in genes)
            matrix[int(drug_idx), -3] = float(bool(genes))
    cyp_cols = [name for name in CYP_COLUMNS]
    if not label_features.empty:
        by_idx = label_features.set_index('drug_idx')
        for row in resolution.itertuples(index=False):
            idx = int(row.drug_idx)
            if idx not in by_idx.index:
                continue
            record = by_idx.loc[idx]
            for offset, column in enumerate(cyp_cols):
                if column in record.index:
                    matrix[idx, cyp_start + offset] = float(record[column])
            matrix[idx, -2] = float(record.get('n_labels', 0) > 0)
    # The reserved FAERS scalar and its availability flag intentionally stay
    # zero. FAERS is audited, but not exposed as a predictor in this run.
    cid_by_idx = {idx: cid for cid, idx in cid_to_idx.items()}
    smiles_by_idx = dict(zip(resolution['drug_idx'], resolution['canonical_smiles']))
    np.savez_compressed(
        out / 'source_feature_matrix.npz',
        drug_idx=np.arange(n_drugs, dtype=np.int64),
        cid=np.array([cid_by_idx.get(i, '') for i in range(n_drugs)], dtype=str),
        canonical_smiles=np.array([str(smiles_by_idx.get(i, '')) for i in range(n_drugs)], dtype=str),
        features=matrix,
        feature_names=np.array(feature_names, dtype=str),
    )

    # ChEMBL input role is recorded without inventing molecule-target activity.
    chembl_files = sorted((root / 'chembl').rglob('*chemreps*.gz'))
    chembl_summary = {
        'status': 'available' if chembl_files else 'not_found',
        'structure_files': [{'path': str(path), 'bytes': path.stat().st_size} for path in chembl_files],
        'role': 'molecular_pretraining_candidate; target metadata alone is not drug-target activity',
    }

    input_paths = [resolution_path, ddinter_path, pharmgkb_path, faers_path, twosides_path, drugs_path]
    pharmgkb_raw = root / 'pharmgkb' / 'relationships.tsv'
    pubchem_aliases = audit / 'twosides_pubchem_aliases.csv'
    verification_manifest = root / 'verification_manifest.json'
    input_paths.extend(
        path for path in (pharmgkb_raw, pubchem_aliases, verification_manifest)
        if path.is_file()
    )
    input_paths.extend(zip_files)
    input_paths.extend(chembl_files)
    manifest = {
        'schema_version': 'auditddi_seven_source_bundle_v1',
        'dataset_root': str(root),
        'output_root': str(out),
        'source_roles': {
            'TWOSIDES': 'supervised reported pair-event labels',
            'PubChem': 'drug identity and canonical structures via the audited CID crosswalk',
            'ChEMBL': chembl_summary,
            'PharmGKB': 'drug-to-gene annotations; source-specific feature table emitted',
            'openFDA': openfda_summary,
            'FAERS': 'matched report counts emitted for coverage and reporting-bias audit; excluded from model inputs pending temporal review',
            'DDInter': 'curated interaction evidence emitted separately and excluded from sampled negatives',
        },
        'counts': {
            'resolved_drugs': drug_count,
            'twosides_pair_rows': int(len(twosides_pairs)),
            'twosides_pair_event_rows': int(len(interactions)),
            'ddinter_matched_rows': int(len(ddinter)),
            'ddinter_unique_pairs': int(ddinter_pairs[['pair_a', 'pair_b']].drop_duplicates().shape[0]),
            'ddinter_pairs_not_in_twosides': ddinter_overlap_summary['ddinter_pairs_not_in_twosides'],
            'pairwise_evidence_union_rows': int(len(pairwise_evidence)),
            'pairwise_both_sources': int((pairwise_evidence['evidence_agreement'] == 'both_sources').sum()),
            'pairwise_twosides_only': int((pairwise_evidence['evidence_agreement'] == 'twosides_only').sum()),
            'pairwise_ddinter_only': int((pairwise_evidence['evidence_agreement'] == 'ddinter_only').sum()),
            'pharmgkb_matched_drug_gene_rows': int(len(gene_long)),
            'faers_matched_drugs': int(faers['drug_idx'].nunique()),
        },
        'drug_feature_matrix': {
            'path': str(out / 'source_feature_matrix.npz'),
            'shape': list(matrix.shape),
            'feature_names': feature_names,
            'selected_pharmgkb_gene_vocabulary': selected_genes,
            'faers_model_feature': 'disabled_pending_temporal_and_reporting_bias_audit',
            'faers_report_counts_remain_in_audit_table': True,
            'openfda_features_are_keyword_heuristics': True,
        },
        'negative_label_policy': 'Only explicitly labeled positives are positives; absent TWOSIDES/DDInter records are unknown, never confirmed safe.',
        'pairwise_evidence_union': {
            'path': str(out / 'pairwise_evidence_union.csv'),
            'sha256': sha256(out / 'pairwise_evidence_union.csv'),
            'role': 'source-aware pair evidence table; not directly a binary training-label table',
            'source_flags': ['twosides_reported', 'ddinter_reported'],
            'absence_semantics': 'absence from either source means unknown for that source',
        },
        'inputs_sha256': {str(path): sha256(path) for path in input_paths},
    }
    _write_json(out / 'source_bundle_manifest.json', manifest)
    print(json.dumps(manifest['counts'], indent=2))
    print(f'Saved source bundle: {out}')


if __name__ == '__main__':
    main()
