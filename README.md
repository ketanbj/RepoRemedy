# RepoRemedy

Standalone remediation for existing repository audit reports. This foundation
normalizes saved RepoAuditor text and Scorecard v5 JSON through independent readers.
It does not import or modify either auditor. The next slice adds the Typer CLI.

Use Python 3.11+ and `uv sync --locked`. Run `uv run pytest` to validate the readers.
See [supported report formats](docs/report-formats.md) and [contribution policy](CONTRIBUTING.md).
