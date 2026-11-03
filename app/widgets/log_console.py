from __future__ import annotations

import time

from PySide6.QtGui import QTextCharFormat, QTextCursor, QFont
from app.styles.palette import qcolor as QColor
from PySide6.QtWidgets import QTextEdit


class LogConsole(QTextEdit):
    COLORS = {
        "info": "#8ea2c7",
        "success": "#2ee6a6",
        "warning": "#f5b942",
        "error": "#ff5d73",
        "ts": "#34466e",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setObjectName("logConsole")
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        font = QFont("Cascadia Mono", 9)
        font.setFamilies(["Cascadia Mono", "Consolas"])
        self.setFont(font)

    def append_log(self, message: str, level: str = "info") -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self._insert(f"[{time.strftime('%H:%M:%S')}] ", "ts")
        self._insert(f"{message}\n", level)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def _insert(self, text: str, level: str) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.COLORS.get(level, self.COLORS["info"])))
        cursor = self.textCursor()
        cursor.setCharFormat(fmt)
        cursor.insertText(text)

