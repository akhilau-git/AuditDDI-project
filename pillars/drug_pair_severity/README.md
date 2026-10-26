# Pillar 3 — Drug-pair FAERS severity

Estimate the descriptive serious-outcome report fraction for a co-reported drug pair. This is distinct from DDI classification and does not establish causality.

## Workflow

- **Colab preparation:** `notebooks/03_FAERS_pair_severity.ipynb` checks the audited pair table and cohort provenance. Pair construction, canonicalization, and audits happen in Colab.
- **Kaggle model training:** `training/03_FAERS_pair_severity_Kaggle_training.ipynb` runs the ECFP6 + ExtraTrees model.
- **Drive data:** `MyDrive/Projects/auditddi` (fixed Colab path `/content/drive/MyDrive/Projects/auditddi`; configure Kaggle path with `AUDITDDI_DATA_BASE`).
- **Results:** `Projects/auditddi/results/pillars/drug_pair_severity/`.
- **Implementation:** `src/training/train_faers_pair_severity.py` and pair preparation scripts under `scripts/`.

Use the same GitHub revision in both environments. Keep this task and its report-fraction target separate from the DDI classifier.
