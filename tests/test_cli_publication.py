import json

import httpx
import pytest
from test_publication import Server, make_run

from reporemedy.cli import main
from reporemedy.github import GitHub


@pytest.fixture
def publication(tmp_path, monkeypatch):
    run, out = make_run(tmp_path)
    server = Server()
    github = GitHub("test", transport=httpx.MockTransport(server))
    monkeypatch.setattr("reporemedy.cli.GitHub", lambda token: github)
    monkeypatch.setattr("reporemedy.cli.github_token", lambda: "test")
    monkeypatch.setattr("reporemedy.cli.load_environment", lambda: None)
    return run, out, server, github


@pytest.mark.parametrize("answer", ["n", "", "eof"])
def test_decline_or_eof_never_publishes(publication, monkeypatch, answer, capsys):
    run, out, server, github = publication

    def confirm(prompt):
        if answer == "eof":
            raise EOFError
        return answer

    monkeypatch.setattr("builtins.input", confirm)
    assert main(["publish", str(out), "--select", run.proposals[0].id]) == 0
    assert not server.calls
    assert "Cancelled" in capsys.readouterr().out
    assert github.client.is_closed


@pytest.mark.parametrize("noninteractive", [True, False])
def test_selected_publication_preserves_confirmation_and_draft_pr(
    publication, monkeypatch, noninteractive
):
    run, out, server, github = publication

    def confirm(prompt):
        assert not noninteractive, "--yes must bypass the prompt"
        return "yes"

    monkeypatch.setattr("builtins.input", confirm)
    assert (
        main(
            ["publish", str(out), "--select", run.proposals[0].id]
            + (["--yes"] if noninteractive else [])
        )
        == 0
    )
    requests = [
        data for method, path, data in server.calls if method == "POST" and path.endswith("/pulls")
    ]
    assert len(requests) == 1
    assert requests[0]["draft"] is True
    assert (
        json.loads((out / "publication.json").read_text(encoding="utf-8"))["items"][0]["status"]
        == "published"
    )
    assert github.client.is_closed


@pytest.mark.parametrize("selection", [None, "unknown", "duplicate"])
def test_bad_selection_fails_before_any_write(publication, selection):
    run, out, server, github = publication
    args = ["publish", str(out), "--yes"]
    if selection is not None:
        value = (
            run.proposals[0].id + "," + run.proposals[0].id
            if selection == "duplicate"
            else selection
        )
        args.extend(["--select", value])
    try:
        with pytest.raises(SystemExit) as error:
            main(args)
        assert error.value.code == 2
        assert not server.calls
    finally:
        github.close()


def test_publication_failure_returns_one_and_closes_client(publication, monkeypatch, capsys):
    run, out, server, github = publication
    monkeypatch.setattr(
        "reporemedy.cli.publish",
        lambda *args: [
            {"id": run.proposals[0].id, "status": "failed", "error": "permission denied"}
        ],
    )
    assert main(["publish", str(out), "--select", run.proposals[0].id, "--yes"]) == 1
    assert "permission denied" in capsys.readouterr().out
    assert github.client.is_closed
