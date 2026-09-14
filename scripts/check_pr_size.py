"""Count reviewable code changes against a pull request's merge base."""

import subprocess
import sys
from pathlib import PurePosixPath

MAX_LINES = 500
CODE_SUFFIXES = {
    ".py",
    ".pyi",
    ".sh",
    ".bash",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".toml",
    ".yaml",
    ".yml",
}
CODE_NAMES = {"Dockerfile", "Makefile", ".env.example"}


def is_code(path: str) -> bool:
    file = PurePosixPath(path)
    if "fixtures" in file.parts:
        return False
    return file.suffix in CODE_SUFFIXES or file.name in CODE_NAMES


def changed_lines(numstat: str) -> tuple[int, int]:
    """Parse NUL-delimited git output, including rename records and binary files."""
    records = iter(numstat.split("\0"))
    counted = excluded = 0
    for record in records:
        if not record:
            continue
        added, deleted, path = record.split("\t", 2)
        paths = [path] if path else [next(records), next(records)]
        if added == "-" or deleted == "-":
            continue
        size = int(added) + int(deleted)
        if any(is_code(name) for name in paths):
            counted += size
        else:
            excluded += size
    return counted, excluded


def main(args: list[str]) -> int:
    if len(args) != 2:
        print("Usage: python scripts/check_pr_size.py BASE_SHA HEAD_SHA", file=sys.stderr)
        return 2
    # Resolve revisions before constructing the range; never interpret them as flags.
    revisions = [
        subprocess.check_output(
            ["git", "rev-parse", "--verify", "--end-of-options", value + "^{commit}"],
            text=True,
        ).strip()
        for value in args
    ]
    diff = subprocess.check_output(
        ["git", "diff", "--numstat", "-z", "--find-renames", "...".join(revisions), "--"],
    ).decode("utf-8", errors="surrogateescape")
    counted, excluded = changed_lines(diff)
    print(f"Code, tests, scripts and configuration: {counted}/{MAX_LINES} changed lines")
    print(f"Documentation, fixtures, generated data and other non-code: {excluded} lines")
    if counted > MAX_LINES:
        print("Split this PR into cohesive, independently testable changes.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
