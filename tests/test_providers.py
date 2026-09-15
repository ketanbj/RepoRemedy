import json

import httpx
import pytest
from test_remedies import context, finding

from reporemedy.errors import RemedyError
from reporemedy.models import Change, Mode, RepositoryFile
from reporemedy.providers import ModelProvider, redact, validate_proposal


def response():
    return {
        "status": "proposed",
        "reason": "missing security policy",
        "proposal": {
            "action": "add-file",
            "title": "Add security policy",
            "purpose": "Private reporting",
            "impact": "Documentation only",
            "effort": "Fill a contact and merge",
            "steps": ["Fill private reporting contact"],
            "validation": ["Test private reporting"],
            "required_inputs": ["Private contact"],
            "changes": [{"path": "SECURITY.md", "content": "# Security\nTODO: Private contact"}],
        },
    }


def provider(monkeypatch, mode=Mode.LOCAL, output=None):
    monkeypatch.setenv("OLLAMA_MODEL", "llama3")
    monkeypatch.setenv("LLM_MODEL", "hosted-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://provider.example/v1")
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/show"):
            return httpx.Response(200, json={"details": {"family": "llama"}})
        content = json.dumps(output if output is not None else response())
        return httpx.Response(
            200,
            json={"message": {"content": content}}
            if mode == Mode.LOCAL
            else {"choices": [{"message": {"content": content}}]},
        )

    return ModelProvider(mode, transport=httpx.MockTransport(handler)), calls


@pytest.mark.parametrize("mode", [Mode.LOCAL, Mode.HOSTED])
def test_both_modes_consult_guidelines_preserve_evidence_and_redact(monkeypatch, mode):
    model, calls = provider(monkeypatch, mode)
    ctx = context(
        paths=["CONTRIBUTING.md"],
        files={
            "CONTRIBUTING.md": RepositoryFile(
                content="Use two spaces. ghp_abcdefghijklmnopqrstuvwxyz", sha="a" * 40
            )
        },
    )
    try:
        result = model.propose(finding(), ctx)
        assert result.finding.evidence == "Missing policy"
        assert result.changes[0].path == "SECURITY.md"
        sent = json.loads(calls[-1].content)
        assert "Use two spaces" in sent["messages"][1]["content"]
        assert "ghp_" not in sent["messages"][1]["content"]
        assert "untrusted DATA" in sent["messages"][0]["content"]
        assert calls[-1].url.path == ("/api/chat" if mode == Mode.LOCAL else "/v1/chat/completions")
    finally:
        model.close()


@pytest.mark.parametrize(
    "model,url",
    [("gpt-oss:120b-cloud", "http://localhost:11434"), ("llama3", "https://remote.example")],
)
def test_local_cannot_silently_become_hosted(monkeypatch, model, url):
    monkeypatch.setenv("OLLAMA_MODEL", model)
    monkeypatch.setenv("OLLAMA_URL", url)
    with pytest.raises(RemedyError, match="local-llm"):
        ModelProvider(Mode.LOCAL)


def test_cloud_model_metadata_is_rejected(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "alias")
    with pytest.raises(RemedyError, match="Cloud-backed"):
        ModelProvider(
            Mode.LOCAL,
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json={"remote_model": "x", "remote_host": "ollama.com"}
                )
            ),
        )


@pytest.mark.parametrize("status", ["needs-input", "unsupported", "skipped"])
def test_explicit_non_proposal_status(monkeypatch, status):
    model, _ = provider(monkeypatch, output={"status": status, "reason": "Need project decision"})
    try:
        assert model.propose(finding(), context()).status == status
    finally:
        model.close()


def test_missing_context_prevents_model_call(monkeypatch):
    model, calls = provider(monkeypatch)
    try:
        result = model.propose(finding(), context(notices=["Guideline not read: AGENTS.md"]))
        assert result.status == "needs-input"
        assert len(calls) == 1  # model metadata only
    finally:
        model.close()


def test_existing_file_gets_real_sha_not_model_claim(monkeypatch):
    output = response()
    output["proposal"]["action"] = "edit-file"
    output["proposal"]["changes"][0]["previous_sha"] = "invented"
    model, _ = provider(monkeypatch, output=output)
    try:
        result = model.propose(
            finding(),
            context(
                paths=["SECURITY.md"],
                files={"SECURITY.md": RepositoryFile(content="Old policy", sha="d" * 40)},
            ),
        )
        assert result.changes[0].previous_sha == "d" * 40
        assert result.changes[0].previous_content == "Old policy"
    finally:
        model.close()


def test_model_cannot_edit_unread_file_or_add_arbitrary_code(monkeypatch):
    output = response()
    output["proposal"]["changes"][0]["path"] = "app.py"
    model, _ = provider(monkeypatch, output=output)
    try:
        for ctx in [context(), context(paths=["app.py"])]:
            with pytest.raises(RemedyError):
                model.propose(finding(), ctx)
    finally:
        model.close()


def test_prepublication_validation(monkeypatch):
    model, _ = provider(monkeypatch)
    try:
        result = model.propose(finding(), context())
        result.changes.append(Change(path="SECURITY.md", content="other"))
        with pytest.raises(RemedyError, match="Duplicate"):
            validate_proposal(result)
    finally:
        model.close()
    assert "PRIVATE KEY" not in redact(
        "-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----"
    )
