"""Explicit GitHub publication, duplicate detection and stale-preview protection."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from reporemedy.catalog import proposal_id
from reporemedy.context import load_context
from reporemedy.errors import RemedyError
from reporemedy.github import GitHub
from reporemedy.models import Context, Proposal, Run
from reporemedy.preview import body
from reporemedy.providers import validate_proposal
from reporemedy.storage import atomic_json, read_run, run_lock


def marker(proposal: Proposal) -> str:
    return f"<!-- reporemedy:v1:{proposal.id} -->"


def validate_run(run: Run, selected: list[str]) -> list[Proposal]:
    if not selected or len(selected) != len(set(selected)):
        raise RemedyError("Select one or more distinct proposal IDs from the preview")
    if run.repository.casefold() != run.report.repository.casefold():
        raise RemedyError("Run and original report repository do not match")
    by_id = {p.id: p for p in run.proposals}
    if len(by_id) != len(run.proposals) or any(i not in by_id for i in selected):
        raise RemedyError("Unknown or duplicate proposal ID")
    proposals = [by_id[i] for i in selected]
    for proposal in proposals:
        if proposal.id != proposal_id(run.repository, proposal.finding.key):
            raise RemedyError("Proposal ID does not match its repository and finding")
        if proposal.finding not in run.report.findings:
            raise RemedyError("Proposal finding does not match the original report")
        validate_proposal(proposal)
    return proposals


def verify_changes(proposal: Proposal, context: Context) -> None:
    for change in proposal.changes:
        if change.path in context.paths:
            old = context.files.get(change.path)
            if (
                old is None
                or old.sha != change.previous_sha
                or old.content != change.previous_content
            ):
                raise RemedyError("Target file differs from the reviewed original; preview again")
        elif change.previous_sha or change.path not in {"SECURITY.md", "CONTRIBUTING.md"}:
            raise RemedyError(
                "New file is outside the supported scope or original file was removed"
            )


def writable_repository(github: GitHub, repository: str, user: str) -> str:
    meta = github.request("GET", f"/repos/{repository}")
    if meta.get("permissions", {}).get("push"):
        return repository
    fork = f"{user}/{repository.split('/')[1]}"
    existing = github.request("GET", f"/repos/{fork}", missing_ok=True)
    if existing:
        if existing.get("source", {}).get("full_name", "").casefold() != repository.casefold():
            raise RemedyError(
                "A same-name repository exists in your account but is not this project's fork"
            )
        return fork
    github.request("POST", f"/repos/{repository}/forks", data={"default_branch_only": True})
    for _ in range(6):
        ready = github.request("GET", f"/repos/{fork}", missing_ok=True)
        if (
            ready
            and ready.get("source", {}).get("full_name", "").casefold() == repository.casefold()
        ):
            return fork
        time.sleep(2)
    raise RemedyError("GitHub is preparing the fork; rerun publish after it is ready")


def create_pr(github: GitHub, run: Run, proposal: Proposal, context: Context, user: str) -> Any:
    target = writable_repository(github, run.repository, user)
    root = f"/repos/{target}"
    branch = f"reporemedy/{proposal.id}-{run.base_commit[:8]}"
    ref = github.request("GET", f"{root}/git/ref/heads/{branch}", missing_ok=True)
    if ref:
        # Resume a prior commit only when its parent and complete tree match.
        commit = github.request("GET", f"{root}/git/commits/{ref['object']['sha']}")
        if [p["sha"] for p in commit["parents"]] != [run.base_commit]:
            raise RemedyError("Existing remedy branch was modified; refusing to overwrite it")
        expected_tree = github.request(
            "POST",
            f"{root}/git/trees",
            data={
                "base_tree": context.tree_sha,
                "tree": [
                    {"path": c.path, "mode": "100644", "type": "blob", "content": c.content}
                    for c in proposal.changes
                ],
            },
        )
        if commit["tree"]["sha"] != expected_tree["sha"]:
            raise RemedyError("Existing remedy branch content differs; refusing to overwrite it")
    else:
        tree = github.request(
            "POST",
            f"{root}/git/trees",
            data={
                "base_tree": context.tree_sha,
                "tree": [
                    {"path": c.path, "mode": "100644", "type": "blob", "content": c.content}
                    for c in proposal.changes
                ],
            },
        )
        commit = github.request(
            "POST",
            f"{root}/git/commits",
            data={"message": proposal.title, "tree": tree["sha"], "parents": [run.base_commit]},
        )
        github.request(
            "POST", f"{root}/git/refs", data={"ref": f"refs/heads/{branch}", "sha": commit["sha"]}
        )
    head = f"{target.split('/')[0]}:{branch}"
    return github.request(
        "POST",
        f"/repos/{run.repository}/pulls",
        data={
            "title": proposal.title,
            "body": publication_body(run, proposal),
            "head": head,
            "base": run.default_branch,
            "draft": True,
            "maintainer_can_modify": True,
        },
    )


def publication_body(run: Run, proposal: Proposal) -> str:
    return (
        body(proposal) + f"\nSource: {run.report.report_type} ({run.report.source_version}); "
        f"report SHA-256: `{run.report.source_sha256}`.\n"
        f"Preview base: `{run.base_commit}`; mode: `{run.mode}`.\n\n"
        "For machine-readable feedback, a maintainer can comment on a separate line:\n"
        "`reporemedy: accepted`, `reporemedy: declined`, `reporemedy: needs-adjustment`, "
        "or `reporemedy: too-difficult`. Free-text feedback is welcome too.\n\n"
        + marker(proposal)
        + "\n"
    )


def publish(directory: Path, selected: list[str], github: GitHub) -> list[dict[str, Any]]:
    if not github.authenticated:
        raise RemedyError("Publishing requires GITHUB_TOKEN or gh auth login")
    with run_lock(directory):
        run = read_run(directory)
        proposals = validate_run(run, selected)
        context = load_context(github, run.repository)
        if context.commit != run.base_commit or context.default_branch != run.default_branch:
            raise RemedyError(
                "Default branch changed since preview; generate and review a new preview"
            )
        for proposal in proposals:
            verify_changes(proposal, context)
        # Paginate all states: closing/declining a suggestion must not cause it to be opened again.
        existing = github.pages(f"/repos/{run.repository}/issues?state=all")
        user = github.request("GET", "/user")["login"]
        ledger_path = directory / "publication.json"
        ledger: dict[str, dict[str, Any]] = {}
        if ledger_path.exists():
            try:
                saved = json.loads(ledger_path.read_text(encoding="utf-8"))
                if saved["repository"] != run.repository:
                    raise ValueError("Repository mismatch")
                ledger = {r["id"]: r for r in saved["items"]}
            except (ValueError, KeyError, TypeError) as exc:
                raise RemedyError(
                    "Invalid publication ledger; preserve it and reconcile GitHub first"
                ) from exc
        receipts: list[dict[str, Any]] = []
        for proposal in proposals:
            prior = next((i for i in existing if marker(proposal) in (i.get("body") or "")), None)
            try:
                if prior:
                    item = prior
                elif proposal.action == "setting":
                    item = github.request(
                        "POST",
                        f"/repos/{run.repository}/issues",
                        data={"title": proposal.title, "body": publication_body(run, proposal)},
                    )
                else:
                    item = create_pr(github, run, proposal, context, user)
                receipt = {
                    "id": proposal.id,
                    "number": item["number"],
                    "url": item["html_url"],
                    "kind": "issue" if proposal.action == "setting" else "pr",
                    "status": "existing" if prior else "published",
                    "proposal_sha256": hashlib.sha256(
                        proposal.model_dump_json().encode()
                    ).hexdigest(),
                }
                existing.append({**item, "body": publication_body(run, proposal)})
            except RemedyError as exc:
                receipt = {"id": proposal.id, "status": "failed", "error": str(exc)}
            receipts.append(receipt)
            ledger[proposal.id] = receipt
            # Save after each outcome; restart also reconciles remote markers after a lost response.
            atomic_json(
                directory / "publication.json",
                {"repository": run.repository, "items": list(ledger.values())},
            )
        return receipts
