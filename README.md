# RepoRemedy

Turn an existing repository audit into focused GitHub issues and draft pull requests.
An auditor can support 5–10 repositories in one batch; a maintainer can use the same
workflow for their own repository.

**Input: report + mode → Output: review and publish → Feedback: act and respond in GitHub.**

RepoRemedy consumes RepoAuditor text or OpenSSF Scorecard JSON. It is a standalone
companion: no plugins, imports, or changes to either auditor. It acts on existing
findings and does not add new best-practice checks.

## Start with a preview

The CLI uses Typer for typed commands, help, and optional shell completion.
Requires Python 3.11+ and a GitHub repository. From a checkout of the implementation:

```sh
uv tool install .
reporemedy --help
# Run directly from this checkout without a persistent tool install:
uvx --from . reporemedy --help
reporemedy preview report.json --repo OWNER/REPO --report-type ossf-scorecard --out runs/first
```

No model setup is needed for the default **non-LLM** mode. If you already use
`gh auth login`, RepoRemedy reuses that session. Otherwise, copy `.env.example` to
`.env` and set `GITHUB_TOKEN`. An unauthenticated public preview also works within
GitHub's lower rate limit. Nothing is published by `preview`.

Read `runs/first/README.md`, the individual proposal Markdown, and the `.patch`
files. Each proposal explains purpose, impact, effort, exact action steps,
verification, original evidence, and any fields the maintainer needs to fill.

```sh
# Replace PROPOSAL_ID with an ID from the preview. The CLI asks for confirmation.
reporemedy publish runs/first --select PROPOSAL_ID
reporemedy feedback runs/first
```

A maintainer receives one of three actionable outcomes:

| Action | GitHub interaction |
| --- | --- |
| Change a setting | Issue with settings link/navigation, required value and verification |
| Add a template file | Draft PR with prepared content and explicit project-specific inputs |
| Change an existing file | Draft PR with a focused diff and validation steps |

Maintainers review, adapt, merge, decline and comment in GitHub. They do not need
to install RepoRemedy to respond. Acting easily means lowering specialist knowledge,
research and manual effort; templates must disclose the remaining work.

## Choose a report and mode

```sh
reporemedy preview report.txt --repo OWNER/REPO --report-type repoauditor --out runs/text
reporemedy preview report.json --repo OWNER/REPO --report-type ossf-scorecard --mode local-llm --out runs/local
reporemedy preview report.json --repo OWNER/REPO --report-type ossf-scorecard --mode llm --out runs/hosted
reporemedy batch batch.json --out runs/pilot --mode non-llm
```

| Mode | Setup |
| --- | --- |
| `non-llm` (default) | Fixed reviewed response catalog; no model credentials |
| `local-llm` | Running Ollama and `OLLAMA_MODEL` in `.env` |
| `llm` | `LLM_BASE_URL`, `LLM_MODEL`, and provider credentials when required |

Both model modes consult the report and relevant repository guidelines. Hosted mode
sends that context to your configured provider. The initial automated file scope is
repository documentation; arbitrary source-code/workflow edits are outside this pilot.
The default `--limit 3` focuses proposals and bounds model calls per repository.
Unsupported, deferred, unavailable and failed findings stay visible in the summary.
Model modes never silently fall back to another mode.

## Reports are generated separately

Use a saved RepoAuditor `--output` text report or Scorecard v5 `--format json` export.
For example, with the corresponding upstream tool installed:

```sh
repoauditor --include CommunityStandards --CommunityStandards-url https://github.com/OWNER/REPO --output report.txt
scorecard --repo=github.com/OWNER/REPO --format=json > report.json
```

See [supported formats](docs/report-formats.md) before importing older exports.
Report generation is not part of the RepoRemedy command or runtime dependencies.

## Documentation

- [Batch manifests and exit codes](docs/batches.md)
- [Fixed remedy coverage](docs/remedies.md)
- [Local/hosted setup and data handling](docs/models.md)
- [Publication, permissions, retries and feedback](docs/publication.md)
- [Architecture and extension boundaries](docs/architecture.md)
- [LoI delivery plan and PR order](docs/delivery-plan.md)
- [Beta pilot evidence and limitations](docs/pilot.md)
- [Development and release checks](CONTRIBUTING.md)

## Development

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov --cov-fail-under=90
uv build
```

GitHub CI runs these checks on Linux, macOS and Windows with Python 3.11 and 3.13.
Publication always requires selected IDs and confirmation. PRs remain drafts;
RepoRemedy never changes settings directly, force-pushes or merges changes.
