# AuditDDI Methodology and End-to-End Workflow

> **Current execution setup:** Colab is used for project work and data preparation. Kaggle is used only for model training. Both use the GitHub repository for code and the logical Drive folder `MyDrive/Projects/auditddi`; Colab accesses it at `/content/drive/MyDrive/Projects/auditddi`, while Kaggle uses its linked mount path in `AUDITDDI_DATA_BASE`. See [EXECUTION_ENVIRONMENT_GUIDE.md](EXECUTION_ENVIRONMENT_GUIDE.md) for active notebook paths.
## 1. What the project does

AuditDDI is a research system for predicting whether a pair of drugs has a reported drug-drug interaction (DDI) association under transductive and cold-start evaluation.

The central prediction is **not** "this pair is clinically safe" versus "this pair is clinically harmful." The training label means:

- `1`: the pair was reported in TWOSIDES.
- `0`: the pair was not reported in the supplied TWOSIDES table and was sampled as an unreported pair.

An unreported pair is unknown, not proven safe. This distinction is essential when interpreting results.

The project has three execution environments:

| Part | Environment | Responsibility |
|---|---|---|
| Dataset linking, label preparation, audits, feature preparation | Google Colab | Prepare and validate inputs; do not fit models here |
| Model fitting | Kaggle | Train models using the prepared Drive inputs and save checkpoints/metrics |
| Application and deployment | Local machine / Docker | Load a reviewed checkpoint and serve predictions through the API and frontend |

The current finalized dataset set is exactly:

1. TWOSIDES
2. PubChem
3. ChEMBL (`chembl` folder; the user may refer to it as Chembel)
4. openFDA
5. FAERS
6. DDInter
7. PharmGKB

The current seven-source training configuration uses TWOSIDES-derived pair labels, PubChem structures, a ChEMBL-pretrained molecular encoder, and matched PharmGKB/openFDA drug-profile features. DDInter and FAERS retain their separate negative-pool and audit roles; they are not converted into TWOSIDES labels.

The preparation step also writes `pairwise_evidence_union.csv`: one row per
mapped drug pair, with separate TWOSIDES and DDInter presence flags, TWOSIDES
event-row counts, DDInter record/severity/description evidence, drug IDs,
structures, and identity-match statuses. This is an evidence inventory, not a
merged binary training table. A missing source flag means “not found in that
source,” not a confirmed negative. Keep the source labels separate unless a
controlled source-aware training experiment improves results on the same held-
out splits.

## 2. Project locations

The logical Drive layout is shared across environments; Colab uses this path:

```text
/content/drive/MyDrive/Projects/auditddi/
├── twosides/
├── pubchem/
├── chembl/
├── openfda/
├── faers/
├── ddinter/
├── pharmgkb/
├── processed/
├── results/
└── checkpoints/
```

The source-code checkout is:

```text
GitHub checkout (pulled into Colab for preparation and Kaggle for training)
├── src/
├── scripts/
├── backend/
├── frontend/
└── tests/
```

Colab preparation uses `/content/drive/MyDrive/Projects/auditddi`. Kaggle training reads the linked data root through `AUDITDDI_DATA_BASE` and writes run artifacts through `AUDITDDI_RESULTS_BASE`.

## 3. Dataset roles

### 3.1 TWOSIDES: primary supervised signal

The raw TWOSIDES file in this project has columns similar to:

```text
drug_1_rxnorm_id
drug_1_concept_name
drug_2_rxnorm_id
drug_2_concept_name
condition_meddra_id
condition_concept_name
A, B, C, D
PRR
PRR_error
mean_reporting_frequency
```

Each row describes a drug pair and an adverse-event condition. `condition_concept_name` becomes the event or interaction type used by the training table.

The raw file contains drug names and identifiers, not molecular graphs. Your
Drive already contains the audited preparation:

```text
processed/twosides_v1/twosides_clean.parquet
processed/twosides_v1/drugs_clean.csv
```

The parquet stores `drug_a`/`drug_b` catalogue indices and event/reporting
statistics. The catalogue maps each index to canonical SMILES. The updated
trainer reads this parquet/catalogue pair first and converts indices to the
pair format used internally. The older
`twosides/drug_drug_edges.csv` remains a fallback for legacy projects only.

