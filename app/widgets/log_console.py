from __future__ import annotations

import time

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from app.styles.palette import qcolor as QColor

# Display order of the legend. Every line belongs to exactly one of these.
LEVELS = ("error", "warning", "success", "info")
TAGS = {"error": "ERR ", "warning": "WARN", "success": "OK  ", "info": "INFO"}
ALIASES = {"warn": "warning", "err": "error", "ok": "success", "fail": "error", "debug": "info"}
MAX_LINES = 5000


def normalize(level: str) -> str:
    level = ALIASES.get(level, level)
    return level if level in LEVELS else "info"


class LogConsole(QTextEdit):
    """Coloured console. Every line keeps its level, so the colours can be re-applied
    after a theme change and a level can be hidden without losing the lines."""

    COLORS = {
        "info": "#8ea2c7",
        "success": "#2ee6a6",
        "warning": "#f5b942",
        "error": "#ff5d73",
        "ts": "#34466e",
    }
    # Faint line background so errors and warnings stand out when scrolling fast.
    TINTS = {"error": (255, 93, 115, 34), "warning": (245, 185, 66, 22)}

    counts_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setObjectName("logConsole")
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        font = QFont("Cascadia Mono", 9)
        font.setFamilies(["Cascadia Mono", "Consolas"])
        self.setFont(font)
        self._entries: list[tuple[str, str, str]] = []  # (time, message, level)
        self._hidden: set[str] = set()
        self._counts = {level: 0 for level in LEVELS}

    # ----- writing -----

    def append_log(self, message: str, level: str = "info") -> None:
        level = normalize(level)
        stamp = time.strftime("%H:%M:%S")
        self._entries.append((stamp, message, level))
        self._counts[level] += 1
        if len(self._entries) > MAX_LINES:
            _, _, old = self._entries.pop(0)
            self._counts[old] = max(0, self._counts[old] - 1)
            if old not in self._hidden:
                self._render()  # the oldest visible line has to go as well
                self.counts_changed.emit()
                return
        if level not in self._hidden:
            self._write(stamp, message, level)
        self.counts_changed.emit()

    def _write(self, stamp: str, message: str, level: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._insert(cursor, f"[{stamp}] ", "ts", None)
        self._insert(cursor, f"{TAGS[level]} ", level, None, bold=level in ("error", "warning"))
        self._insert(cursor, f"{message}\n", level, self.TINTS.get(level), bold=level == "error")
        self.setTextCursor(cursor)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def _insert(self, cursor, text: str, color_key: str, tint, bold: bool = False) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.COLORS.get(color_key, self.COLORS["info"])))
        if tint:
            fmt.setBackground(QColor(*tint))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        cursor.setCharFormat(fmt)
        cursor.insertText(text)

    # ----- filtering / restyling -----

    def _render(self) -> None:
        self.clear()
        self.setUpdatesEnabled(False)
        try:
            for stamp, message, level in self._entries:
                if level not in self._hidden:
                    self._write(stamp, message, level)
        finally:
            self.setUpdatesEnabled(True)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def set_level_visible(self, level: str, visible: bool) -> None:
        level = normalize(level)
        changed = (level in self._hidden) == visible
        if visible:
            self._hidden.discard(level)
        else:
            self._hidden.add(level)
        if changed:
            self._render()

    def is_level_visible(self, level: str) -> bool:
        return normalize(level) not in self._hidden

    def counts(self) -> dict[str, int]:
        return dict(self._counts)

    def restyle(self) -> None:
        """Re-apply the colours after a dark/light or accent change."""
        self._render()

    def full_text(self) -> str:
        """Every line, with its level tag, even the ones currently hidden by a filter."""
        return "".join(f"[{s}] {TAGS[lv]} {m}\n" for s, m, lv in self._entries)

    def clear_log(self) -> None:
        self._entries.clear()
        self._counts = {level: 0 for level in LEVELS}
        self.clear()
        self.counts_changed.emit()
