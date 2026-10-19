"""One-click Windows launcher: start VOIDSCAN if needed, then open browser."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from secret_store import TokenStoreError, read_meta_user_token

# Windows consoles can default to CP1258, which cannot encode many Vietnamese
# characters. Never let a diagnostic print crash the one-click launcher.
if os.name == "nt" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("VOIDSCAN_PORT", "3000"))
URL = f"http://127.0.0.1:{PORT}"


def server_ready() -> bool:
    try:
        with urllib.request.urlopen(URL + "/api/health", timeout=0.8) as response:
            data = json.load(response)
        return data.get("ok") is True and data.get("app") == "VOIDSCAN"
    except (OSError, ValueError, TimeoutError):
        return False


def ensure_credentials():
    if os.environ.get("META_USER_ACCESS_TOKEN", "").strip() or os.environ.get(
        "META_PAGE_ACCESS_TOKEN", ""
    ).strip():
        return True
    try:
        if read_meta_user_token():
            return True
    except TokenStoreError as exc:
        print(f"Không đọc được token lưu trước đó: {exc}")
    print("Chưa lưu Access Token cho phiên khởi động sau.")
    print("VOIDSCAN đang mở hộp thoại để bạn dán token một lần.")
    from token_dialog import enroll_gui
    try:
        return enroll_gui()
    except (TokenStoreError, OSError, KeyboardInterrupt) as exc:
        print("Không thiết lập được token: " + str(exc))
        return False


def main():
    if sys.platform != "win32":
        print("Trình mở nhanh chỉ hỗ trợ Windows. Có thể dùng python server.py.")
        return 1

    # Credential enrollment comes first, including when an old server is running.
    # The token is encrypted for future sessions, never displayed by the launcher.
    if not ensure_credentials():
        print("Bạn vẫn có thể mở VOIDSCAN không có token bằng python server.py.")
        return 2

    if server_ready():
        print("VOIDSCAN đang chạy. Đang mở giao diện...")
        webbrowser.open(URL)
        return 0

    print("Đang khởi động VOIDSCAN...")
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    child = subprocess.Popen([sys.executable, "-u", "server.py"], cwd=str(ROOT),
                             creationflags=flags)
    for _ in range(40):
        if server_ready():
            webbrowser.open(URL)
            print("VOIDSCAN đã sẵn sàng tại " + URL)
            return 0
        if child.poll() is not None:
            print("Server thoát trước khi sẵn sàng. Xem cửa sổ server để biết lỗi.")
            return 1
        time.sleep(0.25)
    print("Server chưa sẵn sàng; xem lỗi trong cửa sổ server.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
