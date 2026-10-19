"""Tests for the paste-friendly enrollment path; never touches real clipboard/token."""
from __future__ import annotations
import unittest
from pathlib import Path
from unittest.mock import patch

import manage_token
import launch_voidscan


class PasteDialogTests(unittest.TestCase):
    def test_set_uses_graphical_dialog(self):
        with patch("token_dialog.enroll_gui", return_value=True) as gui:
            with patch("manage_token.enroll") as old_input:
                self.assertEqual(manage_token.main(["set"]), 0)
                gui.assert_called_once_with()
                old_input.assert_not_called()

    def test_cancel_does_not_claim_saved(self):
        with patch("token_dialog.enroll_gui", return_value=False):
            self.assertEqual(manage_token.main(["set"]), 2)

    def test_one_click_launcher_invokes_dialog_when_no_token(self):
        with patch.dict("os.environ", {
                "META_USER_ACCESS_TOKEN": "",
                "META_PAGE_ACCESS_TOKEN": "",
            }), patch("launch_voidscan.read_meta_user_token", return_value=None), \
                patch("token_dialog.enroll_gui", return_value=True) as gui:
            self.assertTrue(launch_voidscan.ensure_credentials())
            gui.assert_called_once_with()

    def test_stored_token_does_not_open_dialog(self):
        with patch.dict("os.environ", {
                "META_USER_ACCESS_TOKEN": "",
                "META_PAGE_ACCESS_TOKEN": "",
            }), patch("launch_voidscan.read_meta_user_token", return_value="SYNTHETIC"), \
                patch("token_dialog.enroll_gui") as gui:
            self.assertTrue(launch_voidscan.ensure_credentials())
            gui.assert_not_called()

    def test_gui_source_documents_paste_and_masks_input(self):
        source = (Path(__file__).resolve().parents[1] / "token_dialog.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('show="●"', source)
        self.assertIn('"<Control-v>"', source)
        self.assertIn('"<Button-3>"', source)
        self.assertIn("Dán từ clipboard", source)
        self.assertIn("save_meta_user_token(value)", source)
        self.assertNotIn("print(value)", source)

if __name__ == "__main__":
    unittest.main()
