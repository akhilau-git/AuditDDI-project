# Single-drug FAERS severity pilot

This is an exploratory, separate task from the TWOSIDES binary DDI classifier
and the FAERS pair-severity model. Its target is the Q2 2026 FAERS severe-
outcome report fraction associated with a drug name, mapped to a canonical
structure. It is a descriptive pharmacovigilance statistic, not a causal
toxicity probability or a measure of clinical incidence.

## Label preparation

The PubChem-mapped candidate bridge contained 1,500 name rows, of which 1,331
had valid mapped structures. Duplicate canonical structures were collapsed
only where alias scores agreed. The 125 structures with conflicting scores
were excluded rather than averaged. The resulting candidate label table
contains 1,067 unique structures. Report counts from aliases were not summed
or used as model weights because they do not represent a deduplicated
structure-level denominator.

## Pilot design and results

The pilot used 1,024-bit Morgan ECFP6 fingerprints (radius 3) with an
ExtraTrees regressor. Evaluation used five repeated 80/20 scaffold-disjoint
splits, with the training-set mean as the baseline.

| Seed | Train drugs | Test drugs | Model MAE | Mean baseline MAE | Model RMSE | Model R² | Model Spearman |
| ---: | ----------: | ---------: | --------: | ----------------: | ---------: | -------: | -------------: |
| 203 | 784 | 283 | 0.1494 | 0.1497 | 0.1985 | 0.0012 | 0.0939 |
| 204 | 857 | 210 | 0.1265 | 0.1248 | 0.1641 | -0.0217 | 0.0705 |
| 205 | 800 | 267 | 0.1492 | 0.1492 | 0.1972 | -0.0167 | 0.0535 |
| 206 | 876 | 191 | 0.1465 | 0.1488 | 0.1947 | 0.0458 | 0.1745 |
| 207 | 787 | 280 | 0.1364 | 0.1380 | 0.1803 | 0.0056 | 0.0905 |

Across seeds, mean model MAE was 0.1416 versus 0.1421 for the baseline; mean
RMSE was 0.1870 versus 0.1876; mean R² was 0.0028; and mean Spearman was
0.0966. This indicates little to no predictive improvement over a constant
baseline. The pilot does not support claiming a useful chemistry-only
single-drug toxicity predictor.

## Limitations and artifacts

All labels come from one FAERS quarter and inherit reporting, exposure, and
alias-mapping biases. Scaffold splits test structural generalization within
that quarter; they do not provide independent temporal validation. Constant-
baseline Spearman warnings are expected because a constant prediction has no
rank correlation. RDKit's unconnected-hydrogen messages are non-fatal.

Colab outputs were saved under
`processed/seven_branch/single_drug_toxicity_pilot_2026q2/`:

- `repeated_scaffold_metrics.csv`
- `repeated_scaffold_predictions.csv`
- `repeated_scaffold_summary.json`
- `single_drug_ecfp6_extratrees.joblib`

## Fallback MLP pilot (2026 Q2)

The original target-prioritized bridge and TWOSIDES identity crosswalk were not
available in the active Colab Drive. A fallback bridge was rebuilt from the
FDA 2026 Q2 ASCII extract using the 1,500 most-reported FAERS drug names,
without TWOSIDES-name prioritization. It mapped 1,160 rows to structures,
yielded 879 unique structures, excluded 226 structures with conflicting
scores, and retained 653 structures. Results from this fallback cohort are
not directly comparable to the earlier target-prioritized 1,067-structure
cohort.

A 1,024-bit ECFP6 MLP pilot (seed 204, 20 epochs, best validation checkpoint
at epoch 15) produced test MAE 0.1225, RMSE 0.1555, R² 0.0487, and Spearman
0.2235 on 120 held-out drugs. The training-mean baseline had MAE 0.1259 and
RMSE 0.1614. A five-seed repeat using the same architecture yielded mean MAE
0.1139 versus 0.1141 baseline and mean RMSE 0.1463 versus 0.1474 baseline;
the MLP beat the baseline on only two of five splits. This is weak and
inconsistent signal, not evidence of a robust predictor.

The next local training experiment is
`scripts/train_single_drug_toxicity_beta_binomial.py`. It uses the severe and
total report counts (recovering integer severe counts from the four-decimal
fraction when needed) in a beta-binomial objective, which models varying
denominator precision more appropriately than unweighted MSE. This tests a
loss-function improvement only; it does not remove FAERS reporting bias or
make the output a clinical toxicity probability. The experiment should use
the same scaffold splits and be compared against the saved MSE pilot before
any model claim is made.
