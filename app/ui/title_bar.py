from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QPushButton, QWidget

from app.core import i18n, motion
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

    def restyle(self) -> None:
        self.setIcon(app_icon(self.icon_name, "#f4f8ff" if self.property("active") else "#8ea2c7"))

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
        self._current: str | None = None
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
            tab.installEventFilter(self)
            layout.addWidget(tab)

        # The accent line under the current tab: one widget that slides from tab to tab.
        self._indicator = QFrame(self)
        self._indicator.setObjectName("navIndicator")
        self._indicator.hide()
        self._slide: QPropertyAnimation | None = None

    def _target_rect(self) -> QRect | None:
        tab = self._tabs.get(self._current or "")
        if tab is None or tab.width() <= 0:
            return None
        return QRect(tab.x(), tab.y() + tab.height() - 2, tab.width(), 2)

    def _place_indicator(self, animate: bool) -> None:
        rect = self._target_rect()
        if rect is None:
            self._indicator.hide()
            return
        if self._slide is not None:
            self._slide.stop()
            self._slide = None
        first = not self._indicator.isVisible()
        if animate and not first and motion.enabled() and self._indicator.geometry() != rect:
            anim = QPropertyAnimation(self._indicator, b"geometry", self)
            anim.setStartValue(self._indicator.geometry())
            anim.setEndValue(rect)
            anim.setDuration(280)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            self._slide = anim
        else:
            self._indicator.setGeometry(rect)
        self._indicator.show()
        self._indicator.raise_()

    def eventFilter(self, obj, event) -> bool:
        # a tab changed size or moved (language, compact mode, "Server" label): keep the line under it
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move) and obj is self._tabs.get(self._current or ""):
            sliding = self._slide is not None and self._slide.state() == QPropertyAnimation.State.Running
            rect = self._target_rect()
            if sliding and rect is not None:
                self._slide.setEndValue(rect)  # the tab got bold/wider while we slide: aim at its new size
            else:
                self._place_indicator(animate=False)
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place_indicator(animate=False)

    def set_compact(self, compact: bool) -> None:
        if bool(self._tabs["overview"].property("compact")) == compact:
            return
        for tab in self._tabs.values():
            tab.setProperty("compact", compact)
            tab.setIconSize(QSize(0, 0) if compact else QSize(15, 15))
            tab.style().unpolish(tab)
            tab.style().polish(tab)
            tab.updateGeometry()

    def full_width(self) -> int:
        """Width the tabs need with their normal padding and icons."""
        was = bool(self._tabs["overview"].property("compact"))
        self.set_compact(False)
        width = sum(t.sizeHint().width() for t in self._tabs.values()) + 2 * (len(self._tabs) - 1)
        self.set_compact(was)
        return width

    def set_current(self, key: str) -> None:
        for nav_key, tab in self._tabs.items():
            tab.set_active(nav_key == key)
        self._current = key
        self._place_indicator(animate=True)

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
    def restyle(self) -> None:
        """Icons are painted pixmaps: redo them after a mode / accent change."""
        for tab in self.findChildren(NavTab):
            tab.restyle()
        for button in self.findChildren(IconButton):
            button.restyle()
        self.lang_button.setIcon(app_icon("globe", "#8ea2c7"))
        for mark in self.findChildren(BrandMark):
            mark.update()


    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()
    language_requested = Signal()
    update_requested = Signal()

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

        self.update_button = QPushButton()
        self.update_button.setObjectName("updateButton")
        self.update_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_button.setFixedHeight(28)
        self.update_button.setToolTip("A new version is available. Click to open the download page.")
        self.update_button.clicked.connect(self.update_requested)
        self.update_button.hide()
        layout.addWidget(self.update_button)
        layout.addSpacing(8)

        self.lang_button = QPushButton("PT")
        self.lang_button.setObjectName("langButton")
        self.lang_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_button.setIcon(app_icon("globe", "#8ea2c7"))
        self.lang_button.setIconSize(QSize(14, 14))
        self.lang_button.setFixedSize(58, 28)
        self.lang_button.clicked.connect(self.language_requested)
        layout.addWidget(self.lang_button)
        layout.addSpacing(10)

        self.min_button = IconButton("minimize", "Minimize")
        self.max_button = IconButton("square", "Maximize")
        self.close_button = IconButton("close", "Close", "chromeDanger")
        for button in (self.min_button, self.max_button, self.close_button):
            layout.addWidget(button)
            layout.addSpacing(4)

        self.min_button.clicked.connect(self.minimize_requested)
        self.max_button.clicked.connect(self.maximize_requested)
        self.close_button.clicked.connect(self.close_requested)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_nav()

    def _fit_nav(self) -> None:
        # Space left for the tabs = whole bar minus everything that is not the nav.
        other = 18 + 10 + 40 + 14 + 1 + 10 + 8 + 58 + 10 + 3 * (30 + 4) + 12
        if not self.update_button.isHidden():
            other += self.update_button.sizeHint().width()
        self.nav.set_compact(self.nav.full_width() + other > self.width())

    def set_update(self, version: str) -> None:
        """Show the "Update vX" pill (empty version hides it)."""
        if version:
            self.update_button.setText(f"Update v{version}")
            self.update_button.show()
        else:
            self.update_button.hide()
        QTimer.singleShot(0, self._fit_nav)

    def set_language(self, lang: str) -> None:
        """The button shows the current language; clicking it opens the list (names are never translated)."""
        self.lang_button.setText(i18n.SHORT.get(lang, "EN"))
        self.lang_button.setToolTip(i18n.LANGUAGES.get(lang, "English"))
        QTimer.singleShot(50, self._fit_nav)

    def is_control_at(self, global_pos) -> bool:
        widget = self.childAt(self.mapFromGlobal(global_pos))
        return isinstance(widget, QAbstractButton)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self.is_control_at(event.globalPosition().toPoint()):
            self.maximize_requested.emit()
        super().mouseDoubleClickEvent(event)
