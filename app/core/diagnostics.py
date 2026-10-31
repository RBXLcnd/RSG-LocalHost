from __future__ import annotations

import platform
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from app import __app_name__, __version__

LOG_TAIL_LINES = 60
_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_KEEP_IPS = {"127.0.0.1", "0.0.0.0"}


def redact(text: str, secrets: Iterable[str] = (), home: str | None = None) -> str:
    """Hide what shouldn't be pasted in public: the user's folder, given secrets and public IPs.

    `secrets` are replaced longest-first (so a full `host:port` goes before its `host` part)."""
    home = str(Path.home()) if home is None else home
    if home and len(home) > 3:
        for variant in {home, home.replace("\\", "/"), home.replace("/", "\\")}:
            text = re.sub(re.escape(variant), "~", text, flags=re.IGNORECASE)
    for secret in sorted({s for s in secrets if s}, key=len, reverse=True):
        text = re.sub(re.escape(secret), "<hidden>", text, flags=re.IGNORECASE)
    return _IPV4.sub(lambda m: m.group(0) if m.group(0) in _KEEP_IPS else "x.x.x.x", text)


def log_tail(log_text: str, lines: int = LOG_TAIL_LINES) -> str:
    kept = [line for line in log_text.splitlines() if line.strip()]
    return "\n".join(kept[-lines:])


def _qt_versions() -> str:
    try:
        import PySide6

        return f"PySide6 {PySide6.__version__}"
    except Exception:
        return "PySide6 unknown"


def build_diagnostics(
    *,
    mode: str,
    status: str,
    uptime: str,
    port: str,
    tunnel_set: bool,
    map_name: str,
    studio_name: str,
    studio_found: bool,
    log_text: str,
    secrets: Iterable[str] = (),
    now: datetime | None = None,
) -> str:
    """A support summary meant to be pasted in Discord. Never includes the tunnel address or User ID."""
    now = now or datetime.now()
    header = [
        f"{__app_name__} {__version__} diagnostics",
        f"Generated: {now.isoformat(timespec='seconds')}",
        f"System: {platform.platform()}",
        f"Python {platform.python_version()}, {_qt_versions()}",
        f"Studio: {studio_name or 'not configured'} ({'found' if studio_found else 'missing'})",
        f"Mode: {mode}",
        f"Status: {status}",
        f"Live for: {uptime}",
        f"Port: {port or '-'}",
        f"Tunnel: {'set' if tunnel_set else 'none'}",
    ]
    if map_name:
        header.append(f"Map: {map_name}")
    body = log_tail(log_text)
    text = "\n".join(header) + f"\n\nLast log lines:\n{body or '(empty)'}\n"
    return redact(text, secrets)
