"""rsg://join/host:port invite links.

* `parse_link` / `build_link`: the link format. Parsing is strict (host characters and port range), so
  a link can only ever put a plain host:port into the Join field. It never starts anything by itself.
* `register`: makes Windows open `rsg://` links with this program (per-user, no admin; the installer
  does the same). Only done by the packaged exe.
* `LinkServer` / `send_to_running`: a second launch (the OS opening a link) hands it to the copy that is
  already running instead of failing on the single-instance lock.
"""
from __future__ import annotations

import os
import re
import sys
from urllib.parse import unquote

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

SCHEME = "rsg"
SERVER_NAME = "rsg-localhost-link"
_LINK = re.compile(r"^rsg://join/([^/?#\s]+)/?$", re.IGNORECASE)
_TUNNEL = re.compile(r"^([A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?):(\d{1,5})$")


def parse_link(text: str) -> str | None:
    """'host:port' from an rsg://join/host:port link, or None when it is not a valid one."""
    if not isinstance(text, str):
        return None
    match = _LINK.match(text.strip())
    if not match:
        return None
    tunnel = unquote(match.group(1))
    found = _TUNNEL.match(tunnel)
    if not found or not 1 <= int(found.group(2)) <= 65535:
        return None
    return tunnel


def build_link(tunnel: str) -> str:
    return f"{SCHEME}://join/{tunnel.strip()}"


def register(exe: str | None = None) -> bool:
    """Point the rsg:// protocol at this exe for the current Windows user. False when not applicable."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return False
    try:
        import winreg

        exe = exe or sys.executable
        command = f'"{exe}" "%1"'
        base = r"Software\Classes\rsg"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open\command") as key:
                if winreg.QueryValueEx(key, "")[0] == command:
                    return True
        except OSError:
            pass
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:RSG LocalHost")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\DefaultIcon") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{exe}",0')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
        return True
    except Exception:
        return False


class LinkServer(QObject):
    """Receives links sent by later launches of the program."""

    link_received = Signal(str)  # host:port

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        if not self._server.listen(SERVER_NAME):
            QLocalServer.removeServer(SERVER_NAME)  # left behind by a crashed run
            self._server.listen(SERVER_NAME)

    def _on_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(socket.deleteLater)

    def _read(self, socket: QLocalSocket) -> None:
        data = bytes(socket.read(2048)).decode("utf-8", errors="ignore")
        tunnel = parse_link(data)
        if tunnel:
            self.link_received.emit(tunnel)
        socket.disconnectFromServer()


def send_to_running(link: str, timeout_ms: int = 800) -> bool:
    """Hand a link to the copy that is already running. False when nothing answers."""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write(link.encode("utf-8"))
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True
