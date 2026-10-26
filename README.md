# AuditDDI

AuditDDI is a research project for predicting **reported drug–drug interaction (DDI) associations** from molecular structure and linked drug evidence. Data preparation and model training run in Google Colab. Colab pulls code from GitHub and reads datasets, prepared inputs, checkpoints, and run outputs from Google Drive; a reviewed model checkpoint can then be served locally through a FastAPI backend. The existing browser frontend has been removed and will be rebuilt separately.

> **Research prototype:** a model score is not medical advice or a clinical probability. The training labels distinguish reported TWOSIDES pairs from sampled pairs that were not reported in the supplied data. An unreported pair is unknown; it is not known to be safe.

## Project at a glance

```text
Nine source families in Google Drive
        ↓
Drug identity resolution and source audits
        ↓
Molecular and drug-profile feature preparation
        ↓
Colab data preparation → Colab model training
        ↓
Transductive, S1, and S2 evaluation + run artifacts
        ↓
Review a checkpoint → local FastAPI service + web app
```

The repository contains source code, preparation scripts, the model, evaluation tools, a local application, and tests. Raw datasets, generated artifacts, and model checkpoints are kept outside Git—normally in Google Drive or local deployment storage.

## The nine source families and their roles

The project links these nine source families through a drug identity map. They have different jobs; their raw records are **not concatenated into one training-label table**. A source is only included in a run when its files, release, mapping coverage, and license are verified.

| Source | Role in AuditDDI |
|---|---|
| **TWOSIDES** | Main supervised pair labels: reported drug pairs are positive examples. |
| **PubChem** | Drug identity and chemical structure resolution; canonical SMILES are used to build molecular inputs. |
| **ChEMBL** | Chemical structures for leakage-audited molecular encoder pretraining; measured human compound–target activity for the proposed target branch. |
| **DDInter** | Curated interaction evidence; known pairs are excluded from sampled negatives and retained for audit. Unlisted pairs remain unknown. |
| **PharmGKB** | Matched drug–gene evidence used in the drug-profile feature bundle. |
| **openFDA** | Drug-label adverse-reaction text used as an input feature in the proposed DDI model. |
| **FAERS** | Pharmacovigilance coverage and reporting-bias audit. FAERS report counts are not model input features in the current workflow. |
| **LINCS/GEO** | Drug-perturbation expression signatures, when a verified drug mapping and context metadata are available. GEO disease-expression studies must not be treated as drug perturbations. |
| **PDB/RCSB** | Ligand-bound protein structures and pocket descriptors only when the ligand is verified as the drug and the target mapping is supported. |

The existing screening baseline uses an edge-aware GATv2 molecular encoder and Morgan fingerprints. The proposed seven-input model adds five masked feature branches: PharmGKB drug profile, openFDA adverse-event profile, ChEMBL target activity, verified PDB pocket descriptors, and context-defined gene expression. Single-drug toxicity prediction remains separate. Feature preparation exists, but the seven-input model needs a complete feature coverage audit and controlled evaluation before it can be considered validated. TWOSIDES remains the supervised pair-label source.

## Repository layout

```text
backend/                 FastAPI service and local authentication
pillars/                 Four pillar workspaces with Colab preparation and training notebooks
scripts/                 Dataset checks and preparation commands
src/data_prep/           Drug resolution, graph preparation, source linking
src/models/              Molecular encoders, pair model, calibration and audits
src/training/            ChEMBL pretraining, DDI training, evaluation and studies
tests/                   Automated project tests
docs/                    Dataset, methodology, and workflow notes
requirements.txt         Local/API Python dependencies
requirements_colab.txt   Colab preparation dependencies
requirements_kaggle.txt  Legacy Kaggle dependency set; Colab is the current training environment
docker-compose.yml       Local backend-only deployment
```

Get the source code from the project repository:

```bash
git clone https://github.com/akhilau-git/AuditDDI-project.git
cd AuditDDI-project
```

## Data and artifacts

### Canonical locations

