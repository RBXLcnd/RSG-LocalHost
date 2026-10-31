from __future__ import annotations

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

# No .exe (PyInstaller) os dados ficam ao lado do executável, não na pasta temporária.
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT_DIR / "mattslocalhost_data.json"
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
SOUNDS_DIR = ASSETS_DIR / "sounds"
