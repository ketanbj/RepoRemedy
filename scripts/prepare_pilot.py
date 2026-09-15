"""Build a contact-free manifest from the private beta CSV; no network or publication."""

import argparse
import csv
import json
from pathlib import Path

from reporemedy.batch import BatchItem
from reporemedy.models import repository_name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--scorecard-dir", type=Path, required=True)
    parser.add_argument(
        "--overrides", type=Path, help="JSON mapping aliases to explicit manifest entries"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    overrides = json.loads(args.overrides.read_text(encoding="utf-8")) if args.overrides else {}
    entries = []
    with args.csv.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            alias = row["full_name"]
            if alias in overrides:
                entry = BatchItem.model_validate(overrides[alias]).model_dump()
                entry["repository"] = repository_name(entry["repository"])
                entry["report"] = str(Path(entry["report"]).resolve())
            else:
                if Path(alias).name != alias or "/" in alias or "\\" in alias:
                    parser.error("Display alias must be a filename without directory components")
                try:
                    repository = repository_name(row["html_url"])
                except ValueError:
                    parser.error(
                        f"{alias}: website URL needs a verified repository/report override"
                    )
                report = (args.scorecard_dir / f"{alias}.json").resolve()
                if not report.is_file():
                    parser.error(f"Missing report for {alias}")
                entry = {
                    "repository": repository,
                    "report": str(report),
                    "report_type": "ossf-scorecard",
                }
            entries.append(entry)
    if not 1 <= len(entries) <= 10:
        parser.error("Expected 1–10 beta entries")
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(entries, stream, indent=2)
        stream.write("\n")
    print(f"Wrote {len(entries)} report inputs. Contact columns were not copied.")


if __name__ == "__main__":
    main()
