# Pillar 4 — ADMET and property screening

Calculate molecular descriptors and rule-based alerts. Current outputs are a mixture of RDKit descriptors and unvalidated heuristics, not a trained or clinically validated ADMET predictor. Start with [ENGINE_AUDIT.md](ENGINE_AUDIT.md) before interpreting the fields or adding a model.

## Workflow

- **Colab notebook:** `notebooks/04_ADMET_properties.ipynb` runs the current property screen after preparing `inputs/admet_smiles.csv`.
- **Kaggle training:** not applicable to the current rule/descriptor screen.
- **Drive data:** `/content/drive/MyDrive/Projects/auditddi`.
- **Results:** `Projects/auditddi/results/pillars/admet/`.
- **Implementation:** `src/data_prep/admet_engine.py` and chemistry dependencies.
- **Current blocker:** the notebook expects `inputs/admet_smiles.csv`; inspect the Google Drive data root for that input and for property-labeled datasets before screening or training.

This pillar remains separate from FAERS toxicity and DDI prediction.
