"""Read relevant text at one immutable commit; never execute repository code."""

import base64
from pathlib import PurePosixPath
from urllib.parse import quote

from reporemedy.errors import RemedyError
from reporemedy.github import GitHub
from reporemedy.models import Context, RepositoryFile, repository_name

GUIDE_NAMES = {
    "readme.md",
    "readme.rst",
    "readme",
    "contributing.md",
    "contributing.rst",
    "security.md",
    "agents.md",
    "copilot-instructions.md",
    "code_of_conduct.md",
}
MAX_FILE_BYTES = 32_000
MAX_CONTEXT_BYTES = 100_000


def load_context(github: GitHub, repository: str) -> Context:
    repository = repository_name(repository)
    root = f"/repos/{repository}"
    meta = github.request("GET", root)
    if meta.get("archived") or meta.get("disabled"):
        raise RemedyError("Repository is archived or disabled; no changes can be proposed")
    branch = meta["default_branch"]
    commit = github.request("GET", f"{root}/commits/{quote(branch, safe='')}")
    sha = commit["sha"]
    tree_sha = commit["commit"]["tree"]["sha"]
    tree = github.request("GET", f"{root}/git/trees/{tree_sha}?recursive=1")
    if tree.get("truncated"):
        raise RemedyError("Repository tree is truncated; cannot safely establish file presence")
    entries = {e["path"]: e for e in tree["tree"] if e.get("type") == "blob"}
    notices: list[str] = []
    files: dict[str, RepositoryFile] = {}
    total = 0
    for path in sorted(entries, key=lambda p: (len(PurePosixPath(p).parts), p)):
        if PurePosixPath(path).name.lower() not in GUIDE_NAMES:
            continue
        entry = entries[path]
        if entry.get("mode") != "100644" or entry.get("size", MAX_FILE_BYTES + 1) > MAX_FILE_BYTES:
            notices.append(f"Guideline not read (size or non-regular file): {path}")
            continue
        if total + entry["size"] > MAX_CONTEXT_BYTES:
            notices.append(f"Guideline not read (context limit): {path}")
            continue
        blob = github.request("GET", f"{root}/git/blobs/{entry['sha']}")
        try:
            if blob.get("encoding") != "base64":
                raise ValueError("Unexpected blob encoding")
            content = base64.b64decode(blob["content"]).decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise RemedyError("Repository guideline has unsupported encoding") from exc
        if len(content.encode()) > MAX_FILE_BYTES:
            raise RemedyError("Repository blob exceeds its declared size")
        files[path] = RepositoryFile(content=content, sha=entry["sha"])
        total += len(content.encode())
    if not any(PurePosixPath(p).name.lower().startswith("contributing") for p in files):
        notices.append(
            "No contribution guidelines found; maintainer must confirm project conventions."
        )
    analysis = meta.get("security_and_analysis") or {}
    dependabot = analysis.get("dependabot_security_updates", {}).get("status")
    return Context(
        repository=repository,
        default_branch=branch,
        commit=sha,
        tree_sha=tree_sha,
        paths=sorted(entries),
        files=files,
        notices=notices,
        settings={
            "dependabot_security_updates": None if dependabot is None else dependabot == "enabled"
        },
    )