### 3.2 PubChem: identity and structure bridge

PubChem supplies canonical molecular structures and identity resolution. Its output is used to turn drug names into canonical SMILES. Those SMILES are then converted into molecular graphs and Morgan fingerprints when a fingerprint model is selected.

PubChem records are not independently treated as positive or negative DDI labels.

### 3.3 ChEMBL: chemical structure corpus

The supplied ChEMBL `chemreps` file contains molecule structures. The supplied UniProt-to-ChEMBL target list is target metadata; it does not link individual molecules to targets or report molecule-target activity. Do not create drug-target features from those two files. In the current seven-source run, ChEMBL structures support a separate molecular encoder-pretraining stage; they do not provide supervised DDI labels or drug-target profile features.

### 3.4 openFDA: regulatory evidence

openFDA provides drug-label and pharmacokinetic evidence. The prepared source bundle matches available records to the common PubChem drug identity and contributes label-derived features to the 51-dimensional PharmGKB/openFDA drug profile. Label mentions are not treated as confirmed DDI labels.

### 3.5 FAERS: pharmacovigilance evidence

FAERS provides suspected adverse-event reports, not confirmed causal drug effects or DDI labels. The current audit resolved 764,472 of 1,627,222 Q2 2026 DRUG rows to one of the TWOSIDES PubChem CIDs. This is report-row coverage, not causal evidence. Any safety feature or auxiliary target needs a temporal and reporting-bias review before use in DDI training.

### 3.6 DDInter: curated interaction evidence

The current name-to-PubChem audit resolves 79,057 distinct DDInter pairs. Of these, 34,191 also occur in mapped TWOSIDES pairs and 44,866 do not. Overlapping pairs cannot count as independent external test examples. Any reserved DDInter test pair must also be removed from TWOSIDES training. DDInter does not provide confirmed safe negatives: an unlisted pair is unknown. These counts are a mapping audit, not model evaluation.

### 3.7 PharmGKB: pharmacogenomic evidence

PharmGKB relationships include many entity types. Only the prepared, matched drug-gene evidence contributes to the source profile; other relationship rows are not treated as drug evidence. Matching and coverage are recorded in the source-bundle manifest and audit outputs.

### Current seven-source readiness

The selected seven-source configuration is `auditddi_multimodal_v1`. Its roles
are intentionally different: TWOSIDES supplies supervised pair labels;
PubChem supplies structures and the CID identity key; ChEMBL provides a
leakage-filtered encoder-pretraining corpus; PharmGKB and openFDA provide
audited per-drug profile features; FAERS provides coverage/reporting-bias
audits but its report counts are excluded from predictor features because
TWOSIDES is also pharmacovigilance-derived; DDInter positives are excluded
from the sampled-negative pool and retained as separately tagged evidence.
DDInter unlisted pairs are unknown. DDInter pairs are not silently turned into
safe negatives, and openFDA pairwise label mentions are not model features.

The retired feature-store builder targeted a prior DrugCentral/ChEMBL target
schema and has been removed. Use `scripts/prepare_auditddi_source_bundle.py`
for this Drive layout. The current trainer
uses the prepared TWOSIDES parquet/catalogue, the source bundle, and an
explicit ChEMBL-pretrained encoder; its run manifest records the inputs and
their source roles. The older study scripts with BindingDB, GEO, or PDB inputs
are not part of this finalized workflow.

## 4. Input preparation

### Step 1: use the prepared source audits

The identity audits already exist under `processed/auditddi_v1/`. The next
preparation command uses those audit tables and the prepared TWOSIDES parquet;
it does not rescan PubChem's synonym dump:

```bash
python scripts/prepare_auditddi_source_bundle.py \
  --data-root /content/drive/MyDrive/Projects/auditddi \
  --parse-openfda
```

It writes `processed/auditddi_v2/`, including CID-linked TWOSIDES/DDInter
pairs, PharmGKB and FAERS audit tables, openFDA CYP profile features, the
51-column drug-level profile matrix (FAERS report count slot is reserved and
zeroed), and a source manifest. Confirm the
manifest reports `openFDA.status = parsed` before choosing the seven-source
architecture.

### Step 2: select the primary raw source

