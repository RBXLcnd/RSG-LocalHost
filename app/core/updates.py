"""Update check: asks GitHub for the latest Release and compares it with the running version.

Only one small HTTPS request to api.github.com (no data about the user is sent besides what any
request carries). It never downloads or installs anything: the user is pointed at the release page.
Runs on a worker thread; every failure ends as state "error", never as an exception.
"""
from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request

from PySide6.QtCore import QObject, Signal

DEFAULT_REPO = "RBXLcnd/RSG-LocalHost"
API_URL = "https://api.github.com/repos/{repo}/releases/latest"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TIMEOUT = 8

NEWER, CURRENT, ERROR = "newer", "current", "error"


def parse_version(text: str) -> tuple[int, ...] | None:
    """'v2.4.1' -> (2, 4, 1). Anything that is not numbers separated by dots -> None."""
    match = re.match(r"^v?(\d+(?:\.\d+){0,3})$", (text or "").strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def is_newer(latest: str, current: str) -> bool:
    a, b = parse_version(latest), parse_version(current)
    if a is None or b is None:
        return False
    size = max(len(a), len(b))
    return a + (0,) * (size - len(a)) > b + (0,) * (size - len(b))


def effective_repo(configured: str) -> str:
    repo = (configured or "").strip()
    return repo if REPO_RE.match(repo) else DEFAULT_REPO


def fetch_latest(repo: str) -> dict:
    """Latest release JSON. Raises OSError/ValueError on any problem."""
    request = urllib.request.Request(
        API_URL.format(repo=repo),
        headers={"Accept": "application/vnd.github+json", "User-Agent": "RSG-LocalHost-update-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read(1_000_000).decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise OSError(str(exc)) from None
    if not isinstance(data, dict):
        raise ValueError("unexpected answer")
    return data


class UpdateCheck(QObject):
    """Emits result(state, version, url). `url` is always a github.com page of the checked repo.

    The request runs on a daemon thread, so a slow network never delays closing the app."""

    result = Signal(str, str, str)

    def __init__(self, repo: str, current: str, parent=None) -> None:
        super().__init__(parent)
        self.repo = effective_repo(repo)
        self.current = current

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True, name="update-check").start()

    def _run(self) -> None:
        try:
            data = fetch_latest(self.repo)
            tag = str(data.get("tag_name") or "")
            url = str(data.get("html_url") or "")
            if not url.startswith(f"https://github.com/{self.repo}/"):
                url = f"https://github.com/{self.repo}/releases/latest"
            if parse_version(tag) is None:
                raise ValueError("no version in the release tag")
            state = NEWER if is_newer(tag, self.current) else CURRENT
            self.result.emit(state, tag.lstrip("v"), url)
        except (OSError, ValueError):
            self.result.emit(ERROR, "", "")
