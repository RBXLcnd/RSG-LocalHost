"""One switch for every animation in the app (Settings > Appearance can turn them off).

New animations ask this module for their duration: it returns 0 when motion is off,
and an animation of 0 ms simply jumps to its end value."""
from __future__ import annotations

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPropertyAnimation, QVariantAnimation

_enabled = True


def configure(enabled: bool) -> None:
    global _enabled
    _enabled = bool(enabled)


def enabled() -> bool:
    return _enabled


def ms(duration: int) -> int:
    """`duration` when animations are on, 0 when they are off."""
    return duration if _enabled else 0


def tween(parent, start: float, end: float, duration: int, apply, easing=QEasingCurve.Type.OutCubic,
          on_done=None) -> QVariantAnimation | None:
    """Run apply(value) from start to end. With motion off, apply(end) is called at once.
    The animation belongs to `parent`, so it disappears together with it."""
    if not _enabled or duration <= 0:
        apply(end)
        if on_done:
            on_done()
        return None
    anim = QVariantAnimation(parent)
    anim.setStartValue(float(start))
    anim.setEndValue(float(end))
    anim.setDuration(duration)
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(lambda value: apply(float(value)))
    if on_done:
        anim.finished.connect(on_done)
    anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


def fade_in(window, duration: int = 140) -> None:
    """Fade a top-level window (popup, dialog) in."""
    if not _enabled or duration <= 0:
        window.setWindowOpacity(1.0)
        return
    window.setWindowOpacity(0.0)
    anim = QPropertyAnimation(window, b"windowOpacity", window)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
