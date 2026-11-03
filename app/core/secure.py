"""Protect small secrets (the Discord key) with Windows DPAPI.

The encrypted value is tied to the current Windows user account: copying the data file to another
account or computer gives an unreadable blob (the app then just asks for a new Discord sign-in).
On systems without DPAPI (not Windows) the value is stored as-is.
"""
from __future__ import annotations

import base64
import os

PREFIX = "dpapi:"


def available() -> bool:
    return os.name == "nt"


def _blob_call(data: bytes, encrypt: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(data, len(data))
    source = DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    target = DataBlob()
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    if encrypt:
        ok = crypt32.CryptProtectData(ctypes.byref(source), "RSG LocalHost", None, None, None, 0, ctypes.byref(target))
    else:
        ok = crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target))
    if not ok:
        raise OSError("DPAPI call failed")
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(target.pbData)


def protect(value: str) -> str:
    """Text to store in the file. Empty stays empty; without DPAPI (or on error) the value is kept as is."""
    if not value or not available():
        return value
    try:
        return PREFIX + base64.b64encode(_blob_call(value.encode("utf-8"), True)).decode("ascii")
    except Exception:
        return value


def unprotect(stored: str) -> str:
    """Original text. Old plain values pass through; a blob this user can't decrypt becomes empty."""
    if not stored.startswith(PREFIX):
        return stored
    if not available():
        return ""
    try:
        return _blob_call(base64.b64decode(stored[len(PREFIX):]), False).decode("utf-8")
    except Exception:
        return ""
