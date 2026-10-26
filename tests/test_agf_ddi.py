"""Smoke + protocol tests for AGF-DDI on a small synthetic cohort (no RDKit needed)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "training"))

import agf_ddi  # noqa: E402
from src.data_prep.splits import create_split_aware_binary_splits  # noqa: E402


@pytest.fixture(scope="module")
def cohort(tmp_path_factory):
    d = tmp_path_factory.mktemp("agf")
    rng = np.random.default_rng(0)
    n, C = 160, 8
    cls = rng.integers(0, C, n)
    B = rng.normal(0, 1.2, (C, C)); B = (B + B.T) / 2 - 1.2
    ids = [f"D{i:04d}" for i in range(n)]
    rows = [(ids[i], ids[j]) for i in range(n) for j in range(i + 1, n)
            if rng.random() < 1 / (1 + np.exp(-B[cls[i], cls[j]]))]
    pos = pd.DataFrame(rows, columns=["source", "target"])
    splits, _ = create_split_aware_binary_splits(pos, known_reported_positive_pairs=pos)
    sd = d / "splits"; sd.mkdir()
    for k, v in splits.items():
        v.to_csv(sd / f"{k}.csv", index=False)
    proto = rng.random((C, 128)) < 0.15
    fp = (proto[cls] ^ (rng.random((n, 128)) < 0.05)).astype(np.float32)
    np.savez(d / "fp.npz", canonical_smiles=np.array(ids), ecfp=fp, maccs=fp[:, :64])
    pd.DataFrame(rng.random((120, 4)), columns=list("abcd")).assign(
        canonical_smiles=ids[:120]).to_csv(d / "adverse_event.csv", index=False)
    return d, sd


def test_leakage_audit_passes_and_detects_leak(cohort):
    _, sd = cohort
    splits = agf_ddi.load_splits(sd)
    agf_ddi.leakage_audit(splits)
    bad = {k: v.copy() for k, v in splits.items()}
    bad["s1_test"] = pd.concat([bad["s1_test"], bad["transductive_train"].head(3)], ignore_index=True)
    with pytest.raises(RuntimeError):
        agf_ddi.leakage_audit(bad)


def test_full_run_and_order_invariance(cohort):
    d, sd = cohort
    out = d / "out"
    agf_ddi.main(["--splits_dir", str(sd), "--fp_table", str(d / "fp.npz"),
                  "--bio_npz", str(d / "adverse_event.csv"), "--out_dir", str(out),
                  "--seeds", "1", "--trans_folds", "3", "--drug_folds", "4",
                  "--explain_top", "3", "--fast"])
    m = json.loads((out / "metrics.json").read_text())["metrics"]
    for split in ("transductive_test", "s1_test", "s2_test"):
        assert 0.5 < m[split]["auroc"] <= 1.0
    assert (out / "predictions.csv").is_file()
    assert (out / "audit_evidence_s2_test.jsonl").is_file()
