"""Sign in with Discord = paste the key that /host-login gave you in the Discord server.

The key is a private Discord webhook URL that only exists for your account. The app
just verifies it is alive before saving it.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.core.api import ApiError, check_key


class KeyCheck(QThread):
    """state = "ok" | "invalid" | "offline"; label = account name from the webhook (when ok)."""

    result = Signal(str, str)

    def __init__(self, key: str, parent=None) -> None:
        super().__init__(parent)
        self._key = key

    def run(self) -> None:
        try:
            label = check_key(self._key)
            self.result.emit("ok", label)
        except ApiError as exc:
            self.result.emit("invalid" if exc.code == "invalid_key" else "offline", "")