- **Google Drive project folder:** `Projects/auditddi`. This holds the datasets, processed files, checkpoints, and results. In Colab it is `/content/drive/MyDrive/Projects/auditddi`.
- **GitHub repository:** [`akhilau-git/AuditDDI-project`](https://github.com/akhilau-git/AuditDDI-project). It contains code and notebooks, not the datasets or trained checkpoints.
- **Colab code checkout:** the DDI notebook below clones or fast-forwards this repository automatically. Other Colab notebooks use the same repository URL.

The GitHub repository and Drive data folder are separate. Push code and notebooks to GitHub; keep raw and prepared data, pretrained weights, checkpoints, and results in Drive. In Colab, mount Drive at `/content/drive/MyDrive/Projects/auditddi`. The DDI training notebook saves outputs beneath `results/pillars/DDI/` in that folder. Do not put data files in the code checkout or commit them to Git.

The project folder in Google Drive is:

```text
MyDrive/Projects/auditddi
```

Expected source folders are `twosides/`, `pubchem/`, `chembl/`, `pharmgkb/`, `openfda/`, `faers/`, `ddinter/`, `lincs_geo/` (or `lincs/` and `geo/`), and `pdb_rcsb/` (or `pdb/`). The inventory also recognizes common capitalization and legacy folder aliases. Prepared inputs and generated artifacts live beside them:

```text
auditddi/
├── twosides/ pubchem/ chembl/ pharmgkb/ openfda/ faers/ ddinter/
├── lincs_geo/ pdb_rcsb/
├── processed/
│   ├── twosides_v1/
│   ├── auditddi_v1/
│   └── auditddi_v2/
├── checkpoints/
└── results/pillars/{ddi,single_drug_toxicity,drug_pair_severity,admet}/
```

In Colab, the Drive root is `/content/drive/MyDrive/Projects/auditddi`:

```python
import os
os.environ["AUDITDDI_DATA_BASE"] = "/content/drive/MyDrive/Projects/auditddi"
os.environ["AUDITDDI_CODE_ROOT"] = "/content/auditddi_colab_training"
```

Set `AUDITDDI_RESULTS_BASE` as well if results should be written to a different writable Drive path.

## Google Colab DDI training workflow

Open [`pillars/ddi/notebooks/01_DDI_prediction.ipynb`](pillars/ddi/notebooks/01_DDI_prediction.ipynb) in Google Colab. Select a GPU runtime, mount Google Drive, and run the notebook cells in order. It clones or fast-forwards the GitHub code, installs Colab dependencies, checks for the audited inputs and GPU, then runs the strict-identity DDI pilot. Its results are written to `MyDrive/Projects/auditddi/results/pillars/DDI/` so they persist after the runtime ends. The current notebook runs the specified pilot models for seed 42; it does not train every separate research pillar in one job.

Run the other pillars from their own Colab notebooks after their corresponding data preparation is complete:

- DDI graph-factorization baseline: [`pillars/ddi/notebooks/02_AGF_DDI.ipynb`](pillars/ddi/notebooks/02_AGF_DDI.ipynb)
- Single-drug FAERS severity: [`pillars/single_drug_toxicity/notebooks/02_single_drug_FAERS_severity.ipynb`](pillars/single_drug_toxicity/notebooks/02_single_drug_FAERS_severity.ipynb)
- Drug-pair FAERS severity: [`pillars/drug_pair_severity/notebooks/03_FAERS_pair_severity.ipynb`](pillars/drug_pair_severity/notebooks/03_FAERS_pair_severity.ipynb)
- ADMET screening: [`pillars/admet/notebooks/04_ADMET_properties.ipynb`](pillars/admet/notebooks/04_ADMET_properties.ipynb)

These runs have separate inputs and result folders; run them individually and retain their manifests and metrics together with each output folder. ADMET is a descriptor/rule-based screen, not model training. Notebooks named `*_Kaggle_training.ipynb` are legacy versions; use the Colab notebooks listed above.

### 1. Install Colab dependencies

From the repository root:

```python
%pip install -r requirements_colab.txt
```

PyTorch is intentionally not installed by this file, preserving Colab's accelerator-enabled build. If a dependency install requires a runtime restart, restart the session, remount Drive, and rerun the notebook from the first cell.

### 2. Confirm prepared data

Complete source verification, dataset linking, identity audits, and feature preparation in Colab before starting a training notebook:

```bash
python scripts/verify_existing_datasets.py \
  --data-root "$AUDITDDI_DATA_BASE"
```

The finalized TWOSIDES pair table is `processed/twosides_v1/twosides_clean.parquet`, with its drug catalogue in `processed/twosides_v1/drugs_clean.csv`.

### 3. Build the source-linked feature bundle

```bash
python scripts/prepare_auditddi_source_bundle.py \
  --data-root "$AUDITDDI_DATA_BASE" \
  --parse-openfda
```

This produces `processed/auditddi_v2/`, including the source-feature matrix and bundle manifest. The multimodal trainer checks that required prepared files and source evidence are present; inspect `source_bundle_manifest.json` before training.

### 4. Pretrain the molecular encoder on ChEMBL

Set the paths so the encoder checkpoint and run artifacts persist in Drive:

```python
import os
from pathlib import Path

PROJECT = Path(os.environ["AUDITDDI_DATA_BASE"])
os.environ["AUDITDDI_DATA_BASE"] = str(PROJECT)
os.environ["AUDITDDI_RESULTS_BASE"] = str(PROJECT / "results")
os.environ["AUDITDDI_PRETRAIN_CHECKPOINT_PATH"] = str(
    PROJECT / "checkpoints/chembl_pretrained_encoder.pt"
)
os.environ["AUDITDDI_PRETRAINED_ENCODER_PATH"] = str(
    PROJECT / "checkpoints/chembl_pretrained_encoder.pt"
)
os.environ["AUDITDDI_MODEL_ARCHITECTURE"] = "auditddi_multimodal_v1"
```

Then run from the repository root:

```bash
python -u src/training/pretrain_chembl_encoder.py
```

This is a separate self-supervised stage. It writes an encoder checkpoint and a pretraining manifest/history; it does **not** train the DDI classifier. If the audited ChEMBL checkpoint already exists and matches the current inputs, do not repeat pretraining unnecessarily.

### 5. Train and evaluate the multimodal DDI model

Configure the run and keep the outputs in Drive:

```python
import os
from pathlib import Path

PROJECT = Path(os.environ["AUDITDDI_DATA_BASE"])
RESULTS = PROJECT / "results/seed_201"
RESULTS.mkdir(parents=True, exist_ok=True)

os.environ["AUDITDDI_DATA_BASE"] = str(PROJECT)
os.environ["AUDITDDI_RESULTS_BASE"] = str(RESULTS)
os.environ["AUDITDDI_MODEL_ARCHITECTURE"] = "auditddi_multimodal_v1"
os.environ["AUDITDDI_MODEL_SEED"] = "201"
os.environ["AUDITDDI_SPLIT_SEED"] = "42"
os.environ["AUDITDDI_EPOCHS"] = "200"
os.environ["AUDITDDI_PRETRAINED_ENCODER_PATH"] = str(
    PROJECT / "checkpoints/chembl_pretrained_encoder.pt"
)
os.environ["AUDITDDI_PUBLISH_LATEST_RESULTS"] = "false"
```

Run:

```bash
python -u src/training/train_full_pipeline_v2.py
```

Training uses TWOSIDES pair labels, split-aware sampled unreported pairs, and a binary cross-entropy-with-logits objective. The trainer selects the best checkpoint on its model-selection validation split and applies early stopping. Each timestamped run writes manifests, split/input audits, training history, metrics, predictions, plots, and checkpoint metadata under the configured results location. Preserve that run folder with its checkpoint when reporting results.

### 6. Understand and report the evaluation

The pipeline reports three evaluation regimes:

- **Transductive:** both drugs are represented in training.
- **S1:** both drugs are unseen during training.
- **S2:** one drug is unseen during training.

Metrics include AUROC, PR-AUC/average precision, F1, MCC, balanced accuracy, and calibration-related measures. Use the run's final manifest and evaluation artifacts for reported numbers; a checkpoint's stored validation AUROC is a model-selection value, not a test result. A sampled unreported pair is not a confirmed-safe negative, and internal metrics are not clinical validation.

For more detail on split construction, leakage controls, and artifacts, see [`docs/AUDITDDI_METHODOLOGY_AND_WORKFLOW.md`](docs/AUDITDDI_METHODOLOGY_AND_WORKFLOW.md).

### Interrupted runs and warm starts

Training checkpoints normally preserve the best model weights; they do not preserve the complete optimizer state needed for exact epoch-by-epoch continuation. The optional warm-start settings in `train_full_pipeline_v2.py` load a provenance-matched checkpoint and continue with newly initialized optimizer state:

```text
AUDITDDI_RESUME_CHECKPOINT_PATH=/path/to/saved_model.pt
AUDITDDI_RESUME_AFTER_EPOCH=<last completed epoch shown in the log>
AUDITDDI_CHECKPOINT_PATH=/path/to/a/new/output_checkpoint.pt
```

This is a warm start from saved weights, not an exact resume. Keep the input checkpoint and output checkpoint paths different, and use the same data, model configuration, and split seed. The trainer validates the saved input/split provenance before continuing.

## Local deployment

The local application loads a reviewed checkpoint; it does not train the model. For the current D1 demo, place the checkpoint under `demo_artifacts/` using its actual run filename, `auditddi_seven_branch_candidate.pt`, and place the exact matching feature bundle there as `seven_branch_features.npz`. Keep the corresponding run manifest and evaluation artifacts for provenance. The app checks the checkpoint's recorded bundle hash before loading it. Do not deploy a checkpoint solely because its validation score is high.

### Run with Docker Compose

1. Download the selected D1 checkpoint from its run's `checkpoints/candidates/` directory and the matching `processed/auditddi_v3/seven_branch_features.npz` bundle from Drive. Put them in `demo_artifacts/` with these local names: `auditddi_seven_branch_candidate.pt` and `seven_branch_features.npz`. Do not substitute a bundle from another run.
2. Copy `.env.demo.example` to `.env` and set a private one-time bootstrap token. The example config selects the checkpoint by its actual D1 filename; no rename to a legacy `pxddi_model.pt` filename is required.
3. Start the services from the repository root:

   ```bash
   docker compose up --build
   ```

4. Compose starts the backend API only and binds it to `127.0.0.1:8000`. Check `http://localhost:8000/health` and `http://localhost:8000/ready` to inspect service status; for a seven-branch model these responses also identify the loaded feature-bundle hash, dimensions, record count, and branch coverage. The browser frontend is currently absent and will need to be rebuilt before browser-based use.

Useful API routes include `POST /predict`, `POST /explain` when supported by the selected model, and `POST /audit/dossier`. Predictions are research estimates and explicitly retain the TWOSIDES label caveat.

For local development without Docker, install `requirements.txt`, set `AUDITDDI_CHECKPOINT_DIR` to the artifact directory, set `PXDDI_CHECKPOINT_PATH` to the checkpoint filename, and set `AUDITDDI_SIX_BRANCH_FEATURE_BUNDLE` to the matching local `.npz` path. Then start the API from the repository root:

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

The backend only loads checkpoints from the configured artifact directory. See `.env.production.example` for the configuration requirements if adapting the service to a hosted environment. A public deployment also needs infrastructure-managed HTTPS, authentication, shared rate limiting, monitoring, and durable audit logging; the local Compose setup alone does not provide those services.

## Development

Install the development dependencies and run the test suite from the repository root:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Do not commit raw datasets, credentials, local `.env` files, or trained checkpoints. Keep generated run outputs and model artifacts in the designated Drive/results or local checkpoint folders.

## Limitations

- TWOSIDES is observational pharmacovigilance evidence and may contain reporting bias.
- An unreported pair is unknown, not proven safe.
- S1/S2 cold-start performance can differ substantially from transductive performance.
- Calibration, conformal sets, and structural-domain flags are research diagnostics; they do not guarantee reliability under distribution shift.
- The project does not use patient-linked outcome data and is not a patient-specific clinical decision system.


## AGF-DDI (cold-start model, added)

See `docs/AGF_DDI.md`. Quick start: `pillars/ddi/notebooks/02_AGF_DDI.ipynb`, or
`python src/training/agf_ddi.py --splits_dir <frozen_split_folder> --out_dir <results> --seeds 3 --ablate`.
Install with `pip install -r requirements_agf.txt`.