The current primary training source is `TWOSIDES.csv.gz`. `OFFSIDES.csv.gz` is kept as a separate evidence source and is not silently merged into the primary training labels.

### Step 3: resolve drug identity to SMILES

For every unique `drug_1_concept_name` and `drug_2_concept_name`:

1. query or load the PubChem mapping;
2. obtain a molecular SMILES;
3. canonicalize it with RDKit;
4. record unresolved names instead of inventing structures.

### Step 4: use the prepared interaction table

The prepared parquet contains one row per reported pair-event association,
using integer drug indices. The catalogue supplies the SMILES for each index.
The updated trainer reads these artifacts directly and maps them into its
internal pair format (`interaction_type` is retained for source provenance,
while this binary trainer predicts whether the pair was reported):

```text
source,target
```

Duplicate pair-event records are collapsed by the training preparation code.
Drug order is canonicalized so A-B and B-A are one unordered pair. The old
name-based edge preparation script is only needed if the prepared parquet and
catalogue are missing.

### Step 5: validate molecular graphs

RDKit checks whether each SMILES can be represented as a molecular graph. Invalid SMILES, empty structures, counterion-only structures, and incompatible records are excluded and written to audit outputs. The pipeline does not silently replace invalid chemistry with dummy vectors.

## 5. Molecular representation

The default model uses the rich edge-aware molecular graph schema.

For each drug:

- nodes represent atoms;
- `x` contains atom features;
- `edge_index` contains directed graph connectivity for each chemical bond;
- `edge_attr` contains bond features;
- the graph is batched with PyTorch Geometric.

The rich atom representation has 44 features per atom, including:

- atom symbol with an explicit unknown bucket;
- degree;
- formal charge;
- hybridization;
- hydrogen count;
- chirality;
- aromaticity;
- ring membership.

The rich bond representation has 14 features per directed bond, including:

- bond type;
- bond stereo;
- conjugation;
- ring membership.

The graph is a 2D chemical topology representation. It is not a 3D molecular simulation.

## 6. Molecular graph encoder used by `auditddi_multimodal_v1`

The multimodal model uses an edge-aware GATv2 molecular encoder alongside the Morgan fingerprint encoder and the 51-feature drug-source-profile encoder. The graph encoder is shared between Drug A and Drug B.

### 6.1 Drug encoder

Drug A and drug B are encoded by the same shared EdgeAwareMolecularEncoder:

```text
Drug A graph -> GATv2 layer 1 -> ReLU -> GATv2 layer 2 -> ReLU -> mean pooling -> e_A
Drug B graph -> GATv2 layer 1 -> ReLU -> GATv2 layer 2 -> ReLU -> mean pooling -> e_B
```

The two GATv2 layers consume both atom features and bond features. Mean pooling converts the variable-size atom graph into one fixed-length drug vector.

The default hidden size is 128 in the training pipeline. The encoder uses two attention heads in the first GATv2 layer and one head in the second layer.

### 6.2 Pair fusion

The model must give the same result for A-B and B-A. Therefore it does not concatenate `[e_A, e_B]` in an order-sensitive way. Instead it constructs:

```text
sum        = e_A + e_B
absolute difference = |e_A - e_B|
product    = e_A * e_B
```

For the edge-aware architecture, the final pair representation is:

```text
[sum || absolute_difference || product]
```

where `||` means concatenation.

### 6.3 Risk head

The pair representation goes through:

```text
Linear(pair_dimension -> 64)
ReLU
Dropout(0.4)
Linear(64 -> 1)
```

The output is a raw interaction-risk logit. During evaluation and API prediction it is converted to a score with the sigmoid function.

### 6.4 Toxicity head

The shared drug embeddings also pass through a small auxiliary toxicity head. In the current DDI-only configuration:

```text
AUDITDDI_USE_TOXICITY_PAIR_FEATURES=false
AUDITDDI_TOXICITY_LOSS_WEIGHT=0.0
```

Therefore the toxicity bridge is not required for the default run and the toxicity task does not affect the DDI loss. The toxicity head remains in the versioned model code for compatibility and explicitly controlled ablations.

A toxicity-enabled run must use a real validated bridge. A missing bridge must never be replaced by fabricated labels.

## 7. Other implemented model architectures

