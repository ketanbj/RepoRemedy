"""Summarize preview runs without exporting report contents or contact metadata."""

import argparse
import json
from collections import Counter
from pathlib import Path

from reporemedy.storage import read_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    batches = []
    for directory in args.directories:
        rows = []
        totals: Counter[str] = Counter()
        for path in sorted(directory.glob("*/run.json")):
            run = read_run(path.parent)
            outcomes = Counter(o.status for o in run.outcomes)
            totals.update(outcomes)
            rows.append(
                {
                    "repository": run.repository,
                    "mode": run.mode,
                    "model_name": run.model_name,
                    "report_type": run.report.report_type,
                    "report_version": run.report.source_version,
                    "report_sha256": run.report.source_sha256,
                    "base_commit": run.base_commit,
                    "actions": dict(Counter(p.action for p in run.proposals)),
                    "outcomes": dict(outcomes),
                    "rejected": [
                        {"finding": o.finding, "reason": o.message}
                        for o in run.outcomes
                        if o.status == "failed"
                    ],
                }
            )
        batches.append(
            {
                "mode": rows[0]["mode"] if rows else None,
                "repositories": len(rows),
                "totals": dict(totals),
                "items": rows,
            }
        )
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(
            {"schema_version": 1, "publication": "none; preview only", "batches": batches},
            stream,
            indent=2,
        )
        stream.write("\n")


if __name__ == "__main__":
    main()
