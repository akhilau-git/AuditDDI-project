# AuditDDI project status snapshot

**Status date:** 2026-10-26  
**Code repository:** `D:\AuditDDI` → `https://github.com/akhilau-git/AuditDDI-project.git`  
**Data root:** Google Drive `MyDrive/Projects/auditddi`  
**Execution environment:** Colab for project work, data preparation, and model training, as the user chose after purchasing Colab Pro. Kaggle is not required for the current work.

This snapshot consolidates the current plan, local project layout, and results the user has shared from Colab. Google Drive was not queried directly from this local session, so remote file availability must be confirmed in Colab.

## Environment and workflow to keep fixed

| Where | Role | Canonical location/use |
|---|---|---|
| Local Windows | Edit code and use Git | `D:\AuditDDI`; push to GitHub |
| GitHub | Transfer/version code | `https://github.com/akhilau-git/AuditDDI-project.git`; pull the selected commit into Colab |
| Colab | Dataset collection/checks, identity linking, labels/features, audits, model training, and ADMET screen | `/content/drive/MyDrive/Projects/auditddi` |
| Google Drive | Shared durable data, notebooks, processed files, results | `MyDrive/Projects/auditddi`; separate from GitHub code |

Store pillar outputs separately under `Projects/auditddi/results/pillars/<pillar>/`. Do not upload a source ZIP as the normal code transfer path. The DDI deep-learning training plan uses **200 epochs**. Classical estimators do not have epochs.

## The four pillars

### 1. Drug–drug interaction prediction (DDI)

**Goal:** predict whether a pair is reported in TWOSIDES; sampled unreported pairs remain unknown, not known-safe negatives. Keep toxicity out of this pillar.

**Inputs proposed:** (1) molecular graph from SMILES, (2) Morgan/ECFP6 fingerprint, (3) drug/pharmacogenomic profile, (4) adverse-event profile, (5) protein/target information, (6) verified 3D structure/pocket features, and (7) gene-expression profile. Feature branches are used only when their source, identity map, coverage, and provenance are verified.

**What is evidenced complete:** TWOSIDES/identity audit and a PubChem-backed TWOSIDES–DDInter mapping were run in Colab. Shared outputs reported 1,406 catalogue IDs, 1,405 PubChem CIDs, 1,375 exact-structure-confirmed drugs, 30 provisional RxNorm-only matches, and one manual-review drug (ID 930). The trainer audit reported 8,861,574 TWOSIDES event rows, 1,399 active drugs, and 138,652 unordered interaction pairs. The exported CID pair table had 138,603 TWOSIDES pairs because it excluded 49 pairs involving drug 930. DDInter pair exports also had different counts across versions (79,057 in one overlap summary versus 72,243 in the v2 pair table); reconcile the versions/filters before a final run.

**Models/results:** the strict-identity edge-aware GATv2 checkpoint completed 200 epochs. The interrupted evaluation saved headline metrics: Transductive AUROC/accuracy 0.894/0.806, S1 0.529/0.520, and S2 0.664/0.613. This was a graph-only model selected on ordinary validation, not the proposed seven-input system. The output process was interrupted during an optional pair-level novelty audit; the final run manifest was not written.

**Next DDI plan:** train and compare Morgan/ECFP logistic, edge-aware GATv2, and the proposed seven-input model on the same frozen strict-identity splits. Select checkpoints on pair-disjoint S1-dev data, calibrate/choose thresholds from its reserved post-hoc subset, leave S1-test untouched, and disable the optional pair-level Tanimoto audit during the primary run. The seven-input model uses graph, Morgan fingerprint, drug profile, adverse-event profile, target, 3D structure, and gene-expression features, with the ChEMBL-pretrained encoder initialized for the molecular graph branch.

**Still pending:** complete the S1-dev-selected matched model comparison; verify seven-branch coverage and provenance in the run manifest; report cold-start test metrics across repeated seeds; run optional similarity/ablation analyses after the primary metrics; then review the final checkpoint. S1-test must not be used to choose epochs, thresholds, or model settings.

### 2. Single-drug FAERS severity (kept separate from DDI)

**Goal:** estimate the descriptive fraction of eligible FAERS reports for a drug with a recorded serious outcome. This is not patient-level risk, incidence, or causal toxicity probability.

