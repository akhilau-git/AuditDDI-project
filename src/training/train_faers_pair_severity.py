"""Train an exploratory chemistry-only model for FAERS pair severity fractions.

The target is the observed fraction of deduplicated FAERS reports for a drug
pair that include a designated severe outcome. This is a report-level signal,
not a causal toxicity probability, and the model is deliberately separate from
the TWOSIDES DDI classifier.

The default evaluation holds out drug identities: training pairs contain only
training drugs and test pairs contain only held-out drugs. Cross-partition
pairs are excluded to avoid sharing a drug between the training and test sets.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


REQUIRED_COLUMNS = {
    "smiles_a",
    "smiles_b",
    "total_reports",
    "reports_with_severe_outcome",
}


def canonicalize(smiles: Any) -> str | None:
    if pd.isna(smiles):
        return None
    mol = Chem.MolFromSmiles(str(smiles))
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True) if mol else None


def metrics(y_true: np.ndarray, y_pred: np.ndarray, sample_weight: np.ndarray) -> dict[str, Any]:
    corr = spearmanr(y_true, y_pred).statistic if len(y_true) > 1 else float("nan")
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan")
    return {
        "n_pairs": int(len(y_true)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2) if np.isfinite(r2) else None,
        "spearman": float(corr) if np.isfinite(corr) else None,
        "weighted_mae_sqrt_reports": float(
            mean_absolute_error(y_true, y_pred, sample_weight=sample_weight)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--min-reports", type=int, default=20)
    parser.add_argument("--test-drug-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=203)
    parser.add_argument("--n-estimators", type=int, default=200)
    args = parser.parse_args()

    if args.min_reports < 1:
        raise ValueError("--min-reports must be at least 1")
    if not 0.05 <= args.test_drug_fraction <= 0.5:
        raise ValueError("--test-drug-fraction must be between 0.05 and 0.5")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(args.pairs)
    missing = REQUIRED_COLUMNS.difference(raw.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    frame = raw.copy()
    for col in ("total_reports", "reports_with_severe_outcome"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(
        subset=["smiles_a", "smiles_b", "total_reports", "reports_with_severe_outcome"]
    )
    frame["canonical_a"] = frame["smiles_a"].map(canonicalize)
    frame["canonical_b"] = frame["smiles_b"].map(canonicalize)
    frame = frame.dropna(subset=["canonical_a", "canonical_b"])

    # Canonical, unordered identity is the unit of analysis.
    pair_keys = frame.apply(
        lambda row: tuple(sorted((row["canonical_a"], row["canonical_b"]))), axis=1
    )
    frame["canonical_a"] = [key[0] for key in pair_keys]
    frame["canonical_b"] = [key[1] for key in pair_keys]
    frame = frame.groupby(["canonical_a", "canonical_b"], as_index=False).agg(
        total_reports=("total_reports", "sum"),
        reports_with_severe_outcome=("reports_with_severe_outcome", "sum"),
        source_rows=("smiles_a", "size"),
    )
    frame = frame.loc[frame["total_reports"] >= args.min_reports].copy().reset_index(drop=True)
    if (frame["reports_with_severe_outcome"] > frame["total_reports"]).any():
        raise ValueError("Severe report count exceeds total report count after canonical aggregation")
    frame["target"] = (
        frame["reports_with_severe_outcome"] + 1
    ) / (frame["total_reports"] + 2)

    drugs = sorted(set(frame["canonical_a"]) | set(frame["canonical_b"]))
    if len(drugs) < 10 or len(frame) < 100:
        raise ValueError(f"Too little eligible data after filtering: {len(drugs)} drugs, {len(frame)} pairs")

    rng = np.random.default_rng(args.seed)
    shuffled = np.asarray(drugs, dtype=object).copy()
    rng.shuffle(shuffled)
    n_test_drugs = max(1, int(round(len(shuffled) * args.test_drug_fraction)))
    test_drugs = set(shuffled[:n_test_drugs])
    in_test_a = frame["canonical_a"].isin(test_drugs).to_numpy()
    in_test_b = frame["canonical_b"].isin(test_drugs).to_numpy()
    test_mask = in_test_a & in_test_b
    train_mask = ~in_test_a & ~in_test_b
    train = frame.loc[train_mask].reset_index(drop=True)
    test = frame.loc[test_mask].reset_index(drop=True)
    if len(train) < 100 or len(test) < 50:
        raise ValueError(
            "Cold-drug split is too small for a useful estimate: "
            f"train={len(train)}, test={len(test)}. Do not silently switch to a random pair split."
        )

    # Fixed Morgan radius 3 (ECFP6), 1024 bits. Pair features are symmetric:
    # canonical drug order + concatenation + absolute difference + bitwise AND.
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=3, fpSize=1024)
    fp_cache: dict[str, np.ndarray] = {}
    for drug in drugs:
        mol = Chem.MolFromSmiles(drug)
        bitvect = generator.GetFingerprint(mol)
        array = np.zeros((1024,), dtype=np.uint8)
        DataStructs.ConvertToNumpyArray(bitvect, array)
        fp_cache[drug] = array

    def make_matrix(rows: pd.DataFrame) -> np.ndarray:
        result = np.empty((len(rows), 4096), dtype=np.uint8)
        for i, (drug_a, drug_b) in enumerate(zip(rows["canonical_a"], rows["canonical_b"])):
            a = fp_cache[drug_a]
            b = fp_cache[drug_b]
            result[i] = np.concatenate((a, b, np.abs(a.astype(np.int8) - b.astype(np.int8)).astype(np.uint8), a & b))
        return result

    X_train, X_test = make_matrix(train), make_matrix(test)
    y_train, y_test = train["target"].to_numpy(), test["target"].to_numpy()
    # Count-based weights reflect target precision without letting the largest
    # report pairs dominate linearly.
    w_train = np.sqrt(train["total_reports"].to_numpy(dtype=np.float64))
    w_test = np.sqrt(test["total_reports"].to_numpy(dtype=np.float64))

    model = ExtraTreesRegressor(
        n_estimators=args.n_estimators,
        min_samples_leaf=5,
        max_features="sqrt",
        n_jobs=-1,
        random_state=args.seed,
    )
    model.fit(X_train, y_train, sample_weight=w_train)
    pred = np.clip(model.predict(X_test), 0.0, 1.0)
    baseline = np.full_like(y_test, float(np.average(y_train, weights=w_train)))

    predictions = test[["canonical_a", "canonical_b", "total_reports", "reports_with_severe_outcome"]].copy()
    predictions["observed_smoothed_severe_fraction"] = y_test
    predictions["predicted_severe_report_fraction"] = pred
    predictions.to_csv(args.output_dir / "faers_pair_severity_cold_drug_predictions.csv", index=False)
    joblib.dump(model, args.output_dir / "faers_pair_severity_ecfp6_extratrees.joblib")

    results = {
        "task": "regression of FAERS severe-outcome report fraction among co-reported pairs",
        "interpretation": "descriptive pharmacovigilance signal; not causal toxicity probability",
        "source_quarter": "2026Q2",
        "minimum_pair_reports": args.min_reports,
        "feature_type": "symmetric pair ECFP6: ordered concatenation, absolute difference, bitwise intersection",
        "split": "cold-drug: train pairs use only training drugs; test pairs use only held-out drugs; cross-group pairs excluded",
        "seed": args.seed,
        "eligible_pairs_after_canonicalization": int(len(frame)),
        "unique_drugs": int(len(drugs)),
        "train_pairs": int(len(train)),
        "test_pairs": int(len(test)),
        "cross_group_pairs_excluded": int(len(frame) - len(train) - len(test)),
        "train_drugs": int(len(drugs) - n_test_drugs),
        "test_drugs": int(n_test_drugs),
        "model_metrics": metrics(y_test, pred, w_test),
        "weighted_mean_baseline_metrics": metrics(y_test, baseline, w_test),
        "limitation": "single-quarter report-based labels; no unreported pair is treated as a negative; independent temporal validation is still required",
    }
    (args.output_dir / "faers_pair_severity_cold_drug_metrics.json").write_text(
        json.dumps(results, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(results, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
