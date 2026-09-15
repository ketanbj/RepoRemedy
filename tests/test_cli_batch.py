import json
from types import SimpleNamespace

import httpx
import pytest
from test_batch import manifest
from test_providers import provider
from test_publication import Server
from test_readers import scorecard
from test_remedies import context

from reporemedy.cli import main
from reporemedy.github import GitHub
from reporemedy.models import Mode


@pytest.mark.parametrize("mode", ["non-llm", "local-llm", "llm"])
@pytest.mark.parametrize("bad_report", [False, True])
def test_batch_modes_outputs_and_partial_failure_exit(tmp_path, monkeypatch, mode, bad_report):
    server = Server()
    github = GitHub(transport=httpx.MockTransport(server))
    monkeypatch.setattr("reporemedy.cli.GitHub", lambda token: github)
    monkeypatch.setattr("reporemedy.cli.github_token", lambda: None)
    monkeypatch.setattr("reporemedy.cli.load_environment", lambda: None)
    model = None
    if mode != "non-llm":
        model, _ = provider(monkeypatch, Mode(mode))
        monkeypatch.setattr("reporemedy.cli.ModelProvider", lambda selected: model)
    path = manifest(tmp_path, 2)
    if bad_report:
        (tmp_path / "1.json").write_text("broken", encoding="utf-8")
    out = tmp_path / "batch output"
    assert main(["batch", str(path), "--out", str(out), "--mode", mode, "--limit", "1"]) == int(
        bad_report
    )
    saved = json.loads((out / "batch.json").read_text(encoding="utf-8"))
    assert len(saved["items"]) == 2
    assert saved["items"][0]["status"] == "completed"
    assert all(method == "GET" for method, _, _ in server.calls)
    assert github.client.is_closed
    if model:
        assert model.client.is_closed


@pytest.mark.parametrize("limit", ["0", "26", "bad"])
def test_invalid_batch_limit_exits_two_before_clients(tmp_path, monkeypatch, limit):
    def reject(*args):
        pytest.fail("Invalid batch must not create a client")

    monkeypatch.setattr("reporemedy.cli.GitHub", reject)
    monkeypatch.setattr("reporemedy.cli.load_environment", lambda: None)
    with pytest.raises(SystemExit) as error:
        main(["batch", str(tmp_path / "missing.json"), "--limit", limit])
    assert error.value.code == 2


def test_failed_preview_outcome_exits_one(tmp_path, monkeypatch):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(scorecard()), encoding="utf-8")
    github = GitHub(transport=httpx.MockTransport(Server()))
    monkeypatch.setattr("reporemedy.cli.GitHub", lambda token: github)
    monkeypatch.setattr("reporemedy.cli.github_token", lambda: None)
    monkeypatch.setattr("reporemedy.cli.load_environment", lambda: None)
    monkeypatch.setattr("reporemedy.cli.load_context", lambda *args: context())
    monkeypatch.setattr(
        "reporemedy.cli.prepare",
        lambda *args: SimpleNamespace(
            repository="acme/demo", proposals=[], outcomes=[SimpleNamespace(status="failed")]
        ),
    )
    monkeypatch.setattr("reporemedy.cli.write_preview", lambda *args: None)
    assert (
        main(["preview", str(path), "--repo", "acme/demo", "--report-type", "ossf-scorecard"]) == 1
    )
    assert github.client.is_closed
