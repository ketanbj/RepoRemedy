"""Bounded GitHub REST transport; no response bodies or credentials in errors."""

import time
from typing import Any

import httpx

from reporemedy.errors import RemedyError


class GitHub:
    def __init__(self, token: str | None = None, *, transport: httpx.BaseTransport | None = None):
        self.authenticated = bool(token)
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoRemedy/0.1",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=httpx.Timeout(30, connect=10),
            follow_redirects=False,
            transport=transport,
        )

    def close(self) -> None:
        self.client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        missing_ok: bool = False,
    ) -> Any:
        if not path.startswith("/repos/") and path != "/user":
            raise RemedyError("Invalid GitHub API path")
        # GET retries are safe; never retry a write with an unknown server-side outcome.
        attempts = 3 if method == "GET" else 1
        for attempt in range(attempts):
            try:
                response = self.client.request(method, path, json=data)
            except httpx.HTTPError as exc:
                if method == "GET" and attempt + 1 < attempts:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise RemedyError(
                    "GitHub network request failed; check connectivity and retry"
                ) from exc
            if response.status_code == 404 and missing_ok:
                return None
            if response.status_code >= 500 and attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
                continue
            if response.status_code >= 400 or response.is_redirect:
                hint = {
                    401: "check GitHub authentication",
                    403: "check permissions or rate limits",
                    404: "check repository access",
                    409: "repository changed; preview again",
                    422: "check branch, permissions and existing items",
                    429: "rate limited; wait before retrying",
                }.get(response.status_code, "retry after checking GitHub")
                raise RemedyError(f"GitHub HTTP {response.status_code}: {hint}")
            if response.status_code == 204:
                return None
            try:
                return response.json()
            except ValueError as exc:
                raise RemedyError("GitHub returned an invalid JSON response") from exc
        raise RemedyError("GitHub request could not complete")  # pragma: no cover

    def pages(self, path: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for page in range(1, 101):
            separator = "&" if "?" in path else "?"
            result = self.request("GET", f"{path}{separator}per_page=100&page={page}")
            if not isinstance(result, list) or any(not isinstance(i, dict) for i in result):
                raise RemedyError("Expected a GitHub list response")
            items.extend(result)
            if len(result) < 100:
                return items
        raise RemedyError("GitHub pagination limit reached; narrow the repository scope")
