"""OpenSSF Scorecard v5 JSON and the OSPO prototype's report envelopes."""

import json
from typing import Any

from reporemedy.errors import RemedyError
from reporemedy.models import Finding, Report, ReportType, repository_name


def read_scorecard(text: str, repository: str, digest: str) -> Report:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise RemedyError("Scorecard report must be JSON (--format json)") from exc
    # Prototype history files wrap reports in {meta, scorecard}; never retain contact metadata.
    candidates = data if isinstance(data, list) else [data]
    matching: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            raise RemedyError("Invalid Scorecard report object")
        report = item.get("scorecard") if "meta" in item else item
        if not isinstance(report, dict):
            raise RemedyError("Invalid Scorecard envelope")
        try:
            identity = repository_name(report["repo"]["name"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RemedyError("Scorecard report has no valid repository identity") from exc
        if identity.casefold() == repository.casefold():
            matching.append(report)
    if not matching:
        raise RemedyError("Report repository does not match the requested repository")
    if len(matching) != 1:
        raise RemedyError(
            "Multiple reports match; export exactly one scan to avoid stale selection"
        )
    report = matching[0]
    version = report.get("scorecard", {}).get("version", "")
    if not isinstance(version, str) or not version.startswith("v5."):
        raise RemedyError("Supported Scorecard exports: v5.x JSON with checks[]")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        raise RemedyError("Scorecard checks[] is missing or empty")
    findings: list[Finding] = []
    seen: set[str] = set()
    for check in checks:
        if (
            not isinstance(check, dict)
            or not isinstance(check.get("name"), str)
            or not check["name"]
            or type(check.get("score")) is not int
            or not -1 <= check["score"] <= 10
            or not isinstance(check.get("reason"), str)
            or not check["reason"]
        ):
            raise RemedyError("Each Scorecard check needs name, integer score [-1,10], and reason")
        if check["name"] in seen:
            raise RemedyError("Duplicate Scorecard check names are ambiguous")
        seen.add(check["name"])
        if check["score"] == 10:
            continue
        findings.append(
            Finding(
                key=check["name"],
                status="unavailable" if check["score"] < 0 else "gap",
                score=check["score"],
                evidence=json.dumps(check, ensure_ascii=False, sort_keys=True),
            )
        )
    return Report(
        repository=repository,
        report_type=ReportType.SCORECARD,
        source_version=version,
        source_sha256=digest,
        source_commit=report["repo"].get("commit"),
        findings=findings,
        notices=["Scores below 10 are candidate gaps, not proof of a particular fix."],
    )
