import base64
import json
import subprocess

import httpx
import pytest
from test_providers import provider
from test_publication import Server, make_run
from test_readers import scorecard
from test_remedies import context

from shadowreporemedy import config
from shadowreporemedy.context import load_context
from shadowreporemedy.errors import RemedyError
from shadowreporemedy.github import GitHub
from shadowreporemedy.models import Mode, ReportType
from shadowreporemedy.preview import prepare
from shadowreporemedy.providers import ModelProvider
from shadowreporemedy.readers import read_report
from shadowreporemedy.readers.scorecard import read_scorecard


def test_config_precedence_and_no_interpolation(tmp_path, monkeypatch):
    for name in ["GITHUB_TOKEN", "GH_TOKEN", "LLM_API_KEY"]:
        monkeypatch.delenv(name, raising=False)
    env = tmp_path / ".env"
    env.write_text("GITHUB_TOKEN=file-token\nLLM_API_KEY=${GITHUB_TOKEN}\n")
    monkeypatch.setenv("GITHUB_TOKEN", "environment-token")
    config.load_environment(env)
    assert config.github_token() == "environment-token"
    assert config.os.getenv("LLM_API_KEY") == "${GITHUB_TOKEN}"


@pytest.mark.parametrize("outcome", ["token", "failure", "absent", "timeout"])
def test_gh_auth_fallback(monkeypatch, outcome):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    def run(*args, **kwargs):
        if outcome == "absent":
            raise FileNotFoundError()
        if outcome == "timeout":
            raise subprocess.TimeoutExpired("gh", 5)
        return subprocess.CompletedProcess([], 0 if outcome == "token" else 1, stdout="token\n")

    monkeypatch.setattr(config.subprocess, "run", run)
    assert config.github_token() == ("token" if outcome == "token" else None)


def test_transport_read_retries_but_write_does_not(monkeypatch):
    monkeypatch.setattr("shadowreporemedy.github.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request.method)
        raise httpx.ConnectError("secret URL", request=request)

    github = GitHub(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(RemedyError, match="network"):
            github.request("GET", "/repos/a/b")
        assert len(calls) == 3
        with pytest.raises(RemedyError, match="network"):
            github.request("POST", "/repos/a/b/issues", data={})
        assert len(calls) == 4
        with pytest.raises(RemedyError, match="Invalid"):
            github.request("GET", "https://evil.test")
    finally:
        github.close()


def test_pagination_multiple_pages_and_malformed_result():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json=[{"number": i} for i in range(100)]
            if request.url.params["page"] == "1"
            else [{"number": 101}],
        )

    github = GitHub(transport=httpx.MockTransport(handler))
    try:
        assert len(github.pages("/repos/a/b/issues?state=all")) == 101
        assert len(calls) == 2
    finally:
        github.close()
    github = GitHub(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[1])))
    try:
        with pytest.raises(RemedyError, match="list"):
            github.pages("/repos/a/b/issues")
    finally:
        github.close()


@pytest.mark.parametrize("value", [None, [], "v5.5.0"])
def test_scorecard_version_metadata_schema_drift(value):
    data = scorecard()
    data["scorecard"] = value
    with pytest.raises(RemedyError, match="metadata"):
        read_scorecard(json.dumps(data), "acme/demo", "d")


@pytest.mark.parametrize("kind", ["repoauditor", "ossf-scorecard"])
@pytest.mark.parametrize("mode", [Mode.FIXED, Mode.LOCAL, Mode.HOSTED])
def test_all_six_report_and_mode_combinations(tmp_path, monkeypatch, kind, mode):
    path = tmp_path / "report"
    path.write_text(
        json.dumps(scorecard())
        if kind == "ossf-scorecard"
        else "╭─ [Error] SecurityPolicy ─╮\n│ ERROR: Policy missing │\n╰─────────────────────────╯",
        encoding="utf-8",
    )
    report = read_report(path, ReportType(kind), "acme/demo")
    model = None
    if mode != Mode.FIXED:
        model, _ = provider(monkeypatch, mode)
    try:
        run = prepare(report, context(), mode, model)
        assert len(run.proposals) == 1
        assert run.mode == mode
        assert run.proposals[0].finding.evidence == report.findings[0].evidence
    finally:
        if model:
            model.close()