The repository contains versioned alternatives. The selected seven-source run uses `auditddi_multimodal_v1`; the alternatives below are not automatically active in that run.

| Architecture | Main idea | Extra input |
|---|---|---|
| `legacy_gat_v1` | Original two-layer GAT molecular encoder | Atom graph features only |
| `edge_aware_gat_v2` | Edge-aware GATv2 molecular baseline | Rich molecular graph |
| `motif_edge_aware_gat_v1` | Edge-aware GNN plus learned fixed SMARTS motif counts | Molecular graph plus motif vector |
| `cross_attention_edge_aware_gat_v1` | Pair-isolated atom attention between drug A and drug B | Molecular graph and within-pair atom attention |
| `graph_fp_fusion_v1` | Edge-aware graph plus 1024-bit Morgan/ECFP6 projection | Molecular graph plus fingerprint |
| `auditddi_memory_fusion_v1` | Graph/fingerprint model plus auditable nearest-neighbor memory | Training-memory features |
| `auditddi_multimodal_v1` | Selected seven-source model; molecular graph/fingerprint plus audited per-drug feature fusion | PubChem structure; 51 PharmGKB/openFDA features; ChEMBL-pretrained encoder |
| `auditddi_ablation_genes` | Gene-feature ablation/fusion path | PharmGKB-style gene vectors |
| `auditddi_ablation_faers` | Legacy experimental code path; not used by the current workflow | Do not use for current source claims |

The final report must identify the exact architecture recorded in the run manifest. Do not describe an optional architecture as the final model unless that architecture was actually trained and evaluated.

## 8. Label construction

The positive table is created from reported TWOSIDES associations:

```text
source,target,label=1,label_evidence=reported_twosides
```

The system canonicalizes unordered pairs and removes duplicate observations. A contradiction, where the same unordered pair receives both labels, is rejected rather than resolved by row order.

### Negative labels

The pipeline samples unreported pairs from the same TWOSIDES drug universe:

```text
source,target,label=0,label_evidence=unreported_twosides_split_aware_sampled
```

The negative label means only that the pair was not reported in the supplied source. It does not mean non-interacting or safe.

The standard negative ratio is 1:1. With `degree_matched`, drugs with higher observed positive degree are sampled with higher probability, making the negative drug-degree distribution more comparable to the positive distribution.

Every known reported pair is forbidden from the negative pool, including reported pairs omitted by the configured data cap.

## 9. Data splitting and leakage prevention

The default split seed is 42 unless overridden. Pair order is canonicalized before splitting.

### 9.1 Identity groups

The splitter deterministically selects:

- `seen`: drug identities available during training;
- `s1_dev`: held-out drug identities for S1 development;
- `s1_test`: held-out drug identities for S1 testing.

### 9.2 Transductive split

Both drugs come from the seen group:

```text
transductive_train -> model fitting
validation          -> early stopping/model selection
transductive_test  -> final transductive evaluation
```

### 9.3 S1 cold-start split

Both drugs are unseen during training:

```text
S1-dev  = both drugs from s1_dev
S1-test = both drugs from s1_test
```

### 9.4 S2 cold-start split

Exactly one drug is unseen:

```text
S2-dev  = one s1_dev drug + one seen drug
S2-test = one s1_test drug + one seen drug
```

### 9.5 Negative sampling order

The important order is:

```text
1. choose drug-identity groups;
2. assign reported positive pairs to partitions;
3. sample unreported negatives inside each partition's identity geometry;
4. forbid all known reported pairs;
5. train and evaluate.
```

This avoids leaking identity information through negative sampling. Sampling negatives before defining S1/S2 would make the cold-start audit less trustworthy.

### 9.6 Validation roles

The original validation data are divided into a model-selection validation role and a reserved post-hoc validation role. The model-selection portion is used for epoch selection and early stopping. Reserved post-hoc rows are used later for threshold, calibration, and conformal decisions. This prevents threshold and calibration choices from selecting the model itself.

A separate `scaffold_disjoint` protocol exists for chemical scaffold holdout. It is a different experiment and must not be mixed with standard transductive/S1/S2 results.

## 10. Training configuration

