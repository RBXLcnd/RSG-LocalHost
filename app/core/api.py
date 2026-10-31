"""Talks to the Discord bot through a private Discord webhook (the "key" from /host-login).

No server of our own is involved: the app posts a small message to the webhook (HTTPS,
hosted by Discord) and the bot reads it, validates it and updates /server-status.
The webhook belongs to one Discord account, so the bot always knows whose server it is.
Standard library only.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

TIMEOUT = 15
PREFIX = "RSG1 "
HOOK_RE = re.compile(
    r"^https://(?:www\.|canary\.|ptb\.)?discord(?:app)?\.com/api/(?:v\d+/)?webhooks/(\d{15,25})/([A-Za-z0-9_\-]{20,120})/?$"
)


class ApiError(Exception):
    def __init__(self, status: int, code: str = "", message: str = "") -> None:
        super().__init__(message or code or f"HTTP {status}")
        self.status = status      # 0 = no answer at all
        self.code = code
        self.message = message

    def describe(self) -> str:
        if self.code in ("invalid_key", "gone"):
            return "That key is no longer valid. Run /host-login in Discord and sign in again."
        if self.status == 0:
            return "Cannot reach Discord. Check your internet connection."
        if self.status == 429:
            return "Discord is rate limiting this key. Try again in a moment."
        return self.message or f"Discord error ({self.status})."


def normalize_key(text: str) -> str | None:
    """Return the canonical webhook URL, or None if the text is not a Discord webhook URL."""
    match = HOOK_RE.match((text or "").strip())
    if not match:
        return None
    return f"https://discord.com/api/webhooks/{match.group(1)}/{match.group(2)}"


def _request(method: str, url: str, body: dict | None = None) -> bytes:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    request.add_header("User-Agent", "DiscordBot (https://github.com/rsg-localhost, 1.0)")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 404):
            raise ApiError(exc.code, "invalid_key") from None
        raise ApiError(exc.code, "http") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ApiError(0, "network", str(exc)) from None


def check_key(key: str) -> str:
    """Is the webhook alive? Returns the account label stored in its name (e.g. "Joao")."""
    raw = _request("GET", key)
    try:
        name = str(json.loads(raw).get("name", ""))
    except ValueError:
        name = ""
    return name[4:].strip() if name.startswith("RSG ") else name


def post_status(key: str, body: dict) -> None:
    payload = PREFIX + json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    if len(payload) > 1900:
        raise ApiError(0, "too_long", "Status message too long.")
    _request("POST", key + "?wait=false", {"content": payload, "allowed_mentions": {"parse": []}})
