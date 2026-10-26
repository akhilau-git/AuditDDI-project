# AuditDDI pillars

Each pillar has its own preparation/training workflow and result folder. Colab is for project work and data preparation; Kaggle is reserved for model fitting. The code is maintained locally at `D:\AuditDDI` and pulled from GitHub into the notebook runtime. All pillars use the logical Drive data root `MyDrive/Projects/auditddi`.

| Pillar | Colab work | Kaggle training | Drive results |
|---|---|---|---|
| DDI prediction | `ddi/notebooks/01_DDI_prediction.ipynb` | `ddi/training/01_DDI_prediction_Kaggle_training.ipynb` | `Projects/auditddi/results/pillars/ddi/` |
| Single-drug toxicity/severity | `single_drug_toxicity/notebooks/02_single_drug_FAERS_severity.ipynb` | `single_drug_toxicity/training/02_single_drug_FAERS_severity_Kaggle_training.ipynb` | `Projects/auditddi/results/pillars/single_drug_toxicity/` |
| Drug-pair severity | `drug_pair_severity/notebooks/03_FAERS_pair_severity.ipynb` | `drug_pair_severity/training/03_FAERS_pair_severity_Kaggle_training.ipynb` | `Projects/auditddi/results/pillars/drug_pair_severity/` |
| ADMET/property screening | `admet/notebooks/04_ADMET_properties.ipynb` | Not applicable: current screen is not a trained model | `Projects/auditddi/results/pillars/admet/` |

Shared model and data-preparation implementations remain in `scripts/` and `src/` so there is one maintained implementation of each algorithm.
