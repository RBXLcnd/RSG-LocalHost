from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.widgets.icons import app_icon

Validator = Callable[[str], str | None]


class FormField(QFrame):
    """Labelled input. Default layout is a row (label left, input right);
    `stacked=True` puts the label above the input. `action` is an optional
    widget (e.g. a button) attached to the end of the input row.

    `help_text` adds a small "?" next to the label that explains the field on hover.
    Fields with a validator show a green check (and border) once the value is valid."""

    def __init__(
        self,
        label: str,
        value: str = "",
        hint: str = "",
        placeholder: str = "",
        icon: str | None = None,
        validator: Validator | None = None,
        stacked: bool = False,
        action: QWidget | None = None,
        help_text: str = "",
    ) -> None:
        super().__init__()
        self.validator = validator
        self.setObjectName("formField")

        self.label = QLabel(label)
        self.label.setObjectName("fieldLabel")
        self.label_box = QWidget()
        label_row = QHBoxLayout(self.label_box)
        label_row.setContentsMargins(0, 0, 0, 0)
        label_row.setSpacing(6)
        label_row.addWidget(self.label)
        if help_text:
            badge = HelpBadge(help_text)
            self.label.setToolTip(rich_tip(help_text))
            label_row.addWidget(badge)
        label_row.addStretch(1)
        self.error = QLabel("")
        self.error.setObjectName("fieldError")

        self.input_shell = QFrame()
        self.input_shell.setObjectName("inputShell")
        input_layout = QHBoxLayout(self.input_shell)
        input_layout.setContentsMargins(14, 0, 14, 0)
        input_layout.setSpacing(9)
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(app_icon(icon, "#5d7099").pixmap(15, 15))
            icon_label.setObjectName("fieldIcon")
            input_layout.addWidget(icon_label)
        self.edit = QLineEdit()
        self.edit.setText(value)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setObjectName("lineEdit")
        self.edit.textChanged.connect(lambda _: self.validate())
        input_layout.addWidget(self.edit)
        self.valid_icon = QLabel()
        self.valid_icon.setPixmap(app_icon("check", "#2ee6a6").pixmap(16, 16))
        self.valid_icon.setToolTip("Looks good")
        self.valid_icon.setVisible(False)
        input_layout.addWidget(self.valid_icon)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        input_row.addWidget(self.input_shell, 1)
        if action is not None:
            input_row.addWidget(action)

        meta = QHBoxLayout()
        meta.setSpacing(8)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("fieldHint")
            hint_label.setWordWrap(True)
            meta.addWidget(hint_label, 1)
        else:
            meta.addStretch(1)
        meta.addWidget(self.error)

        if stacked:
            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(8)
            root.addWidget(self.label_box)
            root.addLayout(input_row)
            root.addLayout(meta)
        else:
            root = QHBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(20)
            self.label_box.setFixedSize(120, 42)
            root.addWidget(self.label_box, 0, Qt.AlignmentFlag.AlignTop)
            right = QVBoxLayout()
            right.setSpacing(5)
            right.addLayout(input_row)
            right.addLayout(meta)
            root.addLayout(right, 1)
        self.validate()  # a value restored from settings gets its state right away

    def value(self) -> str:
        return self.edit.text().strip()

    def validate(self) -> bool:
        if not self.validator:
            self._set_state("", False)
            return True
        value = self.value()
        if not value:
            self._set_state("", False)
            return True
        error = self.validator(value)
        self._set_state(error or "", error is None)
        return error is None

    def _set_state(self, error: str, valid: bool) -> None:
        self.error.setText(error)
        self.valid_icon.setVisible(valid)
        self.input_shell.setProperty("error", bool(error))
        self.input_shell.setProperty("valid", valid)
        self.input_shell.style().unpolish(self.input_shell)
        self.input_shell.style().polish(self.input_shell)


def rich_tip(text: str, width: int = 260) -> str:
    """Tooltip text that wraps at a sensible width (plain tooltips never wrap)."""
    return f'<table width="{width}"><tr><td>{text}</td></tr></table>'


class HelpBadge(QLabel):
    """Small round "?" that explains a field when hovered."""

    def __init__(self, text: str) -> None:
        super().__init__("?")
        self.setObjectName("helpBadge")
        self.setFixedSize(16, 16)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.setToolTip(rich_tip(text))


class ReadOnlyPath(QFrame):
    def __init__(self, path: str, icon: str = "folder") -> None:
        super().__init__()
        self.setObjectName("inputShell")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(9)

        icon_label = QLabel()
        icon_label.setPixmap(app_icon(icon, "#5d7099").pixmap(15, 15))
        layout.addWidget(icon_label)

        label = QLabel(path or "Not configured")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setObjectName("pathLabel")
        label.setWordWrap(True)
        layout.addWidget(label, 1)
