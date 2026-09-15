# Contributing and release checks

Use Python 3.11+ and `uv sync --locked`. Code lives under `src/reporemedy`; tests use
in-memory HTTP transports and temporary files, with no production credentials.

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov --cov-fail-under=90
uv build
uv run pip-audit --local --progress-spinner off
```

Do not add upstream RepoAuditor/Scorecard imports. Keep parsing, context, remediation,
publication and feedback separate. A new remedy needs evidence-backed applicability,
stale/current-file behavior, purpose/impact/effort, exact actions, required inputs,
verification steps, meaningful tests and a catalog/documentation update.

## Pull request size

Aim for 300–500 changed code lines per PR, with a maximum of 500. Smaller PRs are
welcome when they deliver a complete, independently testable change. Count additions
plus deletions, including tests, scripts, and build/CI configuration. Keep the tests
for a behavior with its implementation; do not remove tests to meet the limit.

The `PR size / size` check compares each PR head with the merge base of its target
branch, so stacked PRs count only their own changes. It counts Python, shell,
JavaScript/TypeScript, TOML, YAML, Dockerfiles, Makefiles, and `.env.example` files.
Fixtures, documentation, lockfiles, and data files are excluded from the code limit
and reported separately. Keep those changes focused and reviewable as well.

Run the same check locally with the actual base and head commit references:

```sh
python scripts/check_pr_size.py BASE_SHA HEAD_SHA
python scripts/test_pr_size.py
```

When a PR exceeds the limit, split it along module or behavior boundaries and keep
each slice buildable and tested. Update PR dependencies and the delivery map when
changing the stack. Keep commits signed with the repository owner's configured key.

A new provider must not bypass output validation or silently send local-mode prompts
to a hosted service. Never log credentials or raw HTTP error bodies. Treat reports,
repository instructions and model output as untrusted. Do not execute proposed commands.
Model tests should cover malformed responses, wrong paths, missing content, secret-like
content, duplicate changes and no-op changes, not only successful responses.

CI runs Linux/macOS/Windows on Python 3.11 and 3.13 and enforces 90% aggregate
branch-inclusive coverage. Live beta previews are opt-in and are not CI tests:
they require network/model access, change over time and must not publish to maintainers
without authorization. See [pilot reproduction](docs/pilot.md).

Before a release, check all stack PRs, rerun CI and dependency audit, build wheel and
source distribution, install the wheel in a clean environment, and run CLI smoke tests
outside the checkout. Tagging or publishing a distribution is a separate owner action.
The project has not yet selected a distribution license; do not assume permission to
relicense this tool or choose licenses for target repositories.
