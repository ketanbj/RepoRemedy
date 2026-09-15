import json

import httpx
import pytest
from test_publication import Server
from test_readers import scorecard

from shadowreporemedy.batch import batch_preview
from shadowreporemedy.cli import main
from shadowreporemedy.errors import RemedyError
from shadowreporemedy.github import GitHub


def manifest(tmp_path, count=10):
    entries = []
    for i in range(count):
        data = scorecard()
        data["repo"]["name"] = f"acme/repo{i}"
        (tmp_path / f"{i}.json").write_text(json.dumps(data))
        entries.append(
            {"repository": f"acme/repo{i}", "report": f"{i}.json", "report_type": "ossf-scorecard"}
        )
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(entries))
    return path


def test_ten_repositories_and_one_bad_report_are_isolated(tmp_path):
    path = manifest(tmp_path)
    (tmp_path / "4.json").write_text("broken report")
    github = GitHub(transport=httpx.MockTransport(Server()))
    try:
        output = tmp_path / "out"
        result = batch_preview(path, output, github)
        assert len(result["items"]) == 10
        assert sum(i["status"] == "completed" for i in result["items"]) == 9
        assert result["items"][4]["status"] == "failed"
        assert result["items"][9]["proposals"] == 1
        assert (output / "README.md").exists()
        assert json.loads((output / "batch.json").read_text())["items"] == result["items"]
    finally:
        github.close()


def test_batch_rejects_duplicate_invalid_and_missing_inputs(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            [{"repository": "acme/a", "report": "absent.json", "report_type": "ossf-scorecard"}] * 2
            + [{"repository": "website"}]
        )
    )
    github = GitHub(transport=httpx.MockTransport(Server()))
    try:
        result = batch_preview(path, tmp_path / "out", github)
        assert all(i["status"] == "failed" for i in result["items"])
        assert "Duplicate" in result["items"][1]["error"]
    finally:
        github.close()


@pytest.mark.parametrize("data", [[], [{}] * 11, {}])
def test_batch_scope_boundaries(tmp_path, data):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    github = GitHub()
    try:
        with pytest.raises(RemedyError, match="between 1 and 10"):
            batch_preview(path, tmp_path / "out", github)
    finally:
        github.close()


def test_cli_batch_and_single_preview_and_cancellation(tmp_path, monkeypatch, capsys):
    server = Server()
    monkeypatch.setattr(
        "shadowreporemedy.cli.GitHub",
        lambda token: GitHub(token, transport=httpx.MockTransport(server)),
    )
    monkeypatch.setattr("shadowreporemedy.cli.github_token", lambda: "test")
    monkeypatch.setattr("shadowreporemedy.cli.load_environment", lambda: None)
    path = manifest(tmp_path, 1)
    assert main(["batch", str(path), "--out", str(tmp_path / "batch")]) == 0
    out = tmp_path / "single"
    assert (
        main(
            [
                "preview",
                str(tmp_path / "0.json"),
                "--repo",
                "acme/repo0",
                "--report-type",
                "ossf-scorecard",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    run = json.loads((out / "run.json").read_text())
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert main(["publish", str(out), "--select", run["proposals"][0]["id"]]) == 0
    assert not any(m == "POST" for m, _, _ in server.calls)
    assert "Cancelled" in capsys.readouterr().out