def test_large_vendor_guidance_is_not_sent_as_project_guidance():
    def handler(request):
        path = request.url.path
        if "/git/trees/" in path:
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {
                            "path": "vendor/dependency/README.md",
                            "type": "blob",
                            "mode": "100644",
                            "size": 999999,
                            "sha": "vendor",
                        },
                        {
                            "path": "CONTRIBUTING.md",
                            "type": "blob",
                            "mode": "100644",
                            "size": 4,
                            "sha": "root",
                        },
                    ]
                },
            )
        if "/git/blobs/" in path:
            assert path.endswith("root")
            return httpx.Response(
                200, json={"encoding": "base64", "content": base64.b64encode(b"test").decode()}
            )
        return Server()(request)

    github = GitHub(transport=httpx.MockTransport(handler))
    try:
        ctx = load_context(github, "acme/demo")
        assert list(ctx.files) == ["CONTRIBUTING.md"]
        assert ctx.notices == []
    finally:
        github.close()


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"LLM_MODEL": "test", "LLM_BASE_URL": "http://remote.example/v1"},
        {"LLM_MODEL": "test", "LLM_BASE_URL": "https://key@remote.example/v1"},
    ],
)
def test_invalid_provider_config_fails_before_network(monkeypatch, env):
    for k in ["LLM_MODEL", "LLM_BASE_URL"]:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(RemedyError):
        ModelProvider(Mode.HOSTED)


def test_publication_failure_is_recorded_and_lock_released(tmp_path):
    from shadowreporemedy.publish import publish

    run, out = make_run(tmp_path, "Branch-Protection")
    server = Server()

    def handler(request):
        if request.method == "POST":
            return httpx.Response(403, json={"message": "private detail"})
        return server(request)

    github = GitHub("token", transport=httpx.MockTransport(handler))
    try:
        result = publish(out, [run.proposals[0].id], github)
        assert result[0]["status"] == "failed"
        assert "private detail" not in json.dumps(result)
        assert not (out / ".publish.lock").exists()
    finally:
        github.close()


def test_draft_branch_resume_and_tampered_branch_rejection(tmp_path):
    from shadowreporemedy.publish import publish

    run, out = make_run(tmp_path)
    server = Server()
    changed = False

    def handler(request):
        if "/git/ref/" in request.url.path:
            return httpx.Response(200, json={"object": {"sha": "prior"}})
        if request.url.path.endswith("/git/commits/prior"):
            return httpx.Response(
                200,
                json={
                    "parents": [{"sha": "a" * 40}],
                    "tree": {"sha": "modified" if changed else "tree"},
                },
            )
        return server(request)

    github = GitHub("token", transport=httpx.MockTransport(handler))
    try:
        assert publish(out, [run.proposals[0].id], github)[0]["status"] == "published"
        assert not any(path.endswith("/git/refs") for _, path, _ in server.calls)
        server.created.clear()
        changed = True
        result = publish(out, [run.proposals[0].id], github)
        assert result[0]["status"] == "failed"
        assert "differs" in result[0]["error"]
    finally:
        github.close()


