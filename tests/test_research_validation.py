"""Independent-event evaluation: holdout by contest and date, never actor claims."""
from __future__ import annotations
import unittest
from datetime import datetime,timedelta,timezone
from research_validation import evaluate, load_cases, wilson

def fixture(n_contests=6, cases_per=20):
    items=[]
    base=datetime(2026,1,1,tzinfo=timezone.utc)
    for contest in range(n_contests):
        for i in range(cases_per):
            manipulated=i%2==0
            items.append({
                "case_id":f"C{contest}-E{i}",
                "contest_id":f"CONTEST_{contest}",
                "event_time":(base+timedelta(days=contest*30,minutes=i)).isoformat(),
                "verified_label":"verified_manipulation" if manipulated else "verified_legitimate",
                "ground_truth_source":"independent_documentation",
                "evidence_ref":f"record-{contest}-{i}",
                "flagged_by_frozen_rule":i%3==0,
            })
    return {"schema_version":1,"cases":items}

class ValidationTests(unittest.TestCase):
    def test_small_dataset_is_not_claimed_as_validated(self):
        data=fixture(1,5)
        r=evaluate(data)
        self.assertEqual(r["validation_status"],"insufficient_independent_cases")
        self.assertIsNone(r["precision"])
        self.assertIsNone(r["recall"])
        self.assertFalse(r["deployable_for_score_deduction"])

    def test_temporal_holdout_excludes_train_contests(self):
        r=evaluate(fixture(6,20))
        self.assertEqual(r["development_contests"],4)
        self.assertEqual(r["heldout_contests"],2)
        self.assertEqual(r["heldout_cases"],40)
        self.assertEqual(r["validation_status"],"exploratory_holdout_descriptive")
        m=r["confusion_matrix"]
        self.assertEqual(sum(m.values()),40)
        self.assertIsNotNone(r["precision_wilson95"])
        self.assertFalse(r["calibrated_bot_probability_available"])

    def test_identical_temporal_signature_can_have_both_labels(self):
        d=fixture(6,20)
        for row in d["cases"]:
            row["flagged_by_frozen_rule"]=True
        r=evaluate(d)
        self.assertEqual(r["precision"],.5)
        self.assertEqual(r["recall"],1)
        self.assertFalse(r["deployable_for_score_deduction"])

    def test_overlapping_contest_windows_are_not_a_holdout(self):
        data=fixture(6,20)
        # Contest 0 starts earliest but one event continues beyond later contests.
        data["cases"][19]["event_time"]="2026-12-01T12:00:00+00:00"
        r=evaluate(data)
        self.assertEqual(r["validation_status"],"overlapping_contest_periods")
        self.assertIsNone(r["precision"])
        self.assertTrue(r["temporal_overlap"])

    def test_no_trust_in_self_labeled_or_unverified_cases(self):
        d=fixture()
        d["cases"][0]["verified_label"]="suspected_bot"
        with self.assertRaises(ValueError):
            evaluate(d)
        d=fixture()
        del d["cases"][0]["evidence_ref"]
        with self.assertRaises(ValueError):
            evaluate(d)

    def test_actor_link_and_duplicate_case_are_rejected(self):
        d=fixture()
        d["cases"][1]["case_id"]=d["cases"][0]["case_id"]
        with self.assertRaises(ValueError):
            evaluate(d)
        d=fixture()
        d["cases"][0]["evidence_ref"]="https://facebook.com/private-user"
        with self.assertRaises(ValueError):
            evaluate(d)

    def test_boolean_flags_are_required(self):
        d=fixture()
        d["cases"][0]["flagged_by_frozen_rule"]="true"
        with self.assertRaises(ValueError):
            load_cases(d)

    def test_wilson_is_bounded(self):
        self.assertIsNone(wilson(0,0))
        self.assertEqual(wilson(0,10)[0],0)
        self.assertEqual(wilson(10,10)[1],1)

if __name__=="__main__":
    unittest.main()
