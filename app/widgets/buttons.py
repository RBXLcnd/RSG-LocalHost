from __future__ import annotations

from PySide6.QtCore import QSize, QTimer
from PySide6.QtWidgets import QPushButton, QToolTip

from app.widgets.effects import animate_glow, apply_glow
from app.widgets.icons import app_icon


class AppButton(QPushButton):
    def __init__(self, text: str, icon: str | None = None, variant: str = "secondary") -> None:
        super().__init__(text)
        self.setProperty("variant", variant)
        self.setCursor(QtCursor.pointing_hand())
        self.setMinimumHeight(36)
        self._glow = None
        if variant == "primary":
            self._glow = apply_glow(self, "#00b2ff", blur=30, alpha=210)
        if icon:
            color = {
                "primary": "#ffffff",
                "danger": "#ff5d73",
                "ghost": "#8ea2c7",
            }.get(variant, "#f4f8ff")
            self.setIcon(app_icon(icon, color))
            self.setIconSize(QSize(15, 15))

    def enterEvent(self, event) -> None:
        if self._glow is not None:
            animate_glow(self._glow, 42, 255)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._glow is not None:
            animate_glow(self._glow, 30, 210)
        super().leaveEvent(event)


class IconButton(QPushButton):
    def __init__(self, icon: str, tooltip: str, variant: str = "chrome") -> None:
        super().__init__()
        self.setProperty("variant", variant)
        self.setCursor(QtCursor.pointing_hand())
        self.setIcon(app_icon(icon, "#f4f8ff" if variant == "chromeDanger" else "#8ea2c7"))
        self.setIconSize(QSize(13, 13))
        self.setToolTip(tooltip)
        self.setFixedSize(28 if variant == "inline" else 32, 28 if variant == "inline" else 32)


class QtCursor:
    @staticmethod
    def pointing_hand():
        from PySide6.QtCore import Qt

        return Qt.CursorShape.PointingHandCursor


COPIED_MS = 1600
COPIED_GREEN = "#2ee6a6"


def flash_copied(button: QPushButton, label: str = "Copied") -> None:
    """Confirm a copy right on the button: green check (and text, if it has any) for a moment.

    Calling it again while it is showing just extends the moment."""
    state = getattr(button, "_copy_flash", None)
    if state is None:
        timer = QTimer(button)
        timer.setSingleShot(True)
        state = {"timer": timer, "active": False, "text": "", "icon": None, "min_w": 0}
        timer.timeout.connect(lambda: _restore_copy(button))
        button._copy_flash = state  # type: ignore[attr-defined]

    if not state["active"]:
        state.update(active=True, text=button.text(), icon=button.icon(), min_w=button.minimumWidth())
        # keep the width so the neighbouring buttons don't jump when the text gets shorter
        button.setMinimumWidth(button.width())
        button.setProperty("copied", True)
        button.setIcon(app_icon("check", COPIED_GREEN))
        if state["text"]:
            button.setText(label)
        else:
            QToolTip.showText(button.mapToGlobal(button.rect().bottomLeft()), label, button, button.rect(), COPIED_MS)
        _repolish(button)
    state["timer"].start(COPIED_MS)


def _restore_copy(button: QPushButton) -> None:
    state = button._copy_flash  # type: ignore[attr-defined]
    state["active"] = False
    button.setProperty("copied", False)
    button.setIcon(state["icon"])
    if state["text"]:
        button.setText(state["text"])
    button.setMinimumWidth(state["min_w"])
    _repolish(button)


def _repolish(widget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
