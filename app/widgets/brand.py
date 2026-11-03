"""RSG brand visuals: ring mark and glow background, painted in code."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget

from PySide6.QtGui import QColor as QtGuiColor
from app.styles import palette
from app.styles.palette import qcolor as QColor

from app.widgets import backgrounds


LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
_logo_cache: QPixmap | None = None


def logo_pixmap() -> QPixmap:
    """The official RSG logo (assets/logo.png), loaded once."""
    global _logo_cache
    if _logo_cache is None:
        _logo_cache = QPixmap(str(LOGO_PATH))
    return _logo_cache


# Angular RSG lettering, drawn as centre-lines on a 50-unit-high grid.
# Each letter is 50 units wide; stroke width is applied when painting.
_LETTERS = {
    "R": [
        [(6, 50), (6, 5.5), (38, 5.5), (46, 12), (46, 19), (38, 25.5), (6, 25.5)],
        [(24, 25.5), (46, 50)],
    ],
    "S": [
        [(48, 5.5), (12, 5.5), (4, 12), (4, 19), (12, 25), (38, 25),
         (46, 31), (46, 38), (38, 44.5), (2, 44.5)],
    ],
    "G": [
        [(48, 5.5), (12, 5.5), (4, 12), (4, 38), (12, 44.5), (38, 44.5),
         (46, 38), (46, 26), (26, 26)],
    ],
}
_WORD_W = 50 * 3 + 6 * 2  # three letters + two gaps
_WORD_H = 50
WORD_ASPECT = _WORD_W / _WORD_H


def _letter_path(name: str, dx: float) -> QPainterPath:
    path = QPainterPath()
    for line in _LETTERS[name]:
        path.moveTo(line[0][0] + dx, line[0][1])
        for x, y in line[1:]:
            path.lineTo(x + dx, y)
    return path


class BrandMark(QWidget):
    """RSG logo: glowing split ring with the angular RSG wordmark (blue S).

    `size` is the ring diameter (= widget height). The widget is wider than
    tall so the wordmark can extend past the open sides of the ring, like the
    original logo.
    """

    def __init__(self, size: int = 34) -> None:
        super().__init__()
        self.setFixedSize(int(size * 1.5), size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _event) -> None:
        pm = logo_pixmap()
        if pm.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dpr = self.devicePixelRatioF()
        w, h = self.width(), self.height()
        if palette.is_light():  # the logo is made for dark surfaces: give it a dark plate
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QtGuiColor("#0a1630"))
            p.drawRoundedRect(QRectF(0, 3, w, h - 6), 9, 9)
        scaled = pm.scaled(
            int(w * dpr), int(h * dpr),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(dpr)
        x = (w - scaled.width() / dpr) / 2
        y = (h - scaled.height() / dpr) / 2
        p.drawPixmap(QPointF(x, y), scaled)


_theme = "classic"


def set_theme(key: str) -> None:
    """Choose the window background (a key of backgrounds.THEMES; unknown -> classic)."""
    global _theme
    _theme = key if key in backgrounds.THEMES else backgrounds.DEFAULT_THEME


def get_theme() -> str:
    return _theme


class GlowBackground(QWidget):
    """Window background, painted by the theme chosen in Settings > Appearance."""

    radius = 0  # >0: clip to a rounded rect and draw a neon border (splash)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if self.radius:
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), self.radius, self.radius)
            p.setClipPath(clip)
        backgrounds.THEMES[_theme][1](p, w, h)

        if self.radius:
            p.setClipping(False)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#1f5bff"), 1.2))
            p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), self.radius, self.radius)


def make_app_icon(active: bool = False) -> QIcon:
    """Tray / window icon built from the RSG logo.
    `active` adds a green badge (a session is running)."""
    icon = QIcon()
    src = logo_pixmap()
    for size in (16, 24, 32, 48, 64, 128):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if not src.isNull():
            scaled = src.scaled(
                size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            p.drawPixmap((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)
        if active:
            u = size / 64.0
            p.setPen(QPen(QColor("#03060d"), 3 * u))
            p.setBrush(QColor("#2ee6a6"))
            p.drawEllipse(QRectF(40 * u, 40 * u, 21 * u, 21 * u))
        p.end()
        icon.addPixmap(pm)
    return icon
