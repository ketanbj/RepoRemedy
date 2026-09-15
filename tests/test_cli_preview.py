import json

import httpx
import pytest
from test_providers import provider
from test_readers import scorecard
from test_remedies import context

from reporemedy.cli import main
from reporemedy.github import GitHub
from reporemedy.models import Mode


@pytest.mark.parametrize("mode", [None, "non-llm", "local-llm", "llm"])
def test_preview_command_writes_review_artifacts_without_requests(
    tmp_path, monkeypatch, capsys, mode
):
    def reject_request(request):
        pytest.fail(f"Preview unexpectedly sent {request.method} {request.url}")

    github = GitHub(transport=httpx.MockTransport(reject_request))
    monkeypatch.setattr("reporemedy.cli.GitHub", lambda token: github)
    monkeypatch.setattr("reporemedy.cli.github_token", lambda: None)
    monkeypatch.setattr("reporemedy.cli.load_environment", lambda: None)
    monkeypatch.setattr("reporemedy.cli.load_context", lambda *args: context())
    model = None
    if mode in {"local-llm", "llm"}:
        model, _ = provider(monkeypatch, Mode(mode))
        monkeypatch.setattr("reporemedy.cli.ModelProvider", lambda selected: model)
    report = tmp_path / "report.json"
    report.write_text(json.dumps(scorecard()), encoding="utf-8")
    out = tmp_path / "review directory"
    assert (
        main(
            [
                "preview",
                str(report),
                "--repo",
                "acme/demo",
                "--report-type",
                "ossf-scorecard",
                "--out",
                str(out),
            ]
            + (["--mode", mode, "--limit", "1"] if mode else [])
        )
        == 0
    )
    saved = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert saved["repository"] == "acme/demo"
    assert saved["proposals"][0]["action"] == "add-file"
    assert list(out.glob("*.patch"))
    assert "Nothing published" in capsys.readouterr().out
    assert github.client.is_closed

    if model:
        assert model.client.is_closed
    assert saved["mode"] == (mode or "non-llm")


@pytest.mark.parametrize(
    "flags", [["--mode", "invalid"], ["--limit", "0"], ["--limit", "26"], ["--limit", "x"]]
)
def test_invalid_preview_options_fail_before_network(tmp_path, monkeypatch, flags):
    def reject(*args, **kwargs):
        pytest.fail("Invalid CLI options must not open network clients")

    monkeypatch.setattr("reporemedy.cli.GitHub", reject)
    monkeypatch.setattr("reporemedy.cli.ModelProvider", reject)
    monkeypatch.setattr("reporemedy.cli.load_environment", lambda: None)
    report = tmp_path / "report.json"
    report.write_text(json.dumps(scorecard()), encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(
            [
                "preview",
                str(report),
                "--repo",
                "acme/demo",
                "--report-type",
                "ossf-scorecard",
                *flags,
            ]
        )
    assert error.value.code == 2
