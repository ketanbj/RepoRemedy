"""User-facing errors, without credentials or raw network response bodies."""


class RemedyError(Exception):
    """An actionable, safely printable operational error."""
