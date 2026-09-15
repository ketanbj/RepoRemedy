import json

import httpx
import pytest
from test_remedies import context

from shadowreporemedy.errors import RemedyError
from shadowreporemedy.feedback import collect_feedback
from shadowreporemedy.github import GitHub
from shadowreporemedy.preview import prepare, write_preview
from shadowreporemedy.publish import marker, publish, validate_run
from shadowreporemedy.readers.scorecard import read_scorecard
from shadowreporemedy.storage import read_run, run_lock


def make_run(tmp_path, key="Security-Policy"):
    report = read_scorecard(
        json.dumps(
            {
                "repo": {"name": "acme/demo"},
                "scorecard": {"version": "v5.5.0"},
                "checks": [{"name": key, "score": 0, "reason": "missing"}],
            }
        ),
        "acme/demo",
        "d" * 64,
    )
    run = prepare(report, context())
    out = tmp_path / "run"
    write_preview(run, out)
    return run, out


class Server:
    def __init__(self, *, fork=False, duplicate=None, stale=False):
        self.calls = []
        self.fork = fork
        self.duplicate = duplicate
        self.stale = stale
        self.created = []

    def __call__(self, request):
        path = request.url.path
        data = json.loads(request.content) if request.content else None
        self.calls.append((request.method, path, data))
        if request.method == "GET":
            if path.endswith("/commits/main"):
                result = {
                    "sha": ("f" if self.stale else "a") * 40,
                    "commit": {"tree": {"sha": "b" * 40}},
                }
            elif "/git/trees/" in path:
                result = {"tree": []}
            elif "/git/ref/" in path:
                return httpx.Response(404)
            elif path.endswith("/issues"):
                result = [self.duplicate] if self.duplicate else self.created
            elif path == "/user":
                result = {"login": "auditor"}
            elif path == "/repos/auditor/demo":
                result = {"source": {"full_name": "acme/demo"}}
            else:
                result = {"default_branch": "main", "permissions": {"push": not self.fork}}
        elif path.endswith("/git/trees"):
            result = {"sha": "tree"}
        elif path.endswith("/git/commits"):
            assert data["parents"] == ["a" * 40]
            result = {"sha": "commit"}
        elif path.endswith("/git/refs"):
            result = {"ref": data["ref"]}
        else:
            if path.endswith("/pulls"):
                assert data["draft"] is True
                assert data["base"] == "main"
            result = {
                "number": 42,
                "html_url": "https://github.com/acme/demo/issues/42",
                "body": data["body"],
            }
            self.created.append(result)
        return httpx.Response(200, json=result)


@pytest.mark.parametrize(
    "key,fork",
    [("Security-Policy", False), ("Security-Policy", True), ("Branch-Protection", False)],
)
def test_selected_publication_and_retry_dedup(tmp_path, key, fork):
    run, out = make_run(tmp_path, key)
    server = Server(fork=fork)
    github = GitHub("test", transport=httpx.MockTransport(server))
    try:
        result = publish(out, [run.proposals[0].id], github)
        assert result[0]["status"] == "published"
        assert len(server.created) == 1
        again = publish(out, [run.proposals[0].id], github)
        assert again[0]["status"] == "existing"
        assert len(server.created) == 1
        assert (out / "publication.json").exists()
        if fork:
            assert any(p == "/repos/auditor/demo/git/trees" for _, p, _ in server.calls)
    finally:
        github.close()


def test_closed_suggestion_is_not_reopened(tmp_path):
    run, out = make_run(tmp_path)
    server = Server(
        duplicate={
            "body": marker(run.proposals[0]),
            "state": "closed",
            "number": 8,
            "html_url": "https://github.com/acme/demo/pull/8",
        }
    )
    github = GitHub("test", transport=httpx.MockTransport(server))
    try:
        assert publish(out, [run.proposals[0].id], github)[0]["status"] == "existing"
        assert not any(m == "POST" for m, _, _ in server.calls)
    finally:
        github.close()


def test_stale_preview_fails_before_any_write(tmp_path):
    run, out = make_run(tmp_path)
    server = Server(stale=True)
    github = GitHub("test", transport=httpx.MockTransport(server))
    try:
        with pytest.raises(RemedyError, match="changed"):
            publish(out, [run.proposals[0].id], github)
        assert not any(m == "POST" for m, _, _ in server.calls)
        assert not (out / ".publish.lock").exists()
    finally:
        github.close()


def test_invalid_selection_and_tampered_evidence(tmp_path):
    run, _ = make_run(tmp_path)
    with pytest.raises(RemedyError, match="Unknown"):
        validate_run(run, ["missing"])
    with pytest.raises(RemedyError, match="distinct"):
        validate_run(run, [])
    run.proposals[0].finding.evidence = "tampered"
    # Deserialization separates the two copies as happens for edited files.
    fresh = type(run).model_validate_json(run.model_dump_json())
    fresh.report.findings[0].evidence = "original"
    with pytest.raises(RemedyError, match="original report"):
        validate_run(fresh, [fresh.proposals[0].id])


def test_exclusive_lock_and_invalid_run(tmp_path):
    with run_lock(tmp_path), pytest.raises(RemedyError, match="locked"), run_lock(tmp_path):
        pass
    assert not (tmp_path / ".publish.lock").exists()
    with pytest.raises(RemedyError, match="run.json"):
        read_run(tmp_path)


@pytest.mark.parametrize(
    "kind,closed,merged,association,comment,expected",
    [
        ("issue", True, False, "OWNER", "Thank you", "closed-without-decision"),
        ("issue", False, False, "OWNER", "shadowreporemedy: accepted", "accepted"),
        ("issue", False, False, "OWNER", "shadowRepoRemedy: accepted", "accepted"),
        ("issue", False, False, "OWNER", "reporemedy: accepted", "accepted"),
        ("issue", False, False, "MEMBER", "reporemedy: declined", "declined"),
        ("issue", False, False, "NONE", "shadowreporemedy: accepted", "pending"),
        ("pr", True, True, "NONE", "", "accepted"),
        (
            "pr",
            False,
            False,
            "COLLABORATOR",
            "shadowreporemedy: needs-adjustment",
            "needs-adjustment",
        ),
    ],
)
def test_feedback_acceptance_is_evidence_based(
    tmp_path, kind, closed, merged, association, comment, expected
):
    (tmp_path / "publication.json").write_text(
        json.dumps(
            {
                "repository": "acme/demo",
                "items": [
                    {
                        "id": "test",
                        "number": 1,
                        "url": "https://github.com/acme/demo/issues/1",
                        "kind": kind,
                        "status": "published",
                    }
                ],
            }
        )
    )

    def handler(request):
        if request.url.path.endswith("/comments"):
            result = [
                {"body": comment, "author_association": association, "html_url": "comment-url"}
            ]
        elif request.url.path.endswith("/reviews"):
            result = []
        else:
            result = {
                "state": "closed" if closed else "open",
                "merged_at": "date" if merged else None,
            }
        return httpx.Response(200, json=result)

    github = GitHub(transport=httpx.MockTransport(handler))
    try:
        result = collect_feedback(tmp_path, github)
        assert result["items"][0]["decision"] == expected
        assert result["summary"]["accepted"] == (1 if expected == "accepted" else 0)
        assert (tmp_path / "feedback.json").exists()
    finally:
        github.close()
