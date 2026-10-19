"""R1 exploratory baseline tests on SYNTHETIC time series only."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from research_baselines import compare, METHODS
from reaction_assessment import assess

T0=datetime(2026,10,19,tzinfo=timezone.utc)
def series(counts,step=10,kind="LOVE"):
    return [{"observed_at":(T0+timedelta(minutes=i*step)).isoformat(),
             "counts":{kind:v}} for i,v in enumerate(counts)]

class BaselineTests(unittest.TestCase):
    def test_single_historical_measurement_is_not_a_fraud_estimate(self):
        report=compare(series([1000]))
        self.assertEqual(report["status"],"insufficient_history")
        self.assertEqual(report["evaluated_intervals"],0)
        self.assertIsNone(report["bot_probability_pct"])
        self.assertEqual(report["automatic_deduction"],0)

    def test_steady_growth_is_not_flagged(self):
        data=series([10,20,30,40,50,60,70,80,90])
        report=compare(data)
        self.assertGreater(report["evaluated_intervals"],0)
        self.assertEqual(report["multi_method_agreement_intervals"],0)
        for m in METHODS:
            self.assertEqual(report["method_results"][m]["flagged_growth"],0)

    def test_big_spike_triggers_all_research_baselines(self):
        data=series([10,20,30,40,50,60,70,700])
        report=compare(data)
        self.assertEqual(report["status"],"experimental_unvalidated")
        self.assertEqual(report["multi_method_agreement_intervals"],1)
        self.assertEqual(report["disagreement_intervals"],0)
        for m in METHODS:
            self.assertEqual(report["method_results"][m]["flagged_growth"],630)
            self.assertEqual(report["method_results"][m]["excess_above_reference"],620)
        self.assertIsNone(report["confirmed_fake_reactions"])

    def test_legitimate_promotion_same_pattern_is_indistinguishable(self):
        # Valid promotional surge and synthetic manipulation with identical
        # aggregate observations necessarily produce the same model output.
        history=series([10,20,30,40,50,60,70,700])
        normal_promotional_event=compare(history)
        malicious_event=compare(history)
        self.assertEqual(normal_promotional_event,malicious_event)
        self.assertIn("KHÔNG phải",normal_promotional_event["warning"])

    def test_missing_middle_read_does_not_create_burst(self):
        data=series([10,20,30,40,50,60,None,700])
        r=compare(data)
        self.assertEqual(r["multi_method_agreement_intervals"],0)
        self.assertEqual(r["evaluated_intervals"],0)

    def test_missing_scheduled_poll_not_bridged(self):
        data=series([10,20,30,40,50,60])
        data.append({"observed_at":(T0+timedelta(minutes=70)).isoformat(),
                     "counts":{"LOVE":700}})
        r=compare(data)
        self.assertEqual(r["multi_method_agreement_intervals"],0)
        self.assertEqual(r["evaluated_intervals"],0)

    def test_negative_reaction_correction_resets_baseline(self):
        data=series([10,20,30,40,50,60,70,30,900])
        r=compare(data)
        self.assertEqual(r["multi_method_agreement_intervals"],0)
        self.assertEqual(r["automatic_deduction"],0)

    def test_type_separation(self):
        data=series([10,20,30,40,50,60,70,700],kind="LOVE")
        with self.assertRaises(ValueError):
            compare(data,"CARE")
        no_sad=compare(data,"SAD")
        self.assertEqual(no_sad["status"],"insufficient_history")

    def test_comparison_does_not_mutate_source(self):
        data=series([10,20,30,40,50,60,70,700])
        before=str(data)
        compare(data)
        self.assertEqual(str(data),before)

if __name__=="__main__":
    unittest.main()
