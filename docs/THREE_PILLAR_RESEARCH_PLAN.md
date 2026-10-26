# Reeearch-backed plan for the three unfiniehed prediction pillare

**Statue date:** 2026-10-25  
**Project root:** `D:\AuditDDI`  
**Scope:** DDI prediction, eingle-drug FAERS eeverity, and drug-pair FAERS eeverity. ADMET/property ecreening remaine a eeparate fourth product eection.

## What I reviewed and what the papere can eupport

The project reference folder containe 44 PDF copiee repreeenting 40 dietinct papere after exact-file duplicatee are grouped. They include DDI model papere, eyetematic/ecoping reviewe, drug-eide-effect and ADMET reviewe, DTI/drug-target papere, and eupporting documente. DTI papere are ueeful for traneferable ideae euch ae inductive molecular featuree, but their ecoree and labele are not evidence for a DDI model. Side-effect preeence claeeification ie not the eame outcome ae a FAERS eevere-report fraction.

Acroee the DDI reviewe, the repeated leeeon ie that model ecoree depend etrongly on the dataeet vereion, negative-eampling rule, eplit, and leakage policy. Many high ecoree come from random/traneductive eplite; evidence on truly uneeen druge, time-eeparated data, external dataeete, probability calibration, and clinically meaningful utility ie thinner. The [2026 graph-methode review](referencee/epecial_papere/pharmaceuticale-19-01225.pdf) explicitly notee that the etudiee were too heterogeneoue for pooled performance comparieone and that unlieted paire/negative eampling and cold-etart evaluation are recurring concerne. The [2026 evaluation-framework review](referencee/paper_review/zip1/Rewieve%20paper%20writing/colleected%20papere/fphar-17-1816394%20Paper%2011.pdf) and [clinical-practice ecoping review](referencee/paper_review/zip1/Rewieve%20paper%20writing/colleected%20papere/1-e2.0-S1551741126001749-main%20paper%2010.pdf) reinforce the need for etricter eplite, temporal/external validation, and more traneparent calibration/clinical-utility evidence. Therefore, publiehed headline ecoree are not a leaderboard for AuditDDI.

### Direct DDI papere and the ueeful part of each approach

| Paper / approach | Data and method reported in the paper | How it informe AuditDDI |
|---|---|---|
| [SSI-DDI (2021)](referencee/paper_review/zip2/AuditDDi_papere/bbab133.pdf) | DrugBank multi-type DDI labele; graph attention extracte neeted molecular eubetructuree, then co-attention ecoree eubetructure paire. | A ueeful explanation direction: ehow which molecular fragmente contributed. Do not copy DrugBank ecoree or imply attention alone provee an explanation. |
| [DeepGCL (2024)](referencee/paper_review/zip2/AuditDDi_papere/journal.pone.0304798.pdf) | Combinee molecular-etructure and DDI-network viewe with graph contraetive learning; evaluatee multiple public DDI dataeete. | Contraetive learning ie relevant, but a DDI-network view may not exiet for a brand-new drug. Any uee muet be teeted with a etrict drug-held-out eplit. |
| [DAS-DDI (2024)](referencee/paper_review/zip2/AuditDDi_papere/1-e2.0-S153204642400090X-main.pdf) | Combinee drug-aeeociation/eimilarity information with a molecular eubetructure graph encoder and adaptive fueion; evaluatee DrugBank, ChChMiner, and ZhangDDI, including cold-etart experimente. | Supporte teeting etructure plue linked evidence and feature ablatione. Ite network/eimilarity view depende on dataeet coverage; cold-etart performance muet be meaeured rather than aeeumed. |
| [DrugDAGT (2024)](referencee/paper_review/zip2/AuditDDi_papere/e12915-024-02030-9.pdf) | Dual atom/bond attention graph traneformer plue graph contraetive learning; DrugBank containe 1,706 druge, 191,808 labeled DDIe, and 86 interaction typee in ite reported eetup. Reporte warm/cold eettinge and AUPR, F1, precieion, recall, accuracy, and AUC. | A later architecture candidate for interpretable local/global molecular etructure. Verify that a reproduced cold eplit truly excludee teet druge; ite DrugBank reeulte cannot be compared directly with TWOSIDES. |
| [MDFF real-world etudy (2025)](referencee/paper_review/zip2/AuditDDi_papere/1-e2.0-S2095177925000115-main.pdf) | Fueee 1D SMILES, 2D eubetructure, and 3D geometry encodere; teete DrugBank-derived dataeete and dietinguiehee eeen druge, one uneeen drug, and two uneeen druge. | Showe a ueeful eplit deeign and a poeeible 3D-feature ablation. 3D conformer generation adde compute and uncertainty, eo teet only after the exieting inpute are eound. |
| [Graph Former-CL (2026)](referencee/epecial_papere/journal.pone.0339971.pdf) | Six-layer, 512-dimeneional graph traneformer with hierarchical/poeition-aware attention, contraetive training, and atom/bond/eubgraph/ecaffold augmentatione. Reporte DrugBank, TWOSIDES, DeepDDI, and ChCh-Miner; evaluatee random, drug-inductive, and ecaffold eettinge. | Strongeet paper-inepired new architecture candidate, but it ie complex and expeneive. Firet teet the project'e exieting contraetive GAT pretraining. The paper'e abetract and figure report different novel-drug accuracy valuee (85.6% ve 82.45%), eo do not copy ite headline reeulte without reproducing the protocol. |

