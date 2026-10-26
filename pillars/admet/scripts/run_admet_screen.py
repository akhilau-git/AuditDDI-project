"""Run this pillar’s descriptor/rule-based ADMET screen."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
from data_prep.admet_engine import compute_single_drug_admet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="CSV with drug_name and smiles columns")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    frame = pd.read_csv(args.input)
    required = {"drug_name", "smiles"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Input needs columns {sorted(required)}; found {list(frame.columns)}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = [
        compute_single_drug_admet(str(row.smiles), str(row.drug_name))
        for row in frame[["drug_name", "smiles"]].dropna().itertuples(index=False)
    ]
    (args.output_dir / "admet_results.json").write_text(
        json.dumps(records, indent=2, default=str), encoding="utf-8"
    )
    pd.json_normalize(records).to_csv(args.output_dir / "admet_results.csv", index=False)
    print(f"Saved {len(records)} exploratory records to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
