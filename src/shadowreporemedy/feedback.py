"""Read maintainer decisions; never infer issue acceptance from closure alone."""

import json
import re
from pathlib import Path
from typing import Any

from shadowreporemedy.errors import RemedyError
from shadowreporemedy.github import GitHub
from shadowreporemedy.models import repository_name
from shadowreporemedy.storage import atomic_json

DECISION = re.compile(
    r"^(?:shadowRepoRemedy|reporemedy): (accepted|declined|needs-adjustment|too-difficult)\s*$",
    re.M | re.I,
)
MAINTAINER = {"OWNER", "MEMBER", "COLLABORATOR"}


def collect_feedback(directory: Path, github: GitHub) -> dict[str, Any]:
    try:
        published = json.loads((directory / "publication.json").read_text(encoding="utf-8"))
        repository = repository_name(published["repository"])
        items = published["items"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RemedyError("No valid publication.json; publish selected proposals first") from exc
    results = []
    for receipt in items:
        if receipt.get("status") == "failed":
            continue
        number = receipt.get("number")
        if type(number) is not int or number < 1:
            raise RemedyError("Invalid issue/PR number in publication receipt")
        root = f"/repos/{repository}"
        endpoint = "pulls" if receipt["kind"] == "pr" else "issues"
        item = github.request("GET", f"{root}/{endpoint}/{number}")
        comments = github.pages(f"{root}/issues/{number}/comments")
        if endpoint == "pulls":
            comments += github.pages(f"{root}/pulls/{number}/reviews")
        comments.sort(key=lambda c: c.get("submitted_at") or c.get("created_at", ""))
        decision = "pending"
        for comment in comments:
            match = DECISION.search(comment.get("body") or "")
            if match and comment.get("author_association") in MAINTAINER:
                decision = match[1]
        if item.get("merged_at"):
            decision = "accepted"
        elif decision == "pending" and item.get("state") == "closed":
            decision = "closed-without-decision"
        results.append(
            {
                "id": receipt["id"],
                "url": receipt["url"],
                "kind": receipt["kind"],
                "decision": decision,
                "merged": bool(item.get("merged_at")),
                "feedback": [
                    {
                        "url": c.get("html_url"),
                        "body": c.get("body") or "",
                        "maintainer": c.get("author_association") in MAINTAINER,
                    }
                    for c in comments
                ],
            }
        )
    accepted = sum(r["decision"] == "accepted" for r in results)
    resolved = sum(r["decision"] in {"accepted", "declined", "too-difficult"} for r in results)
    summary = {
        "published": len(results),
        "accepted": accepted,
        "merged_prs": sum(r["merged"] for r in results),
        "accepted_issues": sum(
            r["kind"] == "issue" and r["decision"] == "accepted" for r in results
        ),
        "pending": sum(r["decision"] == "pending" for r in results),
        "needs_adjustment": sum(r["decision"] == "needs-adjustment" for r in results),
        "closed_without_decision": sum(r["decision"] == "closed-without-decision" for r in results),
        "accept_rate_all_published": accepted / len(results) if results else None,
        "accept_rate_decided": accepted / resolved if resolved else None,
    }
    output = {"repository": repository, "summary": summary, "items": results}
    atomic_json(directory / "feedback.json", output)
    return output
