"""Prepare review artifacts; publication is a separate operation."""

import difflib
from pathlib import Path

from reporemedy.catalog import propose_fixed
from reporemedy.errors import RemedyError
from reporemedy.models import Context, Mode, Outcome, Proposal, Report, Run


def prepare(report: Report, context: Context) -> Run:
    proposals: list[Proposal] = []
    outcomes: list[Outcome] = []
    for finding in report.findings:
        result = propose_fixed(finding, context)
        if isinstance(result, Proposal):
            if any(p.id == result.id for p in proposals):
                outcomes.append(
                    Outcome(
                        finding=finding.key,
                        status="skipped",
                        message="Duplicate finding; see existing proposal.",
                    )
                )
                continue
            proposals.append(result)
            outcomes.append(
                Outcome(
                    finding=finding.key,
                    status="proposed",
                    message=result.title,
                    proposal_id=result.id,
                )
            )
        else:
            outcomes.append(result)
    notices = report.notices + context.notices
    if report.source_commit and report.source_commit != context.commit:
        notices.append(
            "Report commit differs from current default branch; review stale evidence carefully."
        )
    return Run(
        repository=report.repository,
        mode=Mode.FIXED,
        report=report,
        default_branch=context.default_branch,
        base_commit=context.commit,
        proposals=proposals,
        outcomes=outcomes,
        notices=notices,
    )


def body(proposal: Proposal) -> str:
    parts = [
        f"# {proposal.title}",
        f"**Purpose:** {proposal.purpose}",
        f"**Impact:** {proposal.impact}",
        f"**Effort:** {proposal.effort}",
        "## Action\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(proposal.steps, 1)),
        "## Verify\n" + "\n".join(f"- {s}" for s in proposal.validation),
    ]
    if proposal.required_inputs:
        parts.append(
            "## Required project inputs\n" + "\n".join(f"- {s}" for s in proposal.required_inputs)
        )
    if proposal.warnings:
        parts.append("## Review notes\n" + "\n".join(f"- {s}" for s in proposal.warnings))
    parts.extend(
        [
            f"## Original finding: {proposal.finding.key}\n\n"
            + "\n".join("> " + line for line in proposal.finding.evidence.splitlines()),
            "## Feedback\nPlease comment: useful, too difficult, or needs adjustment. "
            "Describe effort, required edits, and whether you adopted or declined the suggestion.",
        ]
    )
    return "\n\n".join(parts) + "\n"


def write_preview(run: Run, directory: Path) -> None:
    # Exclusive creation prevents clobbering an earlier reviewed run.
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise RemedyError("Output already exists; choose a new --out directory") from exc
    (directory / "run.json").write_text(run.model_dump_json(indent=2) + "\n", encoding="utf-8")
    lines = [f"# {run.repository} — {run.mode}", f"Base commit: `{run.base_commit}`", ""]
    for proposal in run.proposals:
        filename = f"{proposal.id}.md"
        (directory / filename).write_text(body(proposal), encoding="utf-8")
        lines.append(f"- [{proposal.id}: {proposal.title}]({filename}) ({proposal.action})")
        patch: list[str] = []
        for change in proposal.changes:
            patch.extend(
                difflib.unified_diff(
                    (change.previous_content or "").splitlines(keepends=True),
                    change.content.splitlines(keepends=True),
                    fromfile=f"a/{change.path}" if change.previous_sha else "/dev/null",
                    tofile=f"b/{change.path}",
                )
            )
        if patch:
            (directory / f"{proposal.id}.patch").write_text("".join(patch), encoding="utf-8")
    lines.extend(
        ["", "## All findings"] + [f"- {o.finding}: {o.status} — {o.message}" for o in run.outcomes]
    )
    lines.extend(["", "## Context notes"] + [f"- {n}" for n in run.notices])
    (directory / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
