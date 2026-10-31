from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QVBoxLayout

from app.pages.base import Page, card, section_label
from app.widgets.buttons import AppButton
from app.widgets.fields import ReadOnlyPath
from app.widgets.status import StatusDot
from app.widgets.toggle import ToggleSwitch
from app.widgets.admin_panel import AdminPanel


class SettingsPage(Page):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        actions = QHBoxLayout()
        back = AppButton("Back", "back", "ghost")
        back.clicked.connect(lambda: window.navigate("overview"))
        actions.addWidget(back)
        self.add_header("Settings", "Configure the launcher.", actions, eyebrow="Setup")

        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(section_label("Studio executable"))
        left.addWidget(ReadOnlyPath(window.studio_path))

        file_name = Path(window.studio_path).name if window.studio_path else "Not selected"
        ok = file_name == "RobloxStudioBeta.exe"
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addWidget(StatusDot("#2ee6a6" if ok else "#f5b942", 7))
        status = QLabel(f"Selected file: {file_name}")
        status.setObjectName("settingsStatusOk" if ok else "settingsStatusWarn")
        status_row.addWidget(status)
        status_row.addStretch()
        left.addLayout(status_row)

        hint = QLabel(
            "Choose the Studio binary named RobloxStudioBeta.exe. "
            "It is usually inside AppData\\Local\\Roblox\\Versions\\version-*."
        )
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        left.addWidget(hint)
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(10)
        browse = AppButton("Choose file", "folder", "primary")
        browse.setMinimumHeight(38)
        browse.clicked.connect(self._browse)
        detect = AppButton("Detect automatically", "refresh", "secondary")
        detect.setMinimumHeight(38)
        detect.clicked.connect(window.auto_detect_studio)
        clear = AppButton("Clear path", "close", "ghost")
        clear.setMinimumHeight(38)
        clear.clicked.connect(window.clear_studio_path)
        right.addWidget(browse)
        right.addWidget(detect)
        right.addWidget(clear)
        right.addStretch()

        body = QHBoxLayout()
        body.setSpacing(18)
        body.addWidget(card(left, (24, 20, 24, 20)), 3)
        body.addWidget(card(right, (18, 18, 18, 18)), 1)
        self.root.addLayout(body)

        notify_text = QVBoxLayout()
        notify_text.setSpacing(3)
        notify_title = QLabel("Notify when the server is ready")
        notify_title.setObjectName("fieldLabel")
        notify_hint = QLabel(
            "Plays a soft chime and flashes the taskbar button if the window is in the background."
        )
        notify_hint.setObjectName("fieldHint")
        notify_hint.setWordWrap(True)
        notify_text.addWidget(notify_title)
        notify_text.addWidget(notify_hint)
        self.notify_toggle = ToggleSwitch(window.settings.notify_ready)
        self.notify_toggle.toggled.connect(window.set_notify_ready)
        notify_row = QHBoxLayout()
        notify_row.setSpacing(18)
        notify_row.addLayout(notify_text, 1)
        notify_row.addWidget(self.notify_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        self.root.addWidget(section_label("Notifications"))
        self.root.addWidget(card(notify_row, (24, 16, 24, 16)))

        auto_text = QVBoxLayout()
        auto_text.setSpacing(3)
        auto_title = QLabel("24/7 mode")
        auto_title.setObjectName("fieldLabel")
        auto_hint = QLabel(
            "Shows the 24/7 section when creating a server (schedule, map rotation, Discord status). "
            "Turn it off to hide it. A running 24/7 cycle must be stopped first."
        )
        auto_hint.setObjectName("fieldHint")
        auto_hint.setWordWrap(True)
        auto_text.addWidget(auto_title)
        auto_text.addWidget(auto_hint)
        self.auto_feature_toggle = ToggleSwitch(window.settings.auto_feature_enabled)
        self.auto_feature_toggle.toggled.connect(self._on_auto_feature)
        auto_row = QHBoxLayout()
        auto_row.setSpacing(18)
        auto_row.addLayout(auto_text, 1)
        auto_row.addWidget(self.auto_feature_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        self.root.addWidget(section_label("24/7"))
        self.root.addWidget(card(auto_row, (24, 16, 24, 16)))

        self.admin_panel = AdminPanel(window.settings.update_repo)
        self.admin_panel.repo_saved.connect(window.set_update_repo)
        self.root.addWidget(self.admin_panel)
        self.root.addStretch()

    def _on_auto_feature(self, enabled: bool) -> None:
        if not self.window.set_auto_feature(enabled):
            self.auto_feature_toggle.blockSignals(True)  # refused: put the switch back without re-triggering
            self.auto_feature_toggle.setChecked(not enabled)
            self.auto_feature_toggle._offset = 1.0 if not enabled else 0.0
            self.auto_feature_toggle.update()
            self.auto_feature_toggle.blockSignals(False)

    def _browse(self) -> None:
        start_dir = ""
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        versions_dir = Path(local_appdata) / "Roblox" / "Versions" if local_appdata else None
        if versions_dir and versions_dir.is_dir():
            start_dir = str(versions_dir)

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose RobloxStudioBeta.exe",
            start_dir,
            "Studio executable (RobloxStudioBeta.exe);;Executable (*.exe)",
        )
        if path:
            self.window.set_studio_path(path)
