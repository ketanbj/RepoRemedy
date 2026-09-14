import base64

import httpx
import pytest

from reporemedy.context import load_context
from reporemedy.errors import RemedyError
from reporemedy.github import GitHub
from reporemedy.models import Change, Context


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


@pytest.mark.parametrize("path", ["../x", "/x", "a//b", "a\\b", ".git/config", ".env", "C:/x"])
def test_unsafe_change_paths(path):
    with pytest.raises(ValueError):
        Change(path=path, content="hi")


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
