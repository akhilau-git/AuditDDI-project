"""Create a privacy-conscious inventory of the nine AuditDDI source families.

The report lists file names, sizes, and tabular column headers. It does not
copy dataset rows into the report.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
import zipfile


DATASET_FOLDERS = {
    "twosides": ("twosides", "TWOSIDES", "nsides/twosides", "nsides"),
    "pubchem": ("pubchem", "PubChem", "PUBCHEM"),
    "chembl": ("chembl", "ChEMBL", "chembel"),
    "pharmgkb": ("pharmgkb", "PharmGKB", "pharmagkb"),
    "openfda": ("openfda", "openFDA"),
    "faers": ("faers", "FAERS", "faeres", "fears"),
    "ddinter": ("ddinter", "DDInter"),
    "lincs_geo": ("lincs_geo", "lincs", "geo", "GEO", "LINCS"),
    "pdb_rcsb": ("pdb_rcsb", "pdb", "PDB", "rcsb", "RCSB"),
}
TABULAR_SUFFIXES = (".csv", ".tsv", ".txt", ".csv.gz", ".tsv.gz", ".txt.gz")


def _read_header(path: Path) -> list[str] | None:
    lower_name = path.name.casefold()
    if not lower_name.endswith(TABULAR_SUFFIXES):
        return None
    opener = gzip.open if lower_name.endswith(".gz") else open
    try:
        with opener(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as stream:
            sample = stream.read(16_384)
        if not sample.strip():
            return []
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel_tab if path.name.casefold().endswith((".tsv", ".tsv.gz")) else csv.excel
        return next(csv.reader(sample.splitlines(), dialect), [])
    except (OSError, EOFError, gzip.BadGzipFile) as error:
        return [f"HEADER_READ_ERROR: {type(error).__name__}: {error}"]


def inventory(data_root: str | Path) -> dict:
    root = Path(data_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset root not found: {root}")
    datasets: dict[str, dict] = {}
    for dataset, folder_aliases in DATASET_FOLDERS.items():
        folders = [root / alias for alias in folder_aliases if (root / alias).is_dir()]
        # Aliases can point at nested or overlapping directories (for example,
        # nsides/twosides and nsides). Prefer the deepest matching folders so
        # a file is inventoried once under its most specific source folder.
        folders = sorted(
            {folder.resolve() for folder in folders},
            key=lambda folder: (len(folder.parts), str(folder)),
            reverse=True,
        )
        selected_folders: list[Path] = []
        for folder in folders:
            if not any(parent in folder.parents for parent in selected_folders):
                selected_folders.append(folder)
        folders = selected_folders
        if not folders:
            datasets[dataset] = {"status": "missing", "files": []}
            continue
        records = []
        seen_paths: set[Path] = set()
        for folder in folders:
            for path in sorted(item for item in folder.rglob("*") if item.is_file()):
                resolved_path = path.resolve()
                if resolved_path in seen_paths:
                    continue
                seen_paths.add(resolved_path)
                record = {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                }
                header = _read_header(path)
                if header is not None:
                    record["columns"] = header
                if path.suffix.casefold() == ".zip":
                    try:
                        with zipfile.ZipFile(path) as archive:
                            record["archive_members"] = [
                                {"path": item.filename, "bytes": item.file_size}
                                for item in archive.infolist()
                                if not item.is_dir()
                            ]
                    except (OSError, zipfile.BadZipFile) as error:
                        record["archive_error"] = f"{type(error).__name__}: {error}"
                records.append(record)
        datasets[dataset] = {
            "status": "present" if records else "empty",
            "file_count": len(records),
            "source_folders": [folder.relative_to(root).as_posix() for folder in folders],
            "files": records,
        }
    return {"dataset_root": str(root), "datasets": datasets}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("auditddi_dataset_inventory.json"))
    args = parser.parse_args()
    report = inventory(args.data_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(args.output.resolve()),
        "datasets": {
            name: {
                "status": item["status"],
                "file_count": item.get("file_count", 0),
            }
            for name, item in report["datasets"].items()
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
