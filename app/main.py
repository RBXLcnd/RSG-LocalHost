from __future__ import annotations

import sys

from PySide6.QtCore import QDir, QLockFile, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app.core import motion, protocol
from app.core.settings import SettingsStore
from app.core.studio import generate_guid, get_studio_path, launch_server
from app.styles import palette
from app.styles.theme import apply_theme
from app.ui.splash import StartupSplash
from app.ui.window import MainWindow
from app.core import i18n
from app.widgets import brand


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith((".rbxl", ".rbxlx")):
        settings = SettingsStore().load()
        studio = settings.studio_path if settings.studio_path else get_studio_path()
        parent_guid = generate_guid()
        play_guid = generate_guid()
        launch_server(
            studio,
            settings.server_port,
            settings.user_id,
            parent_guid,
            play_guid,
            sys.argv[1],
            startup_players=1,
            use_runtime_place=True,
        )
        return 0

    link = next((protocol.parse_link(a) for a in sys.argv[1:] if a.lower().startswith("rsg:")), None)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("RSG LocalHost")
    qt_app.setOrganizationName("LocalHost")
    saved = SettingsStore().load()
    palette.configure(saved.appearance, saved.accent)
    motion.configure(saved.animations)
    apply_theme(qt_app)
    brand.set_theme(saved.background_theme)
    i18n.install_qt_hooks()
    i18n.set_language(saved.language)

    # Only one RSG LocalHost per PC: a second copy would try to create a second server on the same port.
    lock = QLockFile(QDir.temp().filePath("rsg-localhost.lock"))
    lock.setStaleLockTime(0)  # a lock left by a crashed run is detected by its dead PID
    if not lock.tryLock(100):
        if link and protocol.send_to_running(protocol.build_link(link)):
            return 0  # the open copy takes the invite
        QMessageBox.warning(None, "RSG LocalHost", "RSG LocalHost is already running. Only one server can exist at a time.")
        return 0
    qt_app._instance_lock = lock  # keep it alive for the whole run
    protocol.register()  # rsg:// links open this program (packaged exe only)
    link_server = protocol.LinkServer(qt_app)
    qt_app._link_server = link_server

    state: dict[str, MainWindow | StartupSplash | None] = {"window": None, "splash": None}
    splash = StartupSplash()
    state["splash"] = splash

    def show_main() -> None:
        window = MainWindow()
        state["window"] = window
        qt_app.aboutToQuit.connect(window.shutdown_status)
        window.show()
        splash.close()
        QTimer.singleShot(250, window.ask_auto_feature_if_needed)
        QTimer.singleShot(1500, window.verify_discord_session)
        link_server.link_received.connect(window.open_join_link)
        if link:
            QTimer.singleShot(600, lambda: window.open_join_link(link))
        state["splash"] = None

    splash.finished.connect(show_main)
    splash.start()
    return qt_app.exec()
