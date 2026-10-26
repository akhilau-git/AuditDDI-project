# Build the PDB pocket feature table in Colab

This step uses the existing exact ligand audit report. It does not repeat the
1,406-drug RCSB exact-structure audit. The 618 drugs classified as `no exact
match` remain absent from `pdb_structure.csv`; the feature-bundle builder will
mark their PDB branch unavailable with its row mask.

## Run

Upload `auditddi_pdb_feature_builder.zip` to the Colab session, then run:

```python
from google.colab import files
from pathlib import Path
from zipfile import ZipFile
import subprocess, sys

uploaded = files.upload()  # choose auditddi_pdb_feature_builder.zip
with ZipFile('auditddi_pdb_feature_builder.zip') as archive:
    archive.extractall('/content/auditddi_pdb_builder')
%pip -q install "biopython>=1.83,<2" "scipy>=1.11,<2" "requests>=2.31"
```

Set `PROJECT` to the mounted Drive project folder. Use the combined verified
report from the PDB audit, normally
`processed/seven_branch/pdb_audit/rcsb_full_panel_verified_after_retry.csv`.

```python
from pathlib import Path
project = Path('/content/gdrive/MyDrive/Projects/auditddi')  # or /content/drive/...
verified = project / 'processed/seven_branch/pdb_audit/rcsb_full_panel_verified_after_retry.csv'
assert verified.is_file(), verified
```

```python
subprocess.run([
    sys.executable, '-u', '/content/auditddi_pdb_builder/scripts/build_pdb_pocket_features.py',
    '--verified-matches', str(verified),
    '--output-dir', str(project / 'processed/seven_branch'),
    '--resume',
], check=True)
```

The builder caches component searches and mmCIF structures under
`processed/seven_branch/pdb_cache/`. If Colab disconnects, rerun the same cell
with `--resume`; successful API searches and downloaded structures are reused.
HTTP 204 from RCSB means an empty search result and is not counted as a network
error. Transient HTTP failures are retried and logged.

## Outputs and quality checks

- `pdb_structure.csv`: one row per drug with a validated protein-bound exact
  ligand complex; columns are `canonical_smiles` plus 83 numeric features.
- `pdb_structure.manifest.json`: feature definition, mapping and selection
  policy, source hashes, coverage, and output hash.
- `pdb_structure_audit.csv`: candidate checks and the chosen PDB entry for each
  drug with usable pocket features.
- `pdb_structure_errors.csv`: persistent search/download errors only.

The 83 features are 40 amino-acid residue counts at 4/6 Å, 36 ligand/protein
atom-type contact counts at 4.5 Å normalized by ligand heavy-atom count, four
contact totals, ligand heavy-atom count, pocket-residue count, and nearest
protein distance. Multi-model structures use their first deposited model. A
drug is accepted only when the exact CCD ligand has coordinates and a protein
contact within 4.5 Å. Among the first ten exact CCD search hits, the builder
prefers X-ray structures, then lower resolution, then PDB ID. This is a
documented, deterministic pocket descriptor; it is not a binding-affinity or
mechanism prediction.

After generation, rerun `scripts/audit_seven_branch_split_coverage.py` in the
source bundle against this Drive project. Then build the combined feature
bundle and verify the manifest and split-level pair coverage before starting
the 20-epoch pilot.