def test_fork_creation_polling_and_name_collision(monkeypatch):
    from shadowreporemedy.publish import writable_repository

    monkeypatch.setattr("shadowreporemedy.publish.time.sleep", lambda _: None)
    calls = []
    ready = False

    def handler(request):
        nonlocal ready
        calls.append(request.method)
        if request.url.path.endswith("/forks"):
            ready = True
            return httpx.Response(202, json={})
        if request.url.path == "/repos/auditor/demo":
            return (
                httpx.Response(200, json={"source": {"full_name": "acme/demo"}})
                if ready
                else httpx.Response(404)
            )
        return httpx.Response(200, json={"permissions": {"push": False}})

    github = GitHub("token", transport=httpx.MockTransport(handler))
    try:
        assert writable_repository(github, "acme/demo", "auditor") == "auditor/demo"
        assert calls.count("POST") == 1
    finally:
        github.close()
    github = GitHub(
        "token",
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"full_name": "auditor/demo"})
        ),
    )
    try:
        with pytest.raises(RemedyError, match="same-name"):
            writable_repository(github, "acme/demo", "auditor")
    finally:
        github.close()


def test_forged_or_changed_original_file_is_rejected():
    from test_remedies import finding

    from shadowreporemedy.catalog import security
    from shadowreporemedy.models import RepositoryFile
    from shadowreporemedy.publish import verify_changes

    ctx = context(
        paths=["SECURITY.md"], files={"SECURITY.md": RepositoryFile(content="", sha="old")}
    )
    proposal = security(finding(), ctx)
    verify_changes(proposal, ctx)
    ctx.files["SECURITY.md"].content = "New policy"
    with pytest.raises(RemedyError, match="differs"):
        verify_changes(proposal, ctx)
    with pytest.raises(RemedyError, match="removed"):
        verify_changes(proposal, context())


def test_limits_duplicates_and_mismatched_context(tmp_path):
    from shadowreporemedy.models import Finding

    run, _ = make_run(tmp_path)
    report = run.report
    report.findings *= 2
    result = prepare(report, context())
    assert len(result.proposals) == 1
    assert any(o.status == "skipped" for o in result.outcomes)
    report.findings.append(Finding(key="Branch-Protection", status="gap", evidence="missing"))
    limited = prepare(report, context(), limit=1)
    assert "limit" in limited.outcomes[-1].message
    with pytest.raises(RemedyError, match="mismatch"):
        prepare(report, context(repository="another/repo"))
    with pytest.raises(RemedyError, match="configured model"):
        prepare(report, context(), Mode.LOCAL)


@pytest.mark.parametrize("problem", ["archived", "truncated", "encoding", "too-large"])
def test_context_fails_explicitly_on_incomplete_inputs(problem):
    def handler(request):
        if request.url.path == "/repos/acme/demo" and problem == "archived":
            return httpx.Response(200, json={"archived": True})
        if "/git/trees/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "truncated": problem == "truncated",
                    "tree": [
                        {
                            "path": "README.md",
                            "mode": "100644",
                            "size": 4,
                            "sha": "readme",
                            "type": "blob",
                        }
                    ],
                },
            )
        if "/git/blobs/" in request.url.path:
            content = base64.b64encode(b"a" * 40000).decode()
            return httpx.Response(
                200,
                json={"encoding": "raw" if problem == "encoding" else "base64", "content": content},
            )
        return Server()(request)

    github = GitHub(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(RemedyError):
            load_context(github, "acme/demo")
    finally:
        github.close()


def test_generation_schema_preserves_named_properties_and_bounds_are_enforced():
    from shadowreporemedy.models import Change
    from shadowreporemedy.providers import generation_schema

    schema = generation_schema()
    assert "title" in schema["$defs"]["Draft"]["properties"]
    assert "changes" in schema["$defs"]["Draft"]["required"]
    with pytest.raises(ValueError):
        Change(path="SECURITY.md", content="x" * 64001)


def test_model_cannot_hide_placeholder_work(monkeypatch):
    from test_providers import response

    output = response()
    output["proposal"]["required_inputs"] = []
    model, _ = provider(monkeypatch, output=output)
    try:
        from test_remedies import finding

        with pytest.raises(RemedyError, match="placeholders"):
            model.propose(finding(), context())
    finally:
        model.close()


def test_missing_api_context_is_operational_error():
    github = GitHub(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})))
    try:
        with pytest.raises(RemedyError, match="incomplete"):
            load_context(github, "acme/demo")
    finally:
        github.close()
