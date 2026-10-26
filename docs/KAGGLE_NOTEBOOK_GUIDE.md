# Kaggle training guide

> **Historical only:** the current project workflow uses Colab for model training. Follow [EXECUTION_ENVIRONMENT_GUIDE.md](EXECUTION_ENVIRONMENT_GUIDE.md) and the Colab notebook under `pillars/ddi/notebooks/` instead.

Kaggle is used only for model fitting. Dataset collection, matching/linking, label creation, audits, and feature preparation happen in Colab. Edit code locally in `D:\AuditDDI`, push it to GitHub, and pull the intended commit into Kaggle. The Drive data folder stays `MyDrive/Projects/auditddi`; set `AUDITDDI_DATA_BASE` to the path where that linked folder appears in Kaggle.

## Training notebooks

- DDI: `pillars/ddi/training/01_DDI_prediction_Kaggle_training.ipynb` — planned 200 epochs.
- Single-drug FAERS severity: `pillars/single_drug_toxicity/training/02_single_drug_FAERS_severity_Kaggle_training.ipynb`.
- Drug-pair FAERS severity: `pillars/drug_pair_severity/training/03_FAERS_pair_severity_Kaggle_training.ipynb`.

ADMET is currently a descriptor/rule-based calculation, not a trained ML predictor, and remains in Colab at `pillars/admet/notebooks/04_ADMET_properties.ipynb`.

## Kaggle setup

Clone or pull `https://github.com/akhilau-git/AuditDDI-project.git` into Kaggle. Link Google Drive using the method already configured in your Kaggle account, then set:

```python
import os
os.environ["AUDITDDI_CODE_ROOT"] = "/kaggle/working/auditddi"
os.environ["AUDITDDI_DATA_BASE"] = "/your/kaggle/drive/mount/MyDrive/Projects/auditddi"
```

Replace the data path with the actual mounted path. Do not point `AUDITDDI_DATA_BASE` at the GitHub checkout. Training outputs belong in `Projects/auditddi/results/pillars/<pillar>/`.

Run a pillar's Colab preparation and audit steps first. Then execute only that pillar's Kaggle trainer. Record the Git commit, dataset/label snapshot, cohort, split, seed, configuration, and output folder with every result.
