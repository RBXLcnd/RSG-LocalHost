from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel

from app.widgets.status import StatusDot


class Toast(QFrame):
    COLORS = {
        "info": "#f4f8ff",
        "success": "#2ee6a6",
        "warning": "#f5b942",
        "error": "#ff5d73",
    }

    def __init__(self, text: str, tone: str = "info", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 14, 8)
        layout.setSpacing(8)
        layout.addWidget(StatusDot(self.COLORS.get(tone, self.COLORS["info"]), 7))
        label = QLabel(text)
        label.setObjectName("toastLabel")
        layout.addWidget(label)

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._anim: QPropertyAnimation | None = None
        self._dismiss_started = False

    def show_animated(self, duration: int = 2800) -> None:
        self.show()
        self._fade(0.0, 1.0, 170)
        QTimer.singleShot(duration, self.dismiss)

    def dismiss(self) -> None:
        if self._dismiss_started:
            return
        self._dismiss_started = True
        anim = self._fade(1.0, 0.0, 200)
        anim.finished.connect(self._finish_dismiss)

    def _finish_dismiss(self) -> None:
        self.hide()
        self.deleteLater()

    def _fade(self, start: float, end: float, duration: int) -> QPropertyAnimation:
        anim = QPropertyAnimation(self._opacity, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim = anim  # keep a reference so it isn't collected mid-flight
        anim.start()
        return anim
