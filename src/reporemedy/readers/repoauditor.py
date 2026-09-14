"""Parse saved Rich panels emitted by RepoAuditor Display.py (c682a78)."""

import re

from reporemedy.errors import RemedyError
from reporemedy.models import Finding, Report, ReportType

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
HEADER = re.compile(r"\[(Success|Warning|Error|DoesNotApply)\]\s+([A-Za-z][A-Za-z0-9_]*)")
BORDER = " │┃╭╮╰╯┌┐└┘─━┬┴┼├┤"


def read_repoauditor(text: str, repository: str, digest: str) -> Report:
    lines = ANSI.sub("", text).splitlines()
    findings: list[Finding] = []
    seen = 0
    current: tuple[str, str] | None = None
    body: list[str] = []

    def finish() -> None:
        if current and current[0] in {"Warning", "Error"}:
            evidence = "\n".join(body).strip()
            if not evidence:
                raise RemedyError("RepoAuditor finding has no evidence; export complete panels")
            findings.append(Finding(key=current[1], status=current[0].lower(), evidence=evidence))

    for line in lines:
        header = HEADER.search(line)
        # Require a panel border: quoted headers in descriptions must not become findings.
        if header and any(char in line[: header.start()] for char in "╭┌"):
            finish()
            current = (header[1], header[2])
            body = []
            seen += 1
        elif current and any(char in line for char in "╰└"):
            finish()
            current = None
            body = []
        elif current:
            body.append(line.strip(BORDER))
    if current:
        raise RemedyError("Truncated RepoAuditor panel; regenerate the saved report")
    if not seen:
        # Non-verbose successful reports only contain summary metrics.
        has_metrics = all(re.search(rf"{name}:\s+0\s+\(", text) for name in ("Warnings", "Errors"))
        if not (has_metrics and "Successful:" in text and "Metrics" in text):
            raise RemedyError(
                "Unrecognized RepoAuditor export; use saved --output text with intact panels"
            )
    return Report(
        repository=repository,
        report_type=ReportType.REPOAUDITOR,
        source_version="Display.py@c682a78",
        source_sha256=digest,
        findings=findings,
        notices=["RepoAuditor text has no repository identity or commit; URL is user-supplied."],
    )
