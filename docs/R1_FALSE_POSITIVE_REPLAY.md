# VOIDSCAN — Phase R1.5: False-positive review and event replay

Status: engineering capability implemented; **no independently validated Facebook fraud classifier exists in VOIDSCAN**.

## Context annotation in the web interface

After scanning a particular authorized Page photo, expand the "R1 · Bối cảnh tăng reaction" section. Record start/end times and type of event (organizer's request for votes, community sharing, advertising, media mention or other legitimate contextual event). Optionally attach an internal evidence code and note. The annotation belongs to one Page + photo object and is stored in local SQLite.

Annotations are unverified statements by the operator, not evidence that reactions are authentic. They appear beside statistical alert windows when their time ranges overlap, but NEVER suppress alerts, identify bots, or subtract votes. Avoid tokens, actor-level IDs and personal information. Context can be removed manually.

The local context API still works while the Meta user token is expired because this is user-entered metadata and does not request personal Facebook data.

## Independent-label event replay

CLI:

    cd F:\VOIDSCAN
    python research_cli.py replay --input F:\PrivateResearch\reviewed_events.json

Input JSON schema_version=1 with cases array. Each case needs pseudonymous case_id and contest_id, event_time (UTC), reaction_type, verified_label, ground_truth_source, evidence_ref (internal code) and observations (ordered UTC timestamps and aggregate counts). Example of an intentionally short/ineligible case:

    {
      "schema_version":1,
      "cases":[{
        "case_id":"C1-E1","contest_id":"CONTEST_1",
        "event_time":"2026-10-20T00:30:00+00:00",
        "reaction_type":"LOVE",
        "verified_label":"verified_legitimate",
        "ground_truth_source":"independent_documentation",
        "evidence_ref":"REVIEW-LOCAL-001",
        "observations":[
          {"observed_at":"2026-10-20T00:20:00+00:00","counts":{"LOVE":10}},
          {"observed_at":"2026-10-20T00:30:00+00:00","counts":{"LOVE":20}}
        ]
      }]
    }

This example lacks enough history to be evaluated. All observations must be chronologically ordered, have valid timezone-aware timestamps, and the final observation must have the same timestamp as event_time. No future evidence may be used to predict an earlier interval. Counts can be null where unavailable, but are not silently replaced by zeros.

Allowed labels: verified_manipulation and verified_legitimate. Allowed evidence sources: platform_enforcement, consented_audit, independent_documentation and contest_evidence_review. The software cannot authenticate a human reviewer's claim; independent evidence and two-person review are recommended.

R1.5 replay COMPUTES, rather than accepts manually entered, predictions from four frozen rules: median/MAD, rolling P95, mean+5 standard deviations, and at least two-of-three agreement. Only the final event interval is scored; missing histories are excluded with a counter instead of treated as legitimate negatives. The existing contest-group chronological holdout evaluator computes event-level confusion matrices, precision/recall/false-positive rate and Wilson 95% bounds where sufficient independently reviewed cases exist.

Holdout minima are 5 distinct contests overall, >=2 held-out contests, >=40 held-out events including at least 10 verified manipulation and 10 verified legitimate events, and no overlapping contest windows. These are descriptive sample floors, not a demonstration of fitness for automated sanctions.

## Why false positives are unavoidable from counts alone

A legitimate viral share and purchased reactions may produce identical aggregate reaction time series. All three detectors will make identical predictions for identical input. An explicit synthetic regression test asserts this limitation. Their agreement does NOT translate into bot confidence and the models cannot identify individual accounts.

Phase R1.5 tests show reproducible processing on synthetic cases only. No real-world precision, recall or false-positive rate has been measured. R2 requires multiple real competitions, independent ground truth and preregistered candidate thresholds.

No automatic deductions, bot account lists, fake-account count or calibrated probabilities are provided.
