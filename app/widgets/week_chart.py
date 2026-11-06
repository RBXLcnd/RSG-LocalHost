"""Tiny bar chart: hosted time for each of the last days."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QLinearGradient, QPainter
from app.styles.palette import qcolor as QColor
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.core import motion
from app.core.i18n import tr
from app.core.uptime import format_uptime

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class WeekChart(QWidget):
    def __init__(self, days: list[tuple[date, int]]) -> None:
        super().__init__()
        self.days = days
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setToolTip("")
        self._grow = 0.0
        motion.tween(self, 0.0, 1.0, 900, self._set_grow)

    def _set_grow(self, value: float) -> None:
        self._grow = value
        self.update()

    def _bar_progress(self, index: int) -> float:
        """Bars rise one after the other: each one starts a little later than the one before."""
        if self._grow >= 1.0:
            return 1.0
        count = max(1, len(self.days))
        start = 0.45 * index / count
        return max(0.0, min(1.0, (self._grow - start) / (1.0 - 0.45 + 0.45 / count)))

    def _slot(self, x: float) -> int:
        return max(0, min(len(self.days) - 1, int(x / max(1, self.width()) * len(self.days))))

    def mouseMoveEvent(self, event) -> None:
        if self.days:
            day, seconds = self.days[self._slot(event.position().x())]
            self.setToolTip(f"{tr(WEEKDAYS[day.weekday()])} {day.day:02d}/{day.month:02d}  ·  {format_uptime(seconds) if seconds else '0s'}")
        super().mouseMoveEvent(event)

    def paintEvent(self, _event) -> None:
        if not self.days:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        label_h = 20
        chart_h = h - label_h - 6
        top = max(seconds for _, seconds in self.days) or 1
        slot = w / len(self.days)
        bar_w = min(38.0, slot * 0.5)
        font = QFont(self.font())
        font.setPointSizeF(8)
        p.setFont(font)
        for i, (day, seconds) in enumerate(self.days):
            cx = slot * i + slot / 2
            height = chart_h * seconds / top * self._bar_progress(i) if seconds else 0
            track = QRectF(cx - bar_w / 2, 4, bar_w, chart_h)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 40, 84, 140))
            p.drawRoundedRect(track, 5, 5)
            if seconds:
                height = max(height, 6 * self._bar_progress(i))
                bar = QRectF(cx - bar_w / 2, 4 + chart_h - height, bar_w, height)
                grad = QLinearGradient(bar.topLeft(), bar.bottomLeft())
                grad.setColorAt(0, QColor("#00b2ff"))
                grad.setColorAt(1, QColor("#1f5bff"))
                p.setBrush(grad)
                p.drawRoundedRect(bar, 5, 5)
            p.setPen(QColor("#8ea2c7") if i < len(self.days) - 1 else QColor("#f4f8ff"))
            p.drawText(QRectF(cx - slot / 2, h - label_h, slot, label_h), Qt.AlignmentFlag.AlignCenter, tr(WEEKDAYS[day.weekday()]))
        p.end()
