from __future__ import annotations

import ctypes
import os
from datetime import datetime
from pathlib import Path
from ctypes import wintypes

import shiboken6
from PySide6.QtCore import QEasingCurve, QEvent, QMetaObject, QPoint, QPropertyAnimation, QUrl, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QScrollArea,
    QFileDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QInputDialog,
    QDialog,
    QMessageBox,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from app import __app_name__, __version__
from app.core.config import (
    MAX_HISTORY,
    MAX_PROFILES,
    MAX_RECENT_MAPS,
    MAX_RECENT_TUNNELS,
    WINDOW_H,
    WINDOW_MIN_H,
    WINDOW_MIN_W,
    WINDOW_W,
)
from app.core import discord_status, i18n
from app.core.i18n import tr
from app.core.player_count import PlayerCountServer
from app.core import updates
from app.core.api import normalize_key
from app.core.auth import KeyCheck
from app.core.autopilot import AutoConfig, AutoPilot
from app.core.uptime import format_uptime
from app.core.diagnostics import build_diagnostics
from app.core.dnd import dropped_files, place_files
from app.core.invite import build_invite
from app.core.ping import PingMonitor
from app.core.preflight import DNS, OK, RELAY, SILENT, PreflightResult, TunnelCheck, host_message
from app.core.sound import play_ready
from app.core.proxy import proxy
from app.core.qr import qr_matrix
from app.core.settings import AppSettings, SettingsStore
from app.core.studio import (
    get_studio_path,
    has_running_processes,
    launch_client,
    open_place_file,
    stop_all_roblox_processes,
    stop_roblox_processes,
)
from app.core.tasks import HostSessionWorker, JoinSessionWorker
from app.widgets.buttons import flash_copied
from app.pages.create import CreatePage
from app.pages.join import JoinPage, validate_tunnel
from app.pages.overview import OverviewPage
from app.pages.session import SessionPage
from app.pages.settings import SettingsPage
from app.pages.support import SupportPage
from app.ui.footer import StatusStrip
from app.ui.welcome import WelcomeDialog
from app.core import backup
from app.styles import palette
from app.styles.theme import refresh_stylesheet
from app.widgets import theme_picker
from app.ui.title_bar import TitleBar
from app.widgets import brand
from app.widgets.brand import GlowBackground, make_app_icon
from app.widgets.drop_overlay import DropOverlay
from app.widgets.qr_overlay import QrOverlay
from app.widgets.toast import Toast


CHECK_TIMEOUT_MS = 12000  # hard cap on the pre-join tunnel test (DNS can hang)
RESTART_POLL_MS = 100  # how often a restart checks that the old server worker has finished
RESTART_MAX_POLLS = 50  # ...for at most 5 s
RESTART_GRACE_MS = 1500  # extra pause so Windows frees the UDP port and the runtime map file