**What is evidenced complete:** toxicity bridge and FAERS fallback cohort were audited. A clean 1,067-structure cohort was generated. The beta-binomial comparison ran across seeds 203–207. Mean MAE/RMSE were 0.1457/0.1901 versus training-mean baseline 0.1420/0.1875; R² averaged -0.031 and Spearman 0.069. The result is a completed negative experiment: this chemistry-only model did not beat the baseline reliably.

FAERS ASCII quarters 2025 Q1 through 2026 Q2 were downloaded and checksummed; case/version overlaps, deleted case IDs, drug roles, and outcome codes were inspected in Colab.

**Still pending:** build and validate the deduplicated multiquarter case-level cohort; the label-builder failed on a missing `quarter` field, and the repeated attempt showed the same error, so the multiquarter pipeline is not confirmed fixed. Verify temporal split definitions, mapping coverage, and output manifests before another toxicity model run. Do not claim improved toxicity prediction from the completed pilot.

### 3. Drug-pair FAERS severity

**Goal:** estimate the descriptive fraction of eligible FAERS reports for a co-reported pair that include a serious outcome. This is not the TWOSIDES DDI classification task and does not establish causality.

**What is evidenced complete:** Q2 2026 audit/candidate tables exist; a five-seed cold-drug ExtraTrees pilot was run. The results were modest and from one quarter only.

**Still pending:** verify its exact source/cohort and manifests from Drive, compare against a single-drug expectation baseline and count-aware beta-binomial method on identical splits, and obtain a later-quarter temporal validation cohort if compatible data are available.

### 4. ADMET and property screening

**Goal:** calculate molecular properties and structural alerts as a separate pillar.

**What is evidenced complete:** `src/data_prep/admet_engine.py` exists; the Colab notebook is organized under `pillars/admet/`.

**Still pending:** validate property-specific outputs and coverage, document limitations, connect the backend/API if required, and include it in the future frontend. This is currently a descriptor/rule screen, not a trained ADMET ML model.

## Project organization and product

- Four pillar folders now separate DDI, single-drug severity, drug-pair severity, and ADMET notebooks/scripts/results.
- Each model pillar has its own notebook and result folder; Colab is the current environment for preparation and training. ADMET stays in Colab because it is currently a non-training calculation.
- The old frontend was intentionally removed. A new frontend plan/design has not been started; backend/API contracts and model outputs should be settled first.
- HODDI was discussed as a possible higher-order task. It is optional and should remain a separate multi-drug/hypergraph task; do not turn multi-drug sets into assumed pair labels or mix it into the current TWOSIDES pair task without a separate study.

## What should happen next, in order

1. **Reconfirm files in the correct Drive root** `/content/drive/MyDrive/Projects/auditddi` from Colab; do not inspect the code-only folder `MyDrive/AuditDDI` as if it were the data root.
2. **Finish data inventory and identity-link coverage** for the nine planned source families. Keep raw records and source-specific evidence separate; preserve original IDs and match provenance.
3. **Reconcile TWOSIDES/DDInter versions and identity exceptions**, especially the 49 pairs involving drug 930 and the differing DDInter pair totals.
4. **Finalize DDI labels, negative-sampling policy, fixed splits, and leakage audits** in Colab. Save and hash the exact inputs.
5. **Run the DDI matched comparison in Colab** from the selected GitHub revision, up to 200 neural epochs, with saved logs/manifests/checkpoints. Compare the models on identical frozen splits and cold-start regimes.
6. **Continue separate FAERS pillars:** fix/rebuild multiquarter single-drug labels; validate pair-severity pilot provenance and run temporal/count-aware comparisons.
7. **Validate ADMET outputs**, then define backend and new frontend requirements. Keep UI development separate from model/data claims.
8. **Prepare final report and reviewed checkpoint** only after results, splits, and provenance are verified. Ensemble only if the prespecified cold-start results support it.

## Progress estimate

The execution plan currently has **13 of 100 checkboxes marked complete**. That is a tracker count, not a fair project completion percentage: the 100 items are detailed research/evaluation tasks and many accomplishments are recorded in status prose or Colab results instead of checkboxes.

For planning, estimate **about 35% complete and 65% pending** across the broader intended project. This is a judgment-based milestone estimate, not a measured metric. Organization/environment separation and initial audits are substantially done; complete nine-source linking, reproducible DDI training, temporal validation, ADMET validation, final reporting, and the new frontend remain open. Revise this estimate as milestones are verified in Drive and Colab.
