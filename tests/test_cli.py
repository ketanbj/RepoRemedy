"""CLI contracts independent of help styling and terminal color settings."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reporemedy import __version__
from reporemedy.cli import app, main


def test_help_and_version_without_a_subcommand(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == __version__
    assert main(["--help"]) == 0
    assert "inspect" in capsys.readouterr().out
    result = CliRunner().invoke(app, ["inspect", "--help"])
    assert result.exit_code == 0
    # CI can force color even when CliRunner captures output.
    help_text = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert "--repo" in help_text
    assert "--report-type" in help_text


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["unknown-command"],
        ["inspect"],
        ["inspect", "report.json", "--repo", "acme/demo"],
        ["inspect", "report.json", "--repo", "acme/demo", "--report-type", "unknown"],
        ["inspect", "report.json", "--repo", "acme/demo", "--report-type", "repoauditor", "--bad"],
    ],
)
def test_invalid_cli_arguments_exit_two_on_stderr(args, capsys):
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert output.err
    assert not output.out


def test_inspect_json_is_unadorned_and_read_only(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / "fixtures/repoauditor.txt"
    report = tmp_path / "report with spaces.txt"
    report.write_bytes(fixture.read_bytes())
    monkeypatch.chdir(tmp_path)
    before = report.read_bytes()
    result = CliRunner().invoke(
        app, ["inspect", str(report), "--repo", "acme/demo", "--report-type", "repoauditor"]
    )
    assert result.exit_code == 0
    assert not result.stderr
    assert [f["key"] for f in json.loads(result.stdout)["findings"]] == [
        "SecurityPolicy",
        "DependabotSecurityUpdates",
    ]
    assert report.read_bytes() == before
    assert list(tmp_path.iterdir()) == [report]


def test_report_error_is_concise_and_exits_two(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "inspect",
                str(tmp_path / "missing.txt"),
                "--repo",
                "acme/demo",
                "--report-type",
                "repoauditor",
            ]
        )
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert output.err.startswith("Error:")
    assert "Traceback" not in output.err
    assert not output.out


def test_module_entrypoint_works_outside_checkout(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "reporemedy", "--version"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == __version__
    assert not result.stderr
