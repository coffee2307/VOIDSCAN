"""Regression checks for legible, Vietnamese-first VOIDSCAN interface."""
from __future__ import annotations
import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"

def contrast(a, b):
    def channel(s):
        s = s / 255
        return s / 12.92 if s <= .04045 else ((s + .055) / 1.055) ** 2.4
    def lum(s):
        values = [channel(int(s[i:i+2], 16)) for i in (1, 3, 5)]
        return sum(v * w for v, w in zip(values, (.2126, .7152, .0722)))
    x, y = sorted([lum(a), lum(b)], reverse=True)
    return (x + .05) / (y + .05)

class InterfaceTests(unittest.TestCase):
    def test_vietnamese_language_and_viewport(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn('lang="vi"', html)
        self.assertIn('name="viewport"', html)
        self.assertIn('id="theme-toggle"', html)
        self.assertIn('id="reaction-object"', html)
        self.assertIn('id="reaction-watch"', html)
        self.assertIn('id="load-page-photos"', html)

    def test_offline_vietnamese_font_stack(self):
        css = (WEB / "app.css").read_text(encoding="utf-8")
        self.assertIn('"Segoe UI"', css)
        self.assertNotIn("@import", css)
        self.assertNotIn("fonts.googleapis.com", css)
        self.assertNotIn("font-family:Manrope", css)

    def test_text_contrast_on_both_themes(self):
        css = (WEB / "app.css").read_text(encoding="utf-8")
        light = css.split(":root{", 1)[1].split("}", 1)[0]
        dark = css.split(':root[data-theme="dark"]{', 1)[1].split("}", 1)[0]
        def color(block, token):
            m = re.search(r"--" + re.escape(token) + r":(#[0-9a-f]{6})", block)
            self.assertIsNotNone(m, token)
            return m.group(1)
        for block in (light, dark):
            bg = color(block, "surface")
            for token in ("text", "muted", "brand"):
                with self.subTest(mode="dark" if block is dark else "light", token=token):
                    self.assertGreaterEqual(contrast(color(block, token), bg), 4.5)

    def test_appearance_toggle_accessibility(self):
        js = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn('setAttribute("aria-label"', js)
        self.assertIn('localStorage.setItem(key,next)', js)
        self.assertIn('root.dataset.theme=mode', js)

if __name__ == "__main__":
    unittest.main()
