from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

from app.widgets.icons import app_icon


class DropOverlay(QWidget):
    """Full-window hint shown while a file is dragged over the app.

    Blue = a valid map is being dragged, red = the file can't be used."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._valid = True
        self._title = ""
        self._subtitle = ""
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        # one reusable animation; retargeted on every fade
        self._anim = QPropertyAnimation(self._opacity, b"opacity", self)
        self._anim.setDuration(130)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._on_fade_finished)
        self.hide()

    def present(self, valid: bool, name: str = "") -> None:
        """Idempotent: safe to call on every drag-move event."""
        title = "Drop to load this map" if valid else "Can't use this file"
        subtitle = name if valid else "Only .rbxl and .rbxlx maps are supported"
        if (valid, title, subtitle) != (self._valid, self._title, self._subtitle):
            self._valid, self._title, self._subtitle = valid, title, subtitle
            self.update()
        if not self.isVisible():
            self.setGeometry(self.parentWidget().rect())
            self.raise_()
            self.show()
        if self._opacity.opacity() < 1.0 and not self._fading_to(1.0):
            self._fade(1.0)

    def dismiss(self) -> None:
        if self.isVisible() and not self._fading_to(0.0):
            self._fade(0.0)

    def _fading_to(self, end: float) -> bool:
        return self._anim.state() == QPropertyAnimation.State.Running and self._anim.endValue() == end

    def _fade(self, end: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._opacity.opacity())
        self._anim.setEndValue(end)
        self._anim.start()

    def _on_fade_finished(self) -> None:
        if self._opacity.opacity() <= 0.0:
            self.hide()

    def paintEvent(self, event) -> None:
        accent = QColor("#1e9bff" if self._valid else "#ff5d73")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(3, 6, 13, 214))

        frame = QRectF(self.rect()).adjusted(18, 18, -18, -18)
        fill = QColor(accent)
        fill.setAlpha(22)
        pen = QPen(accent, 2, Qt.PenStyle.DashLine)
        pen.setDashPattern([5, 4])
        painter.setPen(pen)
        painter.setBrush(fill)
        painter.drawRoundedRect(frame, 16, 16)

        center = frame.center()
        icon = app_icon("folder", accent.name(), 92).pixmap(46, 46)
        painter.drawPixmap(int(center.x() - 23), int(center.y() - 64), icon)

        title_font = QFont(self.font())
        title_font.setPointSizeF(17)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#f4f8ff"))
        painter.drawText(
            QRectF(frame.left(), center.y() - 6, frame.width(), 34),
            Qt.AlignmentFlag.AlignCenter,
            self._title,
        )

        sub_font = QFont(self.font())
        sub_font.setPointSizeF(10.5)
        painter.setFont(sub_font)
        painter.setPen(QColor("#8ea2c7"))
        painter.drawText(
            QRectF(frame.left() + 20, center.y() + 30, frame.width() - 40, 28),
            Qt.AlignmentFlag.AlignCenter,
            self._subtitle,
        )
