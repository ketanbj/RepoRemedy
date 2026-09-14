"""Versioned contracts shared by independent adapters."""

import re
from enum import StrEnum
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportType(StrEnum):
    REPOAUDITOR = "repoauditor"
    SCORECARD = "ossf-scorecard"


class Mode(StrEnum):
    FIXED = "non-llm"
    LOCAL = "local-llm"
    HOSTED = "llm"


def repository_name(value: str) -> str:
    """Accept only GitHub repository identities, never arbitrary HTTP targets."""
    value = value.strip().rstrip("/")
    if value.startswith("github.com/"):
        value = "https://" + value
    if "://" in value:
        url = urlsplit(value)
        if url.scheme != "https" or url.netloc != "github.com" or url.query or url.fragment:
            raise ValueError("Use https://github.com/OWNER/REPO or OWNER/REPO")
        value = url.path.lstrip("/")
    value = value.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9_.-]{1,100}", value):
        raise ValueError("Expected a GitHub OWNER/REPO (a website is not a repository)")
    if value.split("/")[1] in {".", ".."}:
        raise ValueError("Invalid repository name")
    return value


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class Finding(Contract):
    key: str = Field(min_length=1, max_length=200)
    status: str
    evidence: str = Field(min_length=1, max_length=100_000)
    score: int | None = Field(default=None, ge=-1, le=10)


class Report(Contract):
    repository: str
    report_type: ReportType
    source_version: str
    source_sha256: str
    source_commit: str | None = None
    findings: list[Finding]
    notices: list[str] = Field(default_factory=list)

    _repository = field_validator("repository")(repository_name)
