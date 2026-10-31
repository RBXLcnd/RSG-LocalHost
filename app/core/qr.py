from __future__ import annotations


def qr_matrix(text: str) -> list[list[bool]]:
    """QR modules for `text` (True = dark), without the quiet zone.

    `segno` is imported lazily so the app still starts if it is missing."""
    import segno

    code = segno.make(text, error="m", micro=False)
    return [[bool(cell) for cell in row] for row in code.matrix]
