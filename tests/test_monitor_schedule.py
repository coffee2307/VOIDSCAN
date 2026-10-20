"""R2 live monitoring schedule: due checks without duplicate/early Meta calls."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch

import reaction_history as rh
from research_readiness import readiness

PAGE="123456789012"
PHOTO="123456789013"
NOW=datetime.now(timezone.utc).replace(microsecond=0)

def sample(observed_at, count):
    return {"page":{"id":PAGE},"post":{"id":PHOTO},
            "object":{"id":PHOTO,"type":"photo"},
            "observed_at":observed_at.isoformat(),
            "reaction":{"status":"partial",
                        "counts":{"LIKE":count,"LOVE":count,"WOW":count,
                                  "HAHA":count,"SAD":count,"ANGRY":count},
                        "api_error":None}}

class DuePollingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"monitor.db"
        rh.watch(PAGE,PHOTO,PHOTO,self.db)

    def tearDown(self):
        self.temp.cleanup()

    def _poll(self,now=NOW):
        with patch("reaction_collector.collect_once",
                   return_value=sample(now,120)) as fetch:
            outcome=rh.poll_active_once(
                self.db,due_only=True,poll_seconds=600,now=now)
        return outcome,fetch.call_count

    def test_watch_with_recent_manual_scan_waits_10_minutes(self):
        rh.store_observation(sample(NOW-timedelta(minutes=2),10),self.db)
        result,calls=self._poll()
        self.assertEqual(result,[])
        self.assertEqual(calls,0)
        quality=readiness(self.db,now=NOW)
        self.assertEqual(quality["status"],"collecting")
        self.assertEqual(quality["active_stale"],0)

    def test_due_after_10_minutes(self):
        rh.store_observation(sample(NOW-timedelta(minutes=10,seconds=2),10),self.db)
        outcome,calls=self._poll()
        self.assertEqual(calls,1)
        self.assertEqual(len(outcome),1)
        self.assertEqual(outcome[0]["status"],"partial")
        self.assertEqual(readiness(self.db,now=NOW)["snapshots"],2)

    def test_restart_does_not_create_duplicate_snapshot(self):
        rh.store_observation(sample(NOW-timedelta(minutes=15),10),self.db)
        first,calls=self._poll()
        self.assertEqual(calls,1)
        second,calls=self._poll()
        self.assertEqual(second,[])
        self.assertEqual(calls,0)

    def test_fresh_last_checked_prevents_early_retry(self):
        w=rh.watch_list(self.db)[0]
        rh.update_watch(w["id"],"network",self.db)
        outcome,calls=self._poll()
        self.assertEqual(outcome,[])
        self.assertEqual(calls,0)

    def test_new_watch_without_snapshots_is_polled_on_start(self):
        result,calls=self._poll()
        self.assertEqual(calls,1)
        self.assertEqual(len(result),1)

    def test_inactive_watch_never_polled(self):
        rh.set_watch(rh.watch_list(self.db)[0]["id"],False,self.db)
        outcome,calls=self._poll()
        self.assertEqual(outcome,[])
        self.assertEqual(calls,0)

    def test_invalid_poll_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            rh.poll_active_once(self.db,due_only=True,poll_seconds=10,now=NOW)
        with self.assertRaises(ValueError):
            rh.poll_active_once(self.db,due_only=True,now=NOW.replace(tzinfo=None))

if __name__=="__main__":
    unittest.main()
