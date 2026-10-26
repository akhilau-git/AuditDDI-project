# ADMET engine audit — starting point

**Current state:** this pillar is a descriptor and rule screen, not a trained ADMET model. No ADMET prediction dataset, property-specific training cohort, or independent validation result is currently included in this repository. The Colab notebook expects `inputs/admet_smiles.csv` in the Google Drive data root; that file still needs to be checked in Drive.

## What the current code returns

| Output | Current implementation | Correct interpretation |
|---|---|---|
| Molecular weight, Crippen LogP, TPSA, H-bond counts, rotatable bonds, aromatic rings, heavy atoms, fraction Csp3 | Calculated with RDKit when it is installed and the structure parses | Calculated molecular descriptors; record the RDKit version and units. |
| Same descriptors when RDKit is unavailable | Hand-written SMILES string counting and approximate formulas | Unreliable fallback estimates; do not present these as calculated descriptors. The safe behavior should be to mark them unavailable. |
| Lipinski violations and Veber compliance | Threshold rules applied to descriptors | Rule flags only; not proof that a drug will be absorbed or safe. |
| Human intestinal absorption and Caco-2 category | Hand-set thresholds over MW, LogP, TPSA, H-bond donors, and rotatable bonds | Unvalidated heuristic categories; not measured HIA or Caco-2 assay results. The HIA score values 0.90/0.45 are assigned constants, not calibrated probabilities. |
| Fraction unbound / plasma protein binding | Exponential formula based on LogP | Unvalidated estimate; not an assay value or calibrated prediction. |
| BBB/CNS status | Linear descriptor equation and a zero threshold | Approximation only; not a validated BBB model or clinical CNS-exposure result. |
| CYP affinity profile and primary enzyme | Hand-coded molecular descriptor and SMARTS rules transformed by a sigmoid; the no-RDKit path uses additional SMILES substring heuristics | Uncalibrated structural-liability scores, not enzyme affinity, inhibition, or substrate probabilities. |
| Clearance route | Binary MW/LogP threshold | Heuristic route guess; not measured renal/hepatic clearance. |
| Toxicophore alerts | SMARTS substructure matches, or substring heuristics without RDKit | Structural alerts only. A match is not a toxicity outcome; no match does not establish safety. |
| NTI flag | Small manually maintained exact-name set plus a Warfarin-like string check | Limited name/structure lookup, not a complete or validated NTI drug database. |
| Danger score and danger level | Hand-assigned point weights for NTI, alerts, Lipinski violations, and estimated fraction unbound | Unvalidated composite heuristic; it must not be described as clinical danger, toxicity probability, or patient risk. |
| Guardrail status | SMILES parsing plus simple heavy-atom, molecular-weight, and LogP bounds | Input/domain checks only; passing is not evidence of safety or ADMET suitability. |

## Main issues before model or product claims

1. The engine response does not identify the method, units, source, or confidence for each field.
2. The no-RDKit fallback can emit plausible-looking but inaccurate values instead of abstaining.
3. Several output names imply calibrated measurements or probabilities although the code uses fixed thresholds and hand-authored formulas.
4. The danger score combines unrelated property rules and an incomplete NTI lookup without a validation target.
5. Existing tests check output shape and selected examples; they do not compare predicted ADMET values with experimental reference labels.
6. The code is imported by other safety and polypharmacy modules. Any behavior change needs a compatibility review so that unvalidated scores are not silently treated as measured evidence elsewhere.

## Recommended order

1. Inventory Drive inputs and identify available ADMET datasets, their labels, units, drug identifiers, and licenses.
2. Decide which properties this pillar will support. Keep each endpoint separate (for example, solubility is not permeability, CYP inhibition is not CYP substrate status, and toxicity assay labels are not FAERS report fractions).
3. Preserve exact RDKit descriptor calculations; make heuristic outputs explicit and versioned; return `unavailable` instead of regex-derived chemical measurements when RDKit is absent.
4. Build property-specific, duplicate-aware identity mappings and scaffold-based splits. Do not merge unrelated endpoints into one target.
5. Benchmark only endpoints with usable reference labels. Report endpoint-appropriate metrics, coverage, and applicability-domain limits.
6. Integrate a backend/UI only after the response schema separates measured/calculated descriptors, heuristic alerts, validated model predictions, and abstentions.

Keep this pillar separate from the DDI model and both FAERS report-fraction models.
