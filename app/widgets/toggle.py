from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton


class ToggleSwitch(QAbstractButton):
    """Small on/off switch. Emits the standard `toggled(bool)`."""

    def __init__(self, checked: bool = False) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(QSize(44, 24))
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def sizeHint(self) -> QSize:
        return QSize(44, 24)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        off, on = QColor("#0c1a38"), QColor("#0a8fe0")
        mix = self._offset
        fill = QColor(
            int(off.red() + (on.red() - off.red()) * mix),
            int(off.green() + (on.green() - off.green()) * mix),
            int(off.blue() + (on.blue() - off.blue()) * mix),
        )
        border = QColor("#4db8ff") if self.isChecked() else QColor("#1a3f85")
        if self.hasFocus():
            border = QColor("#8fd4ff")
        painter.setPen(QPen(border, 1.2))
        painter.setBrush(fill)
        painter.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        diameter = track.height() - 6
        x = track.left() + 3 + (track.width() - diameter - 6) * self._offset
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff") if self.isChecked() else QColor("#5d7099"))
        painter.drawEllipse(QRectF(x, track.top() + 3, diameter, diameter))
