"""Explicit, minimal configuration. Only the selected .env file is loaded."""

import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv


def load_environment(path: Path = Path(".env")) -> None:
    load_dotenv(path, override=False, interpolate=False)


def github_token() -> str | None:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token", "--hostname", "github.com"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None