The trainer defaults are shown below. The five-seed journal workflow overrides the model seed for each run and selects `auditddi_multimodal_v1`; run manifests are authoritative for actual settings:

| Setting | Default |
|---|---:|
| Architecture | `edge_aware_gat_v2` unless explicitly set to `auditddi_multimodal_v1` |
| Hidden channels | 128 |
| Maximum epochs | 200 |
| Minimum epochs before early stopping | 40 |
| Early stopping patience | 30 |
| Batch size | 128 |
| Data cap | 200,000 rows |
| Model seed | 42 |
| Split seed | 42 |
| Negative sampling protocol | `split_aware_standard_v1` |
| Negative sampling strategy | `degree_matched` |
| Negative ratio | 1:1 |
| Toxicity pair features | disabled |
| Toxicity loss weight | 0.0 |
| Optimizer | Adam |
| Initial learning rate | 0.001 |
| Weight decay | 0.0001 |
| Scheduler | StepLR, step size 20, gamma 0.7 |
| Device | CUDA when available, otherwise CPU |

The binary DDI objective is `BCEWithLogitsLoss`. The model trains on raw logits; sigmoid is used for probability-like prediction scores after the forward pass. When the optional toxicity objective is enabled, the toxicity labels use a separate BCE-with-logits contribution weighted by `AUDITDDI_TOXICITY_LOSS_WEIGHT`.

Training uses deterministic seeds for Python, NumPy, PyTorch, and CUDA where supported. CuDNN deterministic behavior is enabled and nondeterministic algorithms are configured to warn rather than silently fail.

## 11. Training workflow

### 11.1 Historical Colab training instructions (superseded)

Run this after applying the updated project files to `/content/auditddi`,
mounting Drive, installing `requirements_colab.txt`, and completing the source
bundle step above. The pretraining and DDI training checkpoints are saved to
Drive so Colab runtime loss does not remove them.

```python
from pathlib import Path
import os

%cd /content/auditddi
data_root = Path('/content/drive/MyDrive/Projects/auditddi')
checkpoint = data_root / 'checkpoints' / 'chembl_pretrained_encoder.pt'
checkpoint.parent.mkdir(parents=True, exist_ok=True)

os.environ['AUDITDDI_DATA_BASE'] = str(data_root)
os.environ['AUDITDDI_RESULTS_BASE'] = str(data_root / 'results')
os.environ['AUDITDDI_PRETRAIN_CHECKPOINT_PATH'] = str(checkpoint)
os.environ['AUDITDDI_PRETRAINED_ENCODER_PATH'] = str(checkpoint)
os.environ['AUDITDDI_MODEL_ARCHITECTURE'] = 'auditddi_multimodal_v1'
```

First build the source-linked drug profiles. The openFDA pass reads the bulk
label archives and may take a while:

```bash
python scripts/prepare_auditddi_source_bundle.py \
  --data-root /content/drive/MyDrive/Projects/auditddi \
  --parse-openfda
```

Then pretrain the molecular encoder on ChEMBL and fine-tune/evaluate the
multimodal DDI model:

```bash
python src/training/pretrain_chembl_encoder.py
python src/training/train_full_pipeline_v2.py
```

The training script refuses the seven-source architecture if the bundle lacks
parsed openFDA features, matched PharmGKB/FAERS data, the DDInter mapped-pair
file, or a ChEMBL-pretrained checkpoint. It records the 51 source-profile
columns in the run manifest and embeds their CID/SMILES lookup in the
checkpoint for local API inference. Share `processed/auditddi_v2/source_bundle_manifest.json`,
the ChEMBL `pretraining_split_audit.json`, and the newest training
`run_manifest.json` plus `metrics.json` after the commands finish.

The complete training run is:

```text
processed/twosides_v1/twosides_clean.parquet
        + processed/twosides_v1/drugs_clean.csv
        |
        v
integer drug indices -> canonical SMILES
        |
        v
SMILES validation and positive-pair audit
        |
        v
unordered-pair deduplication
        |
        v
identity-aware positive splits
        |
        v
split-aware degree-matched negative sampling
        |
        v
PyG molecular graph construction
        |
        v
GATv2 pair model
        |
        v
BCE-with-logits optimization
        |
        v
validation checkpoint selection and early stopping
        |
        v
transductive / S1 / S2 evaluation
        |
        v
metrics, predictions, audits, checkpoint, and manifest
```

