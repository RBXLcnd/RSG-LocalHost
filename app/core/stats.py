"""Simple numbers for the Overview page, computed from the saved session history."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any


@dataclass(slots=True)
class WeekStats:
    days: list[tuple[date, int]]  # last N days (oldest first): hosted seconds starting that day
    total_seconds: int
    sessions: int
    peak_players: int  # 0 when unknown (older sessions or the game does not report players)


def compute(history: list[dict[str, Any]], now: datetime | None = None, days: int = 7) -> WeekStats:
    """Hosted sessions that started in the last `days` days (today included)."""
    today = (now or datetime.now()).date()
    first = today - timedelta(days=days - 1)
    per_day = {first + timedelta(days=i): 0 for i in range(days)}
    sessions = peak = total = 0
    for entry in history:
        if entry.get("mode") != "host":
            continue
        try:
            day = datetime.fromisoformat(entry["started"]).date()
        except (KeyError, ValueError, TypeError):
            continue
        if day not in per_day:
            continue
        seconds = int(entry.get("duration", 0))
        per_day[day] += seconds
        total += seconds
        sessions += 1
        peak = max(peak, int(entry.get("peak", 0) or 0))
    return WeekStats(sorted(per_day.items()), total, sessions, peak)