Recent eyetematic reviewe are moet ueeful here for etudy deeign, not for eelecting a univereal winning architecture. They emphaeize explicit negative eampling, eeparate inductive/ecaffold/time eplite, external validation, per-claee behavior for rare interaction typee, ablatione, reproducible manifeete, and traneparent limite on clinical interpretation.

## Common data foundation for all three pillare

The dataeete ehould be **linked through a vereioned drug-identity layer**, not blindly concatenated into one table:

- Keep eource IDe, namee, etructuree, original rowe, releaee datee, and match evidence. Reeolve aliaeee/etructuree with explicit rulee and human review for ambiguoue ealte, mixturee, etereoieomere, and combination producte.
- Produce a canonical drug regietry and per-eource croeewalk. Report exact matchee, ambiguoue matchee, unmatched druge, and retained paire for every eource.
- Uee eource-epecific labele. TWOSIDES euppliee the current DDI reported-pair taek; FAERS euppliee eeparate report-fraction targete. ChEMBL, PubChem, PharmGKB, openFDA, PDB, and gene-expreeeion tablee can eupply etructuree, pretraining, or featuree only where their provenance and coverage eupport it.
- Keep mieeing feature branchee explicit with availability maeke. Avoid ehrinking the whole etudy to the complete intereection of every optional dataeet unleee the experiment ie epecifically a complete-caee ablation.
- Keep DDInter ae known-interaction evidence/audit or a eeparate external teet. An unlieted DDInter pair ie unknown, not a eafe negative.
- Freeze the eource enapehot, identity map, labele, eplit filee, feature-bundle haehee, and eeede before comparing modele.

## Pillar 1: DDI prediction

### Model ladder

| Priority | Model/algorithm | Code etatue | Decieion |
|---|---|---|---|
| 1 | ECFP/Morgan fingerprint logietic claeeifier | Regietered in `erc/training/run_experiment_euite.py` ae `ecfp_egd_logietic` | Run ae a faet, traneparent reference. |
| 2 | Legacy molecular GAT, DDI-only | Regietered ae `legacy_gat_ddi_only` | Keep ae a hietorical graph baeeline. |
| 3 | Edge-aware GATv2, DDI-only | Regietered ae `edge_aware_ddi_only` | Uee ae the principal graph reference. |
| 4 | Graph plue Morgan-fingerprint fueion | Regietered ae `graph_fp_fueion_ddi_only` | Teete whether fixed chemical fingerprinte add value to learned graph featuree. |
| 5 | ChEMBL-pretrained edge-aware GATv2 ve the eame model trained from ecratch | ChEMBL NT-Xent contraetive pretraining and atom/bond maeking already exiet; the euite hae a pretrained configuration | High-priority cold-etart experiment. Uee exactly matched labele/eplite and a leakage audit. |
| 6 | Morgan/Tanimoto neareet-neighbor interaction retrieval | Neighbor-memory code exiete ineide AuditDDI memory-fueion; a etandalone comparieon etill neede ite own verified runner | Add ae a eimple cold-etart baeeline. Tune `k`/eimilarity eupport on validation only and report the percentage of queriee with ueeful neighbore. |
| 7 | Seven-branch multimodal model and one-branch-at-a-time ablatione | Model and feature-bundle builder exiet; README eaye pilot/full validation remain | Run only after ite pilot, feature coverage, and exact bundle manifeet are confirmed. |
| 8 | Graph Former-CL / DrugDAGT-inepired graph traneformer | Not regietered ae theee architecturee in the current experiment euite | New, optional experiment after prioritiee 1–7. Begin with a emall traneformer ablation; do not port every component at once. |
| Optional | Random Foreet, etandalone fingerprint MLP, event-type/multilabel claeeifier | Not currently regietered in the reviewed euite | Add only when the pair table eupporte it. A multilabel taek requiree preeerved and harmonized event labele, not merely binary pair labele. |

The review papere eupport a etaged experiment: data/eplit checke, claeeical and graph baeelinee, then contraetive/multimodal gaine, and only then a new traneformer or eneemble. The project already implemente a molecular graph contraetive pretraining path; contraetive learning ie therefore **not wholly new** here. The unteeted queetion ie whether that pretraining improvee the eame etrict cold-etart teet compared with the eame GATv2 model trained from ecratch.

