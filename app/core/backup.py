"""Export / import of the user's settings and profiles as a small JSON file.

Never included: the Discord key (a secret), the Studio path (specific to this PC), the session
history and the first-run flags. Importing goes through the normal settings validation, so a broken
or hand-edited file can never put the app in a bad state.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app import __version__
from app.core.settings import AppSettings, SettingsStore

FORMAT = "rsg-localhost-settings"

EXPORT_KEYS = (
    "user_id", "host_tunnel", "join_tunnel", "server_port", "place_path",
    "recent_tunnels", "recent_maps", "profiles",
    "notify_ready", "check_updates", "language", "background_theme", "appearance", "accent",
    "server_name",
    "auto_feature_enabled", "auto_enabled", "auto_private", "auto_on_hours", "auto_off_hours", "auto_maps",
)


class BackupError(ValueError):
    """The file is not a usable RSG LocalHost settings export."""


def export_payload(settings: AppSettings) -> dict[str, Any]:
    data = asdict(settings)
    return {
        "format": FORMAT,
        "app_version": __version__,
        "settings": {key: data[key] for key in EXPORT_KEYS},
    }


def export_to(path: Path, settings: AppSettings) -> None:
    path.write_text(json.dumps(export_payload(settings), indent=2, ensure_ascii=False), encoding="utf-8")


def read_import(path: Path) -> dict[str, Any]:
    """The cleaned values from an export file (only EXPORT_KEYS). Raises BackupError for anything else."""
    try:
        if path.stat().st_size > 2_000_000:
            raise BackupError("File too large")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BackupError(str(exc)) from exc
    if not isinstance(payload, dict) or payload.get("format") != FORMAT or not isinstance(payload.get("settings"), dict):
        raise BackupError("Not an RSG LocalHost settings file")
    raw = {k: v for k, v in payload["settings"].items() if k in EXPORT_KEYS}
    if not raw:
        raise BackupError("Empty settings file")
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "data.json"
        scratch.write_text(json.dumps(raw), encoding="utf-8")
        cleaned = asdict(SettingsStore(scratch).load())
    return {key: cleaned[key] for key in raw}
