"""Local browser setup safety checks; no real Chrome or Facebook sign-in."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from facebook_browser import approved_url, post_command, get_state, base_dir


class FacebookBrowserSetupTests(unittest.TestCase):
    def test_allow_only_facebook_https(self):
        for url in (
            "https://www.facebook.com/",
            "https://www.facebook.com/photo/?fbid=123",
            "https://m.facebook.com/tuoitretruongthptdian",
            "https://facebook.com/login",
        ):
            with self.subTest(url=url):
                self.assertEqual(approved_url(url), url)

    def test_reject_non_facebook_and_network_exfiltration(self):
        for url in (
            "http://www.facebook.com/",
            "https://facebook.com.evil.example/steal",
            "https://facebook.com@evil.example/",
            "https://evil.example@facebook.com/",
            "https://www.facebook.com:9222/",
            "file:///C:/Users/abc23/cookies.sqlite",
            "javascript:alert(1)",
            "https://127.0.0.1:3000/",
            "https://www.facebook.com/\nX-Injected: yes",
            "https://facebook.com\\@evil.example/path",
            "",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    approved_url(url)

    def test_files_are_local_to_windows_profile_not_git(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ", {"LOCALAPPDATA": td}
        ):
            self.assertEqual(base_dir(), Path(td) / "VOIDSCAN" / "facebook-browser")
            file=post_command("open",url="https://www.facebook.com/")
            self.assertTrue(file.is_file())
            record=json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(record["command"],"open")
            self.assertEqual(record["url"],"https://www.facebook.com/")
            self.assertNotIn("cookie",str(record).lower())
            self.assertEqual(get_state()["state"],"not_started")

    def test_disallow_arbitrary_commands(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ", {"LOCALAPPDATA": td}
        ):
            with self.assertRaises(ValueError):
                post_command("execute_javascript",url="https://facebook.com/")
            with self.assertRaises(ValueError):
                post_command("open",url="https://other.example/")

if __name__ == "__main__":
    unittest.main()
