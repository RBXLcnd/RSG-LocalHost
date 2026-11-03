"""First-run assistant: language, Roblox Studio, Discord (optional) and the 24/7 question."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core import i18n
from app.core.i18n import tr
from app.widgets.buttons import AppButton

STEPS = 4


def _label(text: str, name: str = "", wrap: bool = True) -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setWordWrap(wrap)
    return label


class WelcomeDialog(QDialog):
    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.auto_enabled = False
        self.setObjectName("welcomeDialog")
        self.setWindowTitle("Welcome")
        self.setModal(True)
        self.setMinimumSize(540, 400)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)

        self.dots = QLabel()
        self.dots.setObjectName("eyebrow")
        root.addWidget(self.dots)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_welcome())
        self.stack.addWidget(self._page_studio())
        self.stack.addWidget(self._page_discord())
        self.stack.addWidget(self._page_auto())
        root.addWidget(self.stack, 1)

        nav = QHBoxLayout()
        self.skip_btn = AppButton("Skip setup", None, "ghost")
        self.skip_btn.clicked.connect(self.reject)
        self.back_btn = AppButton("Back", None, "secondary")
        self.back_btn.clicked.connect(lambda: self._go(self.stack.currentIndex() - 1))
        self.next_btn = AppButton("Next", None, "primary")
        self.next_btn.clicked.connect(self._next)
        nav.addWidget(self.skip_btn)
        nav.addStretch()
        nav.addWidget(self.back_btn)
        nav.addWidget(self.next_btn)
        root.addLayout(nav)

        window.account_changed.connect(self._refresh_discord)
        self._go(0)

    # ---------- pages ----------
    def _page(self, title: str, intro: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(_label(title, "pageTitle"))
        layout.addWidget(_label(intro, "pageSubtitle"))
        return page, layout

    def _page_welcome(self) -> QWidget:
        page, layout = self._page(
            "Welcome to RSG LocalHost",
            "Host Roblox Studio servers for your friends in a few clicks. This short setup takes about a minute and you can change everything later in Settings.",
        )
        layout.addWidget(_label("Language", "fieldLabel"))
        row = QHBoxLayout()
        self.lang_group = QButtonGroup(self)
        self.lang_group.setExclusive(True)
        for code, name in (("en", "English"), ("pt", "Português")):
            button = AppButton(name, None, "secondary")
            button.setCheckable(True)
            button.setChecked(i18n.get_language() == code)
            button.setProperty("lang", code)
            self.lang_group.addButton(button)
            button.clicked.connect(lambda _=False, c=code: self._set_language(c))
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        return page

    def _page_studio(self) -> QWidget:
        page, layout = self._page(
            "Roblox Studio",
            "The app needs RobloxStudioBeta.exe to start servers. It is usually found automatically.",
        )
        self.studio_status = _label("", "settingsStatusOk")
        layout.addWidget(self.studio_status)
        row = QHBoxLayout()
        detect = AppButton("Detect again", None, "secondary")
        detect.clicked.connect(self._detect_studio)
        choose = AppButton("Choose file", "folder", "secondary")
        choose.clicked.connect(self._choose_studio)
        row.addWidget(detect)
        row.addWidget(choose)
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(_label("You can also do this later in Settings.", "fieldHint"))
        layout.addStretch()
        return page

    def _page_discord(self) -> QWidget:
        page, layout = self._page(
            "Discord (optional)",
            "Sign in to show your server in the Discord server list. In the Discord server run /host-login and paste the key it sends you.",
        )
        self.discord_status = _label("", "settingsStatusWarn")
        layout.addWidget(self.discord_status)
        row = QHBoxLayout()
        self.discord_btn = AppButton("Sign in with Discord", None, "secondary")
        self.discord_btn.clicked.connect(self.window.discord_login)
        row.addWidget(self.discord_btn)
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(_label("Not needed to play with friends. Skip it if you do not use Discord.", "fieldHint"))
        layout.addStretch()
        return page

    def _page_auto(self) -> QWidget:
        page, layout = self._page(
            "24/7 mode",
            "It keeps a server online on a schedule (online, pause, next map, repeat) and shows its status on Discord. Do you want it?",
        )
        row = QHBoxLayout()
        self.auto_group = QButtonGroup(self)
        self.auto_group.setExclusive(True)
        self.auto_yes = AppButton("Yes, show 24/7", None, "secondary")
        self.auto_no = AppButton("No, hide it", None, "secondary")
        for button in (self.auto_yes, self.auto_no):
            button.setCheckable(True)
            self.auto_group.addButton(button)
            row.addWidget(button)
        self.auto_no.setChecked(True)
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(_label("You can turn it on or off later in Settings.", "fieldHint"))
        layout.addStretch()
        return page

    # ---------- actions ----------
    def _set_language(self, code: str) -> None:
        self.window.set_language(code)
        self._refresh()

    def _detect_studio(self) -> None:
        from app.core.studio import get_studio_path

        path = get_studio_path()
        if path:
            self.window.set_studio_path(path, navigate=False)
        self._refresh()

    def _choose_studio(self) -> None:
        local = os.environ.get("LOCALAPPDATA", "")
        versions = Path(local) / "Roblox" / "Versions" if local else None
        start = str(versions) if versions and versions.is_dir() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Choose RobloxStudioBeta.exe"), start, "Studio executable (RobloxStudioBeta.exe);;Executable (*.exe)"
        )
        if path:
            self.window.set_studio_path(path, navigate=False)
        self._refresh()

    def _refresh_studio(self) -> None:
        path = self.window.studio_path
        ok = bool(path) and Path(path).is_file()
        self.studio_status.setObjectName("settingsStatusOk" if ok else "settingsStatusWarn")
        self.studio_status.style().unpolish(self.studio_status)
        self.studio_status.style().polish(self.studio_status)
        self.studio_status.setText(
            tr("Found: {}").format(Path(path).name) if ok else tr("Studio not found yet. Install Roblox Studio or choose the file.")
        )

    def _refresh_discord(self) -> None:
        name = self.window.settings.discord_username
        signed = self.window.is_signed_in()
        self.discord_status.setObjectName("settingsStatusOk" if signed else "settingsStatusWarn")
        self.discord_status.style().unpolish(self.discord_status)
        self.discord_status.style().polish(self.discord_status)
        if signed:
            self.discord_status.setText(tr("Signed in as {}").format(name) if name else tr("Signed in"))
        else:
            self.discord_status.setText(tr("Not signed in"))

    def _refresh(self) -> None:
        for button in self.lang_group.buttons():
            button.setChecked(button.property("lang") == i18n.get_language())
        self._refresh_studio()
        self._refresh_discord()
        index = self.stack.currentIndex()
        self.dots.setText(tr("Step {} of {}").format(index + 1, STEPS))
        self.setWindowTitle(tr("Welcome"))

    def _go(self, index: int) -> None:
        index = max(0, min(STEPS - 1, index))
        self.stack.setCurrentIndex(index)
        self.back_btn.setVisible(index > 0)
        self.next_btn.setText("Start" if index == STEPS - 1 else "Next")
        self._refresh()

    def _next(self) -> None:
        if self.stack.currentIndex() >= STEPS - 1:
            self.auto_enabled = self.auto_yes.isChecked()
            self.accept()
        else:
            self._go(self.stack.currentIndex() + 1)
