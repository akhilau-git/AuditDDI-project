# AuditDDI Dataset Catalog

## 1. Source linking scope and run status

The planned cross-source linking scope contains nine source families:

1. TWOSIDES
2. PubChem
3. ChEMBL
4. openFDA
5. FAERS
6. DDInter
7. PharmGKB
8. LINCS/GEO
9. PDB/RCSB

This is the linking scope, not a claim that every source is currently present or ready for training. Earlier audited DDI runs used the seven-source core through PharmGKB; LINCS/GEO and PDB/RCSB require separate file, license, identity, and coverage checks before they can enter a model run. Do not infer current availability from code or this catalog. Inventory the current Google Drive snapshot before processing.

UniProt, BindingDB, DrugCentral, RxNorm, KEGG, DailyMed, DrugBank, and Medi-Span are not part of this nine-source scope. RxNorm IDs may still occur in TWOSIDES and be used as mapping evidence.

Some source-code modules still contain optional or historical support for those sources. A module existing in the repository does not mean that its dataset was used in the final training run.

## 2. Current storage layout

The Google Drive project folder is:

```text
MyDrive/Projects/auditddi/
```

The expected source folders are:

```text
MyDrive/Projects/auditddi/
├── twosides/
├── pubchem/
├── chembl/
├── openfda/
├── faers/
├── ddinter/
├── pharmgkb/
├── lincs_geo/  (or lincs/ and geo/)
└── pdb_rcsb/   (or pdb/)
```

The local Git checkout (`D:\AuditDDI`, pushed through GitHub) contains the code. Colab pulls it for data preparation and uses `/content/drive/MyDrive/Projects/auditddi`. Kaggle pulls the same repository for model training; set `AUDITDDI_DATA_BASE` to the Kaggle-visible mount path for that same Drive folder.
## 3. Dataset summary table

The counts below describe the project’s recorded source snapshot and intended coverage. Exact counts can change when a different release or filtered export is used. Every training run records input paths, hashes, and row counts in its run artifacts; those run-specific values are authoritative for a final result table.

| Dataset | Main data type | Main role | Known project coverage / size | Used as primary DDI labels? |
|---|---|---|---|---|
| TWOSIDES | Drug-pair adverse-event associations | Primary supervised signal | About 4,649,441 pair-event rows, 645 drugs, 63,473 unordered positive pairs, and 1,317 event types in the recorded project snapshot | Yes |
| PubChem | Compound identity and molecular structure records | Name/identifier-to-SMILES bridge | Used to resolve the project drug catalog; the recorded catalog covers about 645 TWOSIDES drugs | No; structures are model inputs, not DDI labels |
| ChEMBL | Molecular structures | Separate molecular-encoder pretraining; pretrained weights initialize the DDI graph encoder | Exact structures and counts are recorded in the pretraining manifest | No |
| openFDA | Drug-label/regulatory evidence | Matched with PubChem drug identity and contributes to the 51-dimensional source profile | Exact coverage is recorded in `source_bundle_manifest.json` | No |
| FAERS | Pharmacovigilance adverse-event reports | Reporting-coverage and reporting-bias audit; report counts are excluded from this DDI model input | Release-dependent; use the run/source manifest for the exact snapshot | No |
| DDInter | Curated drug-pair interaction records | Known mapped pairs are excluded from the sampled-negative pool | Exact mapped pair count is recorded in `source_bundle_manifest.json` | No; not a positive-label source in this run |
| PharmGKB | Drug-gene/pharmacogenomic records | Matched through drug identity and combined with openFDA evidence in the existing source profile | Exact coverage is recorded in `source_bundle_manifest.json` | No |
| LINCS/GEO | Drug perturbation expression data and GEO studies | Use verified drug perturbation signatures with cell, dose, duration, and study context; disease-only GEO signatures are not drug features | Must be inventoried and mapped for the current snapshot | No |
| PDB/RCSB | Protein structures and ligand records | Use verified ligand-bound structures; map ligand and protein target separately before deriving pocket descriptors | Must be inventoried and mapped for the current snapshot | No |

For the earlier seven-source-core DDI configuration, the per-drug model inputs are a
44-feature-per-atom/14-feature-per-bond molecular graph, a 1,024-bit Morgan
fingerprint (radius 2), and a 51-dimensional PharmGKB/openFDA profile. TWOSIDES
provides the supervised pair labels. The source tables are not concatenated
into a single training table; each source enters through its defined identity,
pair-exclusion, pretraining, feature-profile, or audit role.

