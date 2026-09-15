"""Typed command-line interface; publication always requires explicit selection."""

from pathlib import Path
from typing import Annotated

import typer

from reporemedy import __version__
from reporemedy.batch import batch_preview
from reporemedy.config import github_token, load_environment
from reporemedy.context import load_context
from reporemedy.errors import RemedyError
from reporemedy.feedback import collect_feedback
from reporemedy.github import GitHub
from reporemedy.models import Mode, ReportType
from reporemedy.preview import prepare, write_preview
from reporemedy.providers import ModelProvider
from reporemedy.publish import publish, validate_run
from reporemedy.readers import read_report
from reporemedy.storage import read_run

app = typer.Typer(
    help="Turn audit reports into improvements.",
    no_args_is_help=False,
    pretty_exceptions_enable=False,
)


def _version(value: bool) -> None:
    if value:
        print(__version__)
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show version.")
    ] = False,
) -> None:
    """Inspect audit reports and prepare reviewable repository improvements."""


@app.command("inspect")
def inspect_report(
    report: Path,
    repo: Annotated[str, typer.Option(help="OWNER/REPO or GitHub URL")],
    report_type: Annotated[ReportType, typer.Option(help="Input report format")],
) -> None:
    """Validate a report and display its candidate gaps."""
    result = read_report(report, report_type, repo)
    print(result.model_dump_json(indent=2))


@app.command("preview")
def preview_report(
    report: Path,
    repo: Annotated[str, typer.Option(help="OWNER/REPO or GitHub URL")],
    report_type: Annotated[ReportType, typer.Option(help="Input report format")],
    out: Annotated[Path, typer.Option(help="Preview output directory")] = Path("runs/preview"),
    mode: Annotated[Mode, typer.Option(help="Remediation mode")] = Mode.FIXED,
    limit: Annotated[int, typer.Option(help="Maximum remedies/model calls")] = 3,
) -> None:
    """Prepare proposals and diffs without publishing."""
    result = read_report(report, report_type, repo)
    load_environment()
    if not 1 <= limit <= 25:
        raise RemedyError("--limit must be between 1 and 25")
    provider = ModelProvider(mode) if mode != Mode.FIXED else None
    github = GitHub(github_token())
    try:
        context = load_context(github, result.repository)
        run = prepare(result, context, mode, provider, limit)
        write_preview(run, out)
        print(f"{run.repository}: {len(run.proposals)} proposals, {len(run.outcomes)} findings")
        print(f"Review {out / 'README.md'} and the .patch files. Nothing published.")
    finally:
        github.close()
        if provider:
            provider.close()
    raise typer.Exit(1 if any(o.status == "failed" for o in run.outcomes) else 0)


@app.command("publish")
def publish_proposals(
    directory: Path,
    select: Annotated[str, typer.Option(help="Comma-separated proposal IDs from the preview")],
    yes: Annotated[
        bool, typer.Option("--yes", help="Confirm publication non-interactively")
    ] = False,
) -> None:
    """Publish only selected proposals after review."""
    load_environment()
    github = GitHub(github_token())
    try:
        run = read_run(directory)
        selected = [s.strip() for s in select.split(",")]
        for proposal in validate_run(run, selected):
            print(f"{run.repository}: {proposal.id} {proposal.action} — {proposal.title}")
        if not yes:
            try:
                confirmed = input("Publish these selected proposals to GitHub? [y/N] ")
            except EOFError:
                confirmed = ""
            if confirmed.lower() not in {"y", "yes"}:
                print("Cancelled. Nothing published.")
                return
        receipts = publish(directory, selected, github)
        for receipt in receipts:
            print(
                f"{receipt['id']}: {receipt['status']} "
                f"{receipt.get('url', receipt.get('error', ''))}"
            )
        raise typer.Exit(1 if any(r["status"] == "failed" for r in receipts) else 0)
    finally:
        github.close()


@app.command("feedback")
def feedback(directory: Path) -> None:
    """Read GitHub decisions and maintainer feedback."""
    load_environment()
    github = GitHub(github_token())
    try:
        result = collect_feedback(directory, github)
        print(result["summary"])
    finally:
        github.close()


@app.command("batch")
def batch(
    manifest: Path,
    out: Annotated[Path, typer.Option(help="Batch output directory")] = Path("runs/batch"),
    mode: Annotated[Mode, typer.Option(help="Remediation mode")] = Mode.FIXED,
    limit: Annotated[int, typer.Option(help="Maximum remedies/model calls per repository")] = 3,
) -> None:
    """Preview 1–10 repositories from a JSON manifest."""
    load_environment()
    if not 1 <= limit <= 25:
        raise RemedyError("--limit must be between 1 and 25")
    provider = ModelProvider(mode) if mode != Mode.FIXED else None
    github = GitHub(github_token())
    try:
        summary = batch_preview(
            manifest,
            out,
            github,
            mode,
            provider,
            limit,
            progress=lambda message: print(message, flush=True),
        )
        print(f"Review {out / 'README.md'}. Nothing published.")
        raise typer.Exit(1 if any(r["status"] != "completed" for r in summary["items"]) else 0)
    finally:
        github.close()
        if provider:
            provider.close()


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, retaining return codes for callers and errors on stderr."""
    try:
        app(args=argv, prog_name="reporemedy")
    except SystemExit as exc:
        if isinstance(exc.code, int) and exc.code in (0, 1):
            return exc.code
        raise
    except (RemedyError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise SystemExit(2) from None
    return 0  # pragma: no cover - Typer's standalone invocation always exits
