from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
)

from app.widgets.buttons import AppButton
from app.widgets.fields import FormField

ADMIN_CODE = "JoaoDinis0109"


class AdminPanel(QFrame):
    """Hidden panel behind a code, for settings that aren't ready to be public yet.

    Starts as a small "Admin" link. Entering the correct code reveals the
    real settings (currently: the GitHub repository used for update checks).
    Locks again whenever the app restarts.
    """

    repo_saved = Signal(str)

    def __init__(self, repo_value: str = "") -> None:
        super().__init__()
        self.setObjectName("adminPanel")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 0)
        outer.setSpacing(0)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        self.stack.addWidget(self._build_trigger())
        self.stack.addWidget(self._build_code_entry())
        self.stack.addWidget(self._build_unlocked(repo_value))

    # ---- page 0: dormant trigger ----
    def _build_trigger(self) -> QFrame:
        page = QFrame()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        link = AppButton("Admin", None, "ghost")
        link.setObjectName("adminTrigger")
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.setFlat(True)
        link.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        row.addWidget(link)
        return page

    # ---- page 1: code prompt ----
    def _build_code_entry(self) -> QFrame:
        page = QFrame()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addStretch(1)

        self.code_edit = QLineEdit()
        self.code_edit.setObjectName("lineEdit")
        self.code_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.code_edit.setPlaceholderText("Admin code")
        self.code_edit.setFixedWidth(160)
        self.code_edit.returnPressed.connect(self._check_code)
        row.addWidget(self.code_edit)

        confirm = AppButton("Unlock", None, "secondary")
        confirm.clicked.connect(self._check_code)
        row.addWidget(confirm)

        cancel = AppButton("Cancel", None, "ghost")
        cancel.clicked.connect(self._cancel)
        row.addWidget(cancel)
        return page

    def _check_code(self) -> None:
        if self.code_edit.text() == ADMIN_CODE:
            self.code_edit.clear()
            self.stack.setCurrentIndex(2)
        else:
            self.code_edit.selectAll()
            self.code_edit.setFocus()
            window = self.window()
            if hasattr(window, "toast"):
                window.toast("Incorrect code.", "error")

    def _cancel(self) -> None:
        self.code_edit.clear()
        self.stack.setCurrentIndex(0)

    # ---- page 2: unlocked settings ----
    def _build_unlocked(self, repo_value: str) -> QFrame:
        page = QFrame()
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Admin")
        title.setObjectName("sectionTitle")
        head.addWidget(title)
        head.addStretch(1)
        lock = AppButton("Lock", None, "ghost")
        lock.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        head.addWidget(lock)
        col.addLayout(head)

        self.repo_field = FormField(
            "GitHub repository",
            repo_value,
            "Used to check for new releases, e.g. owner/repo. Leave empty until the repo exists.",
            placeholder="owner/repo",
        )
        col.addWidget(self.repo_field)

        save = AppButton("Save", None, "primary")
        save.clicked.connect(self._save)
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_row.addWidget(save)
        col.addLayout(save_row)
        return page

    def _save(self) -> None:
        value = self.repo_field.value().strip()
        self.repo_saved.emit(value)
        window = self.window()
        if hasattr(window, "toast"):
            window.toast("Repository saved." if value else "Repository cleared.", "success")
