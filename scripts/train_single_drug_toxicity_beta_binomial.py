"""Train an exploratory count-aware FAERS single-drug severity model.

The response is the observed severe-outcome report fraction. The model uses a
beta-binomial likelihood over severe and total reports, rather than treating
fractions based on 5 and 5,000 reports as equally precise. This is still a
descriptive FAERS reporting signal, not clinical toxicity probability.

Example:
    python scripts/train_single_drug_toxicity_beta_binomial.py \
      --labels processed/seven_branch/single_drug_toxicity_labels_candidate_2026q2.csv \
      --output-dir results/single_drug_toxicity_beta_binomial
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold
from scipy.stats import spearmanr
from sklearn.model_selection import GroupShuffleSplit
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class ToxicityMLP(nn.Module):
    def __init__(self, input_bits: int = 1024) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_bits, 256),
            nn.ReLU(),
            nn.Dropout(0.30),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Dropout(0.20),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )
        # Learned beta-binomial concentration. Positive via softplus.
        self.log_concentration = nn.Parameter(torch.tensor(3.0))

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        mean = self.network(x).squeeze(-1)
        concentration = torch.nn.functional.softplus(self.log_concentration) + 0.1
        return mean, concentration


def beta_binomial_nll(
    mean: torch.Tensor,
    concentration: torch.Tensor,
    severe: torch.Tensor,
    total: torch.Tensor,
) -> torch.Tensor:
    """Mean negative log beta-binomial likelihood; calculations use float64."""
    mean = mean.to(torch.float64).clamp(1e-6, 1.0 - 1e-6)
    concentration = concentration.to(torch.float64).clamp(0.101, 1e5)
    severe = severe.to(torch.float64)
    total = total.to(torch.float64)
    nonsevere = total - severe
    alpha = (mean * concentration).clamp_min(1e-8)
    beta = ((1.0 - mean) * concentration).clamp_min(1e-8)

    log_choose = (
        torch.lgamma(total + 1.0)
        - torch.lgamma(severe + 1.0)
        - torch.lgamma(nonsevere + 1.0)
    )
    log_beta_post = (
        torch.lgamma(severe + alpha)
        + torch.lgamma(nonsevere + beta)
        - torch.lgamma(total + alpha + beta)
    )
    log_beta_prior = torch.lgamma(alpha) + torch.lgamma(beta) - torch.lgamma(alpha + beta)
    return -(log_choose + log_beta_post - log_beta_prior).mean()


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    rho = (
        spearmanr(y_true, y_pred).statistic
        if len(y_true) > 1 and np.ptp(y_pred) > 0
        else np.nan
    )
    denom = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return {
        "mae": float(np.mean(np.abs(y_true - y_pred))),
        "rmse": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
        "r2": float(1.0 - np.sum((y_true - y_pred) ** 2) / max(denom, 1e-12)),
        "spearman": float(rho) if np.isfinite(rho) else None,
    }


def make_split(
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    outer = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=seed)
    trainval, test = next(outer.split(x, y, groups))
    inner = GroupShuffleSplit(n_splits=1, test_size=0.15 / 0.80, random_state=seed + 1)
    train_rel, val_rel = next(
        inner.split(x[trainval], y[trainval], groups[trainval])
    )
    train, val = trainval[train_rel], trainval[val_rel]
    if (
        not set(groups[train]).isdisjoint(groups[val])
        or not set(groups[train]).isdisjoint(groups[test])
        or not set(groups[val]).isdisjoint(groups[test])
    ):
        raise RuntimeError("Scaffold leakage detected in split construction.")
    return train, val, test


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[203, 204, 205, 206, 207])
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--fingerprint-bits", type=int, default=1024)
    parser.add_argument("--radius", type=int, default=3)
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument(
        "--reference-metrics",
        type=Path,
        default=None,
        help="Optional prior MSE pilot repeated_scaffold_metrics.csv for side-by-side comparison.",
    )
    args = parser.parse_args()
    if not args.labels.is_file():
        raise FileNotFoundError(args.labels)
    if args.epochs < 1 or args.batch_size < 1:
        raise ValueError("epochs and batch size must be positive")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available")
        device = torch.device("cuda")
    elif args.device == "cpu":
        device = torch.device("cpu")
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    frame = pd.read_csv(args.labels)
    required = {"canonical_smiles", "toxicity_score", "n_reports"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Labels missing required columns: {sorted(missing)}")
    frame["toxicity_score"] = pd.to_numeric(frame["toxicity_score"], errors="coerce")
    frame["n_reports"] = pd.to_numeric(frame["n_reports"], errors="coerce")
    frame = frame.dropna(subset=["canonical_smiles", "toxicity_score", "n_reports"])
    frame = frame[
        frame["toxicity_score"].between(0, 1)
        & (frame["n_reports"] >= 1)
        & np.isfinite(frame["n_reports"])
    ].drop_duplicates("canonical_smiles").reset_index(drop=True)

    # The bridge stores severity fractions rounded to four decimals. Recover
    # integer counts from score * denominator and reject data where rounding
    # makes that reconstruction ambiguous.
    n_reports = frame["n_reports"].to_numpy(dtype=np.int64)
    if "severe_reports" in frame.columns:
        severe = pd.to_numeric(frame["severe_reports"], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(severe).all():
            raise ValueError("severe_reports contains missing or nonfinite values")
        severe = np.rint(severe).astype(np.int64)
    else:
        raw_counts = frame["toxicity_score"].to_numpy(dtype=float) * n_reports
        severe = np.rint(raw_counts).astype(np.int64)
        error = np.abs(raw_counts - severe)
        if float(error.max(initial=0.0)) >= 0.500001:
            raise ValueError(
                "Cannot reliably reconstruct severe report counts from the rounded score. "
                "Regenerate labels with severe_reports and non_severe_reports columns."
            )
        print("Recovered severe report counts from rounded score × n_reports.")
    if np.any(severe < 0) or np.any(severe > n_reports):
        raise ValueError("Severe counts must be between 0 and n_reports")

    y = severe.astype(np.float64) / n_reports.astype(np.float64)
    fpgen = rdFingerprintGenerator.GetMorganGenerator(
        radius=args.radius, fpSize=args.fingerprint_bits
    )
    features: list[np.ndarray] = []
    groups: list[str] = []
    smiles: list[str] = []
    kept_severe: list[int] = []
    kept_total: list[int] = []
    invalid = 0
    for row, k, n in zip(frame.itertuples(index=False), severe, n_reports):
        mol = Chem.MolFromSmiles(str(row.canonical_smiles))
        if mol is None:
            invalid += 1
            continue
        canonical = Chem.MolToSmiles(mol, canonical=True)
        arr = np.zeros(args.fingerprint_bits, dtype=np.int8)
        DataStructs.ConvertToNumpyArray(fpgen.GetFingerprint(mol), arr)
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
        group = scaffold if scaffold else f"ACYCLIC::{canonical}"
        features.append(arr)
        groups.append(group)
        smiles.append(canonical)
        kept_severe.append(int(k))
        kept_total.append(int(n))

    x = np.asarray(features, dtype=np.float32)
    severe = np.asarray(kept_severe, dtype=np.float32)
    total = np.asarray(kept_total, dtype=np.float32)
    y = severe / total
    groups_arr = np.asarray(groups)
    smiles_arr = np.asarray(smiles)
    if len(y) < 50 or len(np.unique(groups_arr)) < 5:
        raise ValueError("Not enough valid drugs/scaffolds for this evaluation.")
    print(f"Drugs: {len(y)} | scaffold groups: {len(np.unique(groups_arr))} | invalid SMILES: {invalid}")

    rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    for seed in args.seeds:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        train_idx, val_idx, test_idx = make_split(x, y, groups_arr, seed)

        dataset = TensorDataset(
            torch.from_numpy(x[train_idx]),
            torch.from_numpy(severe[train_idx]),
            torch.from_numpy(total[train_idx]),
        )
        train_loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
        model = ToxicityMLP(args.fingerprint_bits).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        best_val_mae = float("inf")
        best_epoch = 0
        best_state: dict[str, torch.Tensor] | None = None

        for epoch in range(1, args.epochs + 1):
            model.train()
            for xb, kb, nb in train_loader:
                xb, kb, nb = xb.to(device), kb.to(device), nb.to(device)
                optimizer.zero_grad(set_to_none=True)
                mean, concentration = model(xb)
                loss = beta_binomial_nll(mean, concentration, kb, nb)
                if not torch.isfinite(loss):
                    raise FloatingPointError(f"Nonfinite training loss at seed {seed}, epoch {epoch}")
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            model.eval()
            with torch.no_grad():
                val_mean, _ = model(torch.from_numpy(x[val_idx]).to(device))
                val_pred = val_mean.cpu().numpy()
            val_mae = float(np.mean(np.abs(y[val_idx] - val_pred)))
            if val_mae < best_val_mae:
                best_val_mae = val_mae
                best_epoch = epoch
                best_state = {
                    key: value.detach().cpu().clone()
                    for key, value in model.state_dict().items()
                }

        if best_state is None:
            raise RuntimeError(f"No checkpoint selected for seed {seed}")
        model.load_state_dict(best_state)
        model.eval()
        with torch.no_grad():
            test_mean, test_concentration = model(torch.from_numpy(x[test_idx]).to(device))
            pred = test_mean.cpu().numpy()
            concentration_value = float(test_concentration.cpu().item())
        truth = y[test_idx]
        baseline = np.full_like(truth, float(y[train_idx].mean()))
        model_metrics = regression_metrics(truth, pred)
        baseline_metrics = regression_metrics(truth, baseline)
        result = {
            "seed": int(seed),
            "train_n": int(len(train_idx)),
            "validation_n": int(len(val_idx)),
            "test_n": int(len(test_idx)),
            "best_epoch": int(best_epoch),
            "learned_concentration": concentration_value,
            **{f"model_{key}": value for key, value in model_metrics.items()},
            **{f"baseline_{key}": value for key, value in baseline_metrics.items()},
        }
        rows.append(result)
        prediction_frames.append(pd.DataFrame({
            "seed": int(seed),
            "canonical_smiles": smiles_arr[test_idx],
            "severe_reports": severe[test_idx].astype(int),
            "n_reports": total[test_idx].astype(int),
            "y_true": truth,
            "y_pred": pred,
            "train_mean_baseline": baseline,
            "scaffold_group": groups_arr[test_idx],
        }))
        torch.save(
            {
                "model_state_dict": best_state,
                "fingerprint_bits": args.fingerprint_bits,
                "radius": args.radius,
                "seed": int(seed),
                "best_epoch": int(best_epoch),
                "learned_concentration": concentration_value,
                "metrics": result,
            },
            args.output_dir / f"checkpoint_seed_{seed}.pt",
        )
        print(
            f"Seed {seed}: best epoch {best_epoch} | "
            f"MAE {model_metrics['mae']:.4f} vs baseline {baseline_metrics['mae']:.4f} | "
            f"RMSE {model_metrics['rmse']:.4f} vs baseline {baseline_metrics['rmse']:.4f}"
        )

    metrics_df = pd.DataFrame(rows)
    metrics_df.to_csv(args.output_dir / "beta_binomial_metrics.csv", index=False)
    pd.concat(prediction_frames, ignore_index=True).to_csv(
        args.output_dir / "beta_binomial_predictions.csv", index=False
    )
    summary = {}
    for column in ["model_mae", "baseline_mae", "model_rmse", "baseline_rmse", "model_r2", "model_spearman"]:
        values = pd.to_numeric(metrics_df[column], errors="coerce")
        summary[column] = {"mean": float(values.mean()), "std": float(values.std(ddof=1))}
    summary["description"] = (
        "Exploratory beta-binomial ECFP6 model on a fallback FAERS cohort; "
        "target is a report fraction, not clinical toxicity probability."
    )
    summary["seeds"] = [int(seed) for seed in args.seeds]
    (args.output_dir / "beta_binomial_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    if args.reference_metrics and args.reference_metrics.is_file():
        reference = pd.read_csv(args.reference_metrics)
        merged = metrics_df.merge(reference, on="seed", suffixes=("_beta_binomial", "_mse"))
        merged.to_csv(args.output_dir / "comparison_to_mse_pilot.csv", index=False)
        print("Compared against prior MSE metrics:", args.reference_metrics)

    print("\nSummary:\n", json.dumps(summary, indent=2))
    print("Outputs:", args.output_dir)


if __name__ == "__main__":
    main()
