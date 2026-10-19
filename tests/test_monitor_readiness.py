"""R1.6 monitoring observability: read-only and no account-level claims."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import reaction_history as rh
from meta_pages import MetaAccessError
from research_readiness import readiness

PAGE="123456789012"
PHOTO="123456789013"


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"observations.db"
        self.now=datetime.now(timezone.utc).replace(microsecond=0)

    def tearDown(self):
        self.temp.cleanup()

    def sample(self,offset,value,kind="LOVE"):
        when=self.now+timedelta(minutes=offset)
        return {"page":{"id":PAGE,"name":"Do not export this label"},
                "post":{"id":PHOTO},"object":{"id":PHOTO,"type":"photo"},
                "observed_at":when.isoformat(),
                "reaction":{"status":"partial",
                            "counts":{"LIKE":value,"LOVE":value,"WOW":value,
                                      "HAHA":value,"SAD":None,"ANGRY":value}}}

    def test_invalid_poll_interval_or_timezone_rejected(self):
        with self.assertRaises(ValueError):
            readiness(self.db,poll_seconds=15)
        with self.assertRaises(ValueError):
            readiness(self.db,now=datetime(2026,10,20))

    def test_missing_db_does_not_create_database(self):
        report=readiness(self.db,now=self.now)
        self.assertEqual(report["status"],"no_data")
        self.assertFalse(self.db.exists())
        self.assertEqual(report["active_watches"],0)
        self.assertFalse(report["bot_probability_validated"])

    def test_one_snapshot_without_watch(self):
        rh.store_observation(self.sample(0,10),self.db)
        result=readiness(self.db,now=self.now)
        self.assertEqual(result["status"],"not_monitoring")
        self.assertEqual(result["snapshots"],1)
        self.assertEqual(result["historical_objects"],1)
        self.assertNotIn(PHOTO,str(result))
        self.assertNotIn(PAGE,str(result))
        self.assertEqual(result["automatic_deduction"],0)

    def test_active_watch_insufficient_then_enough_and_stop(self):
        wid=rh.watch(PAGE,PHOTO,PHOTO,self.db)
        initial=readiness(self.db,now=self.now)
        self.assertEqual(initial["status"],"monitor_stale")
        rh.update_watch(wid,"ok",self.db)
        for idx in range(7):
            rh.store_observation(self.sample(-60+10*idx,idx*10),self.db)
        fresh=readiness(self.db,now=self.now)
        self.assertEqual(fresh["snapshots"],7)
        self.assertEqual(fresh["active_watches"],1)
        self.assertEqual(fresh["objects_with_usable_history"],1)
        self.assertEqual(fresh["series_with_usable_history"],5)
        self.assertEqual(fresh["status"],"observing_with_history")
        self.assertFalse(fresh["meta_token_validated"])
        rh.set_watch(wid,False,self.db)
        stopped=readiness(self.db,now=self.now)
        self.assertEqual(stopped["status"],"not_monitoring")
        self.assertEqual(stopped["active_watches"],0)

    def test_old_monitor_check_is_stale_not_false_bot_detection(self):
        wid=rh.watch(PAGE,PHOTO,PHOTO,self.db)
        rh.update_watch(wid,"ok",self.db)
        late=self.now+timedelta(hours=1)
        report=readiness(self.db,now=late)
        self.assertEqual(report["status"],"monitor_stale")
        self.assertEqual(report["active_stale"],1)
        self.assertEqual(report["automatic_deduction"],0)

    def test_expired_watch_surfaces_problem_without_secret(self):
        watch=rh.watch(PAGE,PHOTO,PHOTO,self.db)
        rh.update_watch(watch,"expired",self.db)
        r=readiness(self.db,now=self.now)
        self.assertEqual(r["status"],"monitor_errors")
        self.assertEqual(r["last_monitor_errors"]["expired"],1)
        self.assertIn("Meta token",r["instructions"][0])
        self.assertNotIn(PAGE,str(r))

    def test_poll_exception_categorized(self):
        rh.watch(PAGE,PHOTO,PHOTO,self.db)
        with patch("reaction_collector.collect_once",
                   side_effect=MetaAccessError("rate_limit",613)):
            results=rh.poll_active_once(self.db)
        self.assertEqual(results[0]["status"],"rate_limit")
        report=readiness(self.db,now=self.now)
        self.assertEqual(report["last_monitor_errors"]["rate_limit"],1)
        self.assertEqual(report["snapshots"],0)

    def test_poll_unavailable_preserves_api_error_category(self):
        rh.watch(PAGE,PHOTO,PHOTO,self.db)
        s=self.sample(0,None)
        s["reaction"]={"status":"unavailable",
                       "counts":dict.fromkeys(("LIKE","LOVE","WOW","HAHA","SAD","ANGRY")),
                       "api_error":{"kind":"expired","code":190}}
        with patch("reaction_collector.collect_once",return_value=s):
            results=rh.poll_active_once(self.db)
        self.assertEqual(results[0]["status"],"expired")
        self.assertEqual(readiness(self.db,now=self.now)["snapshots"],0)

    def test_gap_prevents_false_ready(self):
        rh.watch(PAGE,PHOTO,PHOTO,self.db)
        rh.update_watch(rh.watch_list(self.db)[0]["id"],"ok",self.db)
        for idx in range(7):
            # One missed 10-minute polling window makes contiguous run too short.
            minute=-70+10*idx+(10 if idx>=4 else 0)
            rh.store_observation(self.sample(minute,idx*10),self.db)
        r=readiness(self.db,now=self.now)
        self.assertEqual(r["objects_with_usable_history"],0)
        self.assertEqual(r["series_with_usable_history"],0)

if __name__=="__main__":
    unittest.main()
