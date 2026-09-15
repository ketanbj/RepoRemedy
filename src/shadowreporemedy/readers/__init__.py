"""Report-file interoperability, explicitly selected by the user."""

import hashlib
from pathlib import Path

from shadowreporemedy.errors import RemedyError
from shadowreporemedy.models import Report, ReportType, repository_name
from shadowreporemedy.readers.repoauditor import read_repoauditor
from shadowreporemedy.readers.scorecard import read_scorecard

MAX_REPORT_BYTES = 20 * 1024 * 1024


def read_report(path: Path, report_type: ReportType, repository: str) -> Report:
    try:
        repository = repository_name(repository)
        with path.open("rb") as stream:
            raw = stream.read(MAX_REPORT_BYTES + 1)
        if len(raw) > MAX_REPORT_BYTES:
            raise RemedyError("Report exceeds the 20 MiB input limit")
        contents = raw.decode("utf-8-sig")
        digest = hashlib.sha256(raw).hexdigest()
        if report_type == ReportType.SCORECARD:
            return read_scorecard(contents, repository, digest)
        return read_repoauditor(contents, repository, digest)
    except (OSError, UnicodeError, ValueError) as exc:
        raise RemedyError(
            "Cannot read report: check path, UTF-8 encoding and supported format"
        ) from exc
