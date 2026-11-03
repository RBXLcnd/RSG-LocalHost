"""Background themes for the app window. Each theme is a function painting onto a QPainter.

Pick one in Settings > Appearance. `THEMES` keeps the display order. Everything is drawn with
gradients and simple shapes (no image files), so it scales to any window size.
"""
from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QConicalGradient, QImage, QLinearGradient, QPen, QPixmap, QPolygonF, QRadialGradient

from app.styles.palette import qcolor as QColor

_grain = None


def _glow(p, cx, cy, r, c, a, a2=0):
    g = QRadialGradient(QPointF(cx, cy), r)
    col = QColor(c); col.setAlpha(a); g.setColorAt(0, col)
    col2 = QColor(c); col2.setAlpha(a2); g.setColorAt(1, col2)
    p.fillRect(p.viewport(), QBrush(g))


def _grain_tile():
    global _grain
    if _grain is None:
        rnd = random.Random(7)
        img = QImage(160, 160, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        for y in range(160):
            for x in range(160):
                if rnd.random() < .5:
                    v = rnd.randint(150, 255)
                    img.setPixelColor(x, y, QColor(v, v, v, rnd.randint(2, 9)))
        _grain = QPixmap.fromImage(img)
    return _grain


def _vignette(p, w, h, a=150):
    g = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * .75)
    g.setColorAt(0.55, QColor(0, 0, 0, 0)); g.setColorAt(1, QColor(0, 0, 0, a))
    p.fillRect(p.viewport(), QBrush(g))


def _finish(p, w, h, vig=110):
    p.drawTiledPixmap(QRectF(0, 0, w, h).toRect(), _grain_tile())
    if vig:
        _vignette(p, w, h, vig)



