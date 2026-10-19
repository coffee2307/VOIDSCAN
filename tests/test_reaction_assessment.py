"""Evidence-aware reaction summaries must never claim bot certainty."""
from __future__ import annotations
import unittest
from datetime import datetime,timedelta,timezone
from reaction_assessment import assess

def points(values, minutes=10):
    t=datetime(2026,1,1,tzinfo=timezone.utc)
    return [{"observed_at":(t+timedelta(minutes=minutes*i)).isoformat(),
             "counts":{"LOVE":v, "LIKE":v}} for i,v in enumerate(values)]

class AssessmentTests(unittest.TestCase):
    def test_historical_one_snapshot_is_not_zero_suspicion(self):
        result=assess(points([1000]))
        self.assertEqual(result["current_reactions"],1000)
        self.assertIsNone(result["suspicious_window_reactions"])
        self.assertIsNone(result["suspicious_share_pct"])
        self.assertEqual(result["evidence_status"],"chưa_đủ_lịch_sử")
        self.assertIsNone(result["bot_probability_pct"])
        self.assertEqual(result["automatic_deduction"],0)

    def test_detects_spike_but_never_claims_fake_accounts(self):
        result=assess(points([10,20,30,40,50,60,70,700]))
        self.assertEqual(result["suspicious_window_reactions"],630)
        self.assertEqual(result["flagged_intervals"],1)
        self.assertEqual(result["current_reactions"],700)
        self.assertEqual(result["suspicious_share_pct"],90.0)
        self.assertIsNone(result["bot_probability_pct"])
        self.assertIsNone(result["confirmed_fake_reactions"])
        self.assertEqual(result["automatic_deduction"],0)
        self.assertEqual(result["evidence_status"],"có_chỉ_báo")

    def test_steady_growth_does_not_fake_flag(self):
        result=assess(points([10,20,30,40,50,60,70,80]))
        self.assertEqual(result["suspicious_window_reactions"],0)
        self.assertEqual(result["suspicious_share_pct"],0)
        self.assertEqual(result["evidence_status"],"chưa_phát_hiện")

    def test_missing_count_is_not_zero(self):
        data=points([5,10,15])
        data[1]["counts"]["LOVE"]=None
        report=assess(data)
        self.assertEqual(report["observed_snapshots"],2)
        self.assertIsNone(report["suspicious_share_pct"])

    def test_negative_reaction_changes_not_flagged(self):
        result=assess(points([100,110,120,130,140,150,160,60]))
        self.assertEqual(result["flagged_intervals"],0)
        self.assertEqual(result["automatic_deduction"],0)

    def test_empty_series(self):
        r=assess([])
        self.assertIsNone(r["current_reactions"])
        self.assertEqual(r["evidence_status"],"không_có_dữ_liệu")
        self.assertIsNone(r["suspicious_share_pct"])

    def test_unaccepted_kind(self):
        with self.assertRaises(ValueError):
            assess([], "CARE")

if __name__=="__main__":
    unittest.main()
