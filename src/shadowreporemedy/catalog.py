"""Small, reviewed response catalog; acts only on imported findings."""

import hashlib
from collections.abc import Callable

from shadowreporemedy.models import Change, Context, Finding, Outcome, Proposal

SECURITY_PATHS = (".github/SECURITY.md", "docs/SECURITY.md", "SECURITY.md")


def proposal_id(repository: str, finding: str) -> str:
    return hashlib.sha256(f"{repository.casefold()}:{finding}".encode()).hexdigest()[:16]


def security(finding: Finding, context: Context) -> Proposal | Outcome:
    existing = next((p for p in SECURITY_PATHS if p in context.paths), None)
    if existing:
        file = context.files.get(existing)
        if file is None:
            return Outcome(
                finding=finding.key,
                status="needs-input",
                message="Existing security policy could not be read; inspect it manually.",
            )
        if file.content.strip():
            return Outcome(
                finding=finding.key,
                status="skipped",
                message=f"{existing} has a policy; rerun the audit before replacing it.",
            )
    path = existing or "SECURITY.md"
    template = (
        "# Security Policy\n\n## Reporting a vulnerability\n\n"
        "Please do not report vulnerabilities in public issues.\n"
        "TODO: Replace this line with a monitored private reporting address or enable and "
        "link GitHub private vulnerability reporting.\n\n## Supported versions\n\n"
        "TODO: List the versions receiving security fixes and the upgrade path "
        "for unsupported versions.\n"
    )
    return Proposal(
        id=proposal_id(context.repository, finding.key),
        finding=finding,
        action="edit-file" if existing else "add-file",
        title="Document security reporting",
        purpose="Give vulnerability reporters a private route to the project maintainers.",
        impact="Adds documentation only; does not enable a reporting service or promise an SLA.",
        effort="Fill two project-specific fields, review the policy, and merge the draft PR.",
        steps=[
            "Set a monitored private reporting route.",
            "List supported versions.",
            "Remove the TODO lines after filling the template, then review and merge.",
        ],
        validation=[
            "Confirm the reporting route works privately and is monitored.",
            "Confirm the supported-version statements match project policy.",
        ],
        required_inputs=["Private reporting route", "Supported versions"],
        changes=[
            Change(
                path=path,
                content=template,
                previous_content=context.files[path].content if existing else None,
                previous_sha=context.files[path].sha if existing else None,
            )
        ],
    )


def dependabot(finding: Finding, context: Context) -> Proposal | Outcome:
    if context.settings.get("dependabot_security_updates"):
        return Outcome(
            finding=finding.key,
            status="skipped",
            message="Dependabot security updates are already enabled.",
        )
    url = f"https://github.com/{context.repository}/settings/security_analysis"
    return Proposal(
        id=proposal_id(context.repository, finding.key),
        finding=finding,
        action="setting",
        title="Enable Dependabot security updates",
        purpose="Receive proposed updates for known vulnerable dependencies.",
        impact="Enables automated security update PRs; version-update schedules are separate.",
        effort="Repository administrator: review the setting and click Enable.",
        steps=[
            f"Open {url} (Settings → Security & analysis / Advanced Security).",
            "Enable Dependency graph and Dependabot alerts if not already enabled.",
            "Next to Dependabot security updates, select Enable.",
        ],
        validation=[
            "Reload the settings page and confirm Dependabot security updates is enabled.",
            "An update PR appears only when a supported, fixable vulnerability exists.",
        ],
        warnings=["Current setting is not visible with this token; verify it first."]
        if context.settings.get("dependabot_security_updates") is None
        else [],
    )


def branch_protection(finding: Finding, context: Context) -> Proposal:
    return Proposal(
        id=proposal_id(context.repository, finding.key),
        finding=finding,
        action="setting",
        title="Require reviewed pull requests on the default branch",
        purpose="Reduce accidental or unreviewed changes to the default branch.",
        impact="May block direct pushes. Review bot/release access before enabling.",
        effort="Administrator: configure a branch rule and confirm an eligible reviewer exists.",
        steps=[
            f"Open https://github.com/{context.repository}/settings/rules.",
            f"Create or edit a branch ruleset targeting {context.default_branch}.",
            "Enable Require a pull request before merging with one required approval.",
            "Review bypass actors and rollout impact; set enforcement to Active and save.",
        ],
        validation=[
            "Confirm the rule targets the default branch and is active.",
            "Use a test PR to confirm an eligible review is required before merging.",
        ],
        required_inputs=["Confirm an eligible reviewer and bot/release access"],
        warnings=[
            "Aggregate score may reflect other protections; this is one focused suggestion.",
            "Check existing rules first; skip this suggestion if already enforced.",
        ],
    )


Remedy = Callable[[Finding, Context], Proposal | Outcome]
CATALOG: dict[str, Remedy] = {
    "SecurityPolicy": security,
    "Security-Policy": security,
    "DependabotSecurityUpdates": dependabot,
    "Branch-Protection": branch_protection,
    "Protected": branch_protection,
}


def propose_fixed(finding: Finding, context: Context) -> Proposal | Outcome:
    if finding.status == "unavailable":
        return Outcome(
            finding=finding.key,
            status="skipped",
            message="The assessment could not evaluate this check; no remediation inferred.",
        )
    remedy = CATALOG.get(finding.key)
    if remedy is None:
        return Outcome(
            finding=finding.key,
            status="unsupported",
            message="No fixed response; select a model mode or triage manually.",
        )
    return remedy(finding, context)
