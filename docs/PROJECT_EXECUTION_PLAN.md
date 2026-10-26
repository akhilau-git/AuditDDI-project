# AuditDDI execution plan and tracker

**Single project folder:** `D:\AuditDDI`  
**Compute plan:** Colab for data work, preparation, and model training, using the canonical Google Drive data folder. Kaggle is optional and not used for the current DDI run.  
**Plan status:** 2026-10-27. Checkboxes are open until the evidence described in the step has been saved.

## Canonical code/data workflow

- **Google Drive project folder:** `MyDrive/Projects/auditddi` — datasets, prepared data, notebooks, and results. Colab uses `/content/drive/MyDrive/Projects/auditddi` or the active mount alias.
- **Local code checkout:** `D:\AuditDDI`, pushed to [`https://github.com/akhilau-git/AuditDDI-project`](https://github.com/akhilau-git/AuditDDI-project).
- **Notebook code checkout:** pull/clone that GitHub repository into Colab. Set `AUDITDDI_CODE_ROOT` if a checkout is not auto-detected.
- Keep code and data locations separate. Do not replace the Drive data root with the repository path or require uploading a source ZIP as the standard workflow.

## Current status

See [PROJECT_STATUS_SNAPSHOT.md](PROJECT_STATUS_SNAPSHOT.md) for the consolidated environment, four-pillar status, pending work, and progress estimate.


- [x] Reviewed the collected paper corpus and wrote a research-backed model/evaluation/display plan for the three non-DDI pillars in [THREE_PILLAR_RESEARCH_PLAN.md](THREE_PILLAR_RESEARCH_PLAN.md). The paper index paths now point to the organized reference folder.
- [x] The C: and D: project copies were consolidated into `D:\AuditDDI`; the C: worktree was removed.
- [x] Generated caches, the local virtual environment, temporary review renders, and duplicate patch bundles were cleaned up. Research papers and project deliverables were retained in organized folders.
- [x] The repository contains the backend, model/training code, data preparation, evaluation, baseline, and test code. The old frontend has been removed; Docker Compose is backend-only until a replacement frontend is built.
- [x] The project plan distinguishes nine source families from the seven model input branches. A shared drug master links records; source-specific labels, evidence, profiles, structures, and context signatures remain separate.
- [x] Prepared the updated Colab source snapshot `deliverables/auditddi_colab_source_20261026_v6.zip`; its file manifest and SHA-256 sidecar are included alongside it. It excludes local datasets, checkpoints, and research PDFs.
- [x] Organized the four pillar notebooks into `pillars/ddi/`, `pillars/single_drug_toxicity/`, `pillars/drug_pair_severity/`, and `pillars/admet/`. Each folder has its own README; Colab handles both data preparation and current model training.
- [ ] Confirm which exact prepared datasets, run folders, checkpoints, and manifests are available in Google Drive. Raw data and most training artifacts are intentionally outside Git.
- [ ] Inventory the datasets and prepared identity/pair tables under the Google Drive project folder `MyDrive/Projects/auditddi` using the active Colab Drive mount. An earlier check inspected the separate `MyDrive/AuditDDI` folder and therefore does not establish that the canonical data root is missing.
- [x] Extend `scripts/audit_dataset_inventory.py` to recognize the nine source families and common folder aliases, including LINCS/GEO and PDB/RCSB. The inventory is ready to run when the source data is restored; it does not create drug matches by itself.
- [ ] Verify the provenance of the existing `results/final_5seed_master_results.csv` and `backend/checkpoints/pxddi_model.pt` before citing their numbers or serving that checkpoint. A file existing is not proof that it came from the intended model, data, or split.
- [ ] A saved seven-branch evaluation is available, but it does not meet the desired cold-start accuracy: the last shared table reports accuracy 0.859 transductive, 0.607 S1, and 0.721 S2. A later 20-epoch run did not start because the runtime lacked `torch_geometric`; reinstall and verify Colab dependencies before retrying. Treat the saved results as exploratory until the selected run is provenance-checked and repeated.
- [x] Completed the single-drug FAERS beta-binomial comparison on the same 1,067-structure cohort used by the target-prioritized ExtraTrees pilot. Across seeds 203–207, beta-binomial mean MAE/RMSE were 0.1457/0.1901, worse than its training-mean baseline (0.1420/0.1875) and the ExtraTrees pilot (0.1416/0.1870). Treat this as a completed negative experiment; it does not support a useful chemistry-only toxicity predictor.
- [x] DDI Colab data audit confirms 8,861,574 TWOSIDES event rows, 1,406 catalogue IDs, 1,399 active drugs, and 138,652 unique unordered pairs. All pair IDs are in the catalogue; seven catalogue drugs are unused. Identity statuses are 1,364 exact RxNorm+structure, 11 structure-resolved conflicts, 30 RxNorm-only provisional, and one manual-review drug (index 930). The review-needed drug appears in 49 active TWOSIDES pairs; the prepared CID pair table excludes those 49. Provisional drugs touch 5,538 active pairs.
- [ ] A separate FAERS pair-severity pilot has five repeated cold-drug splits and a modest improvement over its baseline, but all labels are from one quarter; independent temporal validation remains open.
- [ ] The ADMET calculation module exists in `src/data_prep/admet_engine.py`, but no backend ADMET API route was found. Its estimates/rules need validation and careful labeling before frontend use.
- [ ] The ADMET engine's structural toxicology alerts are not the same as either FAERS statistical prediction task.
- [ ] The local virtual environment was removed during cleanup. Colab can install `requirements_colab.txt`; local development requires a separate environment.

## Four project pillars

Keep these as four separate workstreams with separate targets, models, evaluations, and user-facing outputs. ADMET's rule-based toxicity alerts belong to the ADMET pillar; they are not the single-drug FAERS model.

| Pillar | Task and target | Current status |
|---|---|---|
| 1. DDI prediction | Classify a drug pair as a reported TWOSIDES interaction or a sampled-unreported pair; evaluate cold-start splits separately. | Screening runs use ECFP logistic regression and edge-aware GATv2. The proposed seven-input model combines the molecular graph, Morgan fingerprint, drug profile, adverse-event profile, protein-target, 3D structure, and gene-expression vectors. Single-drug toxicity prediction remains separate. |
| 2. Single-drug toxicity/severity | Estimate the descriptive fraction of mapped FAERS case reports for one drug with a recorded serious outcome. | Existing ExtraTrees and beta-binomial work did not beat the training-mean baseline reliably; do not present this as clinical toxicity risk. |
| 3. Drug-pair severity | Estimate the descriptive severe-outcome report fraction for a drug pair from FAERS. | Q2 2026 pilot exists; repeated cold-drug validation is preliminary and independent temporal validation remains open. |
| 4. ADMET/property screening | Calculate molecular properties and provide clearly labelled heuristic property estimates/structural alerts. | Engine exists; API/UI integration and property-specific validation remain pending. |

Do not merge the four pillars' labels or scores into one prediction model or composite risk score without a separately designed and validated study.

## Rules for a fair study

1. Select and document one reference workflow and data snapshot before comparing scores. Do not mix the older experiment-suite outputs, the seven-source-core multimodal run, and the proposed seven-branch pilot as though they were the same experiment.
2. Every run records code revision, model/configuration, source files and hashes, identity-map version, pair table, split files, seeds, feature bundle/manifest, pretrained checkpoint, and output path.
3. TWOSIDES reported pairs are positive labels. Sampled pairs absent from the supplied interaction data are **unreported/unknown**, not confirmed-safe negatives. DDInter unlisted pairs are unknown too. Keep any DDInter evaluation separate and remove training overlap first.
4. Canonicalize unordered drug pairs so `(A,B)` and `(B,A)` cannot leak across splits. Exclude known interactions from negative sampling using the chosen evidence policy.
5. Use validation for model choice, thresholds, calibration, and ensemble weights. Open the final test results once after decisions are fixed.
6. Treat a prediction as research evidence, not a clinical recommendation or clinical probability.

## End-to-end checklist

### 0. Set up the Colab workflow

- [ ] In Colab, pull the selected GitHub revision and use `/content/drive/MyDrive/Projects/auditddi` for datasets, prepared files, notebooks, and results.
- [ ] Complete dataset collection, matching/linking, label construction, audits, and feature preparation in Colab.
- [ ] For model fitting, use Colab with the same GitHub revision and the canonical Drive data folder.
- [ ] Save each pillar's training outputs under `Projects/auditddi/results/pillars/<pillar>/`; verify the linked Drive location is writable before training.
- [ ] DDI's planned training configuration uses 200 epochs. Record commit, data/cohort snapshot, split, seed, accelerator, and run configuration.

**Output:** prepared inputs, training logs, checkpoints, metrics, and manifests under the Colab-visible Drive project folder.
### 1. Inventory and validate source data

- [ ] Run the existing inventory and preparation checks against the actual Drive data root. Start with `scripts/verify_existing_datasets.py` and `scripts/audit_dataset_inventory.py`; use the source-bundle preparation script only after reviewing the audit.
- [ ] For every source, record release/date, file path, checksum, rows, unique source drug IDs, unique names/structures, and any license/access limitations.
- [ ] Identify which tables exist and which are still missing; do not infer availability from a script or a README count.
- [ ] Keep raw downloads read-only. Write normalized outputs to a new, versioned `processed/` directory so the original source is recoverable.

**Output:** source inventory CSV/JSON and a list of missing or invalid files.

### 2. Resolve drug identity across datasets

- [ ] Create one canonical drug table with an internal canonical ID, source IDs, standardized names, PubChem CID where resolved, canonical/isomeric SMILES, and source/provenance fields.
- [ ] Use identifier joins first where identifiers are trustworthy. Use standardized structure/name evidence for cross-source links; do not silently fuzzy-merge ambiguous names, salts, mixtures, stereoisomers, or combination products.
- [ ] Keep a mapping ledger with match method, confidence/evidence, ambiguous cases, unmatched IDs, and human review decisions. Preserve each source's original ID.
- [ ] Report per-source raw unique drugs, exact/structure/name matches, ambiguous matches, unmatched drugs, and pair retention after resolution. Investigate the current low common-match count before expanding training.
- [ ] PubChem resolves identity/structures; it does not create DDI labels. DrugBank is optional and is not required for this workflow.

#### Nine-source linking contract

Use PubChem-backed canonical drug identities as the shared join layer, while
retaining every source's original ID and record. A single drug may have many
target activities, expression signatures, labels, reports, and structures, so
the source-to-drug relation is often one-to-many rather than a forced one-to-one
row merge.

| Source | Link each record using | Keep after linking |
|---|---|---|
| TWOSIDES | Existing source drug index/RxNorm evidence, then the audited PubChem CID/structure map | Unordered drug pair, event rows/types, TWOSIDES evidence flag |
| PubChem | CID, InChIKey, and stereochemistry-aware structure identifiers | Canonical drug identity, CID, canonical/isomeric SMILES, structure-match provenance |
| ChEMBL | ChEMBL molecule ID plus verified structure/identifier crosswalk to the master drug | Molecule structures for pretraining; activity values joined separately to target IDs and assay metadata. A chemreps structure file alone is not compound-target activity. |
| PharmGKB | Source drug identifiers/names and the available chemical crosswalk | Drug-gene/pharmacogenomic relationships with original relation and match status |
| openFDA | UNII/NDC and unambiguous generic/substance-name aliases | Drug-label features with label version/date; never pairwise DDI labels |
| DDInter | Source drug IDs/names and audited CID/structure matches | Unordered pair, severity, description, source record; keep evidence separate from TWOSIDES |
| FAERS | Report drug names/identifiers mapped through the drug master | Case/version, quarter, drug role, and event evidence for coverage/bias audits or a separately defined FAERS task |
| LINCS/GEO | Perturbagen IDs/names/structures mapped to the master drug | Expression signature plus cell/tissue, dose, duration, and perturbation context; do not collapse contexts without a declared rule |
| PDB/RCSB | Verified ligand CCD chemical structure matched to the drug master; map the protein chain/target separately | PDB entry, ligand, target, and pocket features only for verified ligand-bound structures |

Create four versioned outputs: (1) `drug_master.csv` and a row-level
`drug_identity_map.csv`; (2) `source_link_coverage.csv` with exact, provisional,
ambiguous, and unmatched counts for each source; (3) source-specific relation
tables, including a pairwise evidence table with separate TWOSIDES/DDInter
flags; and (4) the model's per-drug feature bundle keyed by the master drug ID.
Do not turn missing source records into negative labels. Keep HODDI, if later
added, as a separate multi-drug-set task rather than forcing its hyperedges into
the pairwise tables.

**Output:** versioned identity map plus a match-coverage report. Stop here if identity errors or duplicate compounds materially affect pair labels.

### 3. Define labels and build the pair table

- [ ] Use the project-selected TWOSIDES version as the supervised positive-pair source. Record event/pair filtering and deduplicate unordered pairs.
- [ ] Construct sampled-unreported pairs using the configured negative-sampling policy. Exclude known TWOSIDES/DDInter evidence according to the policy; store the sampling seed and policy.
- [ ] Name the label `reported_vs_sampled_unreported`; document that sampled unreported pairs are not known-safe pairs.
- [ ] Keep DDInter as a separate evidence/audit source or a separately defined external evaluation. Never label every pair missing from DDInter as negative.
- [ ] Keep FAERS in coverage/reporting-bias analysis unless a separate, explicitly labelled FAERS task is being studied. Do not turn co-reporting into causal DDI labels.
- [ ] Store pair IDs, canonical drug IDs, label, source evidence, sampling provenance, and exclusion reason.

**Output:** versioned, audited pair table and a label/sampling summary.

### 4. Freeze splits and leakage checks

- [ ] Create and save fixed train/validation/test split files before model comparison; reuse the same split files for each comparable model.
- [ ] Report **transductive**, **S1** (both test drugs unseen in training), and **S2** (one test drug unseen) results separately. Make S1 the primary cold-start metric set.
- [ ] Add scaffold-disjoint evaluation as a separate harder test only after verifying the scaffold split implementation and its coverage. Do not substitute it silently for S1/S2.
- [ ] Audit reversed-pair duplicates, pair overlap, drug overlap per regime, source leakage, and any scaffold overlap. Keep a split manifest with exact files/hashes and seeds.
- [ ] Do not use test examples for early stopping, hyperparameter search, calibration, threshold selection, or ensemble fitting.

**Output:** frozen split tables, leakage audit, counts, and split manifest.

### 5. Build features and verify the selected model inputs

- [ ] Run the source-feature builder only for features selected in the experiment. Inspect `source_bundle_manifest.json`, coverage masks, file hashes, drug-ID ordering, and missingness before training.
- [ ] Current README roles: molecular graph/fingerprint inputs; ChEMBL encoder pretraining and eligible target evidence; PharmGKB/openFDA profile features; PDB-pocket and gene-expression features in the proposed seven-branch bundle; FAERS as an audit, not a default DDI input.
- [ ] Check feature coverage separately for train, validation, S1, S2, and scaffold-disjoint drugs. Missing features must be represented explicitly (for example with availability masks), not filled using information from held-out labels.
- [ ] Save the exact feature bundle and hash with each run. Do not train against a changing Drive file.

**Output:** frozen feature bundle and coverage/provenance manifest.

### DDI results-improvement route (planned; not yet implemented or validated)

The objective is to improve generalization on unseen drugs while using every source in the role its evidence supports. The project must not promise a 90–98% score in advance or tune against held-out test results. A model can meet that target only if the frozen evaluation supports it.

#### Use each source in its scientifically valid role

| Source | Role in this route |
|---|---|
| PubChem | Resolve drug identity and provide canonical structures/SMILES for graph and Morgan inputs. |
| TWOSIDES | Primary supervised reported-pair label source. Sampled unreported pairs remain unknown comparison examples, not proven negatives. |
| ChEMBL | Molecular encoder pretraining and verified protein-target features; record whether held-out structures appear in pretraining. |
| PharmGKB | Drug-profile input branch. |
| openFDA | Drug-level adverse-event/profile branch. Exclude pairwise interaction statements and features derived from the evaluation labels. |
| PDB/RCSB | Verified ligand-bound 3D pocket features where available. |
| LINCS/GEO | Context-preserving gene-expression features where available. |
| DDInter | Curated known-pair evidence and negative-sampling exclusion. If later used for supervision, add a source-specific auxiliary objective with explicit unknown masks; do not label every unlisted pair negative or merge its labels silently with TWOSIDES. |
| FAERS | Reporting-coverage/bias audit and its separately defined severity tasks. Do not use FAERS pair reports as DDI inputs/labels for a TWOSIDES target without a documented overlap audit, because the sources can share reporting evidence. |

The seven-branch feature bundle is expected to hold the five prepared profile/biology branches; the molecular graph and Morgan fingerprint are generated from mapped structures. Verify the bundle manifest lists `drug_profile`, `adverse_event`, `protein_target`, `pdb_structure`, and `gene_expression`, with hashes, source provenance, and nonzero coverage. The prior audit found limited PDB and gene-expression coverage; do not impute unavailable records as if observed. If raw LINCS/GEO or PDB files remain unavailable, document that the model uses only the prepared records currently in the bundle.

#### Candidate model improvement

1. Reproduce the current seven-input model on the strict-identity frozen splits and seed 42 for a 20-epoch pilot, after a Colab import preflight confirms PyTorch, PyG, and RDKit are available. Use S1-dev for checkpoint selection; retain the existing molecular graph, Morgan, and five feature branches.
2. Build a new, separately named candidate with availability-aware modality gating, feature-mask input, and modality dropout. Fuse both drug embeddings using symmetric pair terms such as `hA + hB`, `abs(hA - hB)`, and `hA * hB`. Consider cross-modal contrastive alignment only as an ablation, so its added complexity can be tested rather than assumed to help.
3. Keep TWOSIDES as the main DDI objective. Evaluate a DDInter auxiliary/source-specific objective only as a separate experiment with source labels and unknown masks. Any graph of known DDI edges used as input must be rebuilt using training edges only within each split.
4. Compare the current seven-branch model and each new candidate on the same fixed train, development, post-hoc, S1, S2, and transductive splits. Report graph-only and Morgan baselines as references; do not require weaker baselines to reach the proposed model's score.
5. Proceed to a fresh 200-epoch study only if the 20-epoch run is healthy and S1-dev learning/metrics justify it. Use a new study ID, then repeat selected settings across the planned five seeds. Do not use S1-test or S2-test to choose epochs, features, thresholds, or model variants.

#### Leakage, overfitting, and success checks

- Resolve and freeze identity mappings before generating splits; keep ambiguous/provisional identities excluded in the primary strict cohort and report the sensitivity cohort separately.
- Keep unordered pair duplicates and reverse pairs in a single split. For cold-start splits, verify that held-out drugs and all pair-derived features do not enter training.
- Fit feature scaling, vocabularies, calibration, thresholds, and model selection on training/development partitions only. Record source dates and hashes; exclude label-derived or post-cutoff features.
- Track training loss and S1-dev/validation performance by epoch. Use early stopping and multiple seeds; diagnose underfit/overfit from curves and split-specific errors instead of extending epochs automatically.
- Report accuracy alongside balanced accuracy, AUROC, average precision, MCC, F1, sensitivity, specificity, Brier score, ECE, confidence intervals, and modality coverage. Primary success is a reproducible S1 improvement without material S2/transductive regression, not an accuracy threshold manufactured by threshold tuning.
- A 90–98% accuracy target is an aspiration, not a guaranteed acceptance criterion. If frozen held-out scores do not reach it, report the measured performance and limitations honestly.

**Status:** This is the agreed improvement route. The architecture, auxiliary source losses, and modality-gating/contrastive changes remain to be implemented and validated. The existing seven-branch run is not evidence that these upgrades have improved results.

### 6. Establish a controlled baseline and model comparisons

Use the existing `src/training/run_experiment_suite.py` for the registered suite. It contains these experiment families/configurations:

| Order | Model/configuration | Status in code | Purpose |
|---|---|---|---|
| 1 | ECFP/Morgan + logistic (`ecfp_sgd_logistic`) | Registered | Fast classical reference. |
| 2 | Legacy GAT, DDI-only (`legacy_gat_ddi_only`) | Registered | Existing graph baseline. |
| 3 | Edge-aware GATv2, DDI-only (`edge_aware_ddi_only`) | Registered | Primary graph baseline for fair comparisons. |
| 4 | Graph + fingerprint fusion (`graph_fp_fusion_ddi_only`) | Registered | Tests whether fingerprints add value to the graph encoder. |
| 5 | Motif-aware and cross-attention graph variants | Registered | Optional architecture ablations after the core comparison. |
| 6 | Toxicity multitask variants | Removed from the DDI suite | Single-drug toxicity stays in its own workflow. |
| 7 | ChEMBL-pretrained edge-aware GATv2 (`edge_aware_chembl_pretrained_ddi_only`) | Registered | Measures transfer from molecular pretraining without toxicity inputs. |
| 8 | AuditDDI memory-fusion model | Architecture code exists; not registered in the current experiment suite | Register and evaluate it only as a new DDI candidate with matched splits. |
| 9 | Current seven-branch multimodal model | Code and feature bundle exist; README says pilot/full validation remain | Main proposed model; only compare after inputs and splits are aligned with the reference. |

- [ ] Begin with the strict-identity one-seed comparison on seed 42, selecting checkpoints on pair-disjoint S1-dev data. Compare ECFP logistic, edge-aware GATv2, and the proposed seven-input model for up to 200 neural epochs. Do not report this pilot as final multi-seed evidence.
- [ ] Compare every candidate on the same frozen pair tables, S1-dev selection/post-hoc partitions, and untouched S1/S2/transductive test splits. Confirm the saved run's model name, labels, features, commit, and manifests.
- [ ] Run the **paper** preset only for selected comparable experiments. The suite's default paper seeds are 11, 23, 37, 53, and 71, with 200 epochs. Confirm runtime budget and completed artifacts before launching all five.
- [x] Keep toxicity prediction separate from DDI: the DDI model uses interaction labels and molecular/biological features; the single-drug toxicity workflow remains independent.
- [ ] Record failures and incomplete Colab sessions. Resume from a verified checkpoint only when its manifest/configuration match the run.

**Important code-status distinction:** Random Forest, a standalone fingerprint MLP, and Graph Transformer are not listed as registered suite experiments in the reviewed plan/code. Treat them as **new work**, not models already evaluated. The nearest-neighbor memory component exists in AuditDDI memory-fusion code, but a **standalone Morgan/Tanimoto interaction-neighbor baseline must be verified/implemented and evaluated as its own runner** before claiming that comparison is done.

### 7. Evaluate the nearest-neighbor cold-start baseline

- [ ] Use Morgan/ECFP fingerprints and Tanimoto similarity to find training drugs chemically similar to each query drug.
- [ ] Define a transparent pair score from neighbors' training interaction evidence. Exclude the query pair and all validation/test evidence from the memory.
- [ ] Choose neighbor count `k` and any similarity threshold on validation only; freeze them before final test.
- [ ] Report S1/S2/transductive metrics and **coverage**: fraction of test drugs/pairs with adequate similarity support. Include unsupported-pair behavior rather than hiding it.
- [ ] Compare the standalone method to the existing memory-fusion model; they are distinct experiments.

**Output:** reproducible nearest-neighbor evaluator, settings, predictions, metrics, and support-coverage table.

### 8. Run feature ablations and pretraining comparison

- [ ] On identical splits and seeds, compare graph-only, fingerprint-only, graph+fingerprint, then one biological/profile feature group at a time, then the selected full feature set.
- [ ] Verify each feature branch's mapping coverage and missingness on the held-out drugs. Remove a feature if it creates leakage or unreliable identity matches.
- [ ] Compare the DDI model with and without the ChEMBL-pretrained encoder under the same data/split settings.
- [ ] Keep ChEMBL pretraining separate in the report: it is self-supervised molecular encoder training, not additional supervised DDI labels.

**Output:** ablation table, coverage table, and pretraining comparison with matched run manifests.

### 9. Optional new model and ensemble work

- [ ] Only if the core comparisons show a gap worth addressing, add Random Forest or a standalone fingerprint MLP as extra baselines. Add a Graph Transformer only with a clear hypothesis and enough Colab compute budget.
- [ ] First inspect standalone model errors on validation. Combine models only if their errors are complementary.
- [ ] Fit probability calibration and ensemble weights on validation predictions only. Keep the current ensemble script for compatible repeated runs; mixing different model families may need a separate, audited probability-ensemble runner.
- [ ] Retain an ensemble only if it improves the primary S1 result robustly and does not substantially harm S2 or other regimes.

**Output:** an optional new-model/ensemble report. These are not prerequisites for a valid first comparison.

### 10. Metrics and final report

Report every metric separately for transductive, S1, S2, and scaffold-disjoint (if used):

| Metric | Reporting use |
|---|---|
| AUROC | Threshold-independent ranking; interpret with class balance. |
| Average precision / PR-AUC | Positive-class ranking under imbalance. State the exact implementation. |
| MCC | Balanced summary of all confusion-matrix outcomes. |
| F1, precision, recall/sensitivity, specificity | Thresholded performance. Select threshold on validation and report it. |
| Balanced accuracy and accuracy | Include both; do not select a winner using accuracy alone. |
| Brier score and ECE | Probability calibration; lower is generally better. Define bins/calibration procedure. |
| False-positive and false-negative rates | Explain error trade-offs on the sampled-label task. |

- [ ] For the final candidates, report mean and variation across the five fixed seeds; add confidence intervals with a stated method.
- [ ] Include counts, positive prevalence, runtime, GPU/memory, failed runs, feature coverage, and nearest-neighbor support coverage.
- [ ] Make clear that performance predicts the project's reported-vs-sampled-unreported labels, not clinical safety or causal interaction.
- [ ] Archive exact predictions, metrics, code revision, manifests, split files, feature hashes, and selected checkpoint.

### 11. Checkpoint review and backend API

- [ ] Select a checkpoint using the predeclared validation process and final held-out comparisons. Review its data/split/model manifest and hash-matched feature bundle.
- [ ] Do not use the existing backend checkpoint merely because it is present; first identify its producing run and verify its compatibility with the app's expected architecture.
- [ ] Copy the reviewed checkpoint and exact feature bundle to `demo_artifacts/` using the filenames/configuration in README. Preserve provenance and licensing notes.
- [ ] Recreate the local Python environment from requirements if local execution is needed; run the project's tests and backend API smoke checks before demonstration.
- [ ] After the backend API contract is confirmed, design and build a replacement frontend as a separate work item. The old `frontend/` has been deliberately removed, so browser UI deployment is unavailable until then.
- [ ] Label the app clearly as a research prototype. Do not present scores as medical advice.

## Independent workstream: drug toxicity and severity

Keep this workstream separate from the TWOSIDES binary DDI classifier. The current FAERS targets measure the fraction of submitted reports that contain a severe outcome; they do not estimate a drug's causal toxicity risk, patient incidence, or the safety of a drug. Keep the rule-based alerts in `src/data_prep/admet_engine.py` separate as well.

### Current toxicity work in the project

| Task | Existing work | Status/limitation |
|---|---|---|
| Single-drug FAERS severity | ECFP6 + ExtraTrees, repeated scaffold splits; training-mean baseline. A fallback ECFP6 MLP pilot and beta-binomial comparison are also present. | ExtraTrees was near the constant baseline. The fallback MLP was weak/inconsistent. The five-seed beta-binomial comparison on the same 1,067-structure cohort was worse than both its mean baseline and ExtraTrees. No current chemistry-only single-drug model has a useful validated signal. |
| FAERS pair severity | ECFP6 pair representation + ExtraTrees; weighted-mean baseline; repeated cold-drug splits; implementation in `src/training/train_faers_pair_severity.py`. | Five repeated partitions of the same Q2 2026 cohort modestly favored ExtraTrees. They are not independent temporal validation. |
| ADMET toxicology alerts | Structure-based/rule-based alerts in `src/data_prep/admet_engine.py`. | A heuristic screening aid, not a trained predictor or clinical risk estimate. Evaluate and label separately. |

### Toxicity plan checklist

#### T1. Freeze the single-drug cohort and target

- [ ] Select one FAERS cohort and its mapping bridge. Do not compare the target-prioritized 1,067-structure cohort with the fallback 653-structure cohort as though they were the same dataset.
- [ ] Preserve severe report count `k`, total eligible report count `n`, canonical structure, drug-name aliases, quarter, and mapping provenance. Prefer exact counts over reconstructing `k` from a rounded fraction.
- [ ] Review conflicting alias-level scores and denominator rules. Do not sum report counts across aliases unless the deduplication method proves the reports are distinct.
- [ ] Define the target explicitly as `severe_reports / eligible_reports` within the named FAERS quarter and severity definition.

**Output:** frozen drug-level table, mapping/denominator audit, and cohort manifest.

#### T2. Reproduce and compare single-drug models

- [ ] Reproduce the existing ECFP6 + ExtraTrees pilot and training-mean baseline on the chosen cohort and the exact repeated scaffold splits.
- [x] Ran `scripts/train_single_drug_toxicity_beta_binomial.py` on the 1,067 singleton-structure cohort after excluding 125 structures with conflicting alias labels. Reconstructed integer severe counts from `toxicity_score × n_reports` with maximum rounding error below 5e-13. The historical run is under `MyDrive/AuditDDI/runs/single_drug_faers_severity/beta_binomial_2026q2_run1/`; new runs go under `MyDrive/Projects/auditddi/results/pillars/single_drug_toxicity/`. The beta-binomial model did not improve MAE/RMSE over the training-mean or ExtraTrees references.
- [ ] Compare the existing MLP only if its input cohort and split definitions match. If the fallback cohort is retained, report it as a separate experiment.
- [ ] Select any model settings using validation only; do not tune on held-out scaffold test folds.
- [ ] Report MAE, RMSE, R², Spearman, and appropriate uncertainty across the same seeds. Include the mean baseline and prediction plots. Avoid treating tiny metric changes as a useful gain.

**Output:** matched-cohort, matched-split comparison table and predictions.

#### T3. Reproduce and strengthen pair-severity evaluation

- [ ] Reproduce `src/training/train_faers_pair_severity.py` with the documented Q2 2026 source table, report-count threshold, cold-drug split, and repeated seeds.
- [ ] Report MAE, RMSE, R², Spearman, and square-root-report-weighted MAE against the weighted-mean comparator. Record test pair/drug counts and cross-group pairs excluded.
- [ ] Seek a later, independent FAERS quarter and apply the frozen mapping, severity definition, and model without tuning on that quarter. Treat it as a temporal test.
- [ ] If later-quarter data or consistent labels are unavailable, clearly state that this is repeated-split internal validation only.

**Output:** reproducible repeated-split table; later-quarter results if a compatible quarter is obtained.

#### T4. Decide whether there is a useful toxicity model

- [ ] Require stable improvement over a simple baseline on the same cohort and splits before making a predictive claim.
- [ ] Check robustness by report-count strata, mapping confidence, and scaffold/cold-drug setting. Describe FAERS reporting, exposure, and alias-mapping bias.
- [ ] Do not turn an observed report fraction into a calibrated clinical toxicity probability. Do not combine this score with DDI scores until both targets, units, and validation are clearly defined.
- [ ] Keep the model out of the app's clinical decision path unless it receives appropriate external/clinical validation and review.

**Output:** go/no-go decision and limitations statement. A result showing no useful signal is a valid outcome.

## Fourth product pillar: ADMET and property screening

ADMET is a single-drug property view covering **Absorption, Distribution, Metabolism, Excretion, and Toxicity**. The project has a calculation module, but this is not currently a validated end-to-end ADMET prediction product: no API route was found in the backend, and multiple outputs are formula- or rule-based estimates. Keep it separate from both FAERS report-fraction models and the DDI classifier.

### Existing module outputs

- Physicochemical descriptors, including molecular weight, LogP, TPSA, hydrogen-bond counts, rotatable bonds, aromatic rings, and fraction Csp3.
- Rule-of-five/Veber flags and simple absorption/permeability categories.
- Estimated distribution values such as plasma unbound fraction and a BBB-permeability approximation.
- Estimated CYP profile and a simple predicted clearance route.
- Structural toxicophore alerts, including hERG/hepatotoxicity-related alerts, plus a heuristic danger score/level and guardrail status.

These outputs must be presented as **computed descriptors, heuristics, or unvalidated estimates** according to how each is produced. In particular, do not label the heuristic danger score as clinical toxicity risk, do not imply the CYP scores are measured enzyme results, and do not present a passed physicochemical guardrail as proof of safety.

### ADMET checklist

- [ ] Audit every response field in `src/data_prep/admet_engine.py`; record its formula/rule, units, dependencies (for example RDKit), failure behavior, and intended interpretation.
- [ ] Separate directly calculated molecular descriptors from heuristic property estimates and structural-alert matches. Include an explicit source/method field in API responses.
- [ ] Add unit/edge-case tests for valid structures, salts, invalid SMILES, unsupported chemistry, and out-of-domain inputs; preserve the engine's abstain/guardrail behavior.
- [ ] Define and implement a backend endpoint only after its request/response schema is agreed. Resolve input drugs through the shared canonical drug identity layer where possible; return the structure used and matching evidence.
- [ ] If making predictive claims, compare estimates against appropriate experimental ADMET reference data with drug/scaffold-disjoint evaluation. Report property-specific metrics and coverage; do not validate an entire ADMET panel using one score.
- [ ] In the new frontend, show one selected drug's property panel with units, method/evidence, status, and limitations. Distinguish “not computed,” “out of domain,” and “no alert matched”; none of those means safe.
- [ ] Keep the ADMET panel independent of DDI and FAERS-severity results. Link them through the same drug profile, not through a combined risk score.

**Output:** documented property semantics, backend API contract/implementation, tests, and an ADMET UI panel with appropriate caveats.

## Completion definition

The DDI study is ready to present when there is one chosen, provenance-complete data snapshot; audited drug identity mapping and labels; frozen splits with leakage reports; matched baseline and proposed-model runs; S1/S2 and other split metrics with repeated seeds and uncertainty; documented ablations/nearest-neighbor results; and a reviewed checkpoint paired with its exact input bundle. The toxicity study is ready to present only when its cohort and report-fraction target are audited, single-drug and/or pair-severity models are compared to the same-cohort baselines, and limitations plus temporal-validation status are reported. The ADMET feature is ready to present when each output's method and units are documented, invalid/out-of-domain behavior is tested, and the API/UI clearly distinguish calculated properties from heuristics or validated predictions. Keep these as separate outputs; do not merge their labels or scores into one risk model. Until complete, describe the DDI and toxicity models as research under evaluation and ADMET outputs as calculations/heuristics unless validated.
