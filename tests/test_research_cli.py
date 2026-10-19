"""R0 CLI only reports aggregate quality; never leak Page IDs or raw tokens."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import reaction_history
from research_cli import audit_local

class ResearchCLITests(unittest.TestCase):
    def test_no_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"never-created.sqlite3"
            report=audit_local(path)
            self.assertEqual(report["status"],"no_database")
            self.assertFalse(path.exists())

    def test_report_excludes_page_object_ids(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"data.sqlite3"
            record={
                "page":{"id":"123456789012","name":"Secret Page"},
                "post":{"id":"123456789012_123456789999"},
                "object":{"id":"123456789999","type":"photo"},
                "observed_at":"2026-10-19T15:00:00+00:00",
                "reaction":{"status":"partial","counts":{
                    "LIKE":100,"LOVE":400,"WOW":2,"HAHA":0,"SAD":None,"ANGRY":1
                }}
            }
            reaction_history.store_observation(record,db)
            result=audit_local(db)
            self.assertEqual(result["snapshots"],1)
            self.assertEqual(result["types"]["LOVE"]["valid_observations"],1)
            self.assertEqual(result["types"]["SAD"]["missing_values"],1)
            self.assertNotIn("123456789999",str(result))
            self.assertNotIn("Secret Page",str(result))
            self.assertFalse(result["bot_probability_validated"])

if __name__=="__main__":
    unittest.main()
