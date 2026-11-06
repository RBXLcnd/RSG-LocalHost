from __future__ import annotations

from pathlib import Path

import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMenu, QVBoxLayout, QWidget

from app.core.config import MAX_PROFILES, ROOT_DIR
from app.core.discord_status import NAME_MAX, validate_name
from app.pages.base import Page, card, divider, section_label
from app.widgets.buttons import AppButton
from app.widgets.fields import FormField
from app.widgets.help import with_help
from app.widgets.toggle import ToggleSwitch


TEAMTEST_PORT_HELP = (
    "<b>TeamTest port</b><br>"
    "The local UDP port Studio listens on so other players can join your server. "
    "It must match the port set in your tunnel (protocol UDP). "
    "Leave it at 55555 unless another program on your PC already uses it."
)


def validate_hours(value: str) -> str | None:
    try:
        ok = float(value.replace(",", ".")) > 0
    except ValueError:
        return "Number of hours"
    return None if ok else "Must be above 0"


def validate_user_id(value: str) -> str | None:
    if not (value.isascii() and value.isdigit()):
        return "Numbers only"
    if int(value) == 0:
        return "Must be greater than 0"
    return None


class CreatePage(Page):
    SCROLL = True  # the 24/7 section makes the page taller than a small window

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        actions = QHBoxLayout()
        self.profiles_button = AppButton("Profiles", "user", "secondary")
        self.profiles_button.clicked.connect(self._show_profiles)
        actions.addWidget(self.profiles_button)
        back = AppButton("Back", "back", "ghost")
        back.clicked.connect(lambda: window.navigate("overview"))
        actions.addWidget(back)
        self.add_header(
            "Create session",
            "Launch a local Studio server. Other clients can connect locally or through a tunnel.",
            actions,
            eyebrow="Host",
        )

        form = QVBoxLayout()
        form.setSpacing(14)
        self.user_id = FormField(
            "User ID",
            window.settings.user_id,
            "Creator ID used to authenticate the local session.",
            icon="user",
            validator=validate_user_id,
        )
        self.test_button = AppButton("Test", "network", "secondary")
        self.test_button.setToolTip("Check that the tunnel address answers")
        self.test_button.clicked.connect(self._test_tunnel)
        self.tunnel = FormField(
            "Tunnel address",
            window.settings.host_tunnel,
            "Optional. Format host:port, e.g. your.tunnel.gg:1234.",
            icon="globe",
            action=self.test_button,
        )
        self.port = FormField(
            "TeamTest port",
            window.settings.server_port,
            "Local port the Studio server will listen on.",
            icon="network",
            validator=lambda v: None if v.isdigit() and 1 <= int(v) <= 65535 else "Invalid port",
            help_text=TEAMTEST_PORT_HELP,
        )
        browse = AppButton("Choose map", "folder", "secondary")
        browse.clicked.connect(self._browse_place)
        self.recent_button = AppButton("Recent", "clock", "secondary")
        self.recent_button.clicked.connect(self._show_recent_maps)
        map_actions = QWidget()
        map_row = QHBoxLayout(map_actions)
        map_row.setContentsMargins(0, 0, 0, 0)
        map_row.setSpacing(8)
        map_row.addWidget(self.recent_button)
        map_row.addWidget(browse)
        self.place_path = FormField(
            "Map file",
            window.settings.place_path,
            "Local .rbxl or .rbxlx file. You can also drop it anywhere in this window.",
            icon="folder",
            validator=self._validate_place_path,
            action=map_actions,
        )
        form.addWidget(self._build_account_row(window))
        form.addWidget(divider())
        form.addWidget(self.user_id)
        form.addWidget(self.tunnel)
        form.addWidget(self.port)
        form.addWidget(self.place_path)
        self.auto_toggle = None
        if window.settings.auto_feature_enabled:
            form.addWidget(divider())
            form.addLayout(self._build_auto_section(window))
        form.addStretch(1)  # spare height stays empty instead of stretching the fields

        # ---- right: live summary + launch ----
        summary = QVBoxLayout()
        summary.setSpacing(10)
        summary.addWidget(section_label("Summary", "create_summary"))
        self._summary: dict[str, QLabel] = {}
        for key in ("User ID", "Tunnel", "Port", "Map"):
            name = QLabel(key)
            name.setObjectName("metricLabel")
            value = QLabel("-")
            value.setObjectName("pathLabel")
            value.setWordWrap(True)
            summary.addWidget(name)
            summary.addWidget(value)
            self._summary[key] = value
        summary.addStretch()
        summary.addWidget(divider())
        summary.addSpacing(4)
        create = AppButton("Launch server", "play", "primary")
        create.setMinimumHeight(42)
        create.clicked.connect(self._create)
        summary.addWidget(create)

        for field, key in (
            (self.user_id, "User ID"),
            (self.tunnel, "Tunnel"),
            (self.port, "Port"),
            (self.place_path, "Map"),
        ):
            field.edit.textChanged.connect(lambda _=None: self._refresh_summary())
        self._refresh_summary()

        body = QHBoxLayout()
        body.setSpacing(18)
        body.addWidget(card(form, (24, 22, 24, 18)), 5)
        side = card(summary, (20, 18, 20, 18))
        side.setMinimumWidth(240)
        body.addWidget(side, 2)
        self.root.addLayout(body, 1)

    # ---- Discord account (required to launch) ----
    def _build_account_row(self, window) -> QWidget:
        text = QVBoxLayout()
        text.setSpacing(3)
        title = QLabel("Discord account")
        title.setObjectName("fieldLabel")
        self.account_status = QLabel("")
        self.account_status.setObjectName("fieldHint")
        self.account_status.setWordWrap(True)
        text.addWidget(with_help(title, "create_account"))
        text.addWidget(self.account_status)
        self.account_button = AppButton("", "user", "secondary")
        self.account_button.clicked.connect(self._on_account_clicked)
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(18)
        row.addLayout(text, 1)
        row.addWidget(self.account_button, 0, Qt.AlignmentFlag.AlignVCenter)
        window.account_changed.connect(self.refresh_account)
        self.refresh_account()
        return row_widget

    def refresh_account(self) -> None:
        if not shiboken6.isValid(self):  # page was rebuilt by navigate(); this copy is gone
            return
        window = self.window
        if window.is_logging_in():
            self.account_status.setText("Checking your key\u2026")
            self.account_button.setText("Please wait")
        elif window.is_signed_in():
            name = window.settings.discord_username or "your account"
            self.account_status.setText(f"Signed in as {name}. Your server is listed under this account.")
            self.account_button.setText("Sign out")
        else:
            self.account_status.setText("Sign in with Discord to create a server: run /host-login in the Discord server and paste your key.")
            self.account_button.setText("Sign in with Discord")

    def _on_account_clicked(self) -> None:
        if self.window.is_logging_in():
            return
        elif self.window.is_signed_in():
            self.window.discord_logout()
        else:
            self.window.discord_login()

    # ---- 24/7 auto-cycle ----
    def _build_auto_section(self, window) -> QVBoxLayout:
        settings = window.settings
        box = QVBoxLayout()
        box.setSpacing(12)

        text = QVBoxLayout()
        text.setSpacing(3)
        title = QLabel("24/7 auto-cycle")
        title.setObjectName("fieldLabel")
        hint = QLabel(
            "Keeps the server online, pauses it, then brings it back with the next map. "
            "Updates the Discord /server-status panel. Pressing Stop ends the cycle."
        )
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        text.addWidget(with_help(title, "create_auto"))
        text.addWidget(hint)
        self.auto_toggle = ToggleSwitch(settings.auto_enabled)
        header = QHBoxLayout()
        header.setSpacing(18)
        header.addLayout(text, 1)
        header.addWidget(self.auto_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        box.addLayout(header)

        self.auto_on = FormField(
            "Hours online", settings.auto_on_hours, "", icon="clock", validator=validate_hours, stacked=True
        )
        self.auto_off = FormField(
            "Hours paused", settings.auto_off_hours, "", icon="clock", validator=validate_hours, stacked=True
        )
        self.rotation_button = AppButton("", "folder", "secondary")
        self.rotation_button.clicked.connect(self._show_rotation)
        self._refresh_rotation_label()
        rotation_box = QVBoxLayout()
        rotation_box.setSpacing(8)
        rotation_label = QLabel("Map rotation")
        rotation_label.setObjectName("fieldLabel")
        rotation_box.addWidget(with_help(rotation_label, "create_rotation"))
        rotation_box.addWidget(self.rotation_button)
        rotation_box.addStretch()

        self.server_name = FormField(
            "Server name",
            settings.server_name,
            f"Shown in the Discord /server-status list, together with your tunnel. 3-{NAME_MAX} characters.",
            placeholder="e.g. Joao's Condo",
            icon="user",
            validator=validate_name,
        )

        private_text = QVBoxLayout()
        private_text.setSpacing(3)
        private_title = QLabel("Private server")
        private_title.setObjectName("fieldLabel")
        private_hint = QLabel(
            "Hidden from the Discord /server-status list. Nothing about this server is sent to Discord. "
            "Share your tunnel address only with the people you want."
        )
        private_hint.setObjectName("fieldHint")
        private_hint.setWordWrap(True)
        private_text.addWidget(with_help(private_title, "create_private"))
        private_text.addWidget(private_hint)
        self.private_toggle = ToggleSwitch(settings.auto_private)
        private_row = QHBoxLayout()
        private_row.setSpacing(18)
        private_row.addLayout(private_text, 1)
        private_row.addWidget(self.private_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        self.private_toggle.toggled.connect(self._on_private_toggled)

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self.auto_on, 1)
        row.addWidget(self.auto_off, 1)
        row.addLayout(rotation_box, 1)
        row.setContentsMargins(0, 0, 0, 0)
        hours = QWidget()
        hours.setLayout(row)
        self.auto_fields = QWidget()
        auto_col = QVBoxLayout(self.auto_fields)
        auto_col.setContentsMargins(0, 0, 0, 0)
        auto_col.setSpacing(12)
        auto_col.addLayout(private_row)
        auto_col.addWidget(self.server_name)
        auto_col.addWidget(hours)
        box.addWidget(self.auto_fields)

        self.auto_toggle.toggled.connect(self._on_auto_toggled)
        self._on_auto_toggled(settings.auto_enabled, save=False)
        self._on_private_toggled(settings.auto_private, save=False)
        return box

    def _on_auto_toggled(self, enabled: bool, save: bool = True) -> None:
        self.auto_fields.setEnabled(enabled)
        if save:
            self.window.set_auto_settings(auto_enabled=enabled)

    def _on_private_toggled(self, private: bool, save: bool = True) -> None:
        self.server_name.setVisible(not private)  # no name needed: it is never published
        if save:
            self.window.set_auto_settings(auto_private=private)

    def _refresh_rotation_label(self) -> None:
        count = len(self.window.settings.auto_maps)
        self.rotation_button.setText(f"{count} maps in rotation" if count else "Not set (uses Map file)")

    def _rotation_menu(self) -> QMenu:
        menu = QMenu(self)
        chosen = list(self.window.settings.auto_maps)
        known = {os_key(p) for p in chosen}
        candidates = list(chosen)
        for path in [self.place_path.value(), *self.window.settings.recent_maps]:
            if path and os_key(path) not in known:
                known.add(os_key(path))
                candidates.append(path)
        for path in candidates:
            file = Path(path)
            action = menu.addAction(f"{file.name}  \u00b7  {file.parent.name}" if file.parent.name else file.name)
            action.setToolTip(path)
            action.setCheckable(True)
            action.setChecked(path in chosen)
            action.triggered.connect(lambda checked=False, value=path: self._toggle_rotation_map(value))
        if candidates:
            menu.addSeparator()
        add = menu.addAction("Add map files\u2026")
        add.triggered.connect(self._add_rotation_maps)
        if chosen:
            clear = menu.addAction("Clear rotation")
            clear.triggered.connect(lambda: self._set_rotation([]))
        return menu

    def _show_rotation(self) -> None:
        self._rotation_menu().exec(self.rotation_button.mapToGlobal(self.rotation_button.rect().bottomLeft()))

    def _toggle_rotation_map(self, path: str) -> None:
        maps = list(self.window.settings.auto_maps)
        if path in maps:
            maps.remove(path)
        else:
            maps.append(path)
        self._set_rotation(maps)

    def _add_rotation_maps(self) -> None:
        start = str(Path(self.place_path.value()).parent) if self.place_path.value() else str(ROOT_DIR)
        paths, _ = QFileDialog.getOpenFileNames(self, "Add maps to the rotation", start, "Place (*.rbxl *.rbxlx)")
        if not paths:
            return
        maps = list(self.window.settings.auto_maps)
        for path in paths:
            if path not in maps:
                maps.append(path)
        self._set_rotation(maps)

    def _set_rotation(self, maps: list[str]) -> None:
        self.window.set_auto_settings(auto_maps=maps, auto_map_index=0)
        self._refresh_rotation_label()

    def _test_tunnel(self) -> None:
        self.window.test_host_tunnel(self.tunnel.value(), self.port.value(), self.test_button)

    def _refresh_summary(self) -> None:
        path = self.place_path.value()
        values = {
            "User ID": self.user_id.value(),
            "Tunnel": self.tunnel.value(),
            "Port": self.port.value(),
            "Map": Path(path).name if path else "",
        }
        for key, label in self._summary.items():
            label.setText(values[key] or "-")

    def _create(self) -> None:
        if not self.window.is_signed_in():
            self.window.toast("Sign in with Discord to create a server.", "warning")
            return
        reason = self.window.server_block_reason()
        if reason:
            self.window.toast(reason, "warning")
            return
        valid = self.user_id.validate() and self.port.validate() and self.place_path.validate()
        if not self.user_id.value() or not self.port.value():
            self.window.toast("User ID and port are required.", "warning")
            return
        if not valid:
            self.window.toast("Fix the highlighted fields.", "error")
            return
        args = (self.user_id.value(), self.tunnel.value(), self.port.value(), self.place_path.value())
        if self.auto_toggle is not None and self.auto_toggle.isChecked():
            if not (self.auto_on.validate() and self.auto_off.validate()) or not self.auto_on.value() or not self.auto_off.value():
                self.window.toast("24/7: set the hours online and paused.", "error")
                return
            if not self.window.settings.auto_maps and not args[3]:
                self.window.toast("24/7: choose a Map file or add maps to the rotation.", "warning")
                return
            private = self.private_toggle.isChecked()
            if not private and not self.server_name.validate():
                self.window.toast("24/7: choose a server name (3-24 characters).", "error")
                return
            if not private and not self.tunnel.value().strip():
                self.window.toast("24/7: fill in your tunnel address so players can find the server.", "warning")
                return
            self.window.set_auto_settings(
                auto_on_hours=self.auto_on.value().replace(",", "."),
                auto_off_hours=self.auto_off.value().replace(",", "."),
                server_name=self.server_name.value().strip() if not private else self.window.settings.server_name,
                auto_private=private,
            )
            self.window.start_auto_host(*args)
            return
        self.window.create_session(*args)

    def set_place(self, path: str) -> None:
        """Used by drag & drop: fill the map field without launching anything."""
        self.place_path.edit.setText(path)
        self.place_path.validate()

    # ---- profiles ----
    def _profiles_menu(self) -> QMenu:
        """Saved profiles: click to load. Also save the current form or delete one."""
        menu = QMenu(self)
        profiles = self.window.settings.profiles
        for profile in profiles:
            action = menu.addAction(profile["name"])
            details = [profile["host_tunnel"], f"port {profile['server_port']}" if profile["server_port"] else "",
                       Path(profile["place_path"]).name if profile["place_path"] else ""]
            action.setToolTip("  ·  ".join(d for d in details if d))
            action.triggered.connect(lambda checked=False, value=profile: self.load_profile(value))
        if not profiles:
            empty = menu.addAction("No profiles yet")
            empty.setEnabled(False)
        menu.addSeparator()
        save = menu.addAction("Save current as profile\u2026")
        save.triggered.connect(self._save_profile)
        if profiles:
            delete_menu = menu.addMenu("Delete profile")
            for profile in profiles:
                item = delete_menu.addAction(profile["name"])
                item.triggered.connect(lambda checked=False, value=profile["name"]: self.window.delete_profile(value))
        return menu

    def _show_profiles(self) -> None:
        menu = self._profiles_menu()
        menu.exec(self.profiles_button.mapToGlobal(self.profiles_button.rect().bottomLeft()))

    def load_profile(self, profile: dict[str, str]) -> None:
        self.user_id.edit.setText(profile["user_id"])
        self.tunnel.edit.setText(profile["host_tunnel"])
        self.port.edit.setText(profile["server_port"])
        self.place_path.edit.setText(profile["place_path"])
        if profile["place_path"]:
            self.place_path.validate()
        self.window.toast(f"Profile \u201c{profile['name']}\u201d loaded.", "success")

    def _save_profile(self) -> None:
        if not self.user_id.value() and not self.tunnel.value() and not self.place_path.value():
            self.window.toast("Fill in the form before saving a profile.", "warning")
            return
        path = self.place_path.value()
        suggestion = Path(path).stem if path else ""
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text=suggestion)
        name = name.strip()
        if not ok or not name:
            return
        saved = self.window.save_profile(
            name, self.user_id.value(), self.tunnel.value(), self.port.value(), self.place_path.value()
        )
        if saved:
            self.window.toast(f"Profile \u201c{name[:32]}\u201d saved.", "success")
        else:
            self.window.toast(f"Profile limit reached ({MAX_PROFILES}). Delete one first.", "warning")

    def _recent_map_menu(self) -> QMenu:
        """Menu of the last maps used. Files that no longer exist are listed but disabled."""
        menu = QMenu(self)
        maps = self.window.settings.recent_maps
        for path in maps:
            file = Path(path)
            exists = file.is_file()
            parent = file.parent.name
            label = f"{file.name}  ·  {parent}" if parent else file.name
            action = menu.addAction(label if exists else f"{label}  (not found)")
            action.setToolTip(path)
            action.setEnabled(exists)
            action.triggered.connect(lambda checked=False, value=path: self.set_place(value))
        if maps:
            menu.addSeparator()
            clear = menu.addAction("Clear list")
            clear.triggered.connect(self.window.clear_recent_maps)
        else:
            empty = menu.addAction("No recent maps yet")
            empty.setEnabled(False)
        return menu

    def _show_recent_maps(self) -> None:
        menu = self._recent_map_menu()
        menu.exec(self.recent_button.mapToGlobal(self.recent_button.rect().bottomLeft()))

    def _browse_place(self) -> None:
        current = Path(self.place_path.value()) if self.place_path.value() else ROOT_DIR
        if not current.is_absolute():
            current = ROOT_DIR / current
        condo_dir = ROOT_DIR.parent
        if current.is_file():
            start_dir = str(current.parent)
        elif condo_dir.is_dir():
            start_dir = str(condo_dir)
        else:
            start_dir = str(ROOT_DIR)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose map",
            start_dir,
            "Place (*.rbxl *.rbxlx);;All files (*.*)",
        )
        if path:
            self.place_path.edit.setText(path)
            self._create()

    def _validate_place_path(self, value: str) -> str | None:
        path = Path(value)
        if not path.is_absolute():
            path = ROOT_DIR / path
        if not path.is_file():
            return "File not found"
        if path.suffix.lower() not in {".rbxl", ".rbxlx"}:
            return "Use .rbxl/.rbxlx"
        return None


def os_key(path: str) -> str:
    import os

    return os.path.normcase(os.path.normpath(path))
