# Beta pilot — 13 September 2026

The tool was run in preview mode against **all ten entries** identified by
`GT_OSS_Repos_normalized.csv` in the supplied `oss-security-audit-tools` checkout.
No beta issues, PRs, settings changes or maintainer messages were published.

Nine inputs were the prototype's existing Scorecard v5.5.0 history exports, each
containing one scan. The tenth CSV entry was a website (`vizfold.github.io`): its
homepage links to `AI2Science/vizfold-foundation`. A fresh report was generated
separately using the unmodified reference RepoAuditor CommunityStandards module
for that repository. Therefore this is a mixed **nine Scorecard + one RepoAuditor**
batch, not ten fresh Scorecard scans. Older report commits remain visible as stale
context where they differ from the current default branch.

## Observed results

Each mode processed the ten-repository batch with `--limit 3`. Both model modes
made real inference calls. No mocked response is counted in the table below.

| Mode | Repositories processed | Reviewable proposals | Rejected/failed findings | Needs input |
| --- | ---: | ---: | ---: | ---: |
| Fixed (`non-llm`) | 10 | 17 | 0 | 0 |
| Local Ollama (`local-llm`) | 10 | 20 | 7 | 3 |
| Hosted (`llm`) | 10 | 25 | 2 | 3 |

The fixed run also recorded 81 unsupported and 21 skipped findings. Both model
runs recorded 89 skipped findings, primarily because of the three-call limit.
A completed repository processing pass does **not** mean every finding was fixed.
The model batches exit 1 because rejected/failed findings are explicitly retained.

| Repository | Fixed proposals | Local proposals | Hosted proposals |
| --- | ---: | ---: | ---: |
| poloclub/transformer-explainer | 2 | 2 | 3 |
| borglab/gtsam | 2 | 3 | 2 |
| vortexgpgpu/vortex | 2 | 2 | 3 |
| gt-tinker/qwerty | 1 | 1 | 3 |
| apache/airavata-custos | 1 | 2 | 2 |
| AI2Science/vizfold-foundation | 1 | 1 | 2 |
| psi4/psi4 | 2 | 2 | 3 |
| MolSSI/QCSchema | 2 | 3 | 3 |
| slimgroup/InvertibleNetworks.jl | 2 | 2 | 2 |
| sharc-lab/Edge-MoE | 2 | 2 | 2 |

The action mix was:

- Fixed: 8 new-file templates and 9 settings issues.
- Local: 11 new-file templates and 9 settings issues.
- Hosted: 11 new-file templates, 11 settings issues and 3 existing-file edits.

The hosted Qwerty preview, for example, proposed filling its existing SECURITY.md
rather than replacing the repository blindly. These are proposals for human review;
schema validation is not a finding that their technical claims are correct.

[Machine-readable evidence](pilot-results.json) records each repository, source
report hash/version, inspected commit, action counts, outcomes and rejection reasons.
It omits private contact metadata and full report contents. The pilot used
Ollama 0.32.14 with `qwen2.5:3b` locally and `gpt-oss:120b-cloud` through the local
authenticated Ollama gateway for **hosted** inference. Early pilot runs preceded
addition of model-name provenance to run.json; their JSON field is null, with the
actual model configuration recorded here. Later runs record the model name directly.

## What the pilot changed

Early runs exposed a local schema-grammar incompatibility and irrelevant vendored
README files consuming model context. PR 6 addresses both. The table uses the revised
model runs, not those initial attempts. Remaining rejected output included out-of-scope
files, an unchanged existing file, mismatched file action, missing proposal content,
and invalid schema. One hosted finding encountered an endpoint failure. These were
visible outcomes and never became publishable items; they are not hidden retries.

## Validation and limits

The original pilot suite passed **115 tests with 92.07% branch-inclusive coverage**.
After the Typer CLI migration, the local suite passes **153 tests with 93.66%
branch-inclusive coverage**, including 100% coverage of the CLI module. New CLI
checks cover typed options, help/version, JSON output, all three modes, publication
confirmation and cancellation, and partial-failure exit codes. The pilot inference
results above are unchanged; the migration did not rerun the live beta batches.
The wheel and source distribution built successfully; the wheel was installed in a
clean environment and both report readers ran outside the checkout. A dependency
audit found no known vulnerabilities (the unpublished project itself is not in PyPI).

Automated tests cover both report types in each mode, standalone dependency boundaries,
single/batch CLI flows, existing empty-file changes, fork/direct publication contracts,
stale-preview and original-content rejection, retry deduplication, exact branch recovery,
config/credential handling, and evidence-based feedback classification. CI runs all tests,
formatting, lint, strict type checks and package builds on Linux/macOS/Windows with
Python 3.11 and 3.13, with a 90% branch-inclusive coverage gate.

The GitHub **write** workflow is tested using controlled HTTP fixtures. Actual beta
publication was not authorized in this implementation run, so maintainer acceptance,
merge rates, real settings adoption and user-reported effort are **not measured yet**.
Week-four follow-up requires authorized pilot publication and maintainer responses.
The initial model/file scope and concurrency limits are documented in the user guide.
This is a tested release candidate, not a claim of universal remediation or completed
maintainer validation.

## Reproduce without publishing

Keep the private CSV and saved reports outside this public repository. Generate the
VizFold report separately with the reference RepoAuditor:

```sh
repoauditor --include CommunityStandards --CommunityStandards-url https://github.com/AI2Science/vizfold-foundation --output /absolute/path/VizFold.txt
```

Create an override file (use your actual absolute report path):

```json
{"VizFold": {"repository": "AI2Science/vizfold-foundation", "report": "/absolute/path/VizFold.txt", "report_type": "repoauditor"}}
```

Then, from a RepoRemedy checkout:

```sh
uv run python scripts/prepare_pilot.py /path/to/GT_OSS_Repos_normalized.csv --scorecard-dir /path/to/oss-security-audit-tools/results/history --overrides overrides.json --out batch.json
uv run reporemedy batch batch.json --mode non-llm --out runs/fixed
uv run reporemedy batch batch.json --mode local-llm --out runs/local
uv run reporemedy batch batch.json --mode llm --out runs/hosted
uv run python scripts/summarize_pilot.py runs/fixed runs/local runs/hosted --out pilot-results.json
```

Configure `.env` for the modes you run. Use new output directories each time. GitHub
state and model outputs change, so exact proposal counts are not deterministic.
Review every proposed issue and diff before any later `publish` command.
