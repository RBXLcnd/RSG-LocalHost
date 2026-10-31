from __future__ import annotations

import sys

from PySide6.QtCore import QDir, QLockFile, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.settings import SettingsStore
from app.core.studio import generate_guid, get_studio_path, launch_server
from app.styles.theme import apply_theme
from app.ui.splash import StartupSplash
from app.ui.window import MainWindow


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

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("RSG LocalHost")
    qt_app.setOrganizationName("LocalHost")
    apply_theme(qt_app)

    # Only one RSG LocalHost per PC: a second copy would try to create a second server on the same port.
    lock = QLockFile(QDir.temp().filePath("rsg-localhost.lock"))
    lock.setStaleLockTime(0)  # a lock left by a crashed run is detected by its dead PID
    if not lock.tryLock(100):
        QMessageBox.warning(None, "RSG LocalHost", "RSG LocalHost is already running. Only one server can exist at a time.")
        return 0
    qt_app._instance_lock = lock  # keep it alive for the whole run

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
        state["splash"] = None

    splash.finished.connect(show_main)
    splash.start()
    return qt_app.exec()
