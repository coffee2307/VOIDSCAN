"""Tests use synthetic tokens only, never the user's Meta credential."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import secret_store


class TokenStorageTests(unittest.TestCase):
    def test_token_path_is_outside_repository(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\Fake\AppData\Local"}):
            p = secret_store.token_path()
            self.assertEqual(p.name, "meta-user-token.dpapi")
            self.assertIn("VOIDSCAN", str(p))
            self.assertNotIn(r"F:\VOIDSCAN", str(p))

    def test_rejects_short_or_invalid_token(self):
        with tempfile.TemporaryDirectory() as d:
            for value in ("", "short", "TOKEN WITH SPACE" * 15):
                with self.subTest(value=value[:10]), self.assertRaises(
                    secret_store.TokenStoreError
                ):
                    secret_store.save_meta_user_token(value, Path(d) / "secret.dpapi")

    def test_env_token_has_precedence(self):
        with patch.dict(os.environ, {"META_USER_ACCESS_TOKEN": "existing",
                                     "META_PAGE_ACCESS_TOKEN": ""}):
            with patch("secret_store.read_meta_user_token") as read:
                self.assertFalse(secret_store.load_saved_meta_token_into_process())
                read.assert_not_called()

    def test_missing_encrypted_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "missing.dpapi"
            self.assertIsNone(secret_store.read_meta_user_token(p))
            self.assertFalse(secret_store.clear_meta_user_token(p))

    @unittest.skipUnless(sys.platform == "win32", "Windows DPAPI is Windows-only")
    def test_dpapi_round_trip_and_delete(self):
        fake_token = "SYNTHETIC_TEST_TOKEN_NOT_REAL_" + "A" * 60
        with tempfile.TemporaryDirectory() as d:
            destination = Path(d) / "fake-token.dpapi"
            secret_store.save_meta_user_token(fake_token, destination)
            cipher_bytes = destination.read_bytes()
            self.assertNotIn(fake_token.encode(), cipher_bytes)
            self.assertNotIn(b"SYNTHETIC_TEST_TOKEN", cipher_bytes)
            self.assertEqual(secret_store.read_meta_user_token(destination), fake_token)
            self.assertTrue(secret_store.clear_meta_user_token(destination))
            self.assertIsNone(secret_store.read_meta_user_token(destination))

    @unittest.skipUnless(sys.platform == "win32", "Requires same-user Windows DPAPI")
    def test_server_auto_loads_encrypted_token_in_fresh_process(self):
        """Verify startup uses ciphertext without inheriting any plaintext env token."""
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="voidscan-dpapi-") as d:
            base = Path(d)
            local = base / "LocalAppData"
            encrypted = local / "VOIDSCAN" / "secrets" / "meta-user-token.dpapi"
            synthetic = "SYNTHETIC_INTEGRATION_TOKEN_" + "Z" * 55
            secret_store.save_meta_user_token(synthetic, encrypted)
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
            env = dict(os.environ)
            env.pop("META_USER_ACCESS_TOKEN", None)
            env.pop("META_PAGE_ACCESS_TOKEN", None)
            env["LOCALAPPDATA"] = str(local)
            env["VOIDSCAN_DATA_DIR"] = str(base / "isolated-data")
            env["VOIDSCAN_PORT"] = str(port)
            proc = subprocess.Popen([sys.executable, "-u", "server.py"],
                cwd=str(root), env=env, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            try:
                state = None
                for _ in range(45):
                    if proc.poll() is not None:
                        break
                    try:
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}/api/status", timeout=.4
                        ) as response:
                            state = json.load(response)
                        break
                    except (OSError, ValueError):
                        time.sleep(.1)
                self.assertIsNotNone(state, "Isolated server did not start")
                self.assertTrue(state["connectors"]["meta"])
                self.assertEqual(state["connectors"]["meta_mode"], "user")
                self.assertNotIn(synthetic, json.dumps(state))
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)

    def test_corrupt_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.dpapi"
            p.write_bytes(b"bad")
            with self.assertRaises(secret_store.TokenStoreError):
                secret_store.read_meta_user_token(p)


if __name__ == "__main__":
    unittest.main()
