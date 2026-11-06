from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from app.core.config import OVERVIEW_HISTORY_ROWS, PROXY_PORT
from app.core import motion
from app.core import stats as stats_mod
from app.core.i18n import tr
from app.core.uptime import format_uptime
from app.pages.base import Page, Step, card, divider, section_label, vline
from app.widgets.buttons import AppButton
from app.widgets.effects import animate_glow, apply_glow
from app.widgets.icons import app_icon
from app.widgets.status import StatusDot
from app.widgets.week_chart import WeekChart


class ActionTile(QFrame):
    """Large clickable launch tile (a styled frame, not a QPushButton —
    Fusion paints button chrome over child widgets, which hides text)."""

    clicked = Signal()

    def __init__(self, title: str, text: str, icon: str, primary: bool) -> None:
        super().__init__()
        tone = "primary" if primary else "secondary"
        self.setProperty("tile", tone)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMinimumHeight(128)
        self._glow = apply_glow(self, "#00b2ff", blur=30, alpha=150) if primary else None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(4)

        top = QHBoxLayout()
        badge = QLabel()
        badge.setObjectName("tileBadge")
        badge.setProperty("tone", tone)
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(app_icon(icon, "#ffffff" if primary else "#1e9bff").pixmap(18, 18))
        arrow = QLabel()
        arrow.setPixmap(app_icon("next", "#ffffff" if primary else "#5d7099").pixmap(16, 16))
        top.addWidget(badge)
        top.addStretch()
        top.addWidget(arrow)

        title_label = QLabel(title)
        title_label.setObjectName("tileTitle")
        text_label = QLabel(text)
        text_label.setObjectName("tileText")
        text_label.setProperty("tone", tone)
        text_label.setWordWrap(True)

        layout.addLayout(top)
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(text_label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        if self._glow is not None:
            animate_glow(self._glow, 44, 230)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._glow is not None:
            animate_glow(self._glow, 30, 150)
        super().leaveEvent(event)


def _history_row(entry: dict) -> QFrame:
    """One finished session: kind, what it was, how long it ran, when it started."""
    row = QFrame()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(14)

    host = entry["mode"] == "host"
    kind = QLabel("HOST" if host else "JOIN")
    kind.setObjectName("metricLabel")
    kind.setFixedWidth(44)
    layout.addWidget(kind)

    if host:
        title = entry["map"] or "Local server"
        detail = entry["tunnel"]
    else:
        title = entry["tunnel"] or "Tunnel"
        detail = ""
    name = QLabel(title)
    name.setToolTip("  \u00b7  ".join(part for part in (title, detail) if part))
    layout.addWidget(name, 1)
    if detail:
        extra = QLabel(detail)
        extra.setObjectName("fieldHint")
        layout.addWidget(extra)

    duration = QLabel(format_uptime(entry["duration"]))
    duration.setObjectName("fieldHint")
    duration.setMinimumWidth(56)
    duration.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(duration)

    try:
        when = datetime.fromisoformat(entry["started"]).strftime("%d %b  %H:%M")
    except ValueError:
        when = entry["started"]
    date = QLabel(when)
    date.setObjectName("fieldHint")
    date.setMinimumWidth(96)
    date.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(date)
    return row


def _metric(value: str, caption: str, count_to: int | None = None, fmt=str) -> QVBoxLayout:
    """A number with its caption. With `count_to` the number counts up from 0 when it appears."""
    box = QVBoxLayout()
    box.setSpacing(2)
    number = QLabel(value)
    number.setObjectName("metricValue")
    if count_to:
        number.setText(fmt(0))
        motion.tween(number, 0, count_to, 800, lambda v: number.setText(fmt(round(v))),
                     on_done=lambda: number.setText(value))
    text = QLabel(caption)
    text.setObjectName("fieldHint")
    box.addWidget(number)
    box.addWidget(text)
    return box


def _stats_card(week: stats_mod.WeekStats) -> QFrame:
    """Last 7 days of hosting: totals plus a small bar chart (hours per day)."""
    box = QVBoxLayout()
    box.setSpacing(12)
    box.addWidget(section_label("Last 7 days", "overview_week"))
    numbers = QHBoxLayout()
    numbers.setSpacing(28)
    numbers.addLayout(_metric(format_uptime(week.total_seconds), "Time online", week.total_seconds, lambda s: format_uptime(int(s))))
    numbers.addLayout(_metric(str(week.sessions), "Sessions hosted", week.sessions))
    numbers.addLayout(_metric(str(week.peak_players) if week.peak_players else "-", "Player peak", week.peak_players))
    numbers.addStretch(1)
    box.addLayout(numbers)
    box.addWidget(WeekChart(week.days))
    return card(box, (22, 16, 22, 12))


class OverviewPage(Page):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        active = window.session_active()
        server_active = "create" in getattr(window, "active_modes", set())
        connection_active = "join" in getattr(window, "active_modes", set())
        create_text = "Open server" if server_active else "New server"
        join_text = "Open connection" if connection_active else "Join"

        self.add_header(
            "TeamTest launcher",
            "Host a Studio server or join one through a UDP tunnel proxy.",
            eyebrow="Overview",
        )

        if active:
            banner = QFrame()
            banner.setObjectName("banner")
            row = QHBoxLayout(banner)
            row.setContentsMargins(18, 10, 12, 10)
            row.setSpacing(12)
            live_dot = StatusDot("#2ee6a6", 8)
            live_dot.set_pulsing(True)
            row.addWidget(live_dot)
            if server_active and connection_active:
                what = "Server + tunnel running"
            elif server_active:
                what = "Server running"
            elif connection_active:
                what = "Tunnel connection running"
            else:
                what = "Session running"
            title = QLabel(what)
            title.setObjectName("bannerTitle")
            hint = QLabel("Open it from the tabs above, or stop everything.")
            hint.setObjectName("fieldHint")
            row.addWidget(title)
            row.addWidget(hint)
            row.addStretch()
            stop = AppButton("Stop all sessions", "stop", "danger")
            stop.clicked.connect(window.stop_everything)
            row.addWidget(stop)
            self.root.addWidget(banner)

        tiles = QHBoxLayout()
        tiles.setSpacing(16)
        host = ActionTile(
            create_text,
            "Start a local Studio server. Share your tunnel address so friends can join.",
            "play" if server_active else "create",
            True,
        )
        join = ActionTile(
            join_text,
            "Open a UDP proxy on this PC and launch a Studio client through a tunnel address.",
            "join",
            False,
        )
        host.clicked.connect(lambda: window.navigate("create"))
        join.clicked.connect(lambda: window.navigate("join"))
        tiles.addWidget(host, 1)
        tiles.addWidget(join, 1)
        self.root.addLayout(tiles)

        configure = AppButton("Configure", "settings", "ghost")
        configure.clicked.connect(lambda: window.navigate("settings"))
        studio_ok = bool(window.studio_path)
        studio_text = Path(window.studio_path).name if studio_ok else "Studio path required."

        steps = QHBoxLayout()
        steps.setSpacing(20)
        steps.addWidget(
            Step(1, "Studio ready" if studio_ok else "Studio missing", studio_text,
                 "#2ee6a6" if studio_ok else "#f5b942", configure),
            1,
        )
        steps.addWidget(vline())
        steps.addWidget(
            Step(2, "Tunnel", f"Point your tunnel to port {PROXY_PORT} using the UDP protocol (proxy on 127.0.0.1)."),
            1,
        )
        steps.addWidget(vline())
        steps.addWidget(
            Step(3, "Share", "Send the hostname:port address to the players who will join."),
            1,
        )
        self.root.addWidget(card(steps, (22, 18, 22, 16)))

        history = window.settings.history
        week = stats_mod.compute(history)
        if week.sessions:
            self.root.addWidget(_stats_card(week))
        if history:
            box = QVBoxLayout()
            box.setSpacing(10)
            head = QHBoxLayout()
            head.addWidget(section_label("Recent sessions", "overview_recent"))
            head.addStretch(1)
            clear = AppButton("Clear", None, "ghost")
            clear.setToolTip("Delete the session history")
            clear.clicked.connect(window.clear_history)
            head.addWidget(clear)
            box.addLayout(head)
            for index, entry in enumerate(history[:OVERVIEW_HISTORY_ROWS]):
                if index:
                    box.addWidget(divider())
                box.addWidget(_history_row(entry))
            self.root.addWidget(card(box, (22, 14, 22, 14)))
        self.root.addStretch(1)
