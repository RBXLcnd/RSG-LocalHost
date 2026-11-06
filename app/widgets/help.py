from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from app.core import motion
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

# topic -> (title, explanation, example or ""). English texts; the language tables translate them.
TOPICS: dict[str, tuple[str, str, str]] = {
    "overview_week": (
        "Last 7 days",
        "Time online, number of sessions and the highest number of players at once during the last 7 days, taken from the sessions saved on this PC.",
        "The player peak needs the PlayerCountReporter script in your game. Without it the peak stays empty.",
    ),
    "overview_recent": (
        "Recent sessions",
        "Your latest sessions: the mode, the map or tunnel used, how long it ran and when it started.",
        "",
    ),
    "join_recent": (
        "Recent tunnels",
        "Tunnels you joined before. Click one to fill the address again, or remove the ones you no longer need.",
        "",
    ),
    "create_summary": (
        "Summary",
        "A preview of what will be launched: User ID, tunnel, port and map. Check it before you start.",
        "",
    ),
    "create_account": (
        "Discord account",
        "You need to sign in to create a server. The key is stored encrypted on this PC, so only your Windows account can read it.",
        "In the Discord server run /host-login and paste the key it gives you.",
    ),
    "create_auto": (
        "24/7 auto-cycle",
        "Keeps the server online for some hours, pauses it, then starts again with the next map. Pressing Stop ends the cycle.",
        "Hours online 6 and Hours paused 1: online for 6 hours, off for 1 hour, then back.",
    ),
    "create_rotation": (
        "Map rotation",
        "A list of maps that are used one after another, each time the server comes back.",
        "",
    ),
    "create_private": (
        "Private server",
        "Keeps the server out of the Discord /server-status list. Nothing about it is sent to Discord.",
        "Share the tunnel address only with the people you want.",
    ),
    "console": (
        "Console",
        "The live log of this session. Every line has a type: OK, INFO, WARN or ERR. Click the chips above to hide a type.",
        "Use Copy diagnostics to share a summary. Your tunnel address and User ID are hidden.",
    ),
    "settings_studio": (
        "Studio executable",
        "The file RobloxStudioBeta.exe that this app launches. Use Detect automatically to find it, or choose it yourself.",
        "Usually in AppData\\Local\\Roblox\\Versions\\version-...",
    ),
    "settings_notifications": (
        "Notifications",
        "When the server is ready the app plays a soft sound and flashes the taskbar button if the window is in the background.",
        "",
    ),
    "settings_auto": (
        "24/7 mode",
        "Shows the 24/7 section when you create a server. Turn it off to hide it. A running 24/7 cycle must be stopped first.",
        "",
    ),
    "settings_appearance": (
        "Appearance",
        "Dark or light look, accent color, background theme and animations. Everything applies instantly and is remembered.",
        "",
    ),
    "settings_updates": (
        "Updates",
        "The app can check GitHub for a newer release and show an Update button at the top. It never installs anything by itself.",
        "",
    ),
    "settings_backup": (
        "Backup",
        "Export your settings and profiles to a file, or import them on another PC. The Discord sign-in and the Studio path are never included.",
        "",
    ),
}


class HelpPopover(QFrame):
    """Small card that opens under the "?" and closes when you click anywhere else."""

    def __init__(self, topic: str) -> None:
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("helpPopover")
        title, body, example = TOPICS[topic]
        col = QVBoxLayout(self)
        col.setContentsMargins(16, 14, 16, 14)
        col.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("helpTitle")
        col.addWidget(heading)
        text = QLabel(body)
        text.setObjectName("helpBody")
        text.setWordWrap(True)
        col.addWidget(text)
        if example:
            box = QLabel(example)
            box.setObjectName("helpExample")
            box.setWordWrap(True)
            col.addWidget(box)
        self._fit()

    def _fit(self) -> None:
        # word-wrapped labels only know their height once the width is fixed
        width = 320
        lay = self.layout()
        lay.activate()
        self.setFixedSize(width, max(lay.heightForWidth(width), lay.sizeHint().height()))

    def show_under(self, widget: QWidget) -> None:
        self._fit()
        spot = widget.mapToGlobal(QPoint(0, widget.height() + 6))
        screen = QGuiApplication.screenAt(spot) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        x = min(max(area.left() + 8, spot.x() - 8), area.right() - self.width() - 8)
        y = spot.y()
        if y + self.height() > area.bottom() - 8:  # no room below: open above the button
            y = widget.mapToGlobal(QPoint(0, 0)).y() - self.height() - 6
        self.move(x, max(area.top() + 8, y))
        motion.fade_in(self)
        self.show()


class HelpButton(QPushButton):
    """Round "?" that opens the explanation of one topic."""

    def __init__(self, topic: str) -> None:
        super().__init__("?")
        self.topic = topic
        self.setObjectName("helpButton")
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Explain this section")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.clicked.connect(self._open)
        self._popover: HelpPopover | None = None

    def _open(self) -> None:
        self._popover = HelpPopover(self.topic)
        self._popover.show_under(self)


def with_help(label: QWidget, topic: str) -> QWidget:
    """The label followed by its "?" button, as one widget that goes wherever the label went."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(label)
    layout.addWidget(HelpButton(topic), 0, Qt.AlignmentFlag.AlignVCenter)
    layout.addStretch(1)
    return row