class MainWindow(QMainWindow):
    BORDER = 8

    auto_log = Signal(str, str)  # thread-safe route for 24/7 / Discord log lines
    update_state_changed = Signal()  # update check started / finished (the Settings page listens)
    account_changed = Signal()   # Discord sign-in state changed (login started / finished / signed out)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RSG LocalHost")
        self.resize(WINDOW_W, WINDOW_H)
        self.setMinimumSize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)

        self.store = SettingsStore()
        self.settings: AppSettings = self.store.load()
        self.studio_path = self._initial_studio_path()
        self.mode: str | None = None
        self.running = False
        self.current_key = "overview"
        self.active_modes: set[str] = set()
        self.session_pages: dict[str, SessionPage] = {}
        self.host_session_guids: tuple[str, str] | None = None
        self.workers: dict[str, object] = {}
        self.worker_threads: dict[str, QThread] = {}
        self._toast: Toast | None = None
        self._page_anim: QPropertyAnimation | None = None

        self.ping_monitor: PingMonitor | None = None
        self._join_target: tuple[str, int] | None = None
        self._tunnel_check: TunnelCheck | None = None
        self._join_pending: tuple[str, int, str, str] | None = None  # host, port, raw, studio
        self._check_timeout = QTimer(self)
        self._check_timeout.setSingleShot(True)
        self._check_timeout.timeout.connect(self._on_check_timeout)
        # Session history: wall-clock start of each running session, filled in when it stops.
        self._session_started: dict[str, tuple[str, str, str]] = {}  # mode -> (started, map, tunnel)
        self._peak_players = 0  # most players reported during the current hosted session
        # Restart of the host session (parameters of the running server, so a restart repeats it exactly).
        self._host_params: tuple[str, str, str, str] | None = None
        self._restart_pending = False
        self._restart_polls = 0
        # Host-side tunnel test: independent from the join check above.
        self._host_test: TunnelCheck | None = None
        self._host_test_button = None
        self._host_test_label = ""
        self._host_test_port = ""
        self._host_test_timeout = QTimer(self)
        self._host_test_timeout.setSingleShot(True)
        self._host_test_timeout.timeout.connect(lambda: self._on_host_test_done(PreflightResult(SILENT)))
        # 24/7 cycle + Discord status
        self._auto_internal_stop = False  # True while the cycle itself stops the server (pause / relaunch)
        self.autopilot = AutoPilot(self)
        self.autopilot.state_changed.connect(self._on_auto_state)
        self.autopilot.map_index_changed.connect(self._save_auto_map_index)
        self.auto_log.connect(self._write_auto_log)
        # Discord account (required to create a server)
        self._key_check: KeyCheck | None = None
        discord_status.set_session(self.settings.discord_key)
        # Update check (GitHub latest release): once at startup, then every few hours
        self._update_check: updates.UpdateCheck | None = None
        self.update_state: tuple[str, str, str] = ("idle", "", "")  # (state, version, url)
        self._update_notified = ""
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(6 * 3600 * 1000)
        self._update_timer.timeout.connect(lambda: self.check_for_updates(manual=False))
        self._update_timer.start()
        QTimer.singleShot(6000, lambda: self.check_for_updates(manual=False))
        # Player count reported by the game (HTTP on 127.0.0.1) -> Discord panel
        self.player_count = PlayerCountServer(self)
        self.player_count.count_changed.connect(self._on_player_count)
        self.player_count.start()
        self.setAcceptDrops(True)
        self._drag_active = False
        self._force_quit = False
        self._tray_hint_shown = False
        self.tray: QSystemTrayIcon | None = None
        self.setWindowIcon(make_app_icon())
        self._build_shell()
        self._build_tray()
        self.drop_overlay = DropOverlay(self)
        self.qr_overlay = QrOverlay(self, lambda value, source: self.copy_to_clipboard(value, "Tunnel copied.", source))
        # App-level filter: line edits / the console accept drops themselves and
        # would otherwise swallow a file dragged over them.
        QApplication.instance().installEventFilter(self)
        self.navigate("overview")
        self.update_session_status()

    def _build_shell(self) -> None:
        root = GlowBackground()
        self._background = root
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = TitleBar()
        self.title_bar.language_requested.connect(self.toggle_language)
        self.title_bar.update_requested.connect(self.open_update_page)
        self.title_bar.set_language(i18n.get_language())
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self.toggle_maximize)
        self.title_bar.close_requested.connect(self.close)
        outer.addWidget(self.title_bar)

        self.title_bar.nav.navigate.connect(self.navigate)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        self.footer = StatusStrip()
        outer.addWidget(self.footer)

    # ---------- system tray ----------

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(make_app_icon(), self)
        # hiding the window to the tray must not end the app
        QApplication.setQuitOnLastWindowClosed(False)

        menu = QMenu()
        open_action = QAction(menu)
        i18n.register_action(open_action, "Open RSG LocalHost")
        open_action.triggered.connect(self.restore_from_tray)
        font = open_action.font()
        font.setBold(True)
        open_action.setFont(font)
        self.tray_stop_action = QAction(menu)
        i18n.register_action(self.tray_stop_action, "Stop all sessions")
        self.tray_stop_action.triggered.connect(self.stop_everything)
        quit_action = QAction(menu)
        i18n.register_action(quit_action, "Quit")
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(open_action)
        menu.addAction(self.tray_stop_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self._tray_menu = menu  # keep alive; the tray does not take ownership
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.messageClicked.connect(self.restore_from_tray)
        self.tray.show()
        self._refresh_tray(False, "Ready")

    def _refresh_tray(self, active: bool, text: str) -> None:
        if not self.tray:
            return
        self.tray.setIcon(make_app_icon(active))
        self.tray.setToolTip(f"RSG LocalHost - {text}")
        self.tray_stop_action.setEnabled(active)

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.restore_from_tray()

    def restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def hide_to_tray(self) -> None:
        self.hide()
        if self.tray and not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray.showMessage(
                "RSG LocalHost",
                "Still running in the tray. Your session stays active. Click the icon to reopen.",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )

    def quit_app(self) -> None:
        """Tray > Quit: same as closing for real, but confirm first if a session is running."""
        if self.session_active():
            reply = QMessageBox.question(
                self,
                "Quit RSG LocalHost",
                "Stop active sessions and quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._force_quit = True
        self.close()

    def _ask_close_action(self) -> str:
        """Closing the window while a session runs: 'tray', 'quit' or 'cancel'."""
        box = QMessageBox(self)
        box.setWindowTitle("Session still running")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("A session is still running.")
        box.setInformativeText(
            "Minimize to the tray to keep it running, or quit and stop everything."
        )
        tray_btn = box.addButton("Minimize to tray", QMessageBox.ButtonRole.AcceptRole)
        quit_btn = box.addButton("Quit and stop", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(tray_btn)
        box.setEscapeButton(cancel_btn)
        box.exec()
        clicked = box.clickedButton()
        if clicked is tray_btn:
            return "tray"
        if clicked is quit_btn:
            return "quit"
        return "cancel"

    _DRAG_EVENTS = (
        QEvent.Type.DragEnter,
        QEvent.Type.DragMove,
        QEvent.Type.DragLeave,
        QEvent.Type.Drop,
    )

    def eventFilter(self, obj, event) -> bool:
        etype = event.type()
        if etype not in self._DRAG_EVENTS or not isinstance(obj, QWidget):
            return False
        if obj is not self and not self.isAncestorOf(obj):
            return False

        if etype == QEvent.Type.DragLeave:
            self._drag_active = False
            QTimer.singleShot(60, self._hide_drop_overlay)  # ignore leave/enter between child widgets
            return False

        files = dropped_files(event.mimeData())
        if not files:
            return False  # plain text drags etc. keep their normal behaviour

        if etype == QEvent.Type.Drop:
            self._drag_active = False
            self.drop_overlay.dismiss()
            event.acceptProposedAction()
            QTimer.singleShot(0, lambda: self._handle_dropped(files))
            return True

        maps = place_files(files)
        self._drag_active = True
        self.drop_overlay.present(bool(maps), maps[0].name if maps else "")
        event.acceptProposedAction()
        return True

    def _hide_drop_overlay(self) -> None:
        if not self._drag_active:
            self.drop_overlay.dismiss()

    def _handle_dropped(self, files) -> None:
        maps = place_files(files)
        if not maps:
            self.toast("Only .rbxl / .rbxlx maps can be dropped.", "error")
            return
        if "create" in self.session_pages:
            self.toast("A server is already running. Stop it to change the map.", "warning")
            return
        if not isinstance(self.stack.currentWidget(), CreatePage):
            self.navigate("create")
        page = self.stack.currentWidget()
        if not isinstance(page, CreatePage):
            return
        page.set_place(str(maps[0]))
        extra = f" (using the first of {len(maps)})" if len(maps) > 1 else ""
        self.toast(f"Map loaded: {maps[0].name}{extra}. Press Launch server.", "success")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._enable_windows_backdrop()

    def _initial_studio_path(self) -> str:
        saved = self.settings.studio_path
        if saved and Path(saved).is_file():
            return saved
        path = get_studio_path()
        if path:
            self.settings = self.store.update(self.settings, studio_path=path)
        return path

    def navigate(self, key: str) -> None:
        if self._tunnel_check is not None:
            self._cancel_tunnel_check()
        if key == "create" and key in self.session_pages:
            self._show_session_page(key)
            return
        if key == "join" and key in self.session_pages:
            self._show_session_page(key)
            return

        self.current_key = key
        self.title_bar.nav.set_current(key)
        builders = {
            "overview": lambda: OverviewPage(self),
            "create": lambda: CreatePage(self),
            "join": lambda: JoinPage(self),
            "settings": lambda: SettingsPage(self),
            "support": lambda: SupportPage(self),
        }
        builder = builders.get(key, builders["overview"])
        self._set_page(builder())

    def _set_page(self, page: QWidget) -> None:
        old = self.stack.currentWidget()
        if self.stack.indexOf(page) == -1:
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        self._animate_page_in(page)
        if old and old not in self.session_pages.values():
            self.stack.removeWidget(old)
            old.deleteLater()

    def _animate_page_in(self, page: QWidget) -> None:
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", page)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _clear() -> None:
            if shiboken6.isValid(page) and page.graphicsEffect() is effect:
                page.setGraphicsEffect(None)

        anim.finished.connect(_clear)
        self._page_anim = anim  # keep a reference so it isn't collected mid-flight
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _show_session_page(self, nav_key: str) -> None:
        page = self.session_pages.get(nav_key)
        if not page:
            return
        self.current_key = nav_key
        self.title_bar.nav.set_current(nav_key)
        self._set_page(page)

    def update_session_status(self) -> None:
        active = self.session_active()
        self.footer.set_studio(Path(self.studio_path).name if self.studio_path else "")
        if active:
            if {"create", "join"}.issubset(self.active_modes):
                text = "Server + proxy active"
            elif "create" in self.active_modes:
                text = "Server live"
            elif "join" in self.active_modes:
                text = "Proxy active"
            else:
                text = "Active"
            self.footer.set_status(text, "#2ee6a6", True)
            self.title_bar.nav.set_session(True, text, self.mode, self.active_modes)
            self._refresh_tray(True, text)
        elif self.studio_path and Path(self.studio_path).is_file():
            self.footer.set_status("Ready", "#5d7099")
            self.title_bar.nav.set_session(False, mode=self.mode)
            self._refresh_tray(False, "Ready")
        else:
            self.footer.set_status("Studio not configured", "#f5b942")
            self.title_bar.nav.set_session(False, mode=self.mode)
            self._refresh_tray(False, "Studio not configured")

    def session_active(self) -> bool:
        # an armed 24/7 cycle counts even while it is paused, so it can be stopped and quitting asks first
        return bool(self.active_modes) or proxy.is_running or has_running_processes() or self.autopilot.active

    def server_block_reason(self) -> str:
        """Why a new server cannot be created right now ("" if it can). Only one server may exist."""
        if "create" in self.session_pages:
            return "A server already exists. Stop it before creating another."
        if self.autopilot.active:
            until = self.autopilot.next_switch_at
            when = f" until {until.astimezone():%H:%M}" if until else ""
            return f"The 24/7 cycle is active (paused{when}). Use \u201cStop all sessions\u201d to end it first."
        return ""

    def ensure_studio_path(self) -> str:
        if self.studio_path and Path(self.studio_path).is_file():
            return self.studio_path
        path = get_studio_path()
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select RobloxStudioBeta.exe",
                "",
                "Studio (RobloxStudioBeta.exe);;Executable (*.exe);;All files (*.*)",
            )
        if path and Path(path).is_file():
            self.set_studio_path(path, navigate=False)
            return path
        return ""

    def set_studio_path(self, path: str, navigate: bool = True) -> None:
        candidate = Path(path)
        if not candidate.is_file():
            self.toast("Selected Studio path does not exist.", "error")
            return
        if candidate.name.lower() != "robloxstudiobeta.exe":
            self.toast("Choose RobloxStudioBeta.exe, not another executable.", "error")
            return
        self.studio_path = str(candidate)
        self.settings = self.store.update(self.settings, studio_path=str(candidate))
        self.toast("Studio path saved.", "success")
        self.update_session_status()
        if navigate:
            self.navigate("settings")

    def clear_studio_path(self) -> None:
        self.studio_path = ""
        self.settings = self.store.update(self.settings, studio_path="")
        self.toast("Studio path cleared.", "info")
        self.update_session_status()
        self.navigate("settings")

    def auto_detect_studio(self) -> None:
        path = get_studio_path()
        if path:
            self.set_studio_path(path)
        else:
            self.toast("Studio not found. Use Browse instead.", "warning")

    def create_session(self, user_id: str, tunnel: str, port: str, place_path: str = "") -> None:
        if not self.is_signed_in():
            self.toast("Sign in with Discord to create a server.", "warning")
            return
        if "create" in self.session_pages:
            self.toast("Server is already active.", "warning")
            return
        studio = self.ensure_studio_path()
        if not studio:
            self.toast("Cannot locate RobloxStudioBeta.exe.", "error")
            return
        self.settings = self.store.update(
            self.settings,
            user_id=user_id,
            host_tunnel=tunnel,
            server_port=port,
            place_path=place_path,
        )
        if place_path:
            self.remember_map(place_path)
        self._host_params = (user_id, tunnel, port, place_path)
        self._session_started["create"] = (self._now_iso(), Path(place_path).name if place_path else "", tunnel)
        self._peak_players = 0
        self.mode = "create"
        self.running = True
        self.active_modes.add("create")
        info = [
            ("Mode", "Server (host)"),
            ("User ID", user_id),
            ("Port", port),
            ("Tunnel", tunnel or "-"),
            ("Map", Path(place_path).name if place_path else "-"),
            ("Live for", "-"),
            ("24/7", self._auto_text),
        ]
        page = SessionPage(self, "Server", "Local Studio server.", info, lambda: self.stop_session("create"))
        self.session_pages["create"] = page
        page.went_live.connect(self._on_server_ready)
        page.set_loading_visible(True)
        page.set_console_visible(False)
        page.add_restart(self.restart_host_session)
        self._set_page(page)
        if tunnel:
            page.add_copy_tunnel(
                lambda source, value=tunnel: self.copy_to_clipboard(value, "Tunnel copied.", source)
            )
            page.add_copy_invite(
                lambda source, value=tunnel: self.copy_to_clipboard(
                    build_invite(value), "Invite copied. Paste it in Discord.", source, "Copied - paste in Discord"
                )
            )
            page.add_qr(lambda checked=False, value=tunnel: self.show_tunnel_qr(value))
            page.add_test_tunnel(
                lambda button, value=tunnel, local=port: self.test_host_tunnel(value, local, button)
            )
        self.title_bar.nav.set_current("create")
        self.update_session_status()

        worker = HostSessionWorker(
            studio,
            user_id,
            port,
            place_path,
        )
        self.host_session_guids = (worker.parent_guid, worker.play_guid)
        worker.log.connect(self._worker_log)
        worker.status.connect(self._worker_status)
        worker.progress.connect(self._worker_progress)
        self._start_worker("create", worker)

    # ---------- Discord account ----------
    # "Signing in" = pasting the private key that /host-login gives in the Discord server.

    def is_signed_in(self) -> bool:
        return bool(self.settings.discord_key)

    def is_logging_in(self) -> bool:
        return self._key_check is not None and self._key_check.isRunning()

    def discord_login(self) -> None:
        if self.is_logging_in():
            return
        text, ok = QInputDialog.getText(
            self,
            "Sign in with Discord",
            "In the Discord server run  /host-login  and paste the key it sends you (only you can see it):",
        )
        if not ok:
            return
        key = normalize_key(text)
        if key is None:
            self.toast("That is not a valid key. Copy it exactly as /host-login shows it.", "error")
            return
        check = KeyCheck(key, self)
        check.result.connect(lambda state, label, key=key: self._on_key_checked(key, state, label))
        check.finished.connect(self.account_changed.emit)
        self._key_check = check
        check.start()
        self.account_changed.emit()

    def _on_key_checked(self, key: str, state: str, label: str) -> None:
        if state == "ok":
            self.settings = self.store.update(self.settings, discord_key=key, discord_username=label)
            discord_status.set_session(key)
            self.toast(f"Signed in{' as ' + label if label else ''}.", "success")
        elif state == "invalid":
            self.toast("That key doesn't work. Run /host-login again and paste the new key.", "error")
        else:
            self.toast("Cannot reach Discord. Check your internet connection and try again.", "error")
        self.account_changed.emit()

    def discord_logout(self) -> None:
        if self.autopilot.active:
            self.toast("Stop the running 24/7 server before signing out.", "warning")
            return
        self.settings = self.store.update(self.settings, discord_key="", discord_username="")
        discord_status.set_session("")
        self.toast("Signed out of this app. Use /host-logout in Discord to also revoke the key.", "info")
        self.account_changed.emit()

    def verify_discord_session(self) -> None:
        """Startup: drop a saved key Discord no longer accepts (offline = keep it)."""
        if not self.settings.discord_key:
            return
        check = KeyCheck(self.settings.discord_key, self)
        check.result.connect(self._on_session_checked)
        self._key_check = check
        check.start()

    def _on_player_count(self, count: int) -> None:
        self._peak_players = max(self._peak_players, count)
        discord_status.set_players(count)
        self.autopilot.refresh_status()

    def shutdown_status(self) -> None:
        """Last chance to tell Discord the server is off: tray quit, Windows logoff/shutdown, any exit path."""
        self.autopilot.disarm()  # pushes "offline" only if the 24/7 cycle was running
        self.player_count.stop()
        discord_status.flush(timeout=4.0)

    def _publish_offline_if_idle(self) -> None:
        """A previous run may have been killed while "online": mark it offline right away."""
        s = self.settings
        if self.autopilot.active or not s.discord_key or not s.server_name:
            return
        discord_status.set_identity(s.server_name, "")  # tunnel stays as the bot already has it
        discord_status.push_status(self.log_auto, online=False)

    def _on_session_checked(self, state: str, label: str) -> None:
        if state == "ok":
            self._publish_offline_if_idle()
        if state == "invalid":
            self.settings = self.store.update(self.settings, discord_key="", discord_username="")
            discord_status.set_session("")
            self.toast("Your Discord key is no longer valid. Run /host-login and sign in again.", "warning")
            self.account_changed.emit()
        elif state == "ok" and label and label != self.settings.discord_username:
            self.settings = self.store.update(self.settings, discord_username=label)
            self.account_changed.emit()

    # ---------- 24/7 cycle + Discord status ----------

    _auto_text = "Off"

    def start_auto_host(self, user_id: str, tunnel: str, port: str, place_path: str) -> None:
        """"Launch server" with the 24/7 switch on: arm the cycle (it launches the first session itself)."""
        reason = self.server_block_reason()
        if reason:
            self.toast(reason, "warning")
            return
        s = self.settings
        try:
            on_hours, off_hours = float(s.auto_on_hours), float(s.auto_off_hours)
            if on_hours <= 0 or off_hours <= 0:
                raise ValueError
        except ValueError:
            self.toast("24/7: hours online / paused must be numbers above 0.", "error")
            return
        # A listing from an earlier public run must not stay up: mark it offline once, then go quiet.
        discord_status.set_private(False)
        if s.auto_private and s.discord_key and s.server_name:
            discord_status.set_identity(s.server_name, tunnel)
            discord_status.push_status(self.log_auto, online=False)
        discord_status.set_private(s.auto_private)
        discord_status.set_identity(s.server_name, tunnel)
        config = AutoConfig(
            user_id=user_id,
            tunnel=tunnel,
            port=port,
            fallback_map=place_path,
            on_hours=on_hours,
            off_hours=off_hours,
            maps=list(s.auto_maps),
        )
        self.autopilot.start(config, s.auto_map_index)

    def ask_auto_feature_if_needed(self) -> None:
        """First launch: the welcome assistant (language, Studio, Discord, 24/7). Older installs skip it."""
        if self.settings.onboarded:
            return
        if self.settings.auto_feature_asked:  # existing user from a version before the assistant
            self.settings = self.store.update(self.settings, onboarded=True)
            return
        dialog = WelcomeDialog(self)
        finished = dialog.exec() == QDialog.DialogCode.Accepted
        enabled = finished and dialog.auto_enabled
        self.settings = self.store.update(
            self.settings, onboarded=True, auto_feature_enabled=enabled, auto_feature_asked=True
        )
        self.update_session_status()
        if self.current_key in ("create", "settings"):
            self.navigate("overview")

    def set_auto_feature(self, enabled: bool) -> bool:
        """Settings switch. Refused while a 24/7 cycle is running (stop it first)."""
        if not enabled and self.autopilot.active:
            self.toast("Stop the running 24/7 cycle first (Stop all sessions).", "warning")
            return False
        self.settings = self.store.update(self.settings, auto_feature_enabled=enabled, auto_feature_asked=True)
        self.toast("24/7 mode enabled." if enabled else "24/7 mode hidden.", "info")
        return True

    def set_auto_settings(self, **values) -> None:
        """Persist 24/7 switches/hours/rotation chosen in the Create page."""
        self.settings = self.store.update(self.settings, **values)

    def _save_auto_map_index(self, index: int) -> None:
        self.settings = self.store.update(self.settings, auto_map_index=index)

    def log_auto(self, message: str, level: str = "info") -> None:
        """Safe from any thread (Discord writes report from a worker thread)."""
        self.auto_log.emit(message, level)

    @Slot(str, str)
    def _write_auto_log(self, message: str, level: str) -> None:
        page = self.session_pages.get("create")
        if page:
            page.append_log(message, level)

    @Slot(str, str)
    def _on_auto_state(self, phase: str, text: str) -> None:
        self._auto_text = text
        page = self.session_pages.get("create")
        if page:
            page.set_info("24/7", text)
        if phase:
            self._refresh_tray(self.session_active(), f"24/7 - {text}")

    def restart_host_session(self) -> None:
        """Stop the running server and launch it again with the same User ID, tunnel, port and map."""
        if self._restart_pending or "create" not in self.session_pages or self._host_params is None:
            return
        reply = QMessageBox.question(
            self,
            "Restart server",
            "Restart the Studio server?\n\nEveryone connected will be disconnected and the map will be reloaded.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._restart_pending = True
        worker = self.workers.get("create")
        if worker and shiboken6.isValid(worker) and hasattr(worker, "stop"):
            # Called directly on purpose: it only sets a flag, and a queued call would wait for run() to end.
            worker.stop()
        self.autopilot.note_launch()
        self._auto_internal_stop = True  # a manual restart must not end the 24/7 cycle
        try:
            self.stop_session("create")
        finally:
            self._auto_internal_stop = False
        self.toast("Restarting server...", "info")
        self._restart_polls = 0
        QTimer.singleShot(RESTART_POLL_MS, self._restart_when_stopped)

    def _restart_when_stopped(self) -> None:
        """Wait (briefly) for the old worker thread to finish, then give the OS a moment before relaunching."""
        self._restart_polls += 1
        if "create" in self.worker_threads and self._restart_polls < RESTART_MAX_POLLS:
            QTimer.singleShot(RESTART_POLL_MS, self._restart_when_stopped)
            return
        QTimer.singleShot(RESTART_GRACE_MS, self._finish_restart)

    def _finish_restart(self) -> None:
        params = self._host_params
        self._restart_pending = False
        if params is None or "create" in self.session_pages:
            return  # something else already started a server in the meantime
        self.autopilot.note_launch()
        self.create_session(*params)

    def test_host_tunnel(self, tunnel: str, local_port: str, button=None) -> None:
        """Test the host's own tunnel address without launching anything."""
        tunnel = tunnel.strip()
        if not tunnel:
            self.toast("Enter a tunnel address first.", "warning")
            return
        error = validate_tunnel(tunnel)
        if error:
            self.toast(f"Tunnel address: {error}.", "error")
            return
        if self._host_test is not None:
            self.toast("A tunnel test is already running.", "info")
            return
        host, port = tunnel.rsplit(":", 1)
        self._host_test_button = button
        self._host_test_label = button.text() if button is not None else ""
        self._host_test_port = local_port
        if button is not None:
            button.setEnabled(False)
            button.setText("Testing...")
        self._host_test = TunnelCheck(host, int(port))
        self._host_test.done.connect(self._on_host_test_done)
        self._host_test_timeout.start(CHECK_TIMEOUT_MS)
        self._host_test.start()

    @Slot(object)
    def _on_host_test_done(self, result: PreflightResult) -> None:
        test = self._host_test
        if test is None:
            return
        self._host_test_timeout.stop()
        test.cancel()
        try:
            test.done.disconnect(self._on_host_test_done)
        except (RuntimeError, TypeError):
            pass
        self._host_test = None
        button = self._host_test_button
        self._host_test_button = None
        if button is not None and shiboken6.isValid(button):
            button.setEnabled(True)
            button.setText(self._host_test_label)
        page = self.session_pages.get("create")
        message = host_message(result, self._host_test_port, bool(page and page.is_live))
        self.toast(message, result.level())
        if page:
            page.append_log(f"Tunnel test: {message}", result.level())

    def _on_server_ready(self) -> None:
        self.toast("Server is ready.", "success")
        if not self.settings.notify_ready:
            return
        play_ready()
        if self.isHidden() and self.tray:
            self.tray.showMessage(
                "Server is ready",
                "Your Studio server is live.",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )
        elif not self.isActiveWindow():
            QApplication.alert(self, 0)  # flash the taskbar button until the window is focused

    def set_notify_ready(self, enabled: bool) -> None:
        self.settings = self.store.update(self.settings, notify_ready=enabled)
        if enabled:
            play_ready()  # preview

    def set_language(self, lang: str) -> None:
        """Switch the app between English and Portuguese, instantly and for good."""
        i18n.set_language(lang)
        lang = i18n.get_language()
        self.settings = self.store.update(self.settings, language=lang)
        i18n.retranslate_all()
        self.title_bar.set_language(lang)
        self.update_session_status()
        self._background.update()

    def toggle_language(self) -> None:
        self.set_language("en" if i18n.get_language() == "pt" else "pt")

    def set_appearance(self, mode: str | None = None, accent: str | None = None) -> None:
        """Dark/light mode and accent colour. Re-colours the whole app at once."""
        mode = mode or self.settings.appearance
        accent = accent or self.settings.accent
        self.settings = self.store.update(self.settings, appearance=mode, accent=accent)
        palette.configure(self.settings.appearance, self.settings.accent)
        theme_picker._thumbs.clear()
        refresh_stylesheet(QApplication.instance())
        self.title_bar.restyle()
        self._background.update()
        bar = None
        for area in self.findChildren(QScrollArea):
            if area.isVisible():
                bar = area.verticalScrollBar().value()
                break
        key = self.current_key
        self.navigate(key)
        if bar:
            QTimer.singleShot(0, lambda: [a.verticalScrollBar().setValue(bar) for a in self.findChildren(QScrollArea) if a.isVisible()])

    def set_background_theme(self, key: str) -> None:
        brand.set_theme(key)
        key = brand.get_theme()
        self.settings = self.store.update(self.settings, background_theme=key)
        self._background.update()

    def set_check_updates(self, enabled: bool) -> None:
        self.settings = self.store.update(self.settings, check_updates=enabled)

    def check_for_updates(self, manual: bool = False) -> None:
        """Ask GitHub for the latest release. The automatic check is silent unless there is news."""
        if self._update_check is not None:
            return
        if not manual and not self.settings.check_updates:
            return
        self.update_state = ("checking", "", "")
        self.update_state_changed.emit()
        check = updates.UpdateCheck(self.settings.update_repo, __version__, self)
        check.result.connect(lambda state, version, url: self._on_update_result(state, version, url, manual))
        self._update_check = check
        check.start()

    def _on_update_result(self, state: str, version: str, url: str, manual: bool) -> None:
        self._update_check = None
        self.update_state = (state, version, url)
        self.title_bar.set_update(version if state == updates.NEWER else "")
        if state == updates.NEWER:
            if self._update_notified != version:
                self._update_notified = version
                self.toast(f"Version {version} is available. Click “Update” at the top to download it.", "info")
        elif manual and state == updates.CURRENT:
            self.toast(f"You are up to date (v{__version__}).", "success")
        elif manual:
            self.toast("Could not check for updates. Check your internet connection.", "warning")
        self.update_state_changed.emit()

    def open_update_page(self) -> None:
        url = self.update_state[2]
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def set_update_repo(self, repo: str) -> None:
        self.settings = self.store.update(self.settings, update_repo=repo)

    def show_tunnel_qr(self, tunnel: str) -> None:
        try:
            matrix = qr_matrix(tunnel)
        except ImportError:
            self.toast("QR support is missing. Install it with: pip install segno", "error")
            return
        self.qr_overlay.open_for(tunnel, matrix)

    def open_place_file(self, place_path: str) -> None:
        try:
            open_place_file(place_path)
            self.settings = self.store.update(self.settings, place_path=place_path)
            self.remember_map(place_path)
            self.toast("Map launched in Roblox Studio.", "success")
        except Exception as exc:
            self.toast(f"Map launch failed: {exc}", "error")

    def join_session(self, host: str, port: int, raw: str) -> None:
        if "join" in self.session_pages:
            self.toast("Connection is already active.", "warning")
            return
        if self._tunnel_check is not None:
            return  # a check is already running (e.g. Enter pressed twice)
        studio = self.ensure_studio_path()
        if not studio:
            self.toast("Cannot locate RobloxStudioBeta.exe.", "error")
            return

        if self._matches_active_host_tunnel(host, port, raw):
            self._remember_join(raw)
            self._join_active_host_locally(studio, raw)
            return

        # Test the tunnel first, so an unreachable address never opens Studio for nothing.
        self._join_pending = (host, port, raw, studio)
        self._tunnel_check = TunnelCheck(host, port)
        self._tunnel_check.done.connect(self._on_tunnel_checked)
        self._set_join_checking(True)
        self._check_timeout.start(CHECK_TIMEOUT_MS)
        self._tunnel_check.start()

    def _remember_join(self, raw: str) -> None:
        self.settings = self.store.update(
            self.settings,
            join_tunnel=raw,
            recent_tunnels=self._with_recent(raw),
        )

    def _join_page(self) -> JoinPage | None:
        for i in range(self.stack.count()):
            widget = self.stack.widget(i)
            if isinstance(widget, JoinPage):
                return widget
        return None

    def _set_join_checking(self, checking: bool) -> None:
        page = self._join_page()
        if page:
            page.set_checking(checking)

    def _cancel_tunnel_check(self) -> None:
        self._check_timeout.stop()
        if self._tunnel_check is not None:
            self._tunnel_check.cancel()
            try:
                self._tunnel_check.done.disconnect(self._on_tunnel_checked)
            except (RuntimeError, TypeError):
                pass
        self._tunnel_check = None
        self._join_pending = None
        self._set_join_checking(False)

    def _on_check_timeout(self) -> None:
        self._on_tunnel_checked(PreflightResult(SILENT))

    @Slot(object)
    def _on_tunnel_checked(self, result: PreflightResult) -> None:
        pending = self._join_pending
        if pending is None:
            return
        host, port, raw, studio = pending
        self._cancel_tunnel_check()
        page = self._join_page()
        tone = {OK: "ok", RELAY: "ok", SILENT: "warn", DNS: "err"}[result.state]
        if page:
            page.show_check(result.message(), tone)

        if result.blocking:
            self.toast(result.message(), "error")
            return
        if result.needs_confirmation:
            reply = QMessageBox.question(
                self,
                "Tunnel not answering",
                "The tunnel did not answer. The host may be offline, or the tunnel may block test packets.\n\n"
                "Launch Studio anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._begin_join(host, port, raw, studio, result)

    def _begin_join(self, host: str, port: int, raw: str, studio: str, check: PreflightResult) -> None:
        if "join" in self.session_pages:
            return
        self._remember_join(raw)
        self._session_started["join"] = (self._now_iso(), "", raw)
        self.mode = "join"
        self.running = True
        self.active_modes.add("join")
        info = [
            ("Mode", "Client (join)"),
            ("Target host", host),
            ("Target port", str(port)),
            ("Local proxy", "127.0.0.1:pending"),
            ("Status", "Initializing"),
            ("Ping", "-"),
            ("Live for", "-"),
        ]
        self._join_target = (host, port)
        page = SessionPage(self, "Connection", "UDP proxy and Studio client.", info, lambda: self.stop_session("join"))
        self.session_pages["join"] = page
        self._set_page(page)
        page.append_log(f"Tunnel check: {check.message()}", check.level())
        self.title_bar.nav.set_current("join")
        self.update_session_status()

        worker = JoinSessionWorker(studio, host, port)
        worker.log.connect(self._worker_log)
        worker.status.connect(self._worker_status)
        worker.info_changed.connect(self._worker_info)
        self._start_worker("join", worker)
        # The probes go straight to the tunnel, so they don't need the proxy to be up.
        self._start_ping()

    def remember_map(self, path: str) -> None:
        """Move `path` to the front of the recent maps (dedupe ignores case and slashes)."""
        key = os.path.normcase(os.path.normpath(path))
        rest = [m for m in self.settings.recent_maps if os.path.normcase(os.path.normpath(m)) != key]
        self.settings = self.store.update(self.settings, recent_maps=[path, *rest][:MAX_RECENT_MAPS])

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _record_history(self, mode: str) -> None:
        """Append the session that is ending to the history. Sessions that never went live are skipped."""
        started = self._session_started.pop(mode, None)
        page = self.session_pages.get(mode)
        seconds = page.live_seconds() if page else None
        if started is None or seconds is None:
            return
        entry = {
            "mode": "host" if mode == "create" else "join",
            "started": started[0],
            "duration": int(seconds),
            "map": started[1],
            "tunnel": started[2],
            "peak": self._peak_players if mode == "create" else 0,
        }
        history = [entry, *self.settings.history][:MAX_HISTORY]
        self.settings = self.store.update(self.settings, history=history)

    def export_settings(self, path: str) -> None:
        try:
            backup.export_to(Path(path), self.settings)
        except OSError:
            self.toast("Could not write the file.", "error")
            return
        self.toast("Settings exported.", "success")

    def import_settings(self, path: str) -> None:
        if self.autopilot.active:
            self.toast("Stop the running 24/7 server before importing settings.", "warning")
            return
        try:
            values = backup.read_import(Path(path))
        except backup.BackupError:
            self.toast("That file is not a valid RSG LocalHost settings export.", "error")
            return
        reply = QMessageBox.question(
            self,
            "Import settings",
            "Replace your current settings and profiles with the ones in this file? Your Discord sign-in and Studio path are kept.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if "auto_feature_enabled" in values:
            values["auto_feature_asked"] = True
        self.settings = self.store.update(self.settings, **values)
        brand.set_theme(self.settings.background_theme)
        self.set_appearance()
        self.set_language(self.settings.language)
        self.set_background_theme(self.settings.background_theme)
        self.toast("Settings imported.", "success")
        self.navigate("settings")

    def clear_history(self) -> None:
        self.settings = self.store.update(self.settings, history=[])
        self.toast("Session history cleared.", "info")
        self.navigate("overview")

    def save_profile(self, name: str, user_id: str, host_tunnel: str, server_port: str, place_path: str) -> bool:
        """Save (or overwrite, ignoring case) a named session profile. False if the list is full."""
        name = name.strip()[:32]
        if not name:
            return False
        profile = {
            "name": name,
            "user_id": user_id.strip(),
            "host_tunnel": host_tunnel.strip(),
            "server_port": server_port.strip(),
            "place_path": place_path.strip(),
        }
        existing = [p for p in self.settings.profiles if p["name"].lower() != name.lower()]
        replacing = len(existing) != len(self.settings.profiles)
        if not replacing and len(existing) >= MAX_PROFILES:
            return False
        # Overwriting keeps the profile's position; a new one goes to the top.
        if replacing:
            profiles = [profile if p["name"].lower() == name.lower() else p for p in self.settings.profiles]
        else:
            profiles = [profile, *existing]
        self.settings = self.store.update(self.settings, profiles=profiles)
        return True

    def delete_profile(self, name: str) -> None:
        remaining = [p for p in self.settings.profiles if p["name"] != name]
        self.settings = self.store.update(self.settings, profiles=remaining)
        self.toast(f"Profile \u201c{name}\u201d deleted.", "info")

    def clear_recent_maps(self) -> None:
        self.settings = self.store.update(self.settings, recent_maps=[])
        self.toast("Recent maps cleared.", "info")

    def _with_recent(self, tunnel: str) -> list[str]:
        """Recent list with `tunnel` moved to the front (case-insensitive dedupe)."""
        tunnel = tunnel.strip()
        rest = [t for t in self.settings.recent_tunnels if t.lower() != tunnel.lower()]
        return [tunnel, *rest][:MAX_RECENT_TUNNELS]

    def forget_recent_tunnel(self, tunnel: str) -> None:
        remaining = [t for t in self.settings.recent_tunnels if t.lower() != tunnel.lower()]
        self.settings = self.store.update(self.settings, recent_tunnels=remaining)

    def clear_recent_tunnels(self) -> None:
        self.settings = self.store.update(self.settings, recent_tunnels=[])
        self.toast("Tunnel history cleared.", "info")

    def _matches_active_host_tunnel(self, host: str, port: int, raw: str) -> bool:
        if "create" not in self.active_modes or not self.host_session_guids:
            return False
        host_tunnel = self.settings.host_tunnel.strip()
        if not host_tunnel:
            return False
        if raw.strip().lower() == host_tunnel.lower():
            return True
        if ":" not in host_tunnel:
            return False
        active_host, active_port = host_tunnel.rsplit(":", 1)
        return host.strip().lower() == active_host.strip().lower() and str(port) == active_port.strip()

    def _join_active_host_locally(self, studio: str, raw: str) -> None:
        if not self.host_session_guids:
            self.toast("Local server session is not ready.", "error")
            return
        parent_guid, play_guid = self.host_session_guids
        server_port = self.settings.server_port

        self.mode = "join"
        self.running = True
        self.active_modes.add("join")
        info = [
            ("Mode", "Client (local host)"),
            ("Target host", "127.0.0.1"),
            ("Target port", server_port),
            ("Local proxy", "not used"),
            ("Status", "Launching"),
            ("Live for", "-"),
        ]
        page = SessionPage(
            self,
            "Connection",
            "Direct client to active local server.",
            info,
            lambda: self.stop_session("join"),
        )
        self.session_pages["join"] = page
        self._set_page(page)
        self.title_bar.nav.set_current("join")
        self.update_session_status()

        try:
            page.append_log(f"Detected active host tunnel {raw}; using local server", "info")
            launch_client(
                studio,
                "127.0.0.1",
                server_port,
                parent_guid,
                play_guid,
                "StudioPlayer_Host",
                session_key="join",
            )
            page.set_info("Status", "Connected locally", "#2ee6a6")
            page.set_status("Connected locally", "ok")
            page.append_log("Studio client launched", "success")
            self.toast("Local client launched.", "success")
        except Exception as exc:
            self.active_modes.discard("join")
            self.session_pages.pop("join", None)
            self.stack.removeWidget(page)
            page.deleteLater()
            self.update_session_status()
            self.toast(f"Launch error: {exc}", "error")

    def _start_worker(self, mode: str, worker) -> None:
        existing = self.worker_threads.get(mode)
        if existing and shiboken6.isValid(existing):
            existing.quit()
            existing.wait(500)
        self.worker_threads.pop(mode, None)
        self.workers.pop(mode, None)

        thread = QThread(self)
        thread.setProperty("sessionMode", mode)
        worker.setProperty("sessionMode", mode)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._worker_thread_finished)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        self.workers[mode] = worker
        self.worker_threads[mode] = thread

    @Slot()
    def _worker_thread_finished(self, mode: str | None = None) -> None:
        if not mode:
            mode = self._sender_mode()
        if not mode:
            return
        current = self.worker_threads.get(mode)
        sender = self.sender()
        if current is not None and sender is not None and current is not sender:
            return  # an old thread of this mode finishing after a restart: leave the new session alone
        page = self.session_pages.get(mode)
        if page:
            page.mark_live()  # no-op if the session already failed
        if page and page.loading_visible:
            page.set_progress(100, "Ready")
            page.set_loading_visible(False)
            page.set_console_visible(True)
        self.worker_threads.pop(mode, None)
        self.workers.pop(mode, None)

    def _sender_mode(self) -> str | None:
        sender = self.sender()
        if sender is None:
            return None
        mode = sender.property("sessionMode")
        return str(mode) if mode else None

    @Slot(str, str)
    def _worker_log(self, message: str, level: str) -> None:
        mode = self._sender_mode()
        if mode:
            self._session_log(mode, message, level)

    @Slot(str, str)
    def _worker_status(self, text: str, tone: str) -> None:
        mode = self._sender_mode()
        if mode:
            self._session_status(mode, text, tone)

    @Slot(str, str)
    def _worker_info(self, key: str, value: str) -> None:
        mode = self._sender_mode()
        if mode:
            self._session_info(mode, key, value)

    @Slot(int, str)
    def _worker_progress(self, value: int, text: str) -> None:
        mode = self._sender_mode()
        if mode:
            self._session_progress(mode, value, text)

    def _session_log(self, mode: str, message: str, level: str) -> None:
        page = self.session_pages.get(mode)
        if page:
            page.append_log(message, level)

    def _session_status(self, mode: str, text: str, tone: str) -> None:
        if mode == "join" and tone == "err":
            self._stop_ping()
        if tone == "err":
            self.active_modes.discard(mode)
            if mode == "create":
                self.host_session_guids = None
                self.autopilot.on_host_failed()
            if not self.active_modes:
                self.running = False
        page = self.session_pages.get(mode)
        if page:
            page.set_status(text, tone)
            if tone in {"ok", "err"} and page.loading_visible:
                page.set_progress(100, text)
                page.set_loading_visible(False)
                page.set_console_visible(True)
        self.update_session_status()

    def _session_info(self, mode: str, key: str, value: str) -> None:
        page = self.session_pages.get(mode)
        if page:
            page.set_info(key, value, "#2ee6a6" if key == "Status" else None)

    def _session_progress(self, mode: str, value: int, text: str) -> None:
        page = self.session_pages.get(mode)
        if page:
            page.set_progress(value, text)
            if value >= 100:
                page.set_loading_visible(False)
                page.set_console_visible(True)

    PING_GOOD_MS = 60
    PING_OK_MS = 120

    def _start_ping(self) -> None:
        target = self._join_target
        if not target or (self.ping_monitor and self.ping_monitor.running):
            return
        self._stop_ping()
        self.ping_monitor = PingMonitor(*target)
        self.ping_monitor.sample.connect(self._on_ping)
        self.ping_monitor.start()
        page = self.session_pages.get("join")
        if page:
            page.set_info("Ping", "Measuring...")

    def _stop_ping(self) -> None:
        if self.ping_monitor:
            self.ping_monitor.stop()
            try:
                self.ping_monitor.sample.disconnect(self._on_ping)
            except (RuntimeError, TypeError):
                pass
            self.ping_monitor = None

    @Slot(float, str)
    def _on_ping(self, ms: float, source: str) -> None:
        page = self.session_pages.get("join")
        if not page or "join" not in self.active_modes:
            return
        if ms < 0:
            page.set_info("Ping", "No reply", "#ff5d73")
            return
        color = "#2ee6a6" if ms < self.PING_GOOD_MS else "#f5b942" if ms < self.PING_OK_MS else "#ff5d73"
        suffix = "  (tunnel relay)" if source == "relay" else ""
        page.set_info("Ping", f"{ms:.0f} ms{suffix}", color)

    def _add_local_join(self, port: str, parent_guid: str, play_guid: str) -> None:
        page = self.session_pages.get("create")
        if page:
            page.add_local_join(lambda: self.join_local(port, parent_guid, play_guid))

    def join_local(self, port: str, parent_guid: str, play_guid: str) -> None:
        try:
            studio = self.ensure_studio_path()
            if not studio:
                self.toast("Cannot locate RobloxStudioBeta.exe.", "error")
                return
            launch_client(
                studio,
                "127.0.0.1",
                port,
                parent_guid,
                play_guid,
                "StudioPlayer_Host",
                session_key="create",
            )
            self.toast("Local client launched.", "success")
        except Exception as exc:
            self.toast(f"Launch error: {exc}", "error")

    def stop_session(self, mode: str) -> None:
        worker = self.workers.get(mode)
        if worker and shiboken6.isValid(worker) and hasattr(worker, "stop"):
            QMetaObject.invokeMethod(worker, "stop", Qt.ConnectionType.QueuedConnection)
        if mode == "join":
            self._stop_ping()
            proxy.stop(wait=False)
        if mode == "create":
            self.host_session_guids = None
            if not self._auto_internal_stop:
                self.autopilot.disarm()  # user pressed Stop: end the 24/7 cycle
        self._record_history(mode)

        killed = stop_roblox_processes(mode)
        self.active_modes.discard(mode)
        self.running = bool(self.active_modes)
        self.mode = next(iter(self.active_modes), None)

        page = self.session_pages.pop(mode, None)
        if page:
            self.stack.removeWidget(page)
            page.deleteLater()

        self.toast(f"Session stopped. {killed} process(es) terminated.", "success")
        self.update_session_status()
        next_mode = next(iter(self.active_modes), None)
        if next_mode and next_mode in self.session_pages:
            self._show_session_page(next_mode)
        else:
            self.navigate("overview")

    def stop_everything(self) -> None:
        self.autopilot.disarm()
        for worker in list(self.workers.values()):
            if shiboken6.isValid(worker) and hasattr(worker, "stop"):
                QMetaObject.invokeMethod(worker, "stop", Qt.ConnectionType.QueuedConnection)
        self._stop_ping()
        proxy.stop(wait=False)
        for mode in list(self.session_pages):
            self._record_history(mode)
        killed = stop_all_roblox_processes()
        self.running = False
        self.mode = None
        self.active_modes.clear()
        self.host_session_guids = None
        for page in list(self.session_pages.values()):
            self.stack.removeWidget(page)
            page.deleteLater()
        self.session_pages.clear()
        self.toast(f"Session stopped. {killed} process(es) terminated.", "success")
        self.update_session_status()
        self.navigate("overview")

    def toast(self, text: str, tone: str = "info") -> None:
        if self._toast:
            try:
                self._toast.deleteLater()
            except RuntimeError:
                pass
            self._toast = None
        self._toast = Toast(tr(text), tone, self)
        toast = self._toast
        toast.destroyed.connect(lambda: self._clear_toast_ref(toast))
        self._position_toast()
        self._toast.show_animated()

    def _mode_of(self, page: SessionPage) -> str | None:
        for mode, candidate in self.session_pages.items():
            if candidate is page:
                return mode
        return None

    def export_log(self, page: SessionPage) -> None:
        """Save the console of a session page to a .log file the user picks."""
        text = page.console.toPlainText()
        if not text.strip():
            self.toast("The console is empty, nothing to export.", "warning")
            return
        mode = self._mode_of(page)
        kind = "server" if mode == "create" else "connection"
        name = f"rsg-localhost-{kind}-{datetime.now():%Y%m%d-%H%M%S}.log"
        docs = Path.home() / "Documents"
        start = docs if docs.is_dir() else Path.home()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export log", str(start / name), "Log files (*.log);;Text files (*.txt)"
        )
        if not path:
            return
        header = f"{__app_name__} {__version__} - {kind} log - exported {datetime.now().isoformat(timespec='seconds')}\n\n"
        try:
            Path(path).write_text(header + text, encoding="utf-8")
        except OSError as exc:
            self.toast(f"Could not save the log: {exc.strerror or exc}", "error")
            return
        self.toast(f"Log saved: {Path(path).name}", "success")

    def copy_diagnostics(self, page: SessionPage, button=None) -> None:
        """Copy a redacted support summary (no tunnel address, no User ID, no user folder)."""
        mode = self._mode_of(page)
        secrets: list[str] = []
        map_name, port, tunnel_set = "", "", False
        if mode == "create" and self._host_params:
            user_id, tunnel, port, place = self._host_params
            secrets = [tunnel, tunnel.rsplit(":", 1)[0] if ":" in tunnel else tunnel]
            if len(user_id) >= 5:
                secrets.append(user_id)
            tunnel_set = bool(tunnel)
            map_name = Path(place).name if place else ""
        elif mode == "join" and self._join_target:
            host, target_port = self._join_target
            secrets = [f"{host}:{target_port}", host]
            port, tunnel_set = str(target_port), True
        seconds = page.live_seconds()
        studio = self.studio_path or ""
        text = build_diagnostics(
            mode="Server (host)" if mode == "create" else "Client (join)",
            status=i18n.source_text(page.status_label),
            uptime=format_uptime(seconds) if seconds is not None else "-",
            port=port,
            tunnel_set=tunnel_set,
            map_name=map_name,
            studio_name=Path(studio).name if studio else "",
            studio_found=bool(studio) and Path(studio).is_file(),
            log_text=page.console.toPlainText(),
            secrets=secrets,
        )
        self.copy_to_clipboard(text, "Diagnostics copied.", button, "Copied")

    def copy_to_clipboard(
        self, text: str, message: str = "Copied.", source: QWidget | None = None, flash: str = "Copied"
    ) -> None:
        """Copy `text`. With a `source` button the confirmation appears on it; otherwise as a toast."""
        QApplication.clipboard().setText(text)
        if source is not None and shiboken6.isValid(source):
            flash_copied(source, flash)
        else:
            self.toast(message, "success")

    def _clear_toast_ref(self, toast: Toast) -> None:
        if self._toast is toast:
            self._toast = None

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.drop_overlay.setGeometry(self.rect())
        self.qr_overlay.setGeometry(self.rect())
        self._position_toast()

    def _position_toast(self) -> None:
        if not self._toast:
            return
        self._toast.adjustSize()
        x = (self.width() - self._toast.width()) // 2
        y = self.height() - self._toast.height() - 22
        self._toast.move(max(12, x), max(12, y))

    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def nativeEvent(self, event_type, message):
        if os.name != "nt":
            return False, 0
        if event_type not in (b"windows_generic_MSG", "windows_generic_MSG"):
            return False, 0

        msg = wintypes.MSG.from_address(int(message))
        WM_NCHITTEST = 0x0084
        if msg.message != WM_NCHITTEST:
            return False, 0

        x = ctypes.c_short(msg.lParam & 0xFFFF).value
        y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
        pos = self.mapFromGlobal(QPoint(x, y))
        width = self.width()
        height = self.height()
        border = 0 if self.isMaximized() else self.BORDER

        HTCLIENT = 1
        HTCAPTION = 2
        HTLEFT = 10
        HTRIGHT = 11
        HTTOP = 12
        HTTOPLEFT = 13
        HTTOPRIGHT = 14
        HTBOTTOM = 15
        HTBOTTOMLEFT = 16
        HTBOTTOMRIGHT = 17

        if border:
            left = pos.x() < border
            right = pos.x() >= width - border
            top = pos.y() < border
            bottom = pos.y() >= height - border
            if top and left:
                return True, HTTOPLEFT
            if top and right:
                return True, HTTOPRIGHT
            if bottom and left:
                return True, HTBOTTOMLEFT
            if bottom and right:
                return True, HTBOTTOMRIGHT
            if left:
                return True, HTLEFT
            if right:
                return True, HTRIGHT
            if top:
                return True, HTTOP
            if bottom:
                return True, HTBOTTOM

        if 0 <= pos.y() <= self.title_bar.height() and not self.title_bar.is_control_at(QPoint(x, y)):
            return True, HTCAPTION
        return False, HTCLIENT

    def _enable_windows_backdrop(self) -> None:
        if os.name != "nt":
            return
        try:
            hwnd = int(self.winId())
            dwm = ctypes.windll.dwmapi
            value = ctypes.c_int(1)
            for attr in (20, 19):
                dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
            backdrop = ctypes.c_int(2)
            dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop))
        except Exception:
            pass

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.session_active() and not self._force_quit:
            if self.tray:
                choice = self._ask_close_action()
                if choice == "tray":
                    event.ignore()
                    self.hide_to_tray()
                    return
                if choice == "cancel":
                    event.ignore()
                    return
            else:
                reply = QMessageBox.question(
                    self,
                    "Quit RSG LocalHost",
                    "Stop active sessions and quit?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
        self._cancel_tunnel_check()
        self._stop_ping()
        proxy.stop(wait=False)
        worker = self._key_check
        if worker is not None and worker.isRunning():
            if not worker.wait(3000):
                worker.terminate()
                worker.wait(1000)
        self.autopilot.disarm()  # pushes "offline" to Discord
        for mode in list(self.session_pages):
            self._record_history(mode)
        stop_all_roblox_processes()
        discord_status.flush()
        if self.tray:
            self.tray.hide()  # otherwise Windows leaves a ghost icon behind
        event.accept()
        QApplication.quit()