`prepare_auditddi_source_bundle.py` also emits
`processed/auditddi_v2/pairwise_evidence_union.csv`, which harmonizes the
TWOSIDES and DDInter pair identities while retaining a separate presence flag
and source evidence for each. It is not a binary training-label file: absence
from a source means unknown, and the two sources retain different label
semantics.

The words `about`, `roughly`, and `recorded` are intentional: source releases, filters, and mappings can change counts. Do not claim a precise count for a new run unless it is read from that run’s manifest.

## 4. TWOSIDES

### 4.1 What it contains

TWOSIDES is a pharmacovigilance dataset derived from drug-event reporting. Each record describes:

- drug 1 identifier and concept name;
- drug 2 identifier and concept name;
- adverse-event condition identifier and concept name;
- reporting-count fields such as `A`, `B`, `C`, and `D`;
- disproportionality statistics such as `PRR`, `PRR_error`, and `mean_reporting_frequency`.

The raw project file is:

```text
twosides/TWOSIDES.csv.gz
```

The project also stores:

```text
twosides/OFFSIDES.csv.gz
```

OFFSIDES is kept as a separate source/evidence file. It is not silently merged into the primary TWOSIDES training labels.

### 4.2 Raw input format

The raw TWOSIDES file used in the current preparation workflow contains columns such as:

```text
drug_1_rxnorm_id
drug_1_concept_name
drug_2_rxnorm_id
drug_2_concept_name
condition_meddra_id
condition_concept_name
A
B
C
D
PRR
PRR_error
mean_reporting_frequency
```

### 4.3 Prepared training format

The graph training pipeline does not consume the raw RxNorm-name table directly. It consumes a prepared file:

```text
twosides/drug_drug_edges.csv
```

with columns:

```text
source,target,interaction_type
```

Here:

- `source` is the canonical SMILES for drug 1;
- `target` is the canonical SMILES for drug 2;
- `interaction_type` is the normalized adverse-event/condition name.

### 4.4 How TWOSIDES becomes labels

A reported pair-event association becomes positive evidence:

```text
label = 1
label_evidence = reported_twosides
```

The training pipeline canonicalizes pair order and removes duplicate unordered observations. A pair A-B is the same pair as B-A.

TWOSIDES absence is not a negative clinical finding. For binary training, the pipeline samples unreported drug pairs and records them explicitly as sampled unreported examples:

```text
label = 0
label_evidence = unreported_twosides_split_aware_sampled
```

Therefore, a TWOSIDES negative is an unknown/unreported pair, not a confirmed safe pair.

### 4.5 Reproducible name-to-structure preparation

The prepared edge file is generated with
[`scripts/prepare_twosides_edges.py`](../scripts/prepare_twosides_edges.py).
The resolver queries PubChem by the TWOSIDES concept name and then falls back
to the source `drug_*_rxnorm_id` through PubChem's RxNorm cross-reference.
Lookups use bounded retries and a persistent JSON cache. Unresolved names are
written to an audit report and their rows are excluded; no structure is guessed
for products, mixtures, biological materials, or non-chemical concepts that
PubChem cannot resolve. The run summary must record at least the unique-name,
unresolved-name, written-row, and skipped-row counts.

## 5. PubChem

### 5.1 What it contains

PubChem contains chemical compound identity and structure information, including names, compound identifiers, and molecular representations such as SMILES.

### 5.2 How it is used

PubChem is used to map raw TWOSIDES drug concept names to molecular structures:

```text
TWOSIDES drug name -> PubChem lookup -> SMILES -> RDKit canonical SMILES
```

The canonical SMILES is then used to build the molecular graph. PubChem does not supply the binary DDI label in this project.

### 5.3 Input type

The relevant input is a compound identity/name or identifier. The relevant model-preparation output is a valid canonical SMILES string, for example:

```text
CCO
```

Invalid or unresolved structures are audited and excluded rather than replaced with fake structures.

## 6. ChEMBL

### 6.1 What it contains

ChEMBL is a chemical and bioactivity resource. In this project it is relevant to chemical/target annotation and optional biological feature preparation.

### 6.2 How it is used

ChEMBL can produce drug-target mappings and related feature tables. These features are optional architecture inputs and are not part of the default `edge_aware_gat_v2` molecular-only candidate unless explicitly enabled in the run configuration.

### 6.3 Label semantics

A ChEMBL target or bioactivity record is not a DDI label. It describes chemical/biological evidence at the compound-target level.

## 7. openFDA

### 7.1 What it contains

openFDA provides FDA regulatory and Structured Product Label evidence. The project uses it for label/evidence parsing and optional pharmacokinetic or CYP-related feature blocks.

### 7.2 How it is used

openFDA information can be transformed into per-drug evidence or feature vectors. It is not treated as a pairwise positive or negative DDI table for the primary classifier.

