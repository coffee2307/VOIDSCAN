"""R1 replay only tests algorithm/holdout mechanics on synthetic cases."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from research_replay import replay

def fake_case(contest,idx,viral_lookalike=True):
    endpoint=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=40*contest,hours=idx)
    fraudulent=(idx%2==0)
    # Both a legitimate viral event and synthetic manipulation can have same
    # aggregate trajectory. That creates deliberate false positive tests.
    spike=fraudulent or viral_lookalike
    counts=[10,20,30,40,50,60,70,700 if spike else 80]
    samples=[{"observed_at":(endpoint-timedelta(minutes=70-10*i)).isoformat(),
              "counts":{"LOVE":n}} for i,n in enumerate(counts)]
    return {
        "case_id":f"C{contest}-{idx}", "contest_id":f"CONTEST_{contest}",
        "event_time":endpoint.isoformat(),"reaction_type":"LOVE",
        "verified_label":"verified_manipulation" if fraudulent else "verified_legitimate",
        "ground_truth_source":"independent_documentation",
        "evidence_ref":f"REVIEW-{contest}-{idx}","observations":samples,
    }

def fixture(n=6,amount=20,viral_lookalike=True):
    return {"schema_version":1,"cases":[fake_case(c,i,viral_lookalike) for c in range(n)
                                         for i in range(amount)]}

class ReplayTests(unittest.TestCase):
    def test_correlated_rules_cannot_distinguish_legit_viral_from_fraud(self):
        output=replay(fixture())
        self.assertEqual(output["eligible_cases"],120)
        consensus=output["metrics"]["consensus_2_of_3"]
        self.assertEqual(consensus["validation_status"],"exploratory_holdout_descriptive")
        self.assertEqual(consensus["heldout_cases"],40)
        self.assertEqual(consensus["precision"],0.5)
        self.assertEqual(consensus["recall"],1)
        self.assertEqual(consensus["false_positive_rate"],1)
        self.assertIsNone(output["fake_account_count"])
        self.assertEqual(output["automatic_deduction"],0)

    def test_stable_legitimate_is_not_misflagged_in_synthetic_suite(self):
        result=replay(fixture(6,20,False))
        consensus=result["metrics"]["consensus_2_of_3"]
        self.assertEqual(consensus["false_positive_rate"],0)
        self.assertEqual(consensus["precision"],1)
        self.assertFalse(consensus["deployable_for_score_deduction"])

    def test_insufficient_history_is_excluded_not_called_negative(self):
        data=fixture(6,20)
        data["cases"][1]["observations"]=data["cases"][1]["observations"][-3:]
        r=replay(data)
        self.assertEqual(r["eligible_cases"],119)
        self.assertEqual(r["skipped_insufficient_or_broken_history"],1)

    def test_event_time_must_match_last_observation_no_future_leakage(self):
        data=fixture(1,1)
        data["cases"][0]["event_time"]="2025-01-01T00:00:00+00:00"
        with self.assertRaises(ValueError):
            replay(data)

    def test_duplicate_and_unordered_timestamps_rejected(self):
        data=fixture(1,1)
        items=data["cases"][0]["observations"]
        items[-1]["observed_at"]=items[-2]["observed_at"]
        with self.assertRaises(ValueError):
            replay(data)

    def test_reviews_are_not_auto_validated(self):
        data=fixture(1,1)
        data["cases"][0]["ground_truth_source"]="voidscan_flag"
        with self.assertRaises(ValueError):
            replay(data)

    def test_missing_case_fields_rejected(self):
        data=fixture(1,1)
        data["cases"][0].pop("evidence_ref")
        with self.assertRaises(ValueError):
            replay(data)

    def test_short_holdout_does_not_create_success_claim(self):
        result=replay(fixture(2,3))
        self.assertIsNone(result["metrics"]["robust_mad"]["precision"])
        self.assertEqual(result["metrics"]["robust_mad"]["validation_status"],
                         "insufficient_independent_cases")

if __name__=="__main__":
    unittest.main()
