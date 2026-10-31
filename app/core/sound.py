from __future__ import annotations

import os

from PySide6.QtWidgets import QApplication

from app.core.config import SOUNDS_DIR


def play_ready() -> None:
    """Soft chime. winsound (stdlib) on Windows; the system beep elsewhere."""
    path = SOUNDS_DIR / "ready.wav"
    if os.name == "nt" and path.is_file():
        try:
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            return
        except Exception:
            pass
    QApplication.beep()
