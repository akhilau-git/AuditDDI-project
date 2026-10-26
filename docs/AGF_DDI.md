# AGF-DDI: Auditable Graph-Fingerprint cold-start DDI

Code: `src/training/agf_ddi.py` · Notebook: `pillars/ddi/notebooks/02_AGF_DDI.ipynb` · Test: `tests/test_agf_ddi.py`

## Why it was added
Your split protocol uses degree-matched negatives, so a drug's popularity gives no signal. A graph-only model reached S1 0.529 / S2 0.664, and an ECFP baseline is ~0.53 on S1. AGF-DDI adds label-safe evidence that works for unseen drugs.

## Method
1. **Drug graph fingerprint** – similarity graphs from ECFP, atom-pair, MACCS, and every source table (PharmGKB, openFDA, ChEMBL target, PDB, LINCS/GEO).
2. **Analog transfer** – an unseen drug borrows interactions of its most similar known drugs: `M[a,b] = Σ w(a,a') A[a',b'] w(b,b')`.
3. **Interaction-graph topology** (train positives only) – common neighbours, Adamic-Adar, resource allocation, spectral score, degree.
4. **Leak-free cold-start training** – drug-fold masking: the edges of simulated-cold drugs are removed before their features are computed.
5. **One gradient-boosted head per regime** (transductive, S2, S1), order-invariant by construction.
6. **Audit outputs** – leakage checks (run aborts on violation), SHAP contribution per evidence group, supporting analog drug pairs for top predictions, ablation table.

## Protocol
Dev splits: early stopping and the accuracy threshold only. Test splits: never used for training, features, or tuning. Report whatever the test numbers are. Improvements should come from better inputs (more feature tables, better identity mapping), selected on dev.

## Feature tables
One CSV per source with `canonical_smiles` + numeric columns, in `processed/seven_branch/` (auto-discovered), or pass files with `--bio_npz`.