### 7.3 Label semantics

An openFDA label mention is regulatory evidence. It is not automatically a confirmed interaction label and is not automatically a safe/non-safe decision.

## 8. FAERS

### 8.1 What it contains

FAERS contains spontaneous adverse-event reports. It can include report-level or aggregated pharmacovigilance information about drugs and adverse events.

### 8.2 How it is used

FAERS is retained as an evidence and auxiliary-toxicity source. It can be used in a separately identified ablation or toxicity analysis. It is not merged into the primary TWOSIDES DDI labels.

### 8.3 Important limitation

Spontaneous reports are subject to reporting bias, confounding, missingness, and lack of causal proof. A FAERS report is not by itself proof that a drug caused an interaction or adverse event.

## 9. DDInter

### 9.1 What it contains

DDInter is a curated interaction resource based on literature and clinical evidence. Records can include drug pairs, interaction categories, severity, and supporting evidence fields.

### 9.2 How it is used

DDInter is kept outside the primary supervised training labels and used for external agreement or transfer-style evaluation. This separation matters because using DDInter as hidden training supervision would make external evaluation invalid.

### 9.3 Label semantics

A DDInter record is curated interaction evidence. Lack of a DDInter record is unknown, not proof of no interaction.

## 10. PharmGKB

### 10.1 What it contains

PharmGKB contains pharmacogenomic relationships involving drugs, genes, enzymes, and related evidence.

### 10.2 How it is used

PharmGKB can produce per-drug gene/enzyme profiles. In optional multimodal or ablation architectures, these profiles can be encoded and fused with molecular graph representations.

In the default edge-aware molecular run, PharmGKB is not automatically a label source and does not change the TWOSIDES label definition.

## 11. Optional or out-of-scope sources

The following are excluded from the current finalized dataset contract:

| Excluded source | Reason |
|---|---|
| UniProt | Not a finalized standalone dataset for this project snapshot; any sequence artifacts must be treated as derived/optional artifacts |
| BindingDB | Deferred/optional affinity evidence, not required by the current final run |
| PDB/RCSB | In the nine-source linking scope, but not ready for model use until ligand and target identity plus coverage are audited |
| LINCS/GEO | In the nine-source linking scope; only context-verified drug perturbation signatures are eligible, not arbitrary disease expression |
| DrugCentral | Not in the nine-source scope |
| RxNorm | Raw TWOSIDES identifiers may be present, but RxNorm is not a separate finalized dataset source for this run |
| KEGG | Not in the finalized source list |
| DailyMed | Not in the finalized source list; regulatory evidence is represented through openFDA |
| DrugBank and Medi-Span | Excluded because of access, licensing, and redistribution constraints |

## 12. Source data versus derived artifacts

These are derived artifacts, not additional datasets:

- `drug_drug_edges.csv`;
- canonical SMILES tables;
- molecular graph objects;
- Morgan/ECFP fingerprints;
- split CSV files;
- feature stores;
- model-selection validation tables;
- calibration tables;
- conformal prediction artifacts;
- checkpoints and prediction files;
- run manifests and audit reports.

A derived artifact should always record its source path and, when possible, a SHA-256 hash.

## 13. Dataset-to-model flow

```text
TWOSIDES raw drug names and events
              |
              +-- PubChem identity/structure bridge
              |
              v
canonical drug SMILES and event edge table
              |
              v
RDKit molecular graphs
              |
              v
shared edge-aware GATv2 encoder
              |
              v
symmetric drug-pair representation
              |
              v
binary DDI-risk logit
              |
              v
transductive/S1/S2 metrics and local API checkpoint
```

The other finalized sources remain typed evidence or optional feature sources:

```text
ChEMBL     -> optional target/biological features
PharmGKB   -> optional gene/enzyme profiles
openFDA    -> regulatory/CYP evidence
FAERS      -> pharmacovigilance and toxicity ablation evidence
DDInter    -> external agreement/validation evidence
```

## 14. What to report in the thesis

For every experiment, report:

1. exact dataset release or file snapshot;
2. raw file names;
3. number of raw rows;
4. number of unique drugs;
5. number of unique unordered reported pairs;
6. number of event types;
7. number of rows removed during identity and graph validation;
8. number of positives and sampled unreported negatives;
9. negative-sampling protocol and ratio;
10. model architecture and all enabled feature blocks;
11. model and split seeds;
12. train/validation/test and S1/S2 counts;
13. metrics with confidence intervals;
14. checkpoint hash and run-manifest path.

Do not report a source as "used for training" merely because its folder exists. The run manifest and feature flags must show that the source entered the active computation graph.
