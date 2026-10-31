from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QPushButton, QWidget

from app.widgets.brand import BrandMark
from app.widgets.buttons import IconButton
from app.widgets.icons import app_icon

HEADER_H = 56


class NavTab(QPushButton):
    def __init__(self, key: str, text: str, icon: str) -> None:
        super().__init__(text)
        self.key = key
        self.icon_name = icon
        self.default_text = text
        self.default_icon = icon
        self.setProperty("tab", True)
        self.setProperty("active", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(app_icon(icon, "#8ea2c7"))
        self.setIconSize(QSize(15, 15))
        self.setFixedHeight(HEADER_H)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        self.setIcon(app_icon(self.icon_name, "#f4f8ff" if active else "#8ea2c7"))
        self.style().unpolish(self)
        self.style().polish(self)

    def set_content(self, text: str, icon: str) -> None:
        self.icon_name = icon
        self.setText(text)
        self.setIcon(app_icon(icon, "#f4f8ff" if self.property("active") else "#8ea2c7"))

    def reset_content(self) -> None:
        self.set_content(self.default_text, self.default_icon)


class TopNav(QWidget):
    """Horizontal tab navigation living inside the header."""

    navigate = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._tabs: dict[str, NavTab] = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        for key, label, icon in (
            ("overview", "Overview", "home"),
            ("create", "Create", "create"),
            ("join", "Join", "join"),
            ("settings", "Settings", "settings"),
            ("support", "Support", "globe"),
        ):
            tab = NavTab(key, label, icon)
            tab.clicked.connect(lambda checked=False, k=key: self.navigate.emit(k))
            self._tabs[key] = tab
            layout.addWidget(tab)

    def set_current(self, key: str) -> None:
        for nav_key, tab in self._tabs.items():
            tab.set_active(nav_key == key)

    def set_session(
        self,
        active: bool,
        text: str = "No session",
        mode: str | None = None,
        active_modes: set[str] | None = None,
    ) -> None:
        self._tabs["create"].reset_content()
        self._tabs["join"].reset_content()
        modes = active_modes or ({mode} if mode else set())
        if active and "create" in modes:
            self._tabs["create"].set_content("Server", "play")
        if active and "join" in modes:
            self._tabs["join"].set_content("Connection", "join")


class TitleBar(QWidget):
    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("titleBar")
        self.setFixedHeight(HEADER_H)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 10, 0)
        layout.setSpacing(0)

        layout.addWidget(BrandMark(40))
        layout.addSpacing(14)
        rule = QFrame()
        rule.setObjectName("vline")
        rule.setFixedHeight(26)
        layout.addWidget(rule)
        layout.addSpacing(10)

        self.nav = TopNav()
        layout.addWidget(self.nav)
        layout.addStretch()

        self.min_button = IconButton("minimize", "Minimize")
        self.max_button = IconButton("square", "Maximize")
        self.close_button = IconButton("close", "Close", "chromeDanger")
        for button in (self.min_button, self.max_button, self.close_button):
            layout.addWidget(button)
            layout.addSpacing(4)

        self.min_button.clicked.connect(self.minimize_requested)
        self.max_button.clicked.connect(self.maximize_requested)
        self.close_button.clicked.connect(self.close_requested)

    def is_control_at(self, global_pos) -> bool:
        widget = self.childAt(self.mapFromGlobal(global_pos))
        return isinstance(widget, QAbstractButton)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self.is_control_at(event.globalPosition().toPoint()):
            self.maximize_requested.emit()
        super().mouseDoubleClickEvent(event)
