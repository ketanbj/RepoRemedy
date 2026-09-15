"""Typed command-line interface; publication always requires explicit selection."""

from pathlib import Path
from typing import Annotated

import typer

from reporemedy import __version__
from reporemedy.config import github_token, load_environment
from reporemedy.context import load_context
from reporemedy.errors import RemedyError
from reporemedy.github import GitHub
from reporemedy.models import ReportType
from reporemedy.preview import prepare, write_preview
from reporemedy.readers import read_report

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
) -> None:
    """Prepare proposals and diffs without publishing."""
    result = read_report(report, report_type, repo)
    load_environment()
    github = GitHub(github_token())
    try:
        context = load_context(github, result.repository)
        run = prepare(result, context)
        write_preview(run, out)
        print(f"{run.repository}: {len(run.proposals)} proposals, {len(run.outcomes)} findings")
        print(f"Review {out / 'README.md'} and the .patch files. Nothing published.")
    finally:
        github.close()


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
