"""Accent colour + light/dark mode.

The whole look is written once, for the dark blue design. Light mode and other accents are produced
by transforming every colour of that design:

* the blue family (hue 180-260) is rotated to the chosen accent hue;
* light mode flips lightness (dark navy surfaces become pale, light text becomes dark);
* status colours (green, amber, red) are only darkened in light mode so they stay readable.

`pal()` does this for one colour (used by painted widgets and icons); `qss()` does it for a whole
stylesheet. Pure white (#ffffff) is left alone on purpose: it is the text colour on accent buttons.
"""
from __future__ import annotations

import colorsys
import re

from PySide6.QtGui import QColor

BASE_ACCENT = "#1e9bff"
BASE_HUE = 206.7  # hue of BASE_ACCENT
FAMILY = (180.0, 260.0)

ACCENTS = {
    "blue": "#1e9bff",
    "teal": "#14b8a6",
    "green": "#22c55e",
    "orange": "#f97316",
    "red": "#ef4444",
    "pink": "#ec4899",
    "violet": "#8b5cf6",
}

_mode = "dark"
_accent = BASE_ACCENT
_delta = 0.0
_cache: dict[str, str] = {}

_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
_RGBA = re.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)")


def valid_accent(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value) is not None


def _hue_of(color: str) -> float:
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)[0] * 360


def configure(mode: str = "dark", accent: str = BASE_ACCENT) -> None:
    global _mode, _accent, _delta
    _mode = mode if mode in ("dark", "light") else "dark"
    _accent = accent if valid_accent(accent) else BASE_ACCENT
    _delta = _hue_of(_accent) - BASE_HUE
    _cache.clear()


def mode() -> str:
    return _mode


def is_light() -> bool:
    return _mode == "light"


def accent() -> str:
    return _accent


def _convert(r: int, g: int, b: int) -> tuple[int, int, int]:
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hue = h * 360
    neutral = s < 0.08
    family = FAMILY[0] <= hue <= FAMILY[1]
    if family and not neutral:
        hue = (hue + _delta) % 360
    if _mode == "light":
        if family or neutral:
            l = 0.10 + 0.88 * (1 - l)
            if l > 0.8:
                s *= 0.5
        else:
            l = min(l, 0.42)
    nr, ng, nb = colorsys.hls_to_rgb(hue / 360, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return round(nr * 255), round(ng * 255), round(nb * 255)


def pal(color: str) -> str:
    """Convert one '#rrggbb' colour for the current mode/accent. Anything else is returned as is."""
    if not isinstance(color, str) or not _HEX.fullmatch(color):
        return color
    if _mode == "dark" and _delta == 0:
        return color
    key = color.lower()
    hit = _cache.get(key)
    if hit is None:
        if _mode == "light" and key == "#ffffff":
            hit = key
        else:
            hit = "#%02x%02x%02x" % _convert(*(int(key[i:i + 2], 16) for i in (1, 3, 5)))
        _cache[key] = hit
    return hit


def _light_overrides() -> str:
    a1, a2 = pal("#00a8ff"), pal("#1f4fff")
    return f"""
/* ---------- light mode adjustments ---------- */
QFrame[tile="primary"] {{
  border: 1px solid {pal('#2f8bff')};
  background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {a1}, stop:1 {a2});
}}
QLabel#tileText[tone="primary"] {{ color: #eaf3ff; }}
QFrame[tile="secondary"] QLabel#tileTitle {{ color: {pal('#f4f8ff')}; }}
"""


def qss(text: str) -> str:
    """The stylesheet text converted for the current mode/accent."""
    if _mode == "dark" and _delta == 0:
        return text
    def hex_sub(m: re.Match) -> str:
        return pal(m.group(0))
    def rgba_sub(m: re.Match) -> str:
        r, g, b = _convert(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return f"rgba({r},{g},{b},{m.group(4)})"
    out = _RGBA.sub(rgba_sub, _HEX.sub(hex_sub, text))
    return out + (_light_overrides() if _mode == "light" else "")


def qcolor(*args):
    """Drop-in for QColor(...) that converts '#rrggbb' strings and (r, g, b[, a]) integers."""
    if len(args) == 1 and isinstance(args[0], str):
        return QColor(pal(args[0]))
    if len(args) in (3, 4) and all(isinstance(a, int) and not isinstance(a, bool) for a in args):
        if _mode == "dark" and _delta == 0:
            return QColor(*args)
        r, g, b = _convert(*args[:3])
        return QColor(r, g, b, *args[3:])
    return QColor(*args)
