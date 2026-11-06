from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from app.styles.palette import pal
from app.widgets.buttons import IconButton
from app.widgets.status import StatusDot


def spaced(label: QLabel, px: float = 2.5) -> QLabel:
    """Qt style sheets ignore letter-spacing, so apply it on the font."""
    font = label.font()
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, px)
    label.setFont(font)
    return label


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    return line


def vline() -> QFrame:
    line = QFrame()
    line.setObjectName("vline")
    line.setFixedWidth(1)
    return line


def card(layout, margins=(22, 20, 22, 20), name: str = "card") -> QFrame:
    """Wrap a layout in a rounded card."""
    frame = QFrame()
    frame.setObjectName(name)
    layout.setContentsMargins(*margins)
    frame.setLayout(layout)
    return frame


# kept under the old name so callers keep working
panel = card


def section_label(text: str, help: str = "") -> QWidget:
    """Small caps section title. `help` is a topic from app.widgets.help: adds the "?" button."""
    label = QLabel(text.upper())
    label.setObjectName("sectionTitle")
    spaced(label, 2.0)
    if not help:
        return label
    from app.widgets.help import with_help

    return with_help(label, help)


class Page(QWidget):
    """Centred content column with an eyebrow / title header (no sidebar, no rule)."""

    MAX_WIDTH: int | None = 940
    SCROLL = False  # True: the page scrolls vertically when it is taller than the window

    def __init__(self) -> None:
        super().__init__()
        if self.SCROLL:
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            scroll = QScrollArea()
            scroll.setObjectName("pageScroll")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            body = QWidget()
            body.setObjectName("pageBody")
            scroll.setWidget(body)
            outer.addWidget(scroll)
            shell = QHBoxLayout(body)
        else:
            shell = QHBoxLayout(self)
        shell.setContentsMargins(32, 0, 32, 0)
        column = QWidget()
        column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if self.MAX_WIDTH:
            column.setMaximumWidth(self.MAX_WIDTH)
            shell.addStretch(1)
            shell.addWidget(column, 100)
            shell.addStretch(1)
        else:
            shell.addWidget(column, 1)
        self._column = column if self.MAX_WIDTH else None
        self.root = QVBoxLayout(column)
        self.root.setContentsMargins(0, 22, 0, 18)
        self.root.setSpacing(16)

    def resizeEvent(self, event) -> None:
        """Wide windows get a wider content column, so content does not sit tiny in the middle."""
        super().resizeEvent(event)
        if self._column is not None and self.MAX_WIDTH:
            self._column.setMaximumWidth(max(self.MAX_WIDTH, min(1320, int(self.width() * 0.66))))

    def add_header(
        self,
        title: str,
        subtitle: str = "",
        actions: QHBoxLayout | None = None,
        eyebrow: str = "",
    ) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(3)
        if eyebrow:
            eyebrow_label = QLabel(eyebrow.upper())
            eyebrow_label.setObjectName("eyebrow")
            left.addWidget(spaced(eyebrow_label, 3.0))
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        left.addWidget(title_label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("pageSubtitle")
            sub.setWordWrap(True)
            left.addWidget(sub)
        row.addLayout(left, 1)
        if actions:
            row.addLayout(actions)
        self.root.addLayout(row)


class Step(QWidget):
    """Numbered step: badge, title (optional status dot), text and optional extra widget."""

    def __init__(
        self,
        number: int,
        title: str,
        text: str,
        dot_color: str | None = None,
        extra: QWidget | None = None,
    ) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        badge = QLabel(str(number))
        badge.setObjectName("stepNum")
        badge.setFixedSize(26, 26)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(3)
        head = QHBoxLayout()
        head.setSpacing(7)
        if dot_color:
            head.addWidget(StatusDot(dot_color, 7))
        title_label = QLabel(title)
        title_label.setObjectName("stepTitle")
        head.addWidget(title_label)
        head.addStretch()
        col.addLayout(head)
        body = QLabel(text)
        body.setObjectName("fieldHint")
        body.setWordWrap(True)
        col.addWidget(body)
        if extra is not None:
            col.addSpacing(4)
            col.addWidget(extra, 0, Qt.AlignmentFlag.AlignLeft)
        col.addStretch()
        row.addLayout(col, 1)


class InfoStrip(QFrame):
    """Session facts laid out as a grid of small cells (replaces the old side column)."""

    COLUMNS = 3

    def __init__(self, rows: list[tuple[str, str]]) -> None:
        super().__init__()
        self.setObjectName("card")
        self.labels: dict[str, QLabel] = {}
        self.value_rows: dict[str, QHBoxLayout] = {}
        grid = QGridLayout(self)
        grid.setContentsMargins(20, 14, 20, 14)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)
        for index, (key, value) in enumerate(rows):
            cell = QVBoxLayout()
            cell.setSpacing(2)
            key_label = QLabel(key.upper())
            key_label.setObjectName("metricLabel")
            spaced(key_label, 1.5)
            value_row = QHBoxLayout()
            value_row.setSpacing(6)
            value_label = QLabel(value)
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value_label.setObjectName("pathLabel")
            value_label.setWordWrap(True)
            value_row.addWidget(value_label, 1)
            cell.addWidget(key_label)
            cell.addLayout(value_row)
            grid.addLayout(cell, index // self.COLUMNS, index % self.COLUMNS)
            self.labels[key] = value_label
            self.value_rows[key] = value_row
        for col in range(self.COLUMNS):
            grid.setColumnStretch(col, 1)

    def set_value(self, key: str, value: str, color: str | None = None) -> None:
        label = self.labels.get(key)
        if not label:
            return
        label.setText(value)
        if color:
            label.setStyleSheet(f"color: {pal(color)};")

    def add_inline_action(self, key: str, icon: str, tooltip: str, callback) -> None:
        row = self.value_rows.get(key)
        if row is None:
            return
        button = IconButton(icon, tooltip, "inline")
        button.clicked.connect(lambda checked=False, b=button: callback(b))
        row.addWidget(button)
