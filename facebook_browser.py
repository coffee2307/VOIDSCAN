"""VOIDSCAN isolated, user-controlled Facebook Chrome browser.

Login is MANUAL in a visible Chrome window. Playwright uses an internal pipe:
no remotely exposed debugging port, no passwords/OTP/cookies exported,
no profile-personal-data collection or bypass of Facebook access controls.

Commands:
  python facebook_browser.py launch [--url https://www.facebook.com/...]
  python facebook_browser.py open --url https://www.facebook.com/...
  python facebook_browser.py status
  python facebook_browser.py stop
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_URL = "https://www.facebook.com/"
FACEBOOK_HOSTS = frozenset({
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "web.facebook.com",
})


def approved_url(value: str) -> str:
    """Only navigate to HTTPS Facebook; forbid credentials and custom ports."""
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Invalid Facebook URL")
    try:
        parsed = urlsplit(value)
        accepted = (parsed.scheme == "https"
                    and parsed.hostname in FACEBOOK_HOSTS
                    and not parsed.username and not parsed.password
                    and parsed.port is None
                    and all(ord(c) >= 32 for c in value))
    except ValueError:
        accepted = False
    if not accepted:
        raise ValueError("Only HTTPS Facebook URLs without embedded credentials are allowed")
    return value


def base_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("LOCALAPPDATA is not available; Windows account required")
    return Path(base) / "VOIDSCAN" / "facebook-browser"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def metadata_dir() -> Path:
    path = base_dir() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_file() -> Path:
    return metadata_dir() / "status.json"


def write_state(status: str) -> None:
    # Do NOT serialize login state, names, URLs, cookies or access tokens.
    doc = {"state": status, "pid": os.getpid(), "updated_at": now_utc()}
    path = state_file()
    tmp = path.with_name("status-" + uuid.uuid4().hex + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def get_state() -> dict:
    path = state_file()
    if not path.is_file():
        return {"state": "not_started"}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return {"state": doc.get("state", "unknown"),
                "pid": doc.get("pid"), "updated_at": doc.get("updated_at")}
    except (OSError, ValueError):
        return {"state": "unknown"}


def command_dir() -> Path:
    path = metadata_dir() / "commands"
    path.mkdir(parents=True, exist_ok=True)
    return path


def post_command(operation: str, *, url: str | None = None) -> Path:
    if operation not in {"open", "stop"}:
        raise ValueError("Unsupported operation")
    request = {"command": operation, "created_at": now_utc()}
    if operation == "open":
        request["url"] = approved_url(url or "")
    file = command_dir() / (uuid.uuid4().hex + ".json")
    with file.open("x", encoding="utf-8") as handle:
        json.dump(request, handle)
    return file


def launch(url: str) -> int:
    """Keep Chrome visible for manual sign-in, then accept local URL commands."""
    approved_url(url)
    if sys.platform != "win32":
        print("VOIDSCAN Facebook Browser only supports this Windows installation.")
        return 2

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright missing. Run setup-voidscan-facebook.bat first.")
        return 2

    profile = base_dir() / "chrome-profile"
    profile.mkdir(parents=True, exist_ok=True)
    write_state("launching")
    print("VOIDSCAN Chrome: signing in is a manual user action.")
    print("No cookies, passwords, OTP or profile identities are read or exported.")
    print("Close this dedicated Chrome window to end the session.")
    try:
        with sync_playwright() as playwright:
            # Only an internal pipe to Playwright; never bind remote-debugging
            # port 9222. Never use the personal Chrome Default profile.
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                channel="chrome",
                headless=False,
                viewport=None,
                accept_downloads=False,
                ignore_https_errors=False,
                args=["--no-first-run", "--no-default-browser-check"],
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except PlaywrightError:
                # Chrome may be open even if Facebook returns a network error.
                pass
            write_state("window_open")
            print("BROWSER_WINDOW_OPEN=TRUE")
            print("Wait for user to sign in. The session persists locally.")
            while context.pages:
                for file in sorted(command_dir().glob("*.json")):
                    try:
                        cmd = json.loads(file.read_text(encoding="utf-8"))
                        operation = cmd.get("command")
                        if operation == "stop":
                            print("STOP_REQUESTED=TRUE")
                            return 0
                        if operation == "open":
                            target = approved_url(cmd.get("url"))
                            page = context.pages[0] if context.pages else context.new_page()
                            page.goto(target, wait_until="domcontentloaded", timeout=25000)
                            print("FACEBOOK_PAGE_OPENED=TRUE")
                    except (ValueError, OSError, PlaywrightError, TypeError):
                        # Never log HTML, actor IDs, names, passwords or cookies.
                        print("BROWSER_COMMAND_FAILED=TRUE")
                    finally:
                        try:
                            file.unlink(missing_ok=True)
                        except OSError:
                            pass
                time.sleep(0.75)
            return 0
    except PlaywrightError:
        write_state("launch_failed")
        print("Chrome launch failed; close any previous VOIDSCAN Chrome windows.")
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        write_state("closed")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="VOIDSCAN isolated Chrome session")
    sub = parser.add_subparsers(dest="action", required=True)
    lc = sub.add_parser("launch", help="Open visible Chrome for manual Facebook sign-in")
    lc.add_argument("--url", default=DEFAULT_URL)
    oc = sub.add_parser("open", help="Request Facebook URL in running Chrome")
    oc.add_argument("--url", required=True)
    sub.add_parser("status", help="Show process state, never cookies or login details")
    sub.add_parser("stop", help="Close separate Chrome session")
    args = parser.parse_args(argv)
    try:
        if args.action == "launch":
            return launch(args.url)
        if args.action == "open":
            post_command("open", url=args.url)
            print("REQUEST_SENT=TRUE (running session required)")
        elif args.action == "stop":
            post_command("stop")
            print("STOP_REQUEST_SENT=TRUE")
        else:
            print(json.dumps(get_state(), ensure_ascii=True, sort_keys=True))
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print("BROWSER_SETUP_ERROR=" + type(error).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
