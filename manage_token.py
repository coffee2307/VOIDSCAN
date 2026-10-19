"""One-time, local interactive token enrollment. Never prints or transmits a token."""
from __future__ import annotations
import argparse
import getpass
import sys
from secret_store import (
    TokenStoreError, save_meta_user_token, read_meta_user_token,
    clear_meta_user_token,
)


def enroll() -> bool:
    print("VOIDSCAN | Lưu Meta User Access Token (Windows DPAPI)")
    print("Token được mã hóa theo tài khoản Windows; KHÔNG lưu trong .env hoặc Git.")
    print("Dán token ngay tại máy của bạn. Ký tự không hiển thị trên màn hình.")
    token = getpass.getpass("Access Token: ")
    if not token.strip():
        print("Chưa nhập token; không thay đổi dữ liệu.")
        return False
    save_meta_user_token(token)
    # Forget our local reference; the process exits immediately after enrollment.
    token = None
    if not read_meta_user_token():
        raise TokenStoreError("Không xác minh được token mã hóa.")
    print("Đã lưu token mã hóa thành công cho tài khoản Windows hiện tại.")
    print("Từ lần tới, dùng start-voidscan.bat hoặc python server.py.")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="VOIDSCAN local Meta token manager")
    parser.add_argument("action", nargs="?", default="set",
                        choices=("set", "terminal", "status", "delete"))
    args = parser.parse_args(argv)
    try:
        if args.action == "set":
            from token_dialog import enroll_gui
            return 0 if enroll_gui() else 2
        if args.action == "terminal":
            return 0 if enroll() else 2
        if args.action == "status":
            available = read_meta_user_token()
            print("DPAPI_TOKEN=" + ("available" if available else "not-configured"))
            return 0 if available else 1
        if args.action == "delete":
            removed = clear_meta_user_token()
            print("Đã xóa token mã hóa." if removed else "Không tìm thấy token đã lưu.")
            return 0
    except (TokenStoreError, OSError, KeyboardInterrupt) as exc:
        print("Lỗi cấu hình token: " + ("đã hủy." if isinstance(exc, KeyboardInterrupt)
                                       else str(exc)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
