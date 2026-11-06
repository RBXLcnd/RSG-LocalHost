from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QSize, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel

from app.core import motion
from app.styles.palette import pal


class StatusDot(QLabel):
    def __init__(self, color: str = "#5d7099", size: int = 8) -> None:
        super().__init__()
        self._size = size
        self._pulsing = False
        self._pulse: QVariantAnimation | None = None
        self._effect: QGraphicsOpacityEffect | None = None
        self.setFixedSize(QSize(size, size))
        self.set_color(color)

    def set_color(self, color: str) -> None:
        radius = self._size // 2
        self.setStyleSheet(
            f"background: {pal(color)}; border-radius: {radius}px; min-width: {self._size}px; min-height: {self._size}px;"
        )

    def set_pulsing(self, pulsing: bool) -> None:
        """A slow fade in and out, to show something is live. Off when animations are off."""
        self._pulsing = pulsing
        self._sync_pulse()

    def _sync_pulse(self) -> None:
        want = self._pulsing and motion.enabled() and self.isVisible()
        if want and self._pulse is None:
            self._effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self._effect)
            anim = QVariantAnimation(self)
            anim.setStartValue(1.0)
            anim.setKeyValueAt(0.5, 0.3)
            anim.setEndValue(1.0)
            anim.setDuration(1800)
            anim.setLoopCount(-1)
            anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            anim.valueChanged.connect(lambda v: self._effect.setOpacity(float(v)))
            anim.start()
            self._pulse = anim
        elif not want and self._pulse is not None:
            self._pulse.stop()
            self._pulse.deleteLater()
            self._pulse = None
            self.setGraphicsEffect(None)
            self._effect = None

    # pause while hidden: no needless repaints
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_pulse()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._sync_pulse()
