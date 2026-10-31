from __future__ import annotations

from dataclasses import dataclass

NEW = "new"
IMPROVED = "improved"
FIX = "fix"


@dataclass(frozen=True, slots=True)
class Release:
    version: str
    date: str  # free text, may be empty
    notes: tuple[tuple[str, str], ...]  # (kind, text)


# Newest first. Add a Release at the top and bump app.__version__ for each new build.
RELEASES: tuple[Release, ...] = (
    Release(
        "2.3.0",
        "2026-09-30",
        (
            (NEW, "Session profiles: save a set of User ID, tunnel, port and map under a name and reload it in one click."),
            (NEW, "Export log saves the console to a .log file. Copy diagnostics copies a support summary with the tunnel address, User ID and your user folder hidden."),
            (NEW, "Session history on the Overview page: mode, map or tunnel, how long it ran and when it started."),
            (NEW, "Restart button on the server page: relaunches the server with the same settings."),
            (NEW, "Test your own tunnel: a Test button next to the tunnel address, and Test tunnel on the server page once it is live."),
        ),
    ),
    Release(
        "2.2.0",
        "2026-09-29",
        (
            (NEW, "Recent maps: a Recent button next to Choose map lists the last maps you launched."),
        ),
    ),
    Release(
        "2.1.0",
        "2026-09-29",
        (
            (NEW, "Tunnel test before joining: the address is checked before Studio launches."),
            (NEW, "System tray icon. Closing with a session running offers to keep it in the tray."),
            (NEW, "Tray notification when the server is ready while the window is hidden."),
            (NEW, "Changelog in Support."),
            (IMPROVED, "Copy actions now confirm right on the button instead of only at the bottom."),
            (IMPROVED, "Fields show a green check when the value is valid. User ID must be a number above 0."),
            (IMPROVED, "Help icon on TeamTest port explaining what the port is for."),
        ),
    ),
    Release(
        "2.0.0",
        "",
        (
            (NEW, "New RSG interface. Launcher logic by s0m3thing_matters is unchanged."),
            (NEW, "Sound and taskbar flash when the server is ready, with a switch in Settings."),
            (NEW, "Recent tunnels, invite message, QR code and live ping on the Join page."),
            (NEW, "Drag and drop a .rbxl / .rbxlx map anywhere in the window."),
        ),
    ),
)
