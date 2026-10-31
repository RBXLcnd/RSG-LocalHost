from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import DATA_FILE


@dataclass(slots=True)
class AppSettings:
    user_id: str = ""
    host_tunnel: str = ""
    join_tunnel: str = ""
    server_port: str = "55555"
    place_path: str = ""
    studio_path: str = ""
    recent_tunnels: list[str] = field(default_factory=list)
    recent_maps: list[str] = field(default_factory=list)
    notify_ready: bool = True
    update_repo: str = ""
    profiles: list[dict[str, str]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    # ---- 24/7 auto-cycle (see app/core/autopilot.py) ----
    auto_feature_enabled: bool = False  # is the 24/7 section shown at all (asked on first launch, then in Settings)
    auto_feature_asked: bool = False    # the first-launch question was already answered
    auto_enabled: bool = False
    auto_on_hours: str = "4"      # hours the server stays online
    auto_off_hours: str = "2"     # hours it stays paused before coming back
    auto_maps: list[str] = field(default_factory=list)  # map rotation; empty = just use the Map file field
    auto_map_index: int = 0       # next map in the rotation (kept between runs)
    # ---- identity shown in the Discord /server-status list ----
    server_name: str = ""         # public name chosen by the host
    # ---- Discord sign-in: the private key from /host-login (a webhook URL only for your account) ----
    discord_key: str = ""
    discord_username: str = ""


PROFILE_KEYS = ("user_id", "host_tunnel", "server_port", "place_path")


def _clean_profiles(value: Any) -> list[dict[str, str]]:
    """Saved session profiles: dicts with a non-empty name; anything else is dropped."""
    if not isinstance(value, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        profile = {"name": name.strip()}
        for key in PROFILE_KEYS:
            raw = item.get(key, "")
            profile[key] = raw if isinstance(raw, str) else ""
        cleaned.append(profile)
    return cleaned


def _clean_history(value: Any) -> list[dict[str, Any]]:
    """Finished sessions, newest first. Entries that don't look right are dropped."""
    if not isinstance(value, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        mode, started, duration = item.get("mode"), item.get("started"), item.get("duration")
        if mode not in ("host", "join") or not isinstance(started, str):
            continue
        if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
            continue
        cleaned.append(
            {
                "mode": mode,
                "started": started,
                "duration": duration,
                "map": item["map"] if isinstance(item.get("map"), str) else "",
                "tunnel": item["tunnel"] if isinstance(item.get("tunnel"), str) else "",
            }
        )
    return cleaned


def _clean_list(value: Any) -> list[str]:
    """A list of non-empty strings; anything else in the file is dropped."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


class SettingsStore:
    def __init__(self, path: Path = DATA_FILE) -> None:
        self.path = path

    def load(self) -> AppSettings:
        defaults = asdict(AppSettings())
        try:
            if self.path.exists():
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    known = {k: v for k, v in payload.items() if k in defaults}
                    settings = AppSettings(**{**defaults, **known})
                    settings.recent_tunnels = _clean_list(settings.recent_tunnels)
                    settings.recent_maps = _clean_list(settings.recent_maps)
                    if not isinstance(settings.notify_ready, bool):
                        settings.notify_ready = True
                    if not isinstance(settings.update_repo, str):
                        settings.update_repo = ""
                    settings.auto_maps = _clean_list(settings.auto_maps)
                    for key in ("server_name", "discord_key", "discord_username"):
                        if not isinstance(getattr(settings, key), str):
                            setattr(settings, key, "")
                    for key in ("auto_enabled", "auto_feature_enabled", "auto_feature_asked"):
                        if not isinstance(getattr(settings, key), bool):
                            setattr(settings, key, False)
                    for key, default in (("auto_on_hours", "4"), ("auto_off_hours", "2")):
                        if not isinstance(getattr(settings, key), str) or not getattr(settings, key).strip():
                            setattr(settings, key, default)
                    if not isinstance(settings.auto_map_index, int) or isinstance(settings.auto_map_index, bool):
                        settings.auto_map_index = 0
                    settings.profiles = _clean_profiles(settings.profiles)
                    settings.history = _clean_history(settings.history)
                    return settings
        except Exception:
            pass
        return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.write_text(
            json.dumps(asdict(settings), indent=2),
            encoding="utf-8",
        )

    def update(self, settings: AppSettings, **values: Any) -> AppSettings:
        payload = asdict(settings)
        payload.update(values)
        next_settings = AppSettings(**payload)
        self.save(next_settings)
        return next_settings
