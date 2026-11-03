from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.styles import palette

STYLE_PATH = Path(__file__).with_name("dark.qss")


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    font = QFont("Bahnschrift", 10)
    font.setFamilies(["Bahnschrift", "Segoe UI"])
    app.setFont(font)
    refresh_stylesheet(app)


def refresh_stylesheet(app: QApplication) -> None:
    """(Re)apply the stylesheet for the current mode and accent colour (see palette.py)."""
    app.setStyleSheet(palette.qss(STYLE_PATH.read_text(encoding="utf-8")))
