from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "LocalHost"
PROXY_PORT = 55555
MAX_RECENT_TUNNELS = 8
MAX_RECENT_MAPS = 8
MAX_PROFILES = 12
MAX_HISTORY = 50  # sessions kept on disk
OVERVIEW_HISTORY_ROWS = 4  # sessions shown on the Overview page

WINDOW_W = 1080
WINDOW_H = 700
WINDOW_MIN_W = 780
WINDOW_MIN_H = 540

# In the PyInstaller .exe the data files live next to the executable, not in the temp folder.
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parents[2]

# Settings, profiles, history and the Discord sign-in live in the user's data folder
# (%APPDATA%\RSG LocalHost), NOT next to the program, so updating, reinstalling or moving the app
# never loses them. Without APPDATA (not Windows) they stay next to the program, as before.
DATA_NAME = "mattslocalhost_data.json"
_appdata = os.environ.get("APPDATA")
DATA_DIR = Path(_appdata) / "RSG LocalHost" if _appdata else ROOT_DIR
DATA_FILE = DATA_DIR / DATA_NAME
CACHE_DIR = DATA_DIR / ".localhost_cache"


def _migrate_legacy_data() -> None:
    """First run of a version that uses the data folder: bring over the file an older version kept next to the exe."""
    legacy = ROOT_DIR / DATA_NAME
    try:
        if DATA_DIR != ROOT_DIR and legacy.is_file() and not DATA_FILE.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy, DATA_FILE)
    except OSError:
        pass  # worst case the app starts with defaults; nothing is lost on disk


_migrate_legacy_data()
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
SOUNDS_DIR = ASSETS_DIR / "sounds"
