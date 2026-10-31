from __future__ import annotations

import os
import re
import socket
import struct
import subprocess
import threading
import time
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

# RakNet "offline message" magic, shared by every unconnected packet.
RAKNET_MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")
ID_UNCONNECTED_PING = 0x01
ID_UNCONNECTED_PONG = 0x1C

_REPLY_MS = re.compile(r"[=<]\s*(\d+(?:[.,]\d+)?)\s*ms", re.IGNORECASE)
_HAS_TTL = re.compile(r"ttl\s*=", re.IGNORECASE)

ProbeFn = Callable[..., "float | None"]


def build_unconnected_ping(stamp: int, guid: int = 0x5253474C) -> bytes:
    return bytes([ID_UNCONNECTED_PING]) + struct.pack(">Q", stamp) + RAKNET_MAGIC + struct.pack(">Q", guid)


def is_pong_for(packet: bytes, stamp: int) -> bool:
    return len(packet) >= 9 and packet[0] == ID_UNCONNECTED_PONG and packet[1:9] == struct.pack(">Q", stamp)


def udp_probe(ip: str, port: int, timeout: float = 1.0) -> float | None:
    """Round trip of a RakNet unconnected ping in ms, or None if nobody answered."""
    stamp = int(time.time() * 1000) & 0xFFFFFFFFFFFFFFFF
    packet = build_unconnected_ping(stamp)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            start = time.perf_counter()
            sock.sendto(packet, (ip, port))
            deadline = start + timeout
            while True:
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    return None
                sock.settimeout(remaining)
                data, _ = sock.recvfrom(2048)
                if is_pong_for(data, stamp):
                    return (time.perf_counter() - start) * 1000.0
        except (socket.timeout, OSError):
            return None


def parse_ping_output(text: str) -> float | None:
    """Pull the RTT out of `ping` output in any language.

    Only lines carrying a TTL are considered: the summary lines Windows prints
    (`Average = 0ms`) also appear when every packet was lost."""
    for line in text.splitlines():
        if _HAS_TTL.search(line):
            match = _REPLY_MS.search(line)
            if match:
                return float(match.group(1).replace(",", "."))
    return None


def icmp_probe(host: str, timeout: float = 1.0) -> float | None:
    if os.name == "nt":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout))), host]
        flags = 0
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",  # localized Windows consoles aren't UTF-8
            timeout=timeout + 2,
            creationflags=flags,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_ping_output(result.stdout)


class PingMonitor(QObject):
    """Measures latency to a tunnel in a background thread.

    `sample(ms, source)` is emitted every `interval` seconds:
      * ms   -- round trip in milliseconds, or -1 when there was no reply
      * source -- "udp" (the game server answered) or "relay" (only the tunnel host did)

    Nothing is emitted until the method is decided, so the UI can keep
    showing "Measuring...". The first `udp_attempts` silent UDP probes switch
    the monitor to ICMP for good."""

    sample = Signal(float, str)

    def __init__(
        self,
        host: str,
        port: int,
        interval: float = 2.0,
        udp_attempts: int = 3,
        udp: ProbeFn = udp_probe,
        icmp: ProbeFn = icmp_probe,
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.interval = interval
        self.udp_attempts = udp_attempts
        self._udp = udp
        self._icmp = icmp
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._stop.is_set()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="ping-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        source = "udp"
        udp_answered = False
        udp_misses = 0
        ip: str | None = None
        while not self._stop.is_set():
            if ip is None:
                try:
                    ip = socket.gethostbyname(self.host)
                except OSError:
                    self._emit(None, source)
                    self._stop.wait(self.interval)
                    continue

            if source == "udp":
                ms = self._udp(ip, self.port)
                if ms is None and not udp_answered:
                    udp_misses += 1
                    if udp_misses >= self.udp_attempts:
                        source = "relay"
                    continue  # decide quickly, don't report yet
                udp_answered = udp_answered or ms is not None
            else:
                ms = self._icmp(self.host)

            self._emit(ms, source)
            self._stop.wait(self.interval)

    def _emit(self, ms: float | None, source: str) -> None:
        if not self._stop.is_set():
            self.sample.emit(-1.0 if ms is None else ms, source)
