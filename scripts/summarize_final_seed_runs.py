"""Aggregate completed, matched AuditDDI final multimodal seed evaluations.

This script reads the timestamped artifact layout emitted by
``train_full_pipeline_v2.py``. It deliberately refuses to mix incompatible
data, splits, feature schemas, or incomplete runs. It summarizes held-out
Transductive, S1, and S2 test rows only; validation/dev rows are excluded.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TEST_SPLITS = ("Transductive", "S1", "S2")
METRICS = (
    "auroc",
    "average_precision",
    "mcc",
    "balanced_accuracy",
    "f1",
    "precision",
    "recall",
    "specificity",
    "brier_score_calibrated",
    "ece_calibrated",
)
MATCHED_CONFIG_KEYS = (
    "model_architecture",
    "feature_schema",
    "use_fingerprint_features",
    "use_seven_source_drug_features",
    "seven_source_feature_dimension",
    "negative_sampling_protocol",
    "negative_label_meaning",
    "evaluation_protocol",
    "data_cap",
    "split_seed",
    "epochs",
    "batch_size",
)
MATCHED_MODEL_KEYS = (
    "model_architecture",
    "feature_schema",
    "input_atom_features",
    "edge_feature_dim",
    "use_fingerprint_features",
    "use_gene_encoder",
    "gene_feature_dim",
    "use_pdb_encoder",
    "use_clinical_toxicity",
)


def _split_signature(manifest: dict[str, Any]) -> dict[str, Any]:
    """Compare actual partition hashes, not run-specific artifact paths."""
    split_manifest = manifest.get("split_manifest", {})
    return {
        name: {
            "sha256": details.get("sha256"),
            "rows": details.get("rows"),
            "label_counts": details.get("label_counts"),
        }
        for name, details in sorted(split_manifest.items())
        if isinstance(details, dict)
    }


def _completed_run(results_root: Path, seed: int) -> tuple[Path, dict[str, Any]]:
    candidates = sorted(
        results_root.glob(f"seed_{seed}*/artifacts/run_*/run_manifest.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for manifest_path in candidates:
        metrics_path = manifest_path.parent / "evaluation_metrics.csv"
        checkpoint = manifest_path.parent.parent.parent / "checkpoints"
        if not metrics_path.is_file() or not checkpoint.is_dir():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            config = manifest.get("configuration", {})
            if int(manifest.get("model_seed", -1)) != seed:
                continue
            if manifest.get("completed_at_utc") is None:
                continue
            if config.get("model_architecture") != "auditddi_multimodal_v1":
                continue
            if config.get("use_seven_source_drug_features") is not True:
                continue
            table = pd.read_csv(metrics_path)
            selected = table.loc[table["split"].isin(TEST_SPLITS)]
            if set(selected["split"].astype(str)) == set(TEST_SPLITS) and (
                selected["status"].astype(str).str.lower().eq("evaluated").all()
            ):
                return manifest_path.parent, manifest
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            continue
    raise FileNotFoundError(
        f"No completed seven-source seed {seed} run with Transductive/S1/S2 "
        f"test metrics was found below {results_root}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[201, 202, 203, 204, 205])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--allow-training-source-hash-differences",
        action="store_true",
        help=(
            "Allow differing trainer-file hashes only after confirming the code "
            "changes did not alter the fitted model or evaluation protocol."
        ),
    )
    args = parser.parse_args()
    root = args.results_dir
    output_dir = args.output_dir or root / "final_five_seed_summary"
    if not root.is_dir():
        raise FileNotFoundError(f"Results directory not found: {root}")

    rows: list[dict[str, Any]] = []
    reference_manifest: dict[str, Any] | None = None
    run_paths: dict[str, str] = {}
    input_hashes_reference: dict[str, str] | None = None

    for seed in args.seeds:
        run_dir, manifest = _completed_run(root, seed)
        config = manifest.get("configuration", {})
        if reference_manifest is None:
            reference_manifest = manifest
            input_hashes_reference = manifest.get("input_sha256", {})
        else:
            ref_config = reference_manifest.get("configuration", {})
            mismatches = [
                key for key in MATCHED_CONFIG_KEYS
                if config.get(key) != ref_config.get(key)
            ]
            if mismatches:
                raise ValueError(
                    f"Seed {seed} has a different run configuration for: {mismatches}."
                )
            hashes = manifest.get("input_sha256", {})
            ref_hashes = input_hashes_reference or {}
            comparable_hashes = {k: v for k, v in hashes.items() if k != "training_source"}
            ref_comparable_hashes = {k: v for k, v in ref_hashes.items() if k != "training_source"}
            if comparable_hashes != ref_comparable_hashes:
                raise ValueError(
                    f"Seed {seed} has different data or pretraining input hashes; refusing "
                    "to combine it with the other seeds."
                )
            if hashes.get("training_source") != ref_hashes.get("training_source"):
                if not args.allow_training_source_hash_differences:
                    raise ValueError(
                        f"Seed {seed} was produced by a different trainer-file hash. "
                        "Review the code difference first; then rerun with "
                        "--allow-training-source-hash-differences only if it did not "
                        "change the training or evaluation procedure."
                    )
                print(
                    f"Warning: trainer-file hash differs for seed {seed}; "
                    "the user explicitly allowed this after review."
                )
            model_summary = manifest.get("model_summary", {})
            ref_model_summary = reference_manifest.get("model_summary", {})
            model_mismatches = [
                key for key in MATCHED_MODEL_KEYS
                if model_summary.get(key) != ref_model_summary.get(key)
            ]
            if model_mismatches:
                raise ValueError(
                    f"Seed {seed} has a different instantiated model for: "
                    f"{model_mismatches}."
                )
            if _split_signature(manifest) != _split_signature(reference_manifest):
                raise ValueError(
                    f"Seed {seed} does not use the exact same saved train/validation/test partitions."
                )

        metrics_path = run_dir / "evaluation_metrics.csv"
        table = pd.read_csv(metrics_path)
        for split in TEST_SPLITS:
            match = table.loc[table["split"].astype(str) == split]
            if len(match) != 1:
                raise ValueError(f"Seed {seed}: expected one {split} test row.")
            source = match.iloc[0]
            row: dict[str, Any] = {
                "seed": seed,
                "split": split,
                "run_directory": str(run_dir),
                "checkpoint_epoch": manifest.get("checkpoint", {}).get("epoch"),
                "validation_auroc": manifest.get("checkpoint", {}).get("validation_auroc"),
            }
            for metric in METRICS:
                row[metric] = source.get(metric, np.nan)
            rows.append(row)
        run_paths[str(seed)] = str(run_dir)

    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError("Seed list contains duplicates.")

    detail = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    for split in TEST_SPLITS:
        split_rows = detail.loc[detail["split"] == split]
        for metric in METRICS:
            values = pd.to_numeric(split_rows[metric], errors="coerce").dropna()
            summary_rows.append({
                "split": split,
                "metric": metric,
                "n_seeds": int(values.size),
                "mean": float(values.mean()) if values.size else None,
                "sample_sd": float(values.std(ddof=1)) if values.size > 1 else None,
            })

    output_dir.mkdir(parents=True, exist_ok=True)
    detail.to_csv(output_dir / "five_seed_test_metrics_by_seed.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(
        output_dir / "five_seed_test_metrics_mean_sd.csv", index=False
    )
    summary = {
        "seeds": args.seeds,
        "split_seed": reference_manifest.get("split_seed") if reference_manifest else None,
        "test_splits": list(TEST_SPLITS),
        "aggregation": "mean and sample standard deviation across matched model seeds",
        "validation_and_dev_rows_excluded": True,
        "training_source_hashes": {
            str(seed): _completed_run(root, seed)[1].get("input_sha256", {}).get("training_source")
            for seed in args.seeds
        },
        "run_directories": run_paths,
        "metrics": summary_rows,
    }
    (output_dir / "five_seed_test_metrics_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(f"Summarized {len(args.seeds)} matched seeds across {len(TEST_SPLITS)} held-out test splits.")
    print(f"Per-seed metrics: {output_dir / 'five_seed_test_metrics_by_seed.csv'}")
    print(f"Mean and SD: {output_dir / 'five_seed_test_metrics_mean_sd.csv'}")
    print(f"JSON summary: {output_dir / 'five_seed_test_metrics_summary.json'}")


if __name__ == "__main__":
    main()
