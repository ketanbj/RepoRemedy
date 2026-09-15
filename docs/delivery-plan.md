# Delivery mapped to the Letter of Intent

The supplied Word Letter of Intent remains authoritative. The five external user
stories in [user-stories.md](user-stories.md) are unchanged. The
[internal implementation stories](internal-user-stories.md) break that scope into
project-management tickets and identify acceptance work that remains open.

## Review and merge order

Every PR contains at most 500 changed lines of code, tests, scripts and configuration,
measured against its own base. Smaller integration PRs remain small rather than mixing
unrelated stories. Documentation, fixtures, lockfiles and pilot data are reported
separately by the [size check](../scripts/check_pr_size.py).

| Order | Week | PR | Internal stories | Review scope |
| --- | --- | --- | --- | --- |
| 1 | Supporting engineering | [#8](https://github.com/ketanbj/shadowRepoRemedy/pull/8) | RR-304 | PR-size CI and contribution policy |
| 2 | 1 | [#1](https://github.com/ketanbj/shadowRepoRemedy/pull/1) | RR-102 | Installable reader library and common finding contracts |
| 3 | 1 | [#9](https://github.com/ketanbj/shadowRepoRemedy/pull/9) | RR-103 | Typer inspection CLI and command contracts |
| 4 | 1 | [#10](https://github.com/ketanbj/shadowRepoRemedy/pull/10) | RR-104 | GitHub transport, configuration and immutable context |
| 5 | 1 | [#15](https://github.com/ketanbj/shadowRepoRemedy/pull/15) | RR-105 | Source-linked potential remedy inventory; documentation only |
| 6 | 1 | [#2](https://github.com/ketanbj/shadowRepoRemedy/pull/2) | RR-105, RR-106 | Fixed catalog and self-contained preview artifacts |
| 7 | 2 | [#11](https://github.com/ketanbj/shadowRepoRemedy/pull/11) | RR-201 | Local Ollama and hosted HTTP adapters |
| 8 | 2 | [#3](https://github.com/ketanbj/shadowRepoRemedy/pull/3) | RR-202 | Mode selection, bounded previews and isolated model failures |
| 9 | 2 | [#12](https://github.com/ketanbj/shadowRepoRemedy/pull/12) | RR-204 | Publication engine, validation, locking and receipts |
| 10 | 2 | [#4](https://github.com/ketanbj/shadowRepoRemedy/pull/4) | RR-204 | Explicit selection and confirmation through the CLI |
| 11 | 2 | [#13](https://github.com/ketanbj/shadowRepoRemedy/pull/13) | RR-205 | Feedback collection and evidence-based decision classification |
| 12 | 2 | [#5](https://github.com/ketanbj/shadowRepoRemedy/pull/5) | RR-203 | Single/batch consistency and isolated per-repository outcomes |
| 13 | 3 | [#6](https://github.com/ketanbj/shadowRepoRemedy/pull/6) | RR-301, RR-303, RR-304 | Pilot-driven hardening, HTTP-fixture regressions and coverage gate |
| 14 | 3 | [#14](https://github.com/ketanbj/shadowRepoRemedy/pull/14) | RR-302 | Preview pilot results, provenance and reproduction helpers |
| 15 | 3 | [#7](https://github.com/ketanbj/shadowRepoRemedy/pull/7) | RR-101, RR-305, RR-306 | Scope documentation, installation guide and acceptance-gap handoff |
| 16 | Supporting engineering | [#16](https://github.com/ketanbj/shadowRepoRemedy/pull/16) | — | Rename the project, distribution, CLI and Python package; preserve publication compatibility |

These PRs form a dependent stack. Merge in the order above: merge the first PR into
main, retarget the next PR to main, then merge it. Do not merge an upper PR into its
feature-branch base. The repository owner retains release and merge decisions. The
final PR's branch contains the complete implementation and size check for evaluation.

PR #15 documents [potential remedies](remedies.md) for RepoAuditor and Scorecard;
it does not enable new runtime remedies. The implementation portions of
RR-105 and RR-106 share a slice because the fixed remedy catalog and its review
artifacts form one testable outcome. RR-204 has two slices so the publication engine
and user-confirmation flow can each be reviewed within the limit. The adapter and
preview integration slices likewise preserve executable tests at each boundary.

## Supported implementation scope

- Reports: explicit RepoAuditor saved text and OpenSSF Scorecard v5 JSON, with retained evidence.
- Initial catalog: security policies, Dependabot security-update settings and focused branch-protection guidance.
- Models: fixed/non-LLM, local Ollama and a configured OpenAI-compatible hosted endpoint.
- File changes: supported documentation on GitHub.com; settings remain maintainer actions.
- Workflow: independent repository use and batches of 5–10 repositories, followed by explicit selected publication.
- Platforms: Python 3.11 and 3.13 are exercised on Linux, macOS and Windows.

Unsupported findings remain visible. New audit checks, execution of repository code,
autonomous merges, arbitrary source/workflow rewrites, GitHub Enterprise and a web UI
are outside the current implementation. See the user guide for exact limits.

## Acceptance evidence and outstanding work

The [pilot report](pilot.md) separates live preview inference from controlled
HTTP-fixture publication tests. Splitting PRs does not rerun or expand the live pilot.
Existing automated tests and pilot artifacts remain part of the delivered stack.

| Story | Available evidence | Remaining acceptance work |
| --- | --- | --- |
| RR-101 | Supported implementation scope, model configuration, module boundaries and acceptance criteria are documented. | Record owner agreement on scope, model access, designated controlled repositories and named handoff owners. |
| RR-206 | Publication implementation and HTTP-fixture tests are present in RR-204. | Controlled live settings-issue, template-PR and existing-file-PR publication with recorded GitHub links. No PR in this restack claims this work complete. |
| RR-302 | Ten-repository preview evidence across all three modes, with mixed report formats and recorded outcomes. | Record any further human proposal-quality review, required edits and unresolved correctness issues against the LoI checklist. |
| RR-303 | Automated stale-content, deduplication, direct/fork and recovery regressions; single-publisher guidance. | Controlled live direct/fork publication, retry and interruption recovery evidence in designated repositories. |
| RR-304 | Cross-platform tests, lint, formatting, typing and the 90% branch-inclusive coverage gate; original pilot dependency-audit record. | Refresh and retain dependency-audit evidence for the release actually approved. |
| RR-305 | Installation guide, package builds and outside-checkout smoke validation. | Publish the distribution only after the owner approves distribution prerequisites. |
| RR-306 | Handoff and limitations documentation. | Select the distribution license, establish a private security contact, name the release approver and maintenance contact, and record checklist acceptance or agreed scope/schedule changes. |

Week four collects maintainer usefulness, effort, merges, explicit acceptance,
adjustments, declines and pending responses. Silence and issue closure alone are not
acceptance. Pending maintainer feedback is distinct from unmet engineering or live
publication criteria.
