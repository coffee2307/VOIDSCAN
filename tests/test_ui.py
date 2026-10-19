"""VOIDSCAN guided workflow and readable Vietnamese interface regressions."""
from __future__ import annotations
import re
import unittest
from pathlib import Path

WEB=Path(__file__).resolve().parents[1]/"web"

class InterfaceTests(unittest.TestCase):
    def test_language_and_accessible_workflow(self):
        html=(WEB/"index.html").read_text(encoding="utf-8")
        self.assertIn('lang="vi"',html)
        self.assertIn('name="viewport"',html)
        for id_ in ("page-select","choose-photos","choose-posts","target-url",
                    "reaction-kind","scan-btn","result","watch-btn","export-btn",
                    "auth-warning","view-history","view-method"):
            with self.subTest(element=id_):
                self.assertIn('id="'+id_+'"',html)
        self.assertIn("Quét & phân tích tương tác",html)
        self.assertIn("Độ chắc chắn là bot",html)

    def test_reduced_information_density(self):
        html=(WEB/"index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="metric-scans"',html)
        self.assertNotIn('id="file-picker"',html)
        self.assertNotIn('id="scan-details"',html)
        self.assertEqual(html.count('class="nav-button'),3)

    def test_vietnamese_system_font(self):
        css=(WEB/"app.css").read_text(encoding="utf-8")
        self.assertIn('"Segoe UI"',css)
        self.assertNotIn("fonts.googleapis.com",css)
        self.assertNotIn("@import",css)
        self.assertIn("prefers-reduced-motion",css)
        self.assertIn("focus-visible",css)
        self.assertIn("[hidden]",css)

    def test_no_fabricated_bot_probability(self):
        js=(WEB/"app.js").read_text(encoding="utf-8")
        self.assertIn('setText("bot-probability","Chưa xác định")',js)
        self.assertIn("suspicious_window_reactions",js)
        self.assertIn("suspicious_share_pct",js)
        self.assertIn("/api/reactions/report",js)
        self.assertIn("quality.eligible_adjacent_intervals",js)
        self.assertIn("quality.long_gaps",js)
        self.assertIn("renderR1Comparison",js)
        self.assertIn("renderContext",js)
        self.assertIn("/api/research/readiness",js)
        self.assertIn("loadReadiness",js)
        self.assertIn("readiness-refresh",js)
        self.assertIn('id="readiness-active"',(WEB/"index.html").read_text(encoding="utf-8"))
        self.assertIn('id="context-form"',(WEB/"index.html").read_text(encoding="utf-8"))
        self.assertIn('id="context-list"',(WEB/"index.html").read_text(encoding="utf-8"))
        self.assertIn("/api/reactions/context",js)
        self.assertIn("context_event_ids",js)
        self.assertIn("Đồng thuận KHÔNG đồng nghĩa xác suất gian lận",js)
        self.assertNotIn("Math.random(",js)

    def test_photo_is_selected_before_scanning_parent_with_attachments(self):
        js=(WEB/"app.js").read_text(encoding="utf-8")
        self.assertIn('state.sourceKind="attachments"',js)
        self.assertIn('return false;',js)
        self.assertIn("Không tự sử dụng số reaction của bài mẹ",js)

if __name__=="__main__":
    unittest.main()
