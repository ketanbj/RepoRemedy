"""Atomic local state with an exclusive per-run publication lock."""

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from shadowreporemedy.errors import RemedyError
from shadowreporemedy.models import Run


def read_run(directory: Path) -> Run:
    try:
        path = directory / "run.json"
        if path.stat().st_size > 20 * 1024 * 1024:
            raise RemedyError("Run exceeds 20 MiB")
        return Run.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise RemedyError(
            "Cannot read run.json; use a complete shadowRepoRemedy preview directory"
        ) from exc


def atomic_json(path: Path, value: Any) -> None:
    fd, name = tempfile.mkstemp(prefix=".shadowreporemedy-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def run_lock(directory: Path) -> Iterator[None]:
    path = directory / ".publish.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RemedyError(
            "Run is locked; if the publisher crashed, verify GitHub before removing .publish.lock"
        ) from exc
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        path.unlink()
