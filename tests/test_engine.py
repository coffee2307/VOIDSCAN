import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from engine import analyze, parse_export, safe_csv_cell
from scan import flags, reference, scan, validate_url

COLUMNS = ["Profile Name", "Profile ID", "Message", "Group", "Date"]

def make_csv(data, separator=",", preamble=False):
    out = io.StringIO(newline="")
    import csv
    writer = csv.writer(out, delimiter=separator)
    if preamble:
        writer.writerow(["Exported by", "ExportComments.com"])
        writer.writerow(["Source URL", "https://www.facebook.com/reel/1527428255063081/"])
        writer.writerow([])
    writer.writerow(COLUMNS)
    writer.writerows(data)
    return out.getvalue().encode("utf-8-sig")

class ParserTests(unittest.TestCase):
    def test_comma_and_semicolon_header(self):
        row = [["Nguyá»…n An", "12345678", "Hi", "", "2025-10-11 12:00:00"]]
        for sep in [",", ";"]:
            records, meta = parse_export(make_csv(row, sep, True), "11A2(1).csv")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["class"], "11A2")
            self.assertEqual(records[0]["name"], "Nguyá»…n An")
            self.assertEqual(meta["source_url"], "https://www.facebook.com/reel/1527428255063081/")

    def test_reject_wrong_header(self):
        with self.assertRaises(ValueError):
            parse_export(b"a,b,c\n1,2,3", "invalid.csv")

    def test_dedupe_by_id_not_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "11A2(1).csv").write_bytes(make_csv([
                ["Same Name", "A123", "one", "", ""],
                ["Same Name", "B456", "two", "", ""],
            ]))
            (folder / "11A2(2).csv").write_bytes(make_csv([
                ["Changed Name", "A123", "three", "", ""]
            ]))
            (folder / "10B1.csv").write_bytes(make_csv([
                ["Cross share", "A123", "four", "", ""]
            ]))
            result = analyze(folder)
            self.assertEqual(result["counts"]["total"], 4)
            self.assertEqual(result["counts"]["duplicates"], 1)
            self.assertEqual(result["counts"]["unique"], 3)
            self.assertEqual(result["counts"]["cross_class"], 2)
            self.assertEqual(result["counts"]["classes"], 2)

    def test_local_scan_and_fallback(self):
        rows,_ = parse_export(make_csv([["A", "1234", "", "", ""]], ";", True), "10A1.csv")
        for row in rows: row["duplicate"] = False
        result = scan("https://www.facebook.com/reel/1527428255063081/", rows)
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["total"], 1)

    def test_url_restrictions(self):
        invalid = ["http://www.facebook.com/posts/123",
                   "https://facebook.com.evil.test/posts/123",
                   "https://evil.com/posts/123",
                   "file:///etc/passwd",
                   "https://user:pass@facebook.com/posts/123"]
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_repeated_comment_flag(self):
        comments = [
            {"message": "Same scripted comment", "created_time": "2025-10-10T12:00:00+00:00"},
            {"message": "Same scripted comment", "created_time": "2025-10-10T12:00:10+00:00"},
            {"message": "Same scripted comment", "created_time": "2025-10-10T12:00:20+00:00"},
            {"message": "Actually different", "created_time": "2025-10-10T12:07:10+00:00"}
        ]
        signals, n = flags(comments)
        self.assertEqual(n, 3)
        self.assertEqual(signals[1]["count"], 3)

    def test_csv_injection(self):
        for payload in ["=SUM(A1:B3)", "+100", "-cmd", "@HYPERLINK(...)", "\t=X"]:
            self.assertTrue(safe_csv_cell(payload).startswith("'"))

if __name__ == "__main__":
    unittest.main()