Each run writes an artifact directory containing a run manifest, environment details, input hashes, split audits, training history, checkpoint metadata, prediction tables, metrics, and figures. The artifact is the reproducibility record for that run.

## 12. What is measured

### Primary metrics

- **AUROC**: ranking quality across thresholds;
- **average precision / PR-AUC**: ranking quality that is more informative under class imbalance;
- **MCC**: balanced correlation between predictions and labels;
- **Brier score**: squared probability error;
- **ECE**: expected calibration error.

### Threshold metrics

The run also reports:

- F1 score;
- precision;
- recall/sensitivity;
- specificity;
- negative predictive value;
- false-positive rate;
- false-negative rate;
- balanced accuracy;
- ordinary accuracy.

Ordinary accuracy is not a clinical safety claim because the zero class is sampled unreported data.

### Reliability and cold-start audit outputs

The run also records:

- transductive, S1, and S2 performance separately;
- bootstrap confidence intervals;
- calibration diagnostics;
- conformal prediction coverage and abstention results;
- performance by structural similarity to training drugs;
- false-positive and false-negative examples;
- inference throughput and peak CUDA memory;
- exact split membership and hashes;
- input and checkpoint SHA-256 hashes.

A nominal 90% conformal rule must be checked separately on transductive, S1, and S2 data. Coverage on an easy transductive split must not be presented as cold-start coverage.

## 13. Prediction process

### 13.1 Offline prediction

For an evaluation pair:

1. read the two canonical SMILES;
2. construct two molecular graphs using the checkpoint's recorded feature schema;
3. run both graphs through the shared encoder;
4. create the symmetric pair representation;
5. compute the raw risk logit;
6. apply sigmoid to obtain the raw score;
7. apply saved calibration if the checkpoint contains calibration state;
8. compare the resulting score with the saved decision threshold;
9. write the prediction row and evidence metadata.

The prediction file stores raw and calibrated scores, threshold, predicted label, calibration status, and label evidence.

### 13.2 Local API prediction

The local backend:

1. loads the selected checkpoint from `backend/checkpoints/`;
2. validates the checkpoint metadata and molecular feature schema;
3. constructs graphs from submitted SMILES;
4. runs CPU inference by default in the service container;
5. returns a research-only score, risk category, model metadata, and warnings.

The API does not retrain the model. It uses a reviewed checkpoint produced by model training. A new Kaggle checkpoint must be reviewed before replacing the deployed checkpoint.

The API accepts a drug pair, not patient-linked training data. It rejects unknown fields and patient-context fields. It must not be described as a clinical decision system.

## 14. What happens during local deployment

The deployment boundary is:

```text
Colab:
  datasets -> preprocessing -> training -> checkpoint + evidence

Local:
  reviewed checkpoint -> FastAPI backend -> frontend
```

Docker Compose starts:

- backend API on `127.0.0.1:8000`;
- frontend on `localhost:3000`;
- frontend same-origin `/api` requests proxied to the private backend.

The container mounts the reviewed checkpoint directory read-only. Training data and Colab artifacts are not required for normal API inference.

## 15. How to explain the project in a viva

A concise explanation is:

> AuditDDI predicts reported drug-pair interaction associations from molecular structure. I convert each drug SMILES into an atom-bond graph, encode both drugs with a shared edge-aware GATv2 encoder, combine their embeddings using order-independent sum, absolute difference, and product features, and classify the pair with a binary risk head. Positive pairs come from reported TWOSIDES associations, while negatives are split-aware sampled unreported pairs and are not known-safe labels. I evaluate transductive performance and cold-start S1/S2 performance, where S1 holds out both drugs and S2 holds out one drug. Data preparation happens in Colab; model training happens in Kaggle with the configured accelerator, and the reviewed Kaggle checkpoint is deployed locally through FastAPI and Docker.

The most important limitations to state are:

1. TWOSIDES is observational pharmacovigilance evidence, not complete ground truth.
2. An unreported pair is unknown, not safe.
3. S1/S2 results may be much weaker than transductive results.
4. Internal validation metrics are not clinical validation.
5. The deployed API is research-only and does not replace medical review.
