"""R0 data integrity tests; intentionally fake aggregate counts only."""
from __future__ import annotations
import unittest
from datetime import datetime,timedelta,timezone
from reaction_assessment import assess
from research_quality import audit_series
from reaction_history import anomaly_report

START=datetime(2026,10,19,tzinfo=timezone.utc)
def p(minutes,count,kind="LOVE"):
    return {"observed_at":(START+timedelta(minutes=minutes)).isoformat(),
            "counts":{kind:count}}

class QualityGateTests(unittest.TestCase):
    def test_one_old_photo_is_not_suspicion_estimate(self):
        r=assess([p(0,1000)])
        self.assertEqual(r["current_reactions"],1000)
        self.assertIsNone(r["suspicious_window_reactions"])
        self.assertIsNone(r["bot_probability_pct"])
        self.assertFalse(r["data_quality"]["ready_for_review"])

    def test_missing_middle_row_must_not_be_bridged(self):
        points=[p(i*10,i*10) for i in range(8)]
        points[6]["counts"]["LOVE"]=None
        points[7]["counts"]["LOVE"]=800
        r=assess(points)
        self.assertEqual(r["data_quality"]["missing_counts"],1)
        self.assertEqual(r["data_quality"]["eligible_adjacent_intervals"],5)
        self.assertIsNone(r["suspicious_window_reactions"])
        self.assertEqual(r["flagged_intervals"],None)
        self.assertEqual(r["automatic_deduction"],0)

    def test_long_gap_not_interpreted_as_precise_burst(self):
        points=[p(i*10,i*10) for i in range(7)]+[p(180,1000)]
        quality=audit_series(points,"LOVE")
        r=assess(points)
        self.assertEqual(quality["long_gaps"],1)
        self.assertEqual(quality["eligible_adjacent_intervals"],6)
        self.assertEqual(r["data_quality"]["long_gaps"],1)
        self.assertEqual(r["suspicious_window_reactions"],0)

    def test_duplicate_timestamps_are_not_extra_intervals(self):
        points=[p(i*10,i*10) for i in range(7)]+[p(60,900)]
        q=audit_series(points,"LOVE")
        self.assertEqual(q["repeated_timestamps"],1)
        self.assertEqual(q["eligible_adjacent_intervals"],6)
        self.assertFalse(any(x["flagged"] for x in anomaly_report(points)["intervals"]))

    def test_invalid_timestamps_fail_closed(self):
        points=[p(i*10,i*10) for i in range(8)]
        points[6]["observed_at"]="bad-timestamp"
        a=assess(points)
        self.assertGreaterEqual(a["data_quality"]["invalid_timestamps"],1)
        self.assertIsNone(a["suspicious_share_pct"])

    def test_stale_is_data_freshness_not_bot_probability(self):
        q=audit_series([p(0,100)],now=START+timedelta(days=1))
        self.assertTrue(q["stale"])
        self.assertEqual(q["valid_snapshots"],1)
        self.assertFalse(q["calibrated_bot_probability_available"])

    def test_missing_not_zero_even_when_later_value_exists(self):
        q=audit_series([p(0,0),p(10,None),p(20,500)])
        self.assertEqual(q["missing_counts"],1)
        self.assertEqual(q["eligible_adjacent_intervals"],0)
        self.assertEqual(q["valid_snapshots"],2)

if __name__=="__main__":
    unittest.main()
