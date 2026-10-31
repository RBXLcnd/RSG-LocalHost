from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from app import __version__
from app.core.config import PROXY_PORT
from app.widgets.status import StatusDot


class StatusStrip(QFrame):
    """Bottom bar: live session state on the left, environment facts on the right."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("statusStrip")
        self.setFixedHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(8)

        self.dot = StatusDot("#5d7099", 7)
        self.status = QLabel("Ready")
        self.status.setObjectName("stripStatus")
        layout.addWidget(self.dot)
        layout.addWidget(self.status)
        layout.addStretch()

        self.studio = self._pair(layout, "STUDIO", "-")
        layout.addSpacing(14)
        self._pair(layout, "PROXY", f"UDP {PROXY_PORT}")
        layout.addSpacing(14)
        self._pair(layout, "BUILD", f"v{__version__}")

    def _pair(self, layout: QHBoxLayout, key: str, value: str) -> QLabel:
        k = QLabel(key)
        k.setObjectName("stripKey")
        v = QLabel(value)
        v.setObjectName("stripValue")
        layout.addWidget(k)
        layout.addWidget(v)
        return v

    def set_status(self, text: str, color: str, strong: bool = False) -> None:
        self.dot.set_color(color)
        self.status.setText(text)
        self.status.setProperty("strong", strong)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def set_studio(self, name: str) -> None:
        self.studio.setText(name or "not configured")
