# RepoRemedy

Turn existing RepoAuditor or OpenSSF Scorecard findings into focused, reviewable
repository improvements. RepoRemedy is a standalone companion, with no code-level
integration into either auditor.

The CLI uses Typer for typed commands, help, and optional shell completion.
Requires Python 3.11+. Development setup:

```sh
uv sync
uv run reporemedy --help
uv run reporemedy inspect report.json --repo OWNER/REPO --report-type ossf-scorecard
uv run pytest
uv run ruff check .
uv run mypy
```

Report import is read-only. See [supported report formats](docs/report-formats.md).
Remediation and publication are delivered in subsequent, dependent PRs.
