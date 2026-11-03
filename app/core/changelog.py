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
        "2.4.0",
        "2026-11-01",
        (
            (NEW, "Update notice: the app checks GitHub for a newer release and shows an “Update” button at the top, plus a Check now button in Settings > Updates. It never installs anything by itself."),
            (IMPROVED, "Your settings, profiles, history and Discord sign-in are now kept in your user data folder, so updating or reinstalling the app never loses them. Existing data is moved over automatically."),
            (NEW, "Language button (top right): switch the whole app between English and Português, instantly. The choice is remembered."),
            (NEW, "Background themes: pick Classic, Aurora, Grid, Ring, Hex or Nebula in Settings > Appearance. It applies instantly and is remembered."),
            (NEW, "Player count in the Discord /server-status panel. Add the PlayerCountReporter script to your game (it sends the number to the app on this PC)."),
            (NEW, "Private server: a switch in the 24/7 section keeps the server out of the Discord /server-status list. Nothing about it is sent to Discord."),
            (IMPROVED, "The Settings and Create pages now scroll when the window is small."),
            (NEW, "You can now switch between a dark and a light look and pick the accent color (or any custom color) in Settings > Appearance. It applies instantly."),
            (NEW, "You can now export and import your settings and profiles from Settings > Backup, to keep a copy or move to another PC. The Discord sign-in and Studio path are never included."),
            (NEW, "The Overview page now shows your last 7 days of hosting: time online, sessions, player peak and a small chart. The peak needs the player count script in your game."),
            (NEW, "A short welcome assistant now appears the first time you open the app: language, Roblox Studio, Discord (optional) and the 24/7 mode. You can change everything later in Settings."),
            (IMPROVED, "Your Discord sign-in key is now stored encrypted with Windows, so only your Windows account can read it. An older plain-text key is encrypted automatically."),
            (IMPROVED, "Stopping a session now closes only the Studio windows this app launched. Your other Roblox Studio windows are left alone."),
        ),
    ),
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
