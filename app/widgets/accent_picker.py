"""Settings > Appearance: dark / light switch and accent colour swatches."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QColorDialog, QHBoxLayout, QWidget

from app.styles import palette
from app.widgets.buttons import AppButton


class Swatch(QAbstractButton):
    def __init__(self, color: str, tooltip: str) -> None:
        super().__init__()
        self.color = color
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.color))
        p.drawEllipse(rect)
        if self.isChecked():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#ffffff") if not palette.is_light() else QColor("#0d1b3a"), 2))
            p.drawEllipse(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5))


class AppearancePicker(QWidget):
    mode_selected = Signal(str)
    accent_selected = Signal(str)

    def __init__(self, mode: str, accent: str) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_buttons: dict[str, AppButton] = {}
        for key, label in (("dark", "Dark"), ("light", "Light")):
            button = AppButton(label, None, "secondary")
            button.setCheckable(True)
            button.setChecked(key == mode)
            button.clicked.connect(lambda _=False, k=key: self.mode_selected.emit(k))
            self.mode_group.addButton(button)
            self.mode_buttons[key] = button
            row.addWidget(button)
        row.addSpacing(18)

        self.swatch_group = QButtonGroup(self)
        self.swatch_group.setExclusive(True)
        self.swatches: list[Swatch] = []
        for name, color in palette.ACCENTS.items():
            swatch = Swatch(color, name.capitalize())
            swatch.clicked.connect(lambda _=False, c=color: self.accent_selected.emit(c))
            self.swatch_group.addButton(swatch)
            self.swatches.append(swatch)
            row.addWidget(swatch)
        self.custom = AppButton("Custom", None, "ghost")
        self.custom.clicked.connect(self._pick_custom)
        row.addWidget(self.custom)
        row.addStretch(1)
        self.set_accent(accent)

    def set_accent(self, accent: str) -> None:
        for swatch in self.swatches:
            swatch.setChecked(swatch.color.lower() == accent.lower())
            swatch.update()

    def _pick_custom(self) -> None:
        chosen = QColorDialog.getColor(QColor(palette.accent()), self)
        if chosen.isValid():
            self.accent_selected.emit(chosen.name())
