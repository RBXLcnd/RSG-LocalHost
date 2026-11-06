from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from app.core import motion
from app.styles.palette import pal


def apply_glow(widget: QWidget, color: str = "#0096ff", blur: int = 26, alpha: int = 70) -> QGraphicsDropShadowEffect:
    """Attach a soft coloured glow (drop shadow with no offset) to a widget."""
    glow = QGraphicsDropShadowEffect(widget)
    glow.setOffset(0, 0)
    glow.setBlurRadius(blur)
    tint = QColor(pal(color))
    tint.setAlpha(alpha)
    glow.setColor(tint)
    widget.setGraphicsEffect(glow)
    return glow


def set_glow(effect: QGraphicsDropShadowEffect, blur: int, alpha: int) -> None:
    tint = effect.color()
    tint.setAlpha(alpha)
    effect.setColor(tint)
    effect.setBlurRadius(blur)


def animate_glow(effect: QGraphicsDropShadowEffect, blur: int, alpha: int, duration: int = 180) -> None:
    """Ease a glow's blur radius and alpha to new values instead of snapping.

    Keeps the running animations parented to the effect itself, so callers
    don't need to hold a reference and repeated hover events just retarget
    the same pair of animations.
    """
    target_color = QColor(effect.color())
    target_color.setAlpha(alpha)
    if not motion.enabled():  # no motion: jump straight there
        for name in ("_blurAnim", "_colorAnim"):
            running = effect.property(name)
            if running is not None:
                running.stop()
        effect.setColor(target_color)
        effect.setBlurRadius(blur)
        return

    blur_anim = effect.property("_blurAnim")
    if blur_anim is None:
        blur_anim = QPropertyAnimation(effect, b"blurRadius", effect)
        blur_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        effect.setProperty("_blurAnim", blur_anim)
    blur_anim.stop()
    blur_anim.setDuration(duration)
    blur_anim.setStartValue(effect.blurRadius())
    blur_anim.setEndValue(blur)
    blur_anim.start()

    color_anim = effect.property("_colorAnim")
    if color_anim is None:
        color_anim = QPropertyAnimation(effect, b"color", effect)
        color_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        effect.setProperty("_colorAnim", color_anim)
    color_anim.stop()
    color_anim.setDuration(duration)
    color_anim.setStartValue(effect.color())
    color_anim.setEndValue(target_color)
    color_anim.start()
