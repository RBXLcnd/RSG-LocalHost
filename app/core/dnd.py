from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData

PLACE_SUFFIXES = {".rbxl", ".rbxlx"}


def dropped_files(mime: QMimeData) -> list[Path]:
    """Local files carried by a drag payload (empty for text, links, etc.)."""
    if not mime.hasUrls():
        return []
    return [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile() and url.toLocalFile()]


def place_files(files: list[Path]) -> list[Path]:
    return [f for f in files if f.suffix.lower() in PLACE_SUFFIXES and f.is_file()]
