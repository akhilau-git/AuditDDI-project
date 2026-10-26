# FAERS pair-severity pilot

This is a separate exploratory task from the TWOSIDES binary DDI model. It
regresses a smoothed fraction of deduplicated FAERS reports for a co-reported
drug pair that include a severe outcome. It does not estimate causal toxicity,
clinical incidence, or the safety of an unreported pair.

## Why this pilot uses chemistry only

The Q2 2026 audit contains 22,036 pairs with at least 20 reports. After
canonical SMILES matching, 478 of 1,191 unique pair structures appear in the
current five-vector feature bundle. The pilot therefore uses Morgan ECFP6
fingerprints computed from the pair SMILES, so it can cover eligible pairs
without silently treating unavailable vector branches as observed.

## Evaluation design

`src/training/train_faers_pair_severity.py` groups canonical unordered pairs,
applies the report-count threshold, and uses a cold-drug split. Training pairs
contain only training compounds; test pairs contain only held-out compounds;
cross-group pairs are excluded. The model is an ExtraTrees regression baseline
with a weighted-mean comparator. Unreported pairs are never treated as
negative examples.

## Kaggle invocation

Install RDKit, scikit-learn, SciPy, and joblib if they are not already available,
then run:

```bash
python -u src/training/train_faers_pair_severity.py \
  --pairs "$AUDITDDI_DATA_BASE/processed/seven_branch/faers_pair_severity_audit_2026q2.csv" \
  --output-dir "$AUDITDDI_DATA_BASE/results/pillars/drug_pair_severity/pilot_2026q2"
```

Outputs include cold-drug held-out predictions, a serialized baseline model,
and JSON metrics. Because the labels are from one FAERS quarter and reporting
is affected by exposure and reporting behavior, this remains a feasibility
pilot. Independent-quarter evaluation is needed before making generalization
claims.

## Q2 2026 pilot result

The recorded seed-203 run retained 22,036 eligible pairs and 736 unique drugs.
The cold-drug split used 15,112 training pairs, 639 test pairs, and excluded
6,285 cross-group pairs. ExtraTrees achieved MAE 0.1513, RMSE 0.1926, R²
0.1566, Spearman 0.3658, and square-root-report-weighted MAE 0.1425. The
weighted-mean baseline achieved MAE 0.1645, RMSE 0.2098, R² -0.0009, and
weighted MAE 0.1572. This is a modest improvement over the baseline on this
single held-out split, not evidence of validated clinical prediction. The test
set contains 639 pairs from one quarter, and the target remains a descriptive
fraction among submitted FAERS reports. A later-quarter temporal evaluation is
required before considering broader claims or product integration.

RDKit's “not removing hydrogen atom without neighbors” messages and the
constant-input Spearman warning for the mean baseline were non-fatal warnings;
the run completed and emitted metrics. They do not change the interpretation
limits above.

## Repeated cold-drug split robustness

Five additional seeds (203–207) evaluated the same Q2 2026 candidate set using
different cold-drug partitions. ExtraTrees had lower MAE and square-root-report-
weighted MAE than the weighted-mean baseline in all five splits. Spearman was
positive in all five; R² was positive in four of five and near zero/slightly
negative in seed 204. Across the five runs, mean MAE was 0.1504 versus 0.1561
for the baseline, and mean weighted MAE was 0.1417 versus 0.1485. These are
repeated partitions of the same quarter, not independent temporal validation.

| Seed | Train pairs | Test pairs | Cross-group excluded | Model MAE | Baseline MAE | Model weighted MAE | Baseline weighted MAE | Model R² | Spearman |
| ---: | ----------: | ---------: | -------------------: | --------: | -----------: | ------------------: | --------------------: | -------: | -------: |
| 203 | 15,112 | 639 | 6,285 | 0.1513 | 0.1645 | 0.1425 | 0.1572 | 0.1566 | 0.3658 |
| 204 | 15,175 | 642 | 6,219 | 0.1594 | 0.1612 | 0.1541 | 0.1582 | -0.0054 | 0.2227 |
| 205 | 13,574 | 1,000 | 7,462 | 0.1452 | 0.1502 | 0.1348 | 0.1402 | 0.0791 | 0.2763 |
| 206 | 13,132 | 1,089 | 7,815 | 0.1446 | 0.1490 | 0.1345 | 0.1388 | 0.0993 | 0.2703 |
| 207 | 13,397 | 1,070 | 7,569 | 0.1514 | 0.1558 | 0.1428 | 0.1479 | 0.0732 | 0.2618 |

Raw metrics are saved in
`processed/seven_branch/faers_pair_severity_repeats_2026q2/repeated_cold_drug_metrics.csv`
and `repeated_cold_drug_summary.json` in Drive. The results support only a
modest, split-robust association with the descriptive FAERS report fraction;
they do not establish causality, clinical risk, or out-of-quarter performance.
