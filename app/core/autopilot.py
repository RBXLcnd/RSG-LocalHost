"""24/7 cycle: keep the host server online for N hours, pause it for M hours,
then bring it back (next map of the rotation), forever, and report every
change to the Discord status document (see discord_status.py).

This app *is* the local host, so there is no UI automation any more: the
cycle calls the same create_session / stop_session the "Launch server" and
"Stop session" buttons use.

How it is armed / disarmed:
  * "Launch server" with the 24/7 switch on  -> MainWindow.start_auto_host() -> start()
  * "Stop session" (or Stop all / quit)      -> MainWindow calls disarm()
  * the cycle's own pause uses window._auto_internal_stop, so it does not
    disarm itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from app.core.discord_status import push_status
from app.core.studio import session_running

TICK_MS = 5000          # how often the schedule is checked
RETRY_MINUTES = 3       # wait before retrying after a failed launch
CRASH_GRACE_SECONDS = 90  # after a launch, don't judge "server died" before this
HEARTBEAT_SECONDS = 60  # re-publish the state so Discord can tell "alive" from "app was killed" (the bot shows offline after ~3 missed beats)
RELAUNCH_DELAY_MS = 2500  # let Windows free the UDP port between stop and start

ON, OFF, RETRY = "on", "off", "retry"


@dataclass
class AutoConfig:
    user_id: str
    tunnel: str
    port: str
    fallback_map: str                 # used when the rotation list is empty
    on_hours: float
    off_hours: float
    maps: list[str] = field(default_factory=list)


class AutoPilot(QObject):
    # (phase, human readable text) - shown in the session page and tray
    state_changed = Signal(str, str)
    # persists the rotation pointer
    map_index_changed = Signal(int)

    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.config: AutoConfig | None = None
        self.phase: str | None = None
        self.next_switch_at: datetime | None = None
        self._map_index = 0
        self._current_map = ""
        self._launched_at: datetime | None = None
        self._relaunching = False
        self._last_status: dict | None = None
        self._last_push_at: datetime | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    @property
    def active(self) -> bool:
        return self.config is not None and self._timer.isActive()

    # ---------- arm / disarm ----------

    def start(self, config: AutoConfig, map_index: int = 0) -> None:
        self.config = config
        self._map_index = map_index
        self._timer.start()
        self._begin_on()

    def disarm(self, push_offline: bool = True) -> None:
        """User stopped the server (or the app is closing): end the cycle for good."""
        was_active = self.active
        self._timer.stop()
        self.config = None
        self.phase = None
        self.next_switch_at = None
        self._relaunching = False
        if was_active:
            self.state_changed.emit("", "Off")
            if push_offline:
                self._push(online=False, next_event_at=None)

    # ---------- map rotation ----------

    def _pick_map(self) -> str:
        """Next existing map of the rotation (skips missing files); falls back to the Map file field."""
        cfg = self.config
        if cfg is None:
            return ""
        if not cfg.maps:
            return cfg.fallback_map
        for _ in range(len(cfg.maps)):
            candidate = cfg.maps[self._map_index % len(cfg.maps)]
            self._map_index = (self._map_index + 1) % len(cfg.maps)
            self.map_index_changed.emit(self._map_index)
            if Path(candidate).is_file():
                return candidate
            self._log(f"Rotation: map not found, skipping: {candidate}", "warn")
        return ""

    def _peek_next_map_name(self) -> str:
        cfg = self.config
        if cfg is None:
            return ""
        if not cfg.maps:
            return Path(cfg.fallback_map).name if cfg.fallback_map else ""
        return Path(cfg.maps[self._map_index % len(cfg.maps)]).name

    # ---------- phases ----------

    def _begin_on(self, keep_deadline: bool = False) -> None:
        cfg = self.config
        if cfg is None:
            return
        self._stop_server()  # clear a failed / leftover session page so create_session accepts a new one
        place = self._pick_map()
        if not place:
            self._log("24/7: no usable map to launch. Check the map file / rotation list.", "error")
            self._enter_retry("no usable map")
            return
        now = datetime.now(timezone.utc)
        self.phase = ON
        if not keep_deadline or self.next_switch_at is None:
            self.next_switch_at = now + timedelta(hours=cfg.on_hours)
        self._current_map = place
        self._launched_at = now
        self.window.create_session(cfg.user_id, cfg.tunnel, cfg.port, place)
        self._push(
            online=True,
            map_name=Path(place).name,
            next_map_name=self._peek_next_map_name(),
            started_at=now,
            next_event_at=self.next_switch_at,
            cycle_hours=cfg.on_hours,
        )
        self._announce(f"Online until {self._local(self.next_switch_at)}")

    def _begin_off(self) -> None:
        cfg = self.config
        if cfg is None:
            return
        self.phase = OFF
        self.next_switch_at = datetime.now(timezone.utc) + timedelta(hours=cfg.off_hours)
        self._stop_server()
        self._push(
            online=False,
            next_map_name=self._peek_next_map_name(),
            next_event_at=self.next_switch_at,
            cycle_hours=cfg.off_hours,
        )
        self._announce(f"Paused until {self._local(self.next_switch_at)}")

    def _enter_retry(self, reason: str) -> None:
        self.phase = RETRY
        self.next_switch_at = datetime.now(timezone.utc) + timedelta(minutes=RETRY_MINUTES)
        self._push(
            online=False,
            next_map_name=self._peek_next_map_name(),
            next_event_at=self.next_switch_at,
        )
        self._announce(f"Launch failed ({reason}); retrying at {self._local(self.next_switch_at)}")

    def note_launch(self) -> None:
        """A manual restart is relaunching the server: restart the "died?" grace period."""
        if self.active and self.phase == ON:
            self._launched_at = datetime.now(timezone.utc)

    def on_host_failed(self) -> None:
        """MainWindow tells us the server session reported an error."""
        if self.active and self.phase == ON:
            self._enter_retry("server error")

    # ---------- tick ----------

    def _tick(self) -> None:
        if not self.active or self.next_switch_at is None or self._relaunching:
            return
        now = datetime.now(timezone.utc)
        self._heartbeat(now)

        if now >= self.next_switch_at:
            if self.phase == ON:
                self._begin_off()
            else:  # OFF or RETRY -> bring it back
                self._begin_on()
            return

        # Server died on its own while it should be online: relaunch (same deadline, next map).
        if self.phase == ON and self._launched_at is not None:
            if (now - self._launched_at).total_seconds() > CRASH_GRACE_SECONDS and not session_running("create"):
                self._log("24/7: the Studio server stopped unexpectedly. Relaunching.", "warn")
                self._push(online=False, next_map_name=self._peek_next_map_name())  # show offline while it comes back
                self._relaunching = True
                self._stop_server()
                QTimer.singleShot(RELAUNCH_DELAY_MS, self._finish_relaunch)

    def _finish_relaunch(self) -> None:
        self._relaunching = False
        if self.active and self.phase == ON:
            self._begin_on(keep_deadline=True)

    # ---------- helpers ----------

    def _push(self, **status) -> None:
        self._last_status = status
        self._last_push_at = datetime.now(timezone.utc)
        push_status(self._log, **status)

    def refresh_status(self) -> None:
        """Re-publish the last state now (e.g. the player count changed). Rate-limited."""
        if not self.active or self._last_status is None or self._last_push_at is None:
            return
        if (datetime.now(timezone.utc) - self._last_push_at).total_seconds() >= 10:
            self._push(**self._last_status)

    def _heartbeat(self, now: datetime) -> None:
        if self._last_status is None or self._last_push_at is None:
            return
        if (now - self._last_push_at).total_seconds() >= HEARTBEAT_SECONDS:
            self._push(**self._last_status)

    def _stop_server(self) -> None:
        """Stop the host session without disarming ourselves."""
        if "create" not in self.window.session_pages:
            return
        self.window._auto_internal_stop = True
        try:
            self.window.stop_session("create")
        finally:
            self.window._auto_internal_stop = False

    def _announce(self, text: str) -> None:
        self._log(f"24/7: {text}", "info")
        self.state_changed.emit(self.phase or "", text)

    @staticmethod
    def _local(moment: datetime) -> str:
        return moment.astimezone().strftime("%H:%M")

    def _log(self, message: str, level: str = "info") -> None:
        self.window.log_auto(message, level)
