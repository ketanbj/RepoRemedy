import json
from pathlib import Path

import pytest

from shadowreporemedy.cli import main
from shadowreporemedy.errors import RemedyError
from shadowreporemedy.models import ReportType, repository_name
from shadowreporemedy.readers import read_report
from shadowreporemedy.readers.repoauditor import read_repoauditor
from shadowreporemedy.readers.scorecard import read_scorecard


def scorecard(score=0):
    return {
        "repo": {"name": "github.com/acme/demo", "commit": "abc"},
        "scorecard": {"version": "v5.5.0"},
        "checks": [
            {"name": "Security-Policy", "score": score, "reason": "security policy missing"}
        ],
    }


@pytest.mark.parametrize(
    "name", ["acme/demo", "https://github.com/acme/demo/", "github.com/acme/demo.git"]
)
def test_repository_identity(name):
    assert repository_name(name) == "acme/demo"


@pytest.mark.parametrize(
    "name",
    [
        "https://vizfold.github.io",
        "https://evil.test/acme/demo",
        "https://github.com/acme/demo?x=y",
        "a/..",
        "a/b/c",
        "a/b#x",
    ],
)
def test_unsafe_or_ambiguous_repository(name):
    with pytest.raises(ValueError):
        repository_name(name)


@pytest.mark.parametrize("score,status,count", [(0, "gap", 1), (-1, "unavailable", 1), (10, "", 0)])
def test_scorecard_evidence_preserved(score, status, count):
    report = read_scorecard(json.dumps(scorecard(score)), "acme/demo", "digest")
    assert len(report.findings) == count
    if count:
        assert report.findings[0].status == status
        assert json.loads(report.findings[0].evidence) == scorecard(score)["checks"][0]


def test_wrapper_does_not_copy_contacts():
    data = [{"meta": {"Contact Email": "private@example.org"}, "scorecard": scorecard()}]
    report = read_scorecard(json.dumps(data), "acme/demo", "digest")
    assert "private@example.org" not in report.model_dump_json()
    with pytest.raises(RemedyError, match="Multiple"):
        read_scorecard(json.dumps(data * 2), "acme/demo", "digest")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(checks=[]),
        lambda d: d.update(scorecard={"version": "v6.0.0"}),
        lambda d: d["checks"][0].update(score=True),
        lambda d: d["checks"][0].update(score=11),
        lambda d: d["checks"][0].update(reason=None),
        lambda d: d["checks"].extend(d["checks"][:]),
        lambda d: d.update(repo={"name": "other/repo"}),
    ],
)
def test_scorecard_rejects_incomplete_or_drifted_reports(mutation):
    data = scorecard()
    mutation(data)
    with pytest.raises(RemedyError):
        read_scorecard(json.dumps(data), "acme/demo", "digest")


def test_repoauditor_nested_panels():
    text = Path("tests/fixtures/repoauditor.txt").read_text(encoding="utf-8")
    report = read_repoauditor(text, "acme/demo", "digest")
    assert [f.key for f in report.findings] == ["SecurityPolicy", "DependabotSecurityUpdates"]
    assert "Resolution" in report.findings[0].evidence
    assert "ERROR:" in report.findings[0].evidence


@pytest.mark.parametrize(
    "text",
    [
        "nonsense",
        "╭─ [Error] SecurityPolicy ─╮\n│ missing │",
        "╭─ [Error] SecurityPolicy ─╮\n╰────────╯",
    ],
)
def test_repoauditor_rejects_ambiguous_input(text):
    with pytest.raises(RemedyError):
        read_repoauditor(text, "acme/demo", "digest")


def test_clean_repoauditor_report():
    report = read_repoauditor(
        "Metrics\nSuccessful: 10\nWarnings: 0 (0%)\nErrors: 0 (0%)", "a/b", "d"
    )
    assert report.findings == []


def test_file_and_cli(tmp_path, capsys):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(scorecard()))
    assert read_report(path, ReportType.SCORECARD, "acme/demo").source_sha256
    assert (
        main(["inspect", str(path), "--repo", "acme/demo", "--report-type", "ossf-scorecard"]) == 0
    )
    assert '"Security-Policy"' in capsys.readouterr().out
    with pytest.raises(SystemExit) as error:
        main(["inspect", "absent.json", "--repo", "acme/demo", "--report-type", "ossf-scorecard"])
    assert error.value.code == 2
