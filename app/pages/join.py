from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from app.core import protocol
from app.pages.base import Page, Step, card, section_label, vline
from app.widgets.buttons import AppButton, IconButton
from app.widgets.fields import FormField
from app.widgets.icons import app_icon
from app.widgets.status import StatusDot


def validate_tunnel(value: str) -> str | None:
    if ":" not in value:
        return "Format must be host:port"
    host, port = value.rsplit(":", 1)
    if not host:
        return "Missing host"
    if not port.isdigit():
        return "Port must be numeric"
    return None


class RecentRow(QFrame):
    """One history entry. A styled frame (not a button) so hover paints cleanly."""

    picked = Signal(str)
    removed = Signal(str)

    def __init__(self, tunnel: str) -> None:
        super().__init__()
        self.tunnel = tunnel
        self.setObjectName("recentRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip("Click to use this address")

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 4, 6, 4)
        row.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(app_icon("clock", "#5d7099").pixmap(14, 14))
        text = QLabel(tunnel)
        text.setObjectName("recentText")
        remove = IconButton("close", "Remove from history", "inline")
        remove.clicked.connect(lambda: self.removed.emit(self.tunnel))
        row.addWidget(icon)
        row.addWidget(text, 1)
        row.addWidget(remove)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.picked.emit(self.tunnel)
        super().mousePressEvent(event)


class RecentTunnels(QFrame):
    """Card listing the last tunnels used. Hides itself when the history is empty."""

    picked = Signal(str)
    removed = Signal(str)
    cleared = Signal()

    def __init__(self, items: list[str]) -> None:
        super().__init__()
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 14, 20, 12)
        outer.setSpacing(6)

        head = QHBoxLayout()
        head.addWidget(section_label("Recent tunnels", "join_recent"))
        head.addStretch()
        clear = AppButton("Clear all", None, "ghost")
        clear.setMinimumHeight(26)
        clear.clicked.connect(self.cleared.emit)
        head.addWidget(clear)
        outer.addLayout(head)

        self.rows = QVBoxLayout()
        self.rows.setSpacing(2)
        outer.addLayout(self.rows)
        self.set_items(items)

    def set_items(self, items: list[str]) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for tunnel in items:
            row = RecentRow(tunnel)
            row.picked.connect(self.picked.emit)
            # defer: the row is destroyed while its own button is still handling the click
            row.removed.connect(lambda value: QTimer.singleShot(0, lambda: self.removed.emit(value)))
            self.rows.addWidget(row)
        self.setVisible(bool(items))


class JoinPage(Page):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        actions = QHBoxLayout()
        back = AppButton("Back", "back", "ghost")
        back.clicked.connect(lambda: window.navigate("overview"))
        actions.addWidget(back)
        self.add_header(
            "Join tunnel",
            "Open a UDP proxy locally and launch a Studio client through the tunnel address.",
            actions,
            eyebrow="Connect",
        )

        join = AppButton("Join tunnel", "next", "primary")
        join.setMinimumHeight(42)
        join.clicked.connect(self._join)
        self.join_button = join
        self.tunnel = FormField(
            "Tunnel address",
            window.settings.join_tunnel,
            "Format host:port, e.g. therefore-protocol.tunnel.gg:2842.",
            placeholder="therefore-protocol.tunnel.gg:2842",
            icon="globe",
            validator=validate_tunnel,
            stacked=True,
            action=join,
        )
        self.tunnel.edit.returnPressed.connect(self._join)
        self.tunnel.edit.textChanged.connect(self._maybe_link)  # pasting an rsg://join/... link fills in host:port
        bar = QVBoxLayout()
        bar.addWidget(self.tunnel)

        check_row = QHBoxLayout()
        check_row.setSpacing(8)
        self.check_dot = StatusDot("#5d7099", 7)
        self.check_label = QLabel("")
        self.check_label.setObjectName("checkInfo")
        check_row.addWidget(self.check_dot)
        check_row.addWidget(self.check_label)
        check_row.addStretch()
        self.check_box = QFrame()
        self.check_box.setLayout(check_row)
        self.check_box.setVisible(False)
        bar.addWidget(self.check_box)
        self.root.addWidget(card(bar, (26, 22, 26, 18)))

        self.recent = RecentTunnels(window.settings.recent_tunnels)
        self.recent.picked.connect(self._use_recent)
        self.recent.removed.connect(self._forget_recent)
        self.recent.cleared.connect(self._clear_recent)
        self.root.addWidget(self.recent)

        steps = QHBoxLayout()
        steps.setSpacing(20)
        steps.addWidget(Step(1, "Proxy", "A local UDP proxy opens and forwards traffic to the host."), 1)
        steps.addWidget(vline())
        steps.addWidget(Step(2, "Client", "Studio launches as a client pointed at that proxy."), 1)
        steps.addWidget(vline())
        steps.addWidget(Step(3, "Console", "Incoming packets stream live in the connection console."), 1)
        self.root.addWidget(card(steps, (22, 18, 22, 16)))
        self.root.addStretch(1)

    def set_checking(self, checking: bool) -> None:
        """Lock the form while the tunnel is being tested."""
        self.join_button.setEnabled(not checking)
        self.join_button.setText("Checking..." if checking else "Join tunnel")
        self.tunnel.edit.setReadOnly(checking)
        if checking:
            self.show_check("Checking tunnel...", "info")

    def show_check(self, text: str, tone: str) -> None:
        colors = {"info": "#5d7099", "ok": "#2ee6a6", "warn": "#f5b942", "err": "#ff5d73"}
        names = {"info": "checkInfo", "ok": "checkOk", "warn": "checkWarn", "err": "checkErr"}
        self.check_dot.set_color(colors[tone])
        self.check_label.setObjectName(names[tone])
        self.check_label.style().unpolish(self.check_label)
        self.check_label.style().polish(self.check_label)
        self.check_label.setText(text)
        self.check_box.setVisible(True)

    def _maybe_link(self, text: str) -> None:
        tunnel = protocol.parse_link(text)
        if tunnel and tunnel != text:
            self.tunnel.edit.setText(tunnel)

    def _join(self) -> None:
        if not self.tunnel.validate() or not self.tunnel.value():
            self.window.toast("Fix the tunnel address.", "error")
            return
        host, port = self.tunnel.value().rsplit(":", 1)
        self.window.join_session(host, int(port), self.tunnel.value())

    def _use_recent(self, tunnel: str) -> None:
        self.tunnel.edit.setText(tunnel)
        self.tunnel.edit.setFocus()

    def _forget_recent(self, tunnel: str) -> None:
        self.window.forget_recent_tunnel(tunnel)
        self.recent.set_items(self.window.settings.recent_tunnels)

    def _clear_recent(self) -> None:
        self.window.clear_recent_tunnels()
        self.recent.set_items([])
