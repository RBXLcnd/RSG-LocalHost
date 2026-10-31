from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QStackedLayout, QVBoxLayout, QWidget

from app.core.uptime import format_uptime
from app.pages.base import InfoStrip, Page, divider
from app.widgets.buttons import AppButton
from app.widgets.log_console import LogConsole
from app.widgets.status import StatusDot


class SessionPage(Page):
    MAX_WIDTH = None  # console needs the full width

    went_live = Signal()  # emitted once, the first time the session is live

    def __init__(
        self,
        window,
        title: str,
        subtitle: str,
        info_pairs: list[tuple[str, str]],
        stop_callback=None,
    ) -> None:
        super().__init__()
        self.window = window
        self.stop_callback = stop_callback or window.stop_everything
        self.info_rows: InfoStrip | None = None
        self.local_join_button: AppButton | None = None
        self.invite_button: AppButton | None = None
        self.qr_button: AppButton | None = None
        self.test_button: AppButton | None = None
        self.restart_button: AppButton | None = None
        self.loading_visible = False
        self._live_since: float | None = None
        self._failed = False
        self._uptime_timer = QTimer(self)
        self._uptime_timer.setInterval(1000)
        self._uptime_timer.timeout.connect(self._tick_uptime)

        status = QHBoxLayout()
        status.setSpacing(8)
        self.status_dot = StatusDot("#5d7099", 8)
        self.status_label = QLabel("Initializing")
        self.status_label.setObjectName("pageSubtitle")
        status.addWidget(self.status_dot)
        status.addWidget(self.status_label)
        self.add_header(title, subtitle, status, eyebrow="Session")

        self.content_stack = QStackedLayout()
        self.content_stack.setContentsMargins(0, 0, 0, 0)
        self.content_stack.setStackingMode(QStackedLayout.StackingMode.StackOne)

        self.loader_page = QWidget()
        loader = QVBoxLayout(self.loader_page)
        loader.setContentsMargins(0, 0, 0, 0)
        loader.setSpacing(14)
        loader.addStretch()
        self.loader_title = QLabel("Setting up")
        self.loader_title.setObjectName("loaderTitle")
        self.loader_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loader_status = QLabel("Preparing")
        self.loader_status.setObjectName("loaderStatus")
        self.loader_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loader_progress = QProgressBar()
        self.loader_progress.setObjectName("loaderProgress")
        self.loader_progress.setRange(0, 100)
        self.loader_progress.setValue(0)
        self.loader_progress.setTextVisible(False)
        loader.addWidget(self.loader_title)
        loader.addWidget(self.loader_status)
        loader.addWidget(self.loader_progress, 0, Qt.AlignmentFlag.AlignCenter)
        loader.addStretch()
        loader_actions = QHBoxLayout()
        loader_actions.addStretch()
        loader_stop = AppButton("Stop session", "stop", "danger")
        loader_stop.clicked.connect(self.stop_callback)
        loader_actions.addWidget(loader_stop)
        loader.addLayout(loader_actions)

        self.session_view = QWidget()
        session_root = QVBoxLayout(self.session_view)
        session_root.setContentsMargins(0, 0, 0, 0)
        session_root.setSpacing(16)

        # facts strip across the top, console fills the space below
        self.info_rows = InfoStrip(info_pairs)
        session_root.addWidget(self.info_rows)

        self.progress_panel = QWidget()
        progress_layout = QHBoxLayout(self.progress_panel)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(12)
        progress_label = QLabel("Setup")
        progress_label.setObjectName("sectionTitle")
        self.progress_status = QLabel("Waiting")
        self.progress_status.setObjectName("fieldHint")
        self.progress = QProgressBar()
        self.progress.setObjectName("sessionProgress")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(self.progress_status)
        progress_layout.addWidget(self.progress, 1)
        self.progress_panel.setVisible(False)
        session_root.addWidget(self.progress_panel)

        self.post_actions = QHBoxLayout()
        self.post_actions.setSpacing(10)
        self.post_actions.addStretch()
        session_root.addLayout(self.post_actions)

        header = QHBoxLayout()
        console_label = QLabel("Console")
        console_label.setObjectName("sectionTitle")
        header.addWidget(console_label)
        header.addWidget(StatusDot("#2ee6a6", 6))
        streaming = QLabel("Streaming")
        streaming.setObjectName("fieldHint")
        header.addWidget(streaming)
        header.addStretch()
        self.export_button = AppButton("Export log", "folder", "ghost")
        self.export_button.setToolTip("Save the console to a .log file")
        self.export_button.clicked.connect(lambda: window.export_log(self))
        header.addWidget(self.export_button)
        self.diagnostics_button = AppButton("Copy diagnostics", "copy", "ghost")
        self.diagnostics_button.setToolTip(
            "Copy a summary to paste when asking for help. The tunnel address, User ID and your user folder are hidden."
        )
        self.diagnostics_button.clicked.connect(
            lambda checked=False, b=self.diagnostics_button: window.copy_diagnostics(self, b)
        )
        header.addWidget(self.diagnostics_button)
        session_root.addLayout(header)
        self.console_area = QWidget()
        console_layout = QVBoxLayout(self.console_area)
        console_layout.setContentsMargins(0, 0, 0, 0)
        self.console = LogConsole()
        console_layout.addWidget(self.console)
        session_root.addWidget(self.console_area, 1)

        actions = QHBoxLayout()
        back = AppButton("Back", "back", "ghost")
        stop = AppButton("Stop session", "stop", "danger")
        back.clicked.connect(lambda: window.navigate("overview"))
        stop.clicked.connect(self.stop_callback)
        actions.addWidget(back)
        actions.addStretch()
        actions.addWidget(stop)
        session_root.addLayout(actions)

        self.content_stack.addWidget(self.loader_page)
        self.content_stack.addWidget(self.session_view)
        self.content_stack.setCurrentWidget(self.session_view)
        self.root.addLayout(self.content_stack, 1)

    def append_log(self, message: str, level: str = "info") -> None:
        self.console.append_log(message, level)

    def mark_live(self) -> None:
        """Start the uptime clock (once). Not called while the loader is up or after a failure."""
        if self._live_since is not None or self._failed:
            return
        self._live_since = time.monotonic()
        self._uptime_timer.start()
        self._tick_uptime()
        self.went_live.emit()

    def live_seconds(self) -> float | None:
        """How long the session has been live, or None if it never went live."""
        if self._live_since is None:
            return None
        return max(0.0, time.monotonic() - self._live_since)

    @property
    def is_live(self) -> bool:
        return self._live_since is not None and not self._failed

    def _tick_uptime(self) -> None:
        if self._live_since is not None:
            self.set_info("Live for", format_uptime(time.monotonic() - self._live_since))

    def set_status(self, text: str, tone: str) -> None:
        if tone == "ok":
            self.mark_live()
        elif tone == "err":
            self._failed = True
            self._uptime_timer.stop()
        colors = {"ok": "#2ee6a6", "info": "#5d7099", "warn": "#f5b942", "err": "#ff5d73"}
        self.status_dot.set_color(colors.get(tone, "#5d7099"))
        self.status_label.setText(text)

    def set_info(self, key: str, value: str, color: str | None = None) -> None:
        if self.info_rows:
            self.info_rows.set_value(key, value, color)

    def set_progress(self, value: int, text: str) -> None:
        safe_value = max(0, min(100, value))
        self.progress.setValue(safe_value)
        self.loader_progress.setValue(safe_value)
        self.progress_status.setText(text)
        self.loader_status.setText(text)

    def set_console_visible(self, visible: bool) -> None:
        self.console_area.setVisible(visible)

    def set_loading_visible(self, visible: bool) -> None:
        self.loading_visible = visible
        self.content_stack.setCurrentWidget(self.loader_page if visible else self.session_view)
        self.progress_panel.setVisible(False)

    def add_local_join(self, callback) -> None:
        if self.local_join_button:
            return
        self.local_join_button = AppButton("Join local server", "play", "primary")
        self.local_join_button.clicked.connect(callback)
        self.post_actions.insertWidget(0, self.local_join_button)  # always the first action

    def add_copy_tunnel(self, callback) -> None:
        if self.info_rows:
            self.info_rows.add_inline_action("Tunnel", "copy", "Copy tunnel", callback)

    def add_copy_invite(self, callback) -> None:
        if self.invite_button:
            return
        self.invite_button = AppButton("Copy invite", "copy", "secondary")
        self.invite_button.setToolTip("Copy a ready-to-paste message for Discord")
        self.invite_button.clicked.connect(lambda checked=False, b=self.invite_button: callback(b))
        self.post_actions.insertWidget(self.post_actions.count() - 1, self.invite_button)

    def add_restart(self, callback) -> None:
        if self.restart_button:
            return
        self.restart_button = AppButton("Restart", "refresh", "secondary")
        self.restart_button.setToolTip("Stop the server and launch it again with the same settings")
        self.restart_button.clicked.connect(callback)
        self.post_actions.insertWidget(self.post_actions.count() - 1, self.restart_button)

    def add_test_tunnel(self, callback) -> None:
        if self.test_button:
            return
        self.test_button = AppButton("Test tunnel", "network", "secondary")
        self.test_button.setToolTip("Check that people can reach your server through the tunnel")
        self.test_button.clicked.connect(lambda checked=False, b=self.test_button: callback(b))
        self.post_actions.insertWidget(self.post_actions.count() - 1, self.test_button)

    def add_qr(self, callback) -> None:
        if self.qr_button:
            return
        self.qr_button = AppButton("QR code", "qr-code", "secondary")
        self.qr_button.setToolTip("Show a QR code for the tunnel address")
        self.qr_button.clicked.connect(callback)
        self.post_actions.insertWidget(self.post_actions.count() - 1, self.qr_button)
