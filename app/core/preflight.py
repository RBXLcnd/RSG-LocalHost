from __future__ import annotations

import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from app.core.ping import ProbeFn, icmp_probe, udp_probe

# Outcomes of a check, from best to worst.
OK = "ok"  # the game server answered a RakNet ping
RELAY = "relay"  # only the tunnel host answered (ICMP): the tunnel exists, the server is unconfirmed
SILENT = "silent"  # host resolves but nothing answered: host may be offline, or it drops probes
DNS = "dns"  # the hostname does not resolve at all


@dataclass(frozen=True, slots=True)
class PreflightResult:
    state: str
    ms: float | None = None

    @property
    def blocking(self) -> bool:
        """True when there is no point in launching Studio at all."""
        return self.state == DNS

    @property
    def needs_confirmation(self) -> bool:
        return self.state == SILENT

    def message(self) -> str:
        if self.state == OK:
            return f"Tunnel answered in {self.ms:.0f} ms."
        if self.state == RELAY:
            return f"Tunnel host reachable ({self.ms:.0f} ms), server not confirmed."
        if self.state == SILENT:
            return "No reply from the tunnel. The host may be offline."
        return "Address not found. Check the hostname."

    def level(self) -> str:
        return {OK: "success", RELAY: "info", SILENT: "warning", DNS: "error"}[self.state]


def host_message(result: PreflightResult, local_port: str, server_running: bool) -> str:
    """Wording for the host's own tunnel test (the join-side wording is `PreflightResult.message`)."""
    if result.state == OK:
        return f"Tunnel works: your server answered in {result.ms:.0f} ms."
    if result.state == RELAY:
        if server_running:
            return (
                f"The tunnel host is reachable ({result.ms:.0f} ms), but your server did not answer. "
                f"Check that the tunnel forwards UDP to port {local_port or '55555'}."
            )
        return f"The tunnel host is reachable ({result.ms:.0f} ms). Launch the server to finish the test."
    if result.state == SILENT:
        return "No reply from the tunnel. Check that it is running and set to UDP."
    return "Address not found. Check the tunnel hostname."


def run_preflight(
    host: str,
    port: int,
    udp: ProbeFn = udp_probe,
    icmp: ProbeFn = icmp_probe,
    resolve: Callable[[str], str] = socket.gethostbyname,
    attempts: int = 3,
) -> PreflightResult:
    """Blocking check. Call it from a worker thread, never from the UI thread."""
    try:
        ip = resolve(host)
    except OSError:
        return PreflightResult(DNS)

    for _ in range(attempts):
        ms = udp(ip, port)
        if ms is not None:
            return PreflightResult(OK, ms)

    ms = icmp(host)
    if ms is not None:
        return PreflightResult(RELAY, ms)
    return PreflightResult(SILENT)


class TunnelCheck(QObject):
    """Runs `run_preflight` in a background thread and emits `done(result)` once."""

    done = Signal(object)

    def __init__(self, host: str, port: int, check: Callable[[str, int], PreflightResult] = run_preflight) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self._check = check
        self._cancelled = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._run, name="tunnel-check", daemon=True).start()

    def cancel(self) -> None:
        self._cancelled.set()

    def _run(self) -> None:
        result = self._check(self.host, self.port)
        if not self._cancelled.is_set():
            self.done.emit(result)