def classic(p, w, h):
    """The original RSG look: blue smoke and neon streaks in the corners."""
    k = min(1.0, max(w, h) / 1000)
    p.fillRect(0, 0, w, h, QColor("#03060d"))
    for cx, cy, r, a in ((w, 0, max(w, h) * 0.55, 46), (0, h, max(w, h) * 0.5, 40),
                         (w * 0.62, h * 0.55, max(w, h) * 0.35, 14)):
        g = QRadialGradient(QPointF(cx, cy), r)
        g.setColorAt(0, QColor(20, 90, 255, a))
        g.setColorAt(1, QColor(20, 90, 255, 0))
        p.fillRect(0, 0, w, h, QBrush(g))

    def streak(x1, y1, x2, y2, width, alpha):
        g = QLinearGradient(x1, y1, x2, y2)
        g.setColorAt(0, QColor(30, 110, 255, 0))
        g.setColorAt(0.5, QColor(40, 130, 255, alpha))
        g.setColorAt(1, QColor(30, 110, 255, 0))
        p.setPen(QPen(QBrush(g), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    streak(w - 260 * k, 0, w, 210 * k, 2.0, 150)
    streak(w - 190 * k, 0, w, 150 * k, 1.0, 90)
    streak(0, h - 170 * k, 170 * k, h, 2.0, 130)
    streak(0, h - 250 * k, 250 * k, h, 1.0, 80)

# 1 ─ AURORA: soft drifting colour clouds (blue / cyan / violet) + light grain
def aurora(p, w, h):
    p.fillRect(0, 0, w, h, QColor("#03060d"))
    m = max(w, h)
    _glow(p, w*.85, h*.05, m*.65, "#1f5bff", 95)
    _glow(p, w*.10, h*.95, m*.60, "#00b2ff", 70)
    _glow(p, w*.55, h*.30, m*.45, "#6a3dff", 55)
    _glow(p, w*.30, h*.10, m*.35, "#00e0ff", 28)
    _glow(p, w*.95, h*.85, m*.40, "#8a2be2", 38)
    # soft diagonal light band
    g = QLinearGradient(0, h*.2, w, h*.8)
    g.setColorAt(0, QColor(0, 0, 0, 0)); g.setColorAt(.5, QColor(80, 160, 255, 16)); g.setColorAt(1, QColor(0, 0, 0, 0))
    p.fillRect(0, 0, w, h, QBrush(g))
    _finish(p, w, h, 120)

# 2 ─ GRID: fading tech grid + horizon glow from the top
def grid(p, w, h):
    p.fillRect(0, 0, w, h, QColor("#03060d"))
    _glow(p, w*.5, -h*.15, max(w, h)*.85, "#1f5bff", 110)
    _glow(p, w*.5, h*1.1, max(w, h)*.6, "#00b2ff", 40)
    step = 44
    for pass_, (alpha, wd, s) in enumerate(((46, 1, step), (105, 1, step*4))):
        pen = QPen(QColor(60, 140, 255, alpha), wd); p.setPen(pen)
        x = 0
        while x <= w:
            p.drawLine(QPointF(x, 0), QPointF(x, h)); x += s
        y = 0
        while y <= h:
            p.drawLine(QPointF(0, y), QPointF(w, y)); y += s
    # fade grid towards the centre so content stays readable
    g = QRadialGradient(QPointF(w/2, h*.55), max(w, h)*.55)
    g.setColorAt(0, QColor(3, 6, 13, 215)); g.setColorAt(.55, QColor(3, 6, 13, 120)); g.setColorAt(1, QColor(3, 6, 13, 0))
    p.fillRect(0, 0, w, h, QBrush(g))
    # intersection dots
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(0, 178, 255, 120))
    x = 0
    while x <= w:
        y = 0
        while y <= h:
            d = math.hypot(x - w/2, y - h*.55) / (max(w, h)*.6)
            if d > .55 and (x // step + y // step) % 2 == 0:
                p.drawEllipse(QPointF(x, y), 1.6, 1.6)
            y += step*4
        x += step*4
    _finish(p, w, h, 130)

# 3 ─ RING: giant faint RSG ring (matches the logo) + concentric rings
def ring(p, w, h):
    p.fillRect(0, 0, w, h, QColor("#03060d"))
    cx, cy = w*.78, h*.62
    R = min(w, h) * .62
    _glow(p, cx, cy, R*1.9, "#1f5bff", 90)
    _glow(p, w*.05, h*.05, max(w, h)*.4, "#00b2ff", 34)
    for i, (k, a) in enumerate(((1.0, 70), (1.25, 34), (1.6, 20), (2.1, 12))):
        p.setPen(QPen(QColor(40, 130, 255, a), 1.2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R*k, R*k)
    # neon arc (like the logo's ring)
    g = QConicalGradient(QPointF(cx, cy), 118)
    g.setColorAt(0, QColor(0, 200, 255, 0)); g.setColorAt(.10, QColor(0, 200, 255, 235)); g.setColorAt(.26, QColor(31, 91, 255, 0))
    g.setColorAt(1, QColor(0, 200, 255, 0))
    for wd, mul in ((16, .18), (7, .45), (3, 1.0)):
        g2 = QConicalGradient(QPointF(cx, cy), 118)
        g2.setColorAt(0, QColor(0, 200, 255, 0)); g2.setColorAt(.10, QColor(0, 200, 255, int(235*mul))); g2.setColorAt(.26, QColor(31, 91, 255, 0)); g2.setColorAt(1, QColor(0, 200, 255, 0))
        p.setPen(QPen(QBrush(g2), wd, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(QPointF(cx, cy), R, R)
    _finish(p, w, h, 125)

# 4 ─ HEX: honeycomb pattern that fades out from the corners
def hexa(p, w, h):
    p.fillRect(0, 0, w, h, QColor("#03060d"))
    _glow(p, w, 0, max(w, h)*.7, "#1f5bff", 80)
    _glow(p, 0, h, max(w, h)*.55, "#00b2ff", 55)
    r = 30.0
    dx, dy = r*math.sqrt(3), r*1.5
    p.setBrush(Qt.BrushStyle.NoBrush)
    row = 0; y = -r
    while y < h + r:
        x = -dx if row % 2 == 0 else -dx/2
        while x < w + dx:
            # strength: strong at top-right and bottom-left corners
            d1 = math.hypot(x - w, y) / (max(w, h)*.75)
            d2 = math.hypot(x, y - h) / (max(w, h)*.65)
            s = max(0.0, 1 - min(d1, d2))
            if s > 0.02:
                a = int(120 * s**1.4)
                p.setPen(QPen(QColor(50, 140, 255, a), 1))
                pts = QPolygonF([QPointF(x + r*math.cos(math.radians(60*i - 30)), y + r*math.sin(math.radians(60*i - 30))) for i in range(6)])
                p.drawPolygon(pts)
                if (int(x) * 7 + int(y) * 13) % 11 == 0:
                    p.setBrush(QColor(0, 178, 255, int(55 * s))); p.drawPolygon(pts); p.setBrush(Qt.BrushStyle.NoBrush)
            x += dx
        y += dy; row += 1
    _finish(p, w, h, 120)

# 5 ─ NEBULA: starfield + diagonal light beams + deep blue smoke
def nebula(p, w, h):
    p.fillRect(0, 0, w, h, QColor("#03060d"))
    m = max(w, h)
    _glow(p, w*.75, h*.2, m*.55, "#1f5bff", 70)
    _glow(p, w*.2, h*.85, m*.5, "#0a3cff", 60)
    _glow(p, w*.5, h*.5, m*.5, "#5b2bff", 26)
    rnd = random.Random(42)
    p.setPen(Qt.PenStyle.NoPen)
    for _ in range(170):
        x, y = rnd.random()*w, rnd.random()*h
        s = rnd.random()
        r = .5 + s*1.3
        a = int(40 + 170*s*rnd.random())
        col = QColor(200, 225, 255, a) if rnd.random() > .25 else QColor(90, 190, 255, a)
        p.setBrush(col); p.drawEllipse(QPointF(x, y), r, r)
        if s > .93:
            _glow_dot = QRadialGradient(QPointF(x, y), 9)
            _glow_dot.setColorAt(0, QColor(120, 200, 255, 90)); _glow_dot.setColorAt(1, QColor(120, 200, 255, 0))
            p.setBrush(QBrush(_glow_dot)); p.drawEllipse(QPointF(x, y), 9, 9)
    def beam(x1, y1, x2, y2, wd, a):
        g = QLinearGradient(x1, y1, x2, y2)
        g.setColorAt(0, QColor(30, 110, 255, 0)); g.setColorAt(.5, QColor(70, 160, 255, a)); g.setColorAt(1, QColor(30, 110, 255, 0))
        p.setPen(QPen(QBrush(g), wd, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)); p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    k = min(1.0, m/1000)
    beam(w-420*k, 0, w, 330*k, 2.5, 170); beam(w-300*k, 0, w, 240*k, 1, 110); beam(w-560*k, 0, w, 440*k, 1, 60)
    beam(0, h-330*k, 330*k, h, 2.5, 150); beam(0, h-240*k, 240*k, h, 1, 100); beam(0, h-440*k, 440*k, h, 1, 55)
    _finish(p, w, h, 130)


# key -> (label, painter). Order = order in Settings.
THEMES = {
    "classic": ("Classic", classic),
    "aurora": ("Aurora", aurora),
    "grid": ("Grid", grid),
    "ring": ("Ring", ring),
    "hex": ("Hex", hexa),
    "nebula": ("Nebula", nebula),
}
DEFAULT_THEME = "classic"
