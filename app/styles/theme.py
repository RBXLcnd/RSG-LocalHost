from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

STYLE_PATH = Path(__file__).with_name("dark.qss")


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    font = QFont("Bahnschrift", 10)
    font.setFamilies(["Bahnschrift", "Segoe UI"])
    app.setFont(font)
    app.setStyleSheet(STYLE_PATH.read_text(encoding="utf-8"))

