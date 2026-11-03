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
from app import __version__
from app.widgets.admin_panel import AdminPanel
from app.widgets.theme_picker import ThemePicker
from app.widgets.accent_picker import AppearancePicker


class SettingsPage(Page):
    SCROLL = True

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

        theme_text = QVBoxLayout()
        theme_text.setSpacing(3)
        theme_title = QLabel("Background theme")
        theme_title.setObjectName("fieldLabel")
        theme_hint = QLabel("Pick the look of the app window. It applies instantly and is remembered.")
        theme_hint.setObjectName("fieldHint")
        theme_hint.setWordWrap(True)
        theme_text.addWidget(theme_title)
        theme_text.addWidget(theme_hint)
        look_text = QVBoxLayout()
        look_text.setSpacing(3)
        look_title = QLabel("Mode and accent color")
        look_title.setObjectName("fieldLabel")
        look_hint = QLabel("Switch between the dark and light look and pick the highlight color. It applies instantly.")
        look_hint.setObjectName("fieldHint")
        look_hint.setWordWrap(True)
        look_text.addWidget(look_title)
        look_text.addWidget(look_hint)
        self.appearance_picker = AppearancePicker(window.settings.appearance, window.settings.accent)
        self.appearance_picker.mode_selected.connect(lambda m: window.set_appearance(mode=m))
        self.appearance_picker.accent_selected.connect(lambda c: window.set_appearance(accent=c))
        look_col = QVBoxLayout()
        look_col.setSpacing(12)
        look_col.addLayout(look_text)
        look_col.addWidget(self.appearance_picker)
        self.theme_picker = ThemePicker(window.settings.background_theme)
        self.theme_picker.theme_selected.connect(window.set_background_theme)
        theme_col = QVBoxLayout()
        theme_col.setSpacing(14)
        theme_col.addLayout(theme_text)
        theme_col.addWidget(self.theme_picker)
        self.root.addWidget(section_label("Appearance"))
        self.root.addWidget(card(look_col, (24, 16, 24, 18)))
        self.root.addWidget(card(theme_col, (24, 18, 24, 20)))

        upd_text = QVBoxLayout()
        upd_text.setSpacing(3)
        upd_title = QLabel("Check for updates automatically")
        upd_title.setObjectName("fieldLabel")
        upd_hint = QLabel(
            "Asks GitHub for the latest release when the app starts (and every few hours). "
            "It only tells you: nothing is downloaded or installed by itself."
        )
        upd_hint.setObjectName("fieldHint")
        upd_hint.setWordWrap(True)
        upd_text.addWidget(upd_title)
        upd_text.addWidget(upd_hint)
        self.update_toggle = ToggleSwitch(window.settings.check_updates)
        self.update_toggle.toggled.connect(window.set_check_updates)
        upd_row = QHBoxLayout()
        upd_row.setSpacing(18)
        upd_row.addLayout(upd_text, 1)
        upd_row.addWidget(self.update_toggle, 0, Qt.AlignmentFlag.AlignVCenter)

        self.update_status = QLabel()
        self.update_status.setObjectName("fieldHint")
        self.update_check_button = AppButton("Check now", "refresh", "secondary")
        self.update_check_button.clicked.connect(lambda: window.check_for_updates(manual=True))
        self.update_download_button = AppButton("Download", "arrow-right", "primary")
        self.update_download_button.clicked.connect(window.open_update_page)
        upd_actions = QHBoxLayout()
        upd_actions.setSpacing(10)
        upd_actions.addWidget(self.update_status, 1)
        upd_actions.addWidget(self.update_check_button)
        upd_actions.addWidget(self.update_download_button)
        upd_col = QVBoxLayout()
        upd_col.setSpacing(14)
        upd_col.addLayout(upd_row)
        upd_col.addLayout(upd_actions)
        self.root.addWidget(section_label("Updates"))
        self.root.addWidget(card(upd_col, (24, 16, 24, 16)))
        window.update_state_changed.connect(self._refresh_update)
        self._refresh_update()

        bak_text = QVBoxLayout()
        bak_text.setSpacing(3)
        bak_title = QLabel("Export or import your settings")
        bak_title.setObjectName("fieldLabel")
        bak_hint = QLabel(
            "Saves your profiles, tunnels, 24/7 options, theme and language to a file you can keep or move to another PC. "
            "Your Discord sign-in and Studio path are never included."
        )
        bak_hint.setObjectName("fieldHint")
        bak_hint.setWordWrap(True)
        bak_text.addWidget(bak_title)
        bak_text.addWidget(bak_hint)
        export_btn = AppButton("Export", "arrow-right", "secondary")
        export_btn.clicked.connect(self._export)
        import_btn = AppButton("Import", "folder", "secondary")
        import_btn.clicked.connect(self._import)
        bak_row = QHBoxLayout()
        bak_row.setSpacing(10)
        bak_row.addLayout(bak_text, 1)
        bak_row.addWidget(export_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        bak_row.addWidget(import_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.root.addWidget(section_label("Backup"))
        self.root.addWidget(card(bak_row, (24, 16, 24, 16)))

        self.admin_panel = AdminPanel(window.settings.update_repo)
        self.admin_panel.repo_saved.connect(window.set_update_repo)
        self.root.addWidget(self.admin_panel)
        self.root.addStretch()

    def _refresh_update(self) -> None:
        state, version, _url = self.window.update_state
        busy = state == "checking"
        self.update_check_button.setEnabled(not busy)
        self.update_download_button.setVisible(state == "newer")
        if state == "newer":
            text = f"Version {version} is available."
        elif state == "current":
            text = f"You are up to date (v{__version__})."
        elif state == "checking":
            text = "Checking..."
        elif state == "error":
            text = "Could not check for updates."
        else:
            text = f"Version v{__version__}"
        self.update_status.setText(text)

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export settings", str(Path.home() / "rsg-localhost-settings.json"), "JSON (*.json)"
        )
        if path:
            self.window.export_settings(path)

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import settings", str(Path.home()), "JSON (*.json)")
        if path:
            self.window.import_settings(path)

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
