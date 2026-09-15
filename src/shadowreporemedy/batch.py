"""Sequential 1–10 repository batches with independent outcomes and durable summaries."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import field_validator

from shadowreporemedy.context import load_context
from shadowreporemedy.errors import RemedyError
from shadowreporemedy.github import GitHub
from shadowreporemedy.models import Contract, Mode, ReportType, repository_name
from shadowreporemedy.preview import prepare, write_preview
from shadowreporemedy.providers import ModelProvider
from shadowreporemedy.readers import read_report
from shadowreporemedy.storage import atomic_json


class BatchItem(Contract):
    repository: str
    report: str
    report_type: ReportType

    _repository = field_validator("repository")(repository_name)


def batch_preview(
    manifest: Path,
    directory: Path,
    github: GitHub,
    mode: Mode = Mode.FIXED,
    provider: ModelProvider | None = None,
    limit: int = 3,
    progress: Callable[[str], None] = print,
) -> dict[str, Any]:
    try:
        if manifest.stat().st_size > 1024 * 1024:
            raise RemedyError("Batch manifest exceeds 1 MiB")
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RemedyError("Batch manifest must be a readable UTF-8 JSON list") from exc
    if not isinstance(raw, list) or not 1 <= len(raw) <= 10:
        raise RemedyError("A batch must contain between 1 and 10 repository inputs")
    try:
        directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    except FileExistsError as exc:
        raise RemedyError("Batch output exists; use a new --out directory") from exc
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw, 1):
        repository = "invalid input"
        try:
            item = BatchItem.model_validate(entry)
            repository = item.repository
            if repository.casefold() in seen:
                raise RemedyError(
                    "Duplicate repository input; use a separate batch for another scan"
                )
            seen.add(repository.casefold())
            progress(f"[{index}/{len(raw)}] {repository}: reading report and current context...")
            report_path = Path(item.report)
            if not report_path.is_absolute():
                report_path = manifest.parent / report_path
            report = read_report(report_path, item.report_type, repository)
            context = load_context(github, repository)
            run = prepare(report, context, mode, provider, limit)
            child = f"{index:02d}-{repository.replace('/', '--')}"
            write_preview(run, directory / child)
            failed = any(o.status == "failed" for o in run.outcomes)
            result = {
                "repository": repository,
                "status": "partial" if failed else "completed",
                "directory": child,
                "proposals": len(run.proposals),
                "outcomes": [o.model_dump() for o in run.outcomes],
                "base_commit": run.base_commit,
            }
            progress(f"  {len(run.proposals)} proposals; review {child}/README.md")
        except (RemedyError, OSError, ValueError) as exc:
            message = (
                str(exc) if isinstance(exc, RemedyError) else "Invalid input or inaccessible output"
            )
            result = {
                "repository": repository,
                "input_index": index,
                "status": "failed",
                "error": message,
            }
            progress(f"  Failed: {message}")
        results.append(result)
        atomic_json(directory / "batch.json", {"schema_version": 1, "mode": mode, "items": results})
    summary = {"schema_version": 1, "mode": mode, "items": results}
    lines = ["# Batch preview", "", "No issues or PRs were published.", ""]
    for result in results:
        label = f"{result['repository']}: {result['status']}"
        lines.append(
            f"- [{label}]({result['directory']}/README.md)"
            if "directory" in result
            else f"- {label} — {result['error']}"
        )
    (directory / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary
