"""Publishes the host's online/offline state to the Discord bot (/server-status).

Goes through the user's private key (a Discord webhook from /host-login, see api.py): the bot
knows which Discord account owns the key, validates the fields and stamps the time.
There is no database access in this app.

Every send runs on a background thread. This is called from Qt's main thread (the
24/7 timer) and a slow or unreachable bot must never freeze the window. Failures
only produce a log line; they never raise.
"""
from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime, timezone

from app.core.api import ApiError, post_status

NAME_MIN, NAME_MAX = 3, 24

LogFn = Callable[[str, str], None] | None

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="discord-status")  # 1 worker = sends stay in order
_key = ""
_name = ""
_tunnel = ""
_private = False
_players: int | None = None
_players_at = 0.0
PLAYERS_FRESH_SECONDS = 150  # the game reports every 30 s; older than this = unknown


def set_session(key: str) -> None:
    global _key
    _key = (key or "").strip()


def set_private(private: bool) -> None:
    """Private server: nothing is published to Discord, so it never shows in /server-status."""
    global _private
    _private = bool(private)


def set_players(count: int | None) -> None:
    """Latest player count reported by the game (see player_count.py)."""
    global _players, _players_at
    _players = count
    _players_at = time.monotonic()


def current_players() -> int | None:
    if _players is None or time.monotonic() - _players_at > PLAYERS_FRESH_SECONDS:
        return None
    return _players


def set_identity(name: str, tunnel: str) -> None:
    """Name and tunnel shown in the Discord list. Called before every launch (they may have changed)."""
    global _name, _tunnel
    _name = clean_name(name)
    _tunnel = (tunnel or "").strip()


def clean_name(name: str) -> str:
    """Single line, no control characters, max NAME_MAX chars."""
    flat = " ".join("".join(ch for ch in (name or "") if ch.isprintable()).split())
    return flat[:NAME_MAX]


def validate_name(name: str) -> str | None:
    cleaned = clean_name(name)
    if len(cleaned) < NAME_MIN:
        return f"At least {NAME_MIN} characters"
    if len(" ".join((name or "").split())) > NAME_MAX:
        return f"Max {NAME_MAX} characters"
    return None


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


def _send(body: dict, key: str, log_fn: LogFn) -> None:
    try:
        post_status(key, body)
    except ApiError as exc:
        if log_fn is None:
            return
        level = "error" if exc.code == "invalid_key" else "warn"
        log_fn(f"Discord status: update failed. {exc.describe()}", level)


def push_status(
    log_fn: LogFn = None,
    *,
    online: bool,
    map_name: str | None = None,
    next_map_name: str | None = None,
    started_at: datetime | None = None,
    next_event_at: datetime | None = None,
    cycle_hours: float | None = None,
) -> None:
    """Fire-and-forget. Datetimes should be timezone-aware (or UTC)."""
    if _private:
        return
    if not _key or not _name:
        if log_fn:
            log_fn("Discord status: not signed in or no server name, nothing was published.", "warn")
        return
    body: dict = {"name": _name, "online": online, "players": current_players() if online else None}
    if _tunnel:
        body["tunnel"] = _tunnel
    if map_name is not None:
        body["mapName"] = map_name
    if next_map_name is not None:
        body["nextMapName"] = next_map_name
    if started_at is not None:
        body["startedAt"] = _iso(started_at)
    if next_event_at is not None:
        body["nextEventAt"] = _iso(next_event_at)
    if cycle_hours is not None:
        body["cycleHours"] = cycle_hours
    _executor.submit(_send, body, _key, log_fn)


def flush(timeout: float = 6.0) -> None:
    """Wait for queued sends (used on quit so the final "offline" gets out)."""
    try:
        _executor.submit(lambda: None).result(timeout=timeout)
    except Exception:
        pass
