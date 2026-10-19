"""User-scoped Meta access token storage using native Windows DPAPI.

The ciphertext lives outside the Git repository under LOCALAPPDATA.
No plaintext .env file, token logging, cloud sync, third-party package,
or user-level environment registry variable is required.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import sys
from pathlib import Path

_TOKEN_FILE = "meta-user-token.dpapi"


class TokenStoreError(RuntimeError):
    """Safe diagnostic without secret values."""


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def token_path() -> Path:
    """Per-Windows-user storage, always outside the working repository."""
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise TokenStoreError("Không tìm thấy LOCALAPPDATA của tài khoản Windows.")
    return Path(base) / "VOIDSCAN" / "secrets" / _TOKEN_FILE


def _windows_dpapi(data: bytes, protect: bool) -> bytes:
    if sys.platform != "win32":
        raise TokenStoreError("Lưu token mã hóa yêu cầu hệ điều hành Windows.")
    if not data:
        raise TokenStoreError("Không thể xử lý token rỗng.")
    crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    src_buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(len(data), ctypes.cast(src_buffer, ctypes.POINTER(ctypes.c_byte)))
    target = _DataBlob()
    blob_ptr = ctypes.POINTER(_DataBlob)
    if protect:
        fn = crypt32.CryptProtectData
        fn.argtypes = [blob_ptr, wintypes.LPCWSTR, blob_ptr,
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, blob_ptr]
        fn.restype = wintypes.BOOL
        succeeded = fn(ctypes.byref(source), "VOIDSCAN Meta access token",
                       None, None, None, 0x01, ctypes.byref(target))
    else:
        fn = crypt32.CryptUnprotectData
        fn.argtypes = [blob_ptr, ctypes.POINTER(wintypes.LPWSTR), blob_ptr,
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, blob_ptr]
        fn.restype = wintypes.BOOL
        succeeded = fn(ctypes.byref(source), None, None,
                       None, None, 0x01, ctypes.byref(target))
    if not succeeded:
        raise TokenStoreError("Windows không thể giải mã dữ liệu token đã lưu. Hãy lưu lại token.")
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(target.pbData, ctypes.c_void_p))


def save_meta_user_token(secret: str, path: Path | None = None) -> Path:
    if not isinstance(secret, str):
        raise TokenStoreError("Access Token không hợp lệ.")
    secret = secret.strip()
    if len(secret) < 30 or len(secret) > 8192 or any(c.isspace() for c in secret):
        raise TokenStoreError("Access Token không hợp lệ: kiểm tra nội dung đã dán.")
    destination = Path(path) if path is not None else token_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    ciphertext = _windows_dpapi(secret.encode("utf-8"), protect=True)
    # Atomic replace; never persist or print a plaintext temporary file.
    staging = destination.with_suffix(".tmp")
    try:
        staging.write_bytes(ciphertext)
        os.chmod(staging, 0o600)
        staging.replace(destination)
    finally:
        staging.unlink(missing_ok=True)
    return destination


def read_meta_user_token(path: Path | None = None) -> str | None:
    stored = Path(path) if path is not None else token_path()
    if not stored.is_file():
        return None
    try:
        blob = stored.read_bytes()
        if len(blob) < 64 or len(blob) > 65536:
            raise TokenStoreError("File token đã mã hóa không hợp lệ.")
        value = _windows_dpapi(blob, protect=False).decode("utf-8")
        if not 30 <= len(value) <= 8192:
            raise TokenStoreError("Dữ liệu Access Token đã lưu không hợp lệ.")
        return value
    except (OSError, UnicodeError) as exc:
        raise TokenStoreError("Không đọc được token mã hóa; hãy lưu lại token.") from None


def clear_meta_user_token(path: Path | None = None) -> bool:
    stored = Path(path) if path is not None else token_path()
    if stored.exists():
        stored.unlink()
        return True
    return False


def load_saved_meta_token_into_process() -> bool:
    """An explicitly configured process token always takes precedence."""
    if os.environ.get("META_USER_ACCESS_TOKEN", "").strip() or os.environ.get(
        "META_PAGE_ACCESS_TOKEN", ""
    ).strip():
        return False
    token = read_meta_user_token()
    if not token:
        return False
    # Process-scoped env only: do not write a persistent plaintext env registry key.
    os.environ["META_USER_ACCESS_TOKEN"] = token
    return True
