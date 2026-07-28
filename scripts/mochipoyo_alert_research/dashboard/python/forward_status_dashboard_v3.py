from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path
from typing import Any

import forward_status_dashboard_v2 as v2

base = v2.base
DASHBOARD_VERSION = "M9V_PLUS_FORWARD_STATUS_DASHBOARD_V3_WINDOWS_DELETE_SHARE_SAFE"


def _windows_shared_read(path: Path) -> bytes:
    """Read without blocking atomic replacement on Windows.

    FILE_SHARE_DELETE is required because the forward loops publish status JSON
    through os.replace(). A normal reader can briefly deny that replacement.
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE

    read_file = kernel32.ReadFile
    read_file.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    read_file.restype = wintypes.BOOL

    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    generic_read = 0x80000000
    file_share_read = 0x00000001
    file_share_write = 0x00000002
    file_share_delete = 0x00000004
    open_existing = 3
    file_attribute_normal = 0x00000080
    invalid_handle_value = ctypes.c_void_p(-1).value

    handle = create_file(
        str(path),
        generic_read,
        file_share_read | file_share_write | file_share_delete,
        None,
        open_existing,
        file_attribute_normal,
        None,
    )
    if handle == invalid_handle_value:
        error = ctypes.get_last_error()
        raise OSError(error, f"CreateFileW failed for shared read: {path}")

    chunks: list[bytes] = []
    try:
        while True:
            buffer = ctypes.create_string_buffer(64 * 1024)
            read = wintypes.DWORD(0)
            ok = read_file(handle, buffer, len(buffer), ctypes.byref(read), None)
            if not ok:
                error = ctypes.get_last_error()
                raise OSError(error, f"ReadFile failed: {path}")
            if read.value == 0:
                break
            chunks.append(buffer.raw[: read.value])
    finally:
        close_handle(handle)
    return b"".join(chunks)


def shared_read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "MISSING"
    try:
        raw = _windows_shared_read(path) if os.name == "nt" else path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON_NOT_OBJECT"
    return payload, None


base.read_json = shared_read_json


if __name__ == "__main__":
    raise SystemExit(base.main())
