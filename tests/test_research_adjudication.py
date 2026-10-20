"""R2 reviewer adjudication quality gates; all cases are synthetic fixtures."""
from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

from research_adjudication import curate
from research_cli import main as cli_main
from research_replay import replay

T0=datetime(2026,10,20,0,tzinfo=timezone.utc)

def review(who="RV_A",verdict="manipulation",ref="EV-123"):
    return {
        "reviewer_id":who,"verdict":verdict,
        "ground_truth_source":"independent_documentation",
        "evidence_ref":ref,"blinded_to_model_flag":True
    }

def sample(verdict_a="manipulation",verdict_b="manipulation",arb=None):
    counts=[10,20,30,40,50,60,70,700]
    points=[{"observed_at":(T0+timedelta(minutes=i*10)).isoformat(),
             "counts":{"LOVE":value,"LIKE":value}}
            for i,value in enumerate(counts)]
    case={
        "case_id":"CASE_001","contest_id":"COMP_001",
        "event_time":points[-1]["observed_at"],"reaction_type":"LOVE",
        "observations":points,
        "reviews":[review("RV_A",verdict_a,"EV-A"),review("RV_B",verdict_b,"EV-B")],
    }
    if arb is not None:
        case["adjudication"]=arb
    return case

def doc(*cases):
    return {"schema_version":1,"cases":list(cases)}

class AdjudicationTests(unittest.TestCase):
    def test_two_independent_reviewers_same_decision_admitted(self):
        result=curate(doc(sample()))
        self.assertEqual(result["review_audit"]["accepted_for_replay"],1)
        self.assertEqual(result["review_audit"]["accepted_by_process"]["two_primary_agreement"],1)
        accepted=result["cases"][0]
        self.assertEqual(accepted["verified_label"],"verified_manipulation")
        self.assertEqual(set(accepted["observations"][0]["counts"]),{"LOVE"})
        self.assertNotIn("reviews",accepted)
        self.assertEqual(accepted["review_evidence_refs"],["EV-A","EV-B"])
        self.assertEqual(accepted["review_resolution_method"],"two_primary_agreement")
        self.assertNotIn("reviewer_id",json.dumps(result))
        self.assertFalse(result["review_audit"]["evidence_authenticity_not_verified"] is False)
        replayed=replay(result)
        self.assertEqual(replayed["eligible_cases"],1)
        self.assertEqual(replayed["automatic_deduction"],0)
        self.assertIsNone(replayed["metrics"]["robust_mad"]["precision"])

    def test_disagreement_not_forced_into_ground_truth(self):
        result=curate(doc(sample("manipulation","legitimate")))
        self.assertEqual(result["cases"],[])
        self.assertEqual(result["review_audit"]["excluded"]["unresolved_disagreement_or_inconclusive"],1)

    def test_third_independent_reviewer_resolves(self):
        result=curate(doc(sample("manipulation","legitimate",
                                  review("RV_C","legitimate","EV-ARBITER"))))
        self.assertEqual(result["cases"][0]["verified_label"],"verified_legitimate")
        self.assertEqual(result["cases"][0]["evidence_ref"],"EV-ARBITER")
        self.assertEqual(result["cases"][0]["review_evidence_refs"],
                         ["EV-A","EV-B","EV-ARBITER"])
        self.assertEqual(result["review_audit"]["accepted_by_process"]["independent_third_adjudicator"],1)

    def test_indeterminate_third_review_excluded(self):
        result=curate(doc(sample("manipulation","legitimate",
                                  review("RV_C","inconclusive","EV-ARBITER"))))
        self.assertEqual(len(result["cases"]),0)
        self.assertEqual(result["review_audit"]["excluded"]["adjudicator_inconclusive"],1)

    def test_duplicate_reviewer_identity_rejected(self):
        case=sample()
        case["reviews"][1]["reviewer_id"]="RV_A"
        with self.assertRaises(ValueError):
            curate(doc(case))

    def test_same_reviewer_cannot_adjudicate(self):
        with self.assertRaises(ValueError):
            curate(doc(sample("legitimate","manipulation",
                              review("RV_A","manipulation","EV-C"))))

    def test_blinding_and_prediction_leakage_rejected(self):
        case=sample()
        case["reviews"][0]["blinded_to_model_flag"]=False
        with self.assertRaises(ValueError):
            curate(doc(case))
        case=sample()
        case["model_prediction"]="bot"
        with self.assertRaises(ValueError):
            curate(doc(case))
        case=sample()
        case["flagged_by_frozen_rule"]=True
        with self.assertRaises(ValueError):
            curate(doc(case))

    def test_evidence_codes_not_urls(self):
        case=sample()
        case["reviews"][0]["evidence_ref"]="https://facebook.com/person"
        with self.assertRaises(ValueError):
            curate(doc(case))

    def test_actor_information_cannot_pass_through_observations(self):
        case=sample()
        case["observations"][0]["reactor_ids"]=["personal_account_id"]
        with self.assertRaises(ValueError):
            curate(doc(case))
        case=sample()
        case["observations"][0]["counts"]["username"]="ABC"
        with self.assertRaises(ValueError):
            curate(doc(case))

    def test_future_data_and_invalid_counts_rejected(self):
        case=sample()
        case["event_time"]=T0.isoformat()
        with self.assertRaises(ValueError):
            curate(doc(case))
        case=sample()
        case["observations"][-1]["counts"]["LOVE"]=-1
        with self.assertRaises(ValueError):
            curate(doc(case))

    def test_duplicate_cases_rejected(self):
        with self.assertRaises(ValueError):
            curate(doc(sample(),sample()))

    def test_cli_no_overwrite_and_no_leakage(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            source=path/"private.json"
            destination=path/"accepted.json"
            source.write_text(json.dumps(doc(sample())),encoding="utf-8")
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(cli_main([
                    "adjudicate","--input",str(source),"--output",str(destination)
                ]),0)
                self.assertEqual(cli_main([
                    "adjudicate","--input",str(source),"--output",str(destination)
                ]),2)
            result=json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(len(result["cases"]),1)
            self.assertNotIn("RV_A",destination.read_text(encoding="utf-8"))
            self.assertIn("saved_reviewed_cases",output.getvalue())

if __name__=="__main__":
    unittest.main()
