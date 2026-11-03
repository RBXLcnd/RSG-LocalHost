"""Settings > Appearance: a grid of clickable previews, one per background theme."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget

from app.core.i18n import tr
from app.widgets import backgrounds

THUMB_W, THUMB_H = 480, 300
_thumbs: dict[str, QPixmap] = {}


def _thumb(key: str) -> QPixmap:
    """The theme rendered once at a fixed size, with two card shapes so it reads like the real window."""
    if key not in _thumbs:
        pm = QPixmap(THUMB_W, THUMB_H)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        backgrounds.THEMES[key][1](p, THUMB_W, THUMB_H)
        p.setPen(QPen(QColor(31, 91, 255, 120), 1.2))
        p.setBrush(QColor(8, 16, 40, 190))
        p.drawRoundedRect(QRectF(48, 96, 180, 96), 10, 10)
        p.drawRoundedRect(QRectF(244, 96, 188, 96), 10, 10)
        p.drawRoundedRect(QRectF(48, 206, 384, 56), 10, 10)
        p.end()
        _thumbs[key] = pm
    return _thumbs[key]


class _Tile(QWidget):
    clicked = Signal(str)

    def __init__(self, key: str, label: str) -> None:
        super().__init__()
        self.key = key
        self.label = label
        self.selected = False
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(112)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip(f"{label} background")

    def enterEvent(self, _e) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, _e) -> None:
        self._hover = False
        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)
        clip = QPainterPath()
        clip.addRoundedRect(r, 10, 10)
        p.setClipPath(clip)
        pm = _thumb(self.key)
        # "cover": fill the tile, crop the overflow
        scale = max(r.width() / pm.width(), r.height() / pm.height())
        tw, th = pm.width() * scale, pm.height() * scale
        p.drawPixmap(QRectF(r.center().x() - tw / 2, r.center().y() - th / 2, tw, th), pm, QRectF(pm.rect()))
        strip = QLinearGradient(0, r.bottom() - 36, 0, r.bottom())
        strip.setColorAt(0, QColor(3, 6, 13, 0))
        strip.setColorAt(1, QColor(3, 6, 13, 235))
        p.fillRect(QRectF(r.left(), r.bottom() - 36, r.width(), 36), strip)
        p.setClipping(False)

        font = QFont(self.font())
        font.setPointSizeF(9.5)
        font.setBold(self.selected)
        p.setFont(font)
        p.setPen(QColor("#ffffff") if self.selected else QColor("#c5d2ee"))
        p.drawText(QRectF(r.left() + 12, r.bottom() - 28, r.width() - 40, 22),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, tr(self.label))

        if self.selected:
            p.setPen(QPen(QColor("#00b2ff"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, 10, 10)
            p.setBrush(QColor("#00b2ff"))
            p.setPen(Qt.PenStyle.NoPen)
            cx, cy = r.right() - 16, r.bottom() - 17
            p.drawEllipse(QRectF(cx - 8, cy - 8, 16, 16))
            p.setPen(QPen(QColor("#03060d"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline([QPointF(cx - 4, cy), QPointF(cx - 1, cy + 3), QPointF(cx + 4, cy - 3)])
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(110, 160, 255, 150 if self._hover else 55), 1.2))
            p.drawRoundedRect(r, 10, 10)


class ThemePicker(QWidget):
    theme_selected = Signal(str)

    COLUMNS = 3

    def __init__(self, current: str) -> None:
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        self._tiles: dict[str, _Tile] = {}
        for i, (key, (label, _fn)) in enumerate(backgrounds.THEMES.items()):
            tile = _Tile(key, label)
            tile.clicked.connect(self._on_clicked)
            grid.addWidget(tile, i // self.COLUMNS, i % self.COLUMNS)
            self._tiles[key] = tile
        for c in range(self.COLUMNS):
            grid.setColumnStretch(c, 1)
        self.set_current(current)

    def set_current(self, key: str) -> None:
        if key not in self._tiles:
            key = backgrounds.DEFAULT_THEME
        for k, tile in self._tiles.items():
            tile.selected = k == key
            tile.update()

    def _on_clicked(self, key: str) -> None:
        self.set_current(key)
        self.theme_selected.emit(key)