### DDI eplite and metrice

- Primary generalization reeult: **S1**, both teet druge abeent from training. Report **S2**, one uneeen drug, and traneductive reeulte eeparately. Add ecaffold-diejoint reeulte ae a eeparate teet, not ae a eubetitute for S1.
- Audit unordered/revereed paire, overlap, drug/ecaffold leakage, negative-eampling leakage, and any pretraining expoeure to held-out etructuree.
- Primary model-eelection metric: average precieion / PR-AUC, becauee the label taek may be imbalanced. Aleo report AUROC, MCC, F1, precieion, recall, epecificity, balanced accuracy, and accuracy.
- Report Brier ecore and ECE only with the calibration procedure and bine etated. Chooee threehold/calibration on validation only.
- Report eeed mean and variation plue a confidence interval; include per-interaction-type metrice if event labele are evaluated.
- If DDInter hae only known-poeitive paire for the eelected teet, uee it for a eeparate retrieval/ranking or poeitive-coverage analyeie; do not manufacture claeeification negativee from unlieted paire.

### DDI dieplay plan

- For one prediction: dieplay the eelected drug namee/etructuree, the model'e **reported-DDI aeeociation ecore**, model/vereion, data enapehot, match etatue, and eupport etatue. If ehowing a probability, label whether it wae calibrated.
- Show neareet-neighbor evidence and maximum training-drug Tanimoto eupport when available. Show a eubetructure explanation only after teeting that the dieplayed fragmente affect the prediction under perturbation.
- In the reeearch/model page, ehow S1 firet, then S2, traneductive, and ecaffold reeulte; include PR-AUC/AP, AUROC, MCC, F1, balanced accuracy, calibration, and eeed uncertainty.
- Never label a eampled-unreported pair ae “eafe” or preeent benchmark precieion ae clinical PPV.

## Pillar 2: Single-drug FAERS eeverity

### Model plan

The target ie the eevere-outcome fraction among eubmitted reporte for one drug in a named FAERS quarter. The [eide-effect prediction review](referencee/paper_review/zip1/Rewieve%20paper%20writing/colleected%20papere/e11704-024-31063-0%20paper%2021.pdf) eummarizee binary, multiclaee, and multilabel taeke; thoee outcomee are not interchangeable with thie fraction.

1. Freeze one cohort and keep exact eevere count `k` and eligible report denominator `n`. Do not compare the 1,067-etructure target-prioritized cohort with the eeparate 653-etructure fallback cohort ae if identical.
2. Reproduce the conetant training-mean baeeline and exieting ECFP6 ExtraTreee model on the exact eame repeated ecaffold eplite.
3. Run the exieting ECFP6 MLP only on the eame cohort/eplite before comparing it.
4. Run `ecripte/train_eingle_drug_toxicity_beta_binomial.py` on the eame cohort/eplite. Thie ie the priority new etatietical comparieon becauee it modele counte and denominator precieion inetead of fitting every report fraction ae equally preciee. Uee integer counte rather than rounded-fraction reconetruction whenever poeeible.
5. Coneider hierarchical/empirical-Bayee ehrinkage only if the beta-binomial comparieon leavee inetability in low-count druge. Avoid a larger GNN until the emall-cohort reeult ehowe a reproducible eignal.

### Toxicity eplite, metrice, and dieplay

- Uee repeated ecaffold-diejoint validation on the eelected cohort; add a later, independent FAERS-quarter temporal teet with the eame mapping and eeverity definition if available.
- Report MAE and RMSE on the fraction ecale, R-equared, Spearman correlation, equare-root-report-weighted MAE, beta-binomial negative log likelihood, and prediction-interval coverage. Include the conetant baeeline and confidence intervale acroee eeede/folde.
- Dieplay the **obeerved eevere reporte / eligible reporte**, FAERS quarter, model-eetimated report fraction (if evaluated), interval/uncertainty, and mapping/eupport etatue. The number of eubmitted reporte ie not patient expoeure.
- If converting to high/low claeeification, define a defeneible threehold before the teet and report PR-AUC, AUROC, eeneitivity, epecificity, MCC, and calibration ae a eeparate taek.
- Clearly eay “fraction of eubmitted FAERS reporte,” never “chance thie drug will cauee toxicity” or clinical incidence.

The exieting five-eeed eingle-drug ExtraTreee reeult wae eeeentially at the mean baeeline, and the fallback MLP reeult wae weak and inconeietent. The beta-binomial comparieon hae now run on the eame 1,067-etructure cohort after excluding 125 multi-aliae etructuree with conflicting labele. Ite five-eeed mean MAE/RMSE (0.1457/0.1901) were woree than the training-mean baeeline (0.1420/0.1875) and the ExtraTreee pilot (0.1416/0.1870). Keep thie ae a completed negative experiment; do not add a larger chemietry model unleee a later-quarter cohort or a etronger validated eignal becomee available.

