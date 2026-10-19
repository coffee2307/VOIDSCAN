import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import storage

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "scan.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def test_clean_empty_history(self):
        self.assertEqual(storage.stats(self.db)["scans"], 0)
        self.assertEqual(storage.list_scans(path=self.db), [])

    def test_persist_only_aggregates_and_get_detail(self):
        raw = {
            "status": "live", "source": "meta_graph_api", "comments": 5,
            "suspicious": 3, "message": "partial sample",
            "examples": [{"name": "SECRET USER NAME", "profile_id": "SECRET POST"}],
            "signals": [{"label": "Repeated text", "count": 3,
                         "explanation": "three repeated comments", "level": "review"}]
        }
        result = storage.persist_scan("https://www.facebook.com/posts/1234?utm_source=PRIVATE",raw,self.db)
        self.assertEqual(storage.stats(self.db)["live"], 1)
        self.assertEqual(storage.stats(self.db)["flagged"], 1)
        self.assertEqual(len(storage.list_scans(path=self.db)), 1)
        self.assertNotIn("SECRET USER NAME", self.db.read_bytes().decode("utf-8", errors="replace"))
        self.assertNotIn("utm_source", self.db.read_bytes().decode("utf-8", errors="replace"))
        detail = storage.get_scan(result["id"], self.db)
        self.assertEqual(detail["result"]["comments"], 5)
        self.assertNotIn("examples", detail["result"])
        self.assertEqual(detail["post_url"], "https://www.facebook.com/posts/1234")

    def test_invalid_id_not_matched(self):
        self.assertIsNone(storage.get_scan("bad", self.db))

    def test_purge_expired(self):
        r = storage.persist_scan("https://www.facebook.com/reel/123456",{"status":"unavailable"},self.db)
        old_time = (datetime.now(timezone.utc)-timedelta(days=120)).isoformat(timespec="seconds")
        with closing(sqlite3.connect(self.db)) as connection:
            with connection:
                connection.execute("UPDATE scan_jobs SET created_at=? WHERE id=?",(old_time,r["id"]))
        self.assertEqual(storage.purge_expired(90,self.db), 1)
        self.assertEqual(storage.stats(self.db)["scans"], 0)

if __name__=="__main__":
    unittest.main()
