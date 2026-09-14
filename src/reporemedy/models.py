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


class RepositoryFile(Contract):
    content: str
    sha: str


class Context(Contract):
    repository: str
    default_branch: str
    commit: str
    tree_sha: str
    paths: list[str]
    files: dict[str, RepositoryFile]
    settings: dict[str, bool | None] = Field(default_factory=dict)
    notices: list[str] = Field(default_factory=list)


class Change(Contract):
    path: str
    content: str = Field(min_length=1, max_length=64_000)
    previous_content: str | None = Field(default=None, max_length=64_000)
    previous_sha: str | None = None

    @field_validator("path")
    @classmethod
    def safe_path(cls, value: str) -> str:
        parts = value.split("/")
        if (
            not value
            or len(value) > 240
            or any(p in {"", ".", ".."} for p in parts)
            or any(c in value for c in "\\\x00\r\n:")
            or any(p.lower() == ".git" or p.lower().startswith(".env") for p in parts)
        ):
            raise ValueError("Unsafe repository file path")
        return value


class Proposal(Contract):
    id: str = Field(pattern=r"^[a-f0-9]{16}$")
    finding: Finding
    action: str = Field(pattern=r"^(setting|add-file|edit-file)$")
    title: str = Field(min_length=1, max_length=180)
    purpose: str = Field(min_length=1, max_length=4000)
    impact: str = Field(min_length=1, max_length=4000)
    effort: str = Field(min_length=1, max_length=2000)
    steps: list[str] = Field(min_length=1, max_length=20)
    validation: list[str] = Field(min_length=1, max_length=20)
    required_inputs: list[str] = Field(default_factory=list)
    changes: list[Change] = Field(default_factory=list, max_length=5)
    warnings: list[str] = Field(default_factory=list)


class Outcome(Contract):
    finding: str
    status: str = Field(pattern=r"^(proposed|unsupported|skipped|needs-input|failed)$")
    message: str
    proposal_id: str | None = None


class Run(Contract):
    schema_version: int = Field(default=1, ge=1, le=1)
    repository: str
    mode: Mode
    report: Report
    default_branch: str
    base_commit: str
    proposals: list[Proposal]
    outcomes: list[Outcome]
    notices: list[str] = Field(default_factory=list)

    _repository = field_validator("repository")(repository_name)