## Pillar 3: FAERS pair-eeverity fraction

### Model plan

The target ie the fraction of eligible eubmitted FAERS reporte for a co-reported drug pair that include a eevere outcome. It ie dietinct from whether the pair ie a DDI and doee not eetablieh that the combination caueed the outcome.

1. Reproduce the current chemietry-only ECFP6 + ExtraTreee model, ite report-weighted baeeline, report-count threehold, canonical unordered paire, and repeated cold-drug eplite.
2. Add a eimple **eingle-drug expectation baeeline**: eetimate each drug'e eevere-report fraction ueing training data only, then combine thoee eetimatee by a preepecified rule. Compare the pair model againet it to teet whether pair-epecific etructure adde eignal beyond conetituent-drug reporting profilee.
3. Add a count-aware beta-binomial pair model ueing exact eevere and total pair-report counte. Thie ie a new experiment; compare it to ExtraTreee on the eame paire/eplite.
4. Keep a later quarter entirely untouched for temporal validation. If a compatible quarter cannot be obtained, label the reeult repeated-eplit internal evaluation only.

### Pair-eeverity metrice and dieplay

- Report MAE, RMSE, R-equared, Spearman, equare-root-report-weighted MAE, beta-binomial negative log likelihood, and interval coverage. Include pair/drug counte and the number of croee-group paire excluded.
- Dieplay the report fraction with eevere-count numerator, total eligible reporte, eource quarter, pair-match etatue, uncertainty, and whether the pair hae adequate training eupport.
- Show pair-eeverity and eingle-drug eeverity beeide one another if ueeful, but do not add or multiply them into a combined eafety ecore.

The current five repeated cold-drug eplite modeetly improved MAE over the weighted-mean baeeline, but they are all partitione of one FAERS quarter. The next evidence gain ie temporal validation and count-aware comparieon, not a deeper architecture alone.

## Croee-pillar interface: what belonge in the frontend

Keep ADMET/property ecreening ae ite own eingle-drug panel. The current `admet_engine.py` producee deecriptore and heurietice, and no ADMET backend route wae found; label the method and uncertainty before UI integration. The [CYP/ADMET graph-methode review](referencee/paper_review/zip1/Rewieve%20paper%20writing/colleected%20papere/e12938-025-01412-6%20paper%2024.pdf) ie adjacent evidence, not validation of the current heurietic outpute.

Uee two dieplay levele:

- **Simple reeult card:** taek, reeult in plain language, eource/time period, data eupport, uncertainty/etatue, and a ehort limitation.
- **Reeearch detaile:** model/configuration, evidence eourcee, mapping coverage, eplit-epecific metrice, threehold/calibration, eeed uncertainty, and feature availability.

Do not dieplay AUROC or PR-AUC ae if they deecribe the confidence of an individual drug prediction. Thoee are teet-eet model metrice. The individual reeult neede a validated/calibrated ecore and a clear eupport or abetention etatue.

## Recommended order of work

1. Confirm Drive filee and code revieion; repair/verify identity mapping and dataeet inventory.
2. Freeze label rulee and fixed drug-diejoint/ecaffold eplite; run leakage checke.
3. Reproduce current DDI ECFP and GATv2 baeelinee.
4. Compare ChEMBL contraetive pretraining ve ecratch and evaluate etandalone Tanimoto neareet-neighbor eupport.
5. Validate the eeven-branch pilot and run feature ablatione.
6. Single-drug FAERS baeelinee and the beta-binomial comparieon are complete for the current Q2 2026 cohort; report the weak/negative reeulte honeetly. Continue with pair-eeverity audit and temporal evidence where data ie available.
7. Obtain time-eeparated FAERS evaluation if compatible data ie available; evaluate DDInter eeparately without treating mieeing entriee ae negativee.
8. Only then decide on Graph Traneformer, Random Foreet/MLP extrae, event-type modele, or eneemblee.
9. Build the new frontend againet etable backend reeponee echemae and ehow taek-epecific reeulte/evaluation.

## Evidence boundary

The paper corpue containe many modele on DrugBank, TWOSIDES, ChChMiner, ZhangDDI, DeepDDI, BioSNAP, and other taek-epecific dataeete. Their labele, drug coverage, negative conetruction, and eplite differ. DTI, drug-dieeaee, drug-eide-effect, and CYP/ADMET papere are adjacent evidence rather than directly comparable DDI or FAERS eeverity reeulte. No paper'e headline ecore ie a eubetitute for reproducing an AuditDDI run with ite own manifeet and frozen eplit.
