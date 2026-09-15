import base64
import json

import httpx
import pytest

from reporemedy.catalog import propose_fixed
from reporemedy.context import load_context
from reporemedy.errors import RemedyError
from reporemedy.github import GitHub
from reporemedy.models import Change, Context, Finding, RepositoryFile
from reporemedy.preview import body, prepare, write_preview
from reporemedy.readers.scorecard import read_scorecard


def context(**updates):
    data = dict(
        repository="acme/demo",
        default_branch="main",
        commit="a" * 40,
        tree_sha="b" * 40,
        paths=[],
        files={},
    )
    data.update(updates)
    return Context(**data)


def finding(key="Security-Policy", status="gap"):
    return Finding(key=key, status=status, evidence="Missing policy", score=0)


def test_security_new_template_and_empty_existing_file():
    new = propose_fixed(finding(), context())
    assert new.action == "add-file"
    assert new.required_inputs == ["Private reporting route", "Supported versions"]
    existing = propose_fixed(
        finding(),
        context(
            paths=["SECURITY.md"], files={"SECURITY.md": RepositoryFile(content="", sha="c" * 40)}
        ),
    )
    assert existing.action == "edit-file"
    assert existing.changes[0].previous_sha == "c" * 40
    assert "Effort" in body(existing) and "Original finding" in body(existing)


@pytest.mark.parametrize("path", ["SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"])
def test_existing_policy_is_never_overwritten(path):
    result = propose_fixed(
        finding(),
        context(
            paths=[path], files={path: RepositoryFile(content="Our custom policy", sha="c" * 40)}
        ),
    )
    assert result.status == "skipped"
    unreadable = propose_fixed(finding(), context(paths=[path]))
    assert unreadable.status == "needs-input"


def test_setting_is_security_updates_not_version_updates():
    result = propose_fixed(finding("DependabotSecurityUpdates"), context())
    assert result.action == "setting"
    assert result.changes == []
    assert "version-update" in result.impact
    assert "Enable" in " ".join(result.steps)
    assert (
        propose_fixed(
            finding("DependabotSecurityUpdates"),
            context(settings={"dependabot_security_updates": True}),
        ).status
        == "skipped"
    )


def test_branch_rule_is_focused_and_requires_project_decision():
    result = propose_fixed(finding("Branch-Protection"), context())
    assert result.required_inputs
    assert "one required approval" in " ".join(result.steps)
    assert result.warnings


def test_unsupported_and_unknown_are_visible():
    assert propose_fixed(finding("License"), context()).status == "unsupported"
    assert propose_fixed(finding(status="unavailable"), context()).status == "skipped"


@pytest.mark.parametrize("path", ["../x", "/x", "a//b", "a\\b", ".git/config", ".env", "C:/x"])
def test_unsafe_change_paths(path):
    with pytest.raises(ValueError):
        Change(path=path, content="hi")


def test_prepare_and_preview(tmp_path):
    report = read_scorecard(
        json.dumps(
            {
                "repo": {"name": "acme/demo", "commit": "old"},
                "scorecard": {"version": "v5.5.0"},
                "checks": [{"name": "Security-Policy", "score": 0, "reason": "missing"}],
            }
        ),
        "acme/demo",
        "digest",
    )
    run = prepare(report, context())
    out = tmp_path / "preview"
    write_preview(run, out)
    assert "Report commit differs" in " ".join(run.notices)
    assert list(out.glob("*.patch"))
    assert "Original finding" in (out / f"{run.proposals[0].id}.md").read_text()
    with pytest.raises(RemedyError, match="exists"):
        write_preview(run, out)


def test_context_fetches_immutable_regular_guidelines_only():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if request.url.path.endswith("/commits/main"):
            return httpx.Response(
                200, json={"sha": "a" * 40, "commit": {"tree": {"sha": "b" * 40}}}
            )
        if "/git/trees/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {
                            "path": "CONTRIBUTING.md",
                            "type": "blob",
                            "mode": "100644",
                            "size": 4,
                            "sha": "c",
                        },
                        {"path": ".env", "type": "blob", "mode": "100644", "size": 4, "sha": "d"},
                        {
                            "path": "SECURITY.md",
                            "type": "blob",
                            "mode": "120000",
                            "size": 4,
                            "sha": "e",
                        },
                    ]
                },
            )
        if "/git/blobs/" in request.url.path:
            return httpx.Response(
                200, json={"encoding": "base64", "content": base64.b64encode(b"test").decode()}
            )
        return httpx.Response(200, json={"default_branch": "main"})

    github = GitHub(transport=httpx.MockTransport(handler))
    try:
        result = load_context(github, "acme/demo")
        assert result.files["CONTRIBUTING.md"].content == "test"
        assert ".env" not in result.files
        assert any("non-regular" in n for n in result.notices)
        assert "/repos/acme/demo/git/blobs/d" not in paths
    finally:
        github.close()


@pytest.mark.parametrize("status", [301, 401, 403, 404, 409, 422, 429, 500])
def test_github_errors_do_not_leak_response_or_credentials(status, monkeypatch):
    monkeypatch.setattr("reporemedy.github.time.sleep", lambda _: None)
    github = GitHub(
        "secret",
        transport=httpx.MockTransport(lambda r: httpx.Response(status, json={"message": "secret"})),
    )
    with pytest.raises(RemedyError) as error:
        github.request("GET", "/repos/a/b")
    assert "secret" not in str(error.value)
    github.close()
