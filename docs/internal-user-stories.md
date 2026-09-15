# Internal implementation stories

These engineering tickets derive from the supplied Letter of Intent and support the
five fixed [external user stories](user-stories.md). Acceptance criteria below are
requirements, not claims that all work is complete. The [delivery map](delivery-plan.md)
links each implementation slice to a PR and records outstanding evidence and decisions.

## Epic 1 — Week 1 — Report ingestion and initial remedy preview

### RR-101 — Agree scope and supported environments

As the technical lead, I want to agree the initial remedy scope and supported
environments so the team has a testable delivery boundary.

Acceptance: record supported report versions, documentation file types, platforms,
models, remedy catalog and acceptance checklist; identify test repositories and
handoff owners. Documentation is supplied by PR #7; owner agreement remains open.

### RR-102 — Normalize both report formats

As a developer, I want separate RepoAuditor and Scorecard readers so both report
formats produce a common finding model.

Acceptance: explicit report-type selection works; source evidence is retained;
malformed, ambiguous and unsupported inputs receive clear outcomes. PR #1.

### RR-103 — Expose an installable Typer CLI

As a developer, I want an installable Typer CLI so users can inspect reports through
a consistent command interface.

Acceptance: package entry point, inspect, help and version work; required arguments
are validated; JSON output and exit codes are tested. PR #9.

### RR-104 — Retrieve immutable repository context

As a developer, I want to retrieve repository context at a recorded commit so
remedies reflect the files actually reviewed.

Acceptance: capture relevant guidance and existing files with commit/file references;
handle unavailable context; do not execute repository code. PR #10.

### RR-105 — Implement the fixed remedy catalog

As a developer, I want a reviewed catalog of fixed remedies so supported findings
produce useful proposals without an LLM.

Acceptance: cover security policies, Dependabot settings and branch-protection
guidance; respect existing content; retain unsupported findings. PR #15 supplies
the source-linked potential remedy inventory; PR #2 implements the initial fixed
catalog. Additional candidates in the inventory remain future implementation work.

### RR-106 — Produce self-contained preview artifacts

As a developer, I want self-contained preview artifacts so users can review proposed
actions before publication.

Acceptance: produce Markdown proposals and applicable diffs with evidence, purpose,
impact, required inputs and validation instructions; preview performs no publication.
PR #2.

## Epic 2 — Week 2 — Modes, batches and controlled publication

### RR-201 — Implement local and hosted model adapters

As a developer, I want local Ollama and hosted model adapters so users can choose
either alongside fixed remediation.

Acceptance: all three explicit modes work with both report types; validate model
configuration and call limits; close clients reliably. PR #11 supplies the adapters;
PR #3 completes their CLI and preview integration.

### RR-202 — Ground and validate model proposals

As a developer, I want model proposals grounded in repository guidance and validated
against a common contract so they remain reviewable and bounded.

Acceptance: include finding evidence and relevant guidance; reject malformed or
out-of-scope output; expose missing/conflicting guidance for user resolution; isolate
individual failures. PR #11 provides provider validation; PR #3 integrates it into runs.

### RR-203 — Share single and batch behavior

As a developer, I want single-repository and batch workflows to share remediation
behavior so independent maintainers and auditors receive consistent results.

Acceptance: process 5–10 repositories with explicit report types; preserve individual
artifacts and summaries; continue after one input fails; return a partial-failure
exit code. PR #5.

### RR-204 — Publish selected and confirmed proposals

As a developer, I want to publish only selected and confirmed proposals so users
control GitHub changes.

Acceptance: settings proposals create issues and file proposals create draft PRs;
support direct/fork contributions; check stale content and duplicates; persist
publication receipts. PR #12 supplies the engine; PR #4 supplies user confirmation.

### RR-205 — Collect feedback and explicit decisions

As a developer, I want to retrieve comments, reviews and decision outcomes so
maintainer feedback can be evaluated accurately.

Acceptance: preserve free-text feedback; distinguish merges, explicit acceptance,
adjustments, declines and pending responses; never infer acceptance from closure alone.
PR #13.

### RR-206 — Validate controlled live publication

As a QA engineer, I want controlled live publication tests so we verify the workflow
against GitHub itself.

Acceptance: in designated repositories publish a settings issue, template PR and
existing-file PR; verify actionable content; record commands, results and GitHub links.
Outstanding follow-up: no implementation PR or fixture result is a substitute for this evidence.

## Epic 3 — Week 3 — Release validation, hardening and handoff

### RR-301 — Fix failures observed in pilot runs

As a developer, I want to fix failures discovered during pilot runs so supported
models and repository inputs behave reliably.

Acceptance: resolve model-schema compatibility and irrelevant-context issues; handle
malformed upstream responses; expose placeholders and stale-context warnings; add
regression coverage. PR #6.

### RR-302 — Record reproducible beta preview evidence

As a QA engineer, I want reproducible previews across 5–10 beta repositories so we can
assess proposal quality and supported scope.

Acceptance: cover both report types and all three modes across the pilot; record
provenance, inspected commits, model configuration, outcomes, required edits and
quality limitations. PR #14 preserves the original preview evidence and reproduction
scripts; the delivery map identifies the remaining human quality review.

### RR-303 — Validate publication recovery and failure behavior

As a QA engineer, I want publication recovery and failure tests so retries and
interruptions do not create unsafe or duplicate changes.

Acceptance: demonstrate live direct/fork publication, stale-preview rejection,
deduplication and interrupted-publication recovery; automate permission failures;
test concurrency or document a single-publisher restriction. PRs #12 and #6 provide
automated regressions; controlled live evidence remains outstanding.

### RR-304 — Automate engineering and dependency checks

As a developer, I want automated engineering and dependency checks so release quality
is measurable and repeatable.

Acceptance: CI passes tests, lint, formatting and strict typing on supported platforms;
branch-inclusive coverage is at least 90%; record vulnerability-scan results and their
disposition. PR #8 adds the PR-size guardrail; PRs #1 and #6 provide the engineering
pipeline and coverage gate. Refresh the audit for the release candidate being approved.

### RR-305 — Verify package installation and user guidance

As a release engineer, I want a verified package and installation guide so a new user
can run RepoRemedy outside the development checkout.

Acceptance: build distributions; verify clean installation and CLI smoke tests outside
the checkout; document configuration, sample reports, commands and limits. PR #7,
using the sample report and reproduction helpers in PR #14.

### RR-306 — Record release acceptance and handoff

As the release owner, I want an evidence-based acceptance and handoff record so the
candidate can be approved for supervised use.

Acceptance: map evidence to each LoI criterion; record unmet items and agreed
scope/schedule changes; confirm owner, approver and maintenance contact; resolve the
license and private security contact before public distribution. PR #7 documents the
handoff requirements; the named owner decisions and acceptance remain outstanding.
