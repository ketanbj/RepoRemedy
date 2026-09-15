import json

import httpx
import pytest
from test_readers import scorecard
from test_remedies import context

from reporemedy.cli import main
from reporemedy.github import GitHub


def test_preview_command_writes_review_artifacts_without_requests(tmp_path, monkeypatch, capsys):
    def reject_request(request):
        pytest.fail(f"Preview unexpectedly sent {request.method} {request.url}")

    github = GitHub(transport=httpx.MockTransport(reject_request))
    monkeypatch.setattr("reporemedy.cli.GitHub", lambda token: github)
    monkeypatch.setattr("reporemedy.cli.github_token", lambda: None)
    monkeypatch.setattr("reporemedy.cli.load_environment", lambda: None)
    monkeypatch.setattr("reporemedy.cli.load_context", lambda *args: context())
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
        )
        == 0
    )
    saved = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert saved["repository"] == "acme/demo"
    assert saved["proposals"][0]["action"] == "add-file"
    assert list(out.glob("*.patch"))
    assert "Nothing published" in capsys.readouterr().out
    assert github.client.is_closed
