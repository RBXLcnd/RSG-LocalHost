"""Receives the player count from the game server (a Roblox script running inside Studio).

The game does an HTTP POST to http://127.0.0.1:PLAYER_COUNT_PORT/players with {"count": N}.
Only this PC can reach it (bound to 127.0.0.1). The number goes to discord_status, which sends
it to the Discord panel together with the rest of the server state.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtCore import QObject, Signal

PLAYER_COUNT_PORT = 55557
MAX_PLAYERS = 500
MAX_BODY = 1024


class PlayerCountServer(QObject):
    count_changed = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._httpd: ThreadingHTTPServer | None = None

    def start(self) -> bool:
        if self._httpd is not None:
            return True
        emit = self.count_changed.emit

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                    if self.path.rstrip("/") != "/players" or not 0 < length <= MAX_BODY:
                        self.send_response(400); self.end_headers(); return
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                    count = int(data["count"])
                    if not 0 <= count <= MAX_PLAYERS:
                        raise ValueError("out of range")
                except Exception:
                    self.send_response(400); self.end_headers(); return
                emit(count)
                self.send_response(204); self.end_headers()

            def log_message(self, *_args) -> None:  # keep the console quiet
                pass

        try:
            self._httpd = ThreadingHTTPServer(("127.0.0.1", PLAYER_COUNT_PORT), Handler)
        except OSError:
            self._httpd = None
            return False
        threading.Thread(target=self._httpd.serve_forever, daemon=True, name="player-count").start()
        return True

    def stop(self) -> None:
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None
