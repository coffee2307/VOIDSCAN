"""R2 independent human-review intake gate (research only).

No verdict can be inferred from VOIDSCAN's own anomaly output. Two independent
pseudonymous reviewers must concur, or an independent third reviewer resolves
disagreement. Claim of independence and evidence authenticity is NOT verified
by this software; an external trusted review process remains mandatory.
"""
from __future__ import annotations

from collections import Counter
import re

from research_quality import parse_utc
from research_validation import LABELS, SOURCES, load_cases

MAX_CASES = 5000
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,79}$")
VERDICTS = {"manipulation": "verified_manipulation",
            "legitimate": "verified_legitimate"}
ALL_VERDICTS = set(VERDICTS) | {"inconclusive"}
MODEL_FIELDS = {"verified_label", "flagged_by_frozen_rule",
                "bot_probability_pct", "model_prediction",
                "r1_research_comparison", "suspicious_share_pct"}
BASE_FIELDS = {"case_id", "contest_id", "event_time", "reaction_type",
               "observations", "reviews", "adjudication"}
REVIEW_FIELDS = {"reviewer_id", "verdict", "ground_truth_source",
                 "evidence_ref", "blinded_to_model_flag"}


def _review(value):
    if not isinstance(value, dict) or set(value) != REVIEW_FIELDS:
        raise ValueError("Each review must contain exactly the required fields")
    reviewer=value.get("reviewer_id")
    if not isinstance(reviewer,str) or SAFE_ID.fullmatch(reviewer) is None:
        raise ValueError("Reviewer IDs must be non-identifying pseudonyms")
    decision=value["verdict"]
    if decision not in ALL_VERDICTS:
        raise ValueError("Unsupported event-level review verdict")
    source=value["ground_truth_source"]
    if source not in SOURCES:
        raise ValueError("Review evidence source not permitted")
    ref=value["evidence_ref"]
    if (not isinstance(ref,str) or not 4<=len(ref)<=160 or
        any(ord(c)<32 for c in ref) or
        ref.lower().startswith(("http://","https://"))):
        raise ValueError("Evidence reference must be an internal code")
    if value["blinded_to_model_flag"] is not True:
        raise ValueError("Reviewer must attest no access to model prediction")
    return value


def curate(document):
    """Validate blinded two-review assertions and create replay-ready cases.

    Unresolved events are excluded. These data fields are reviewer ASSERTIONS,
    not platform-certified labels or model calibration evidence.
    """
    if not isinstance(document,dict) or set(document)!={"schema_version","cases"}:
        raise ValueError("Expected schema_version=1 and cases only")
    if document["schema_version"] != 1 or not isinstance(document["cases"],list) or len(document["cases"]) > MAX_CASES:
        raise ValueError("Invalid review case collection")

    seen=set()
    accepted=[]
    excluded=Counter()
    outcome_methods=Counter()
    for index,case in enumerate(document["cases"]):
        if not isinstance(case,dict) or set(case)-BASE_FIELDS or BASE_FIELDS-{"adjudication"}-set(case):
            raise ValueError(f"Invalid case fields at index {index}")
        if set(case)&MODEL_FIELDS:
            raise ValueError("Model predictions must not be shown to blinded reviewers")
        case_id,contest=case["case_id"],case["contest_id"]
        if (not isinstance(case_id,str) or SAFE_ID.fullmatch(case_id) is None or
            not isinstance(contest,str) or SAFE_ID.fullmatch(contest) is None or
            case_id in seen):
            raise ValueError("Invalid/duplicate case or contest pseudonym")
        seen.add(case_id)
        when=parse_utc(case["event_time"])
        if when is None:
            raise ValueError("Event time must contain timezone")
        if case["reaction_type"] not in ("LIKE","LOVE","WOW","HAHA","SAD","ANGRY"):
            raise ValueError("Unsupported reaction type")
        # The full event-observation contract is checked when research_replay
        # evaluates this output. Keep only whitelisted fields in the export.
        series=case["observations"]
        if not isinstance(series,list) or not 2<=len(series)<=500:
            raise ValueError("Observations must be 2..500 timestamped snapshots")
        sanitized=[]
        previous=None
        for point in series:
            if not isinstance(point,dict) or set(point)!={"observed_at","counts"}:
                raise ValueError("Observation fields may only contain time and aggregate counts")
            observed=parse_utc(point["observed_at"])
            counts=point["counts"]
            if observed is None or (previous is not None and observed<=previous):
                raise ValueError("Observations must have strictly increasing timezone-aware times")
            previous=observed
            if not isinstance(counts,dict) or set(counts)-{"LIKE","LOVE","WOW","HAHA","SAD","ANGRY"}:
                raise ValueError("Only aggregate reaction counts are permitted")
            n=counts.get(case["reaction_type"])
            if n is not None and (type(n) is not int or n<0):
                raise ValueError("Reaction count must be nonnegative integer or null")
            sanitized.append({"observed_at":observed.isoformat(),
                              "counts":{case["reaction_type"]:n}})
        if previous!=when:
            raise ValueError("Case event must match latest observation (no future leakage)")
        reviews=case["reviews"]
        if not isinstance(reviews,list) or len(reviews)!=2:
            raise ValueError("Exactly two primary independent reviews are required")
        r1,r2=(_review(x) for x in reviews)
        if r1["reviewer_id"]==r2["reviewer_id"]:
            raise ValueError("Primary reviewer pseudonyms must differ")

        verdict=None
        ref=None
        source=None
        method=None
        arb=case.get("adjudication")
        if r1["verdict"]==r2["verdict"] and r1["verdict"] in VERDICTS:
            if arb is not None:
                raise ValueError("Adjudication not required when two labels agree")
            verdict=r1["verdict"]
            ref=r1["evidence_ref"]
            source=r1["ground_truth_source"]
            method="two_primary_agreement"
        else:
            if arb is None:
                excluded["unresolved_disagreement_or_inconclusive"]+=1
                continue
            arb=_review(arb)
            if arb["reviewer_id"] in (r1["reviewer_id"],r2["reviewer_id"]):
                raise ValueError("Adjudicator must be a third reviewer")
            if arb["verdict"]=="inconclusive":
                excluded["adjudicator_inconclusive"]+=1
                continue
            verdict=arb["verdict"]
            ref=arb["evidence_ref"]
            source=arb["ground_truth_source"]
            method="independent_third_adjudicator"
        labeled={
            "case_id":case_id,
            "contest_id":contest,
            "event_time":when.isoformat(),
            "reaction_type":case["reaction_type"],
            "verified_label":VERDICTS[verdict],
            "ground_truth_source":source,
            "evidence_ref":ref,
            "review_evidence_refs":[r1["evidence_ref"],r2["evidence_ref"]] +
                ([arb["evidence_ref"]] if isinstance(arb,dict) else []),
            "review_resolution_method":method,
            "observations":sanitized,
        }
        # The existing evaluator validates metadata and evidence-ref contract.
        meta={k:labeled[k] for k in ("case_id","contest_id","event_time",
                                    "verified_label","ground_truth_source","evidence_ref")}
        load_cases({"schema_version":1,"cases":[{**meta,"flagged_by_frozen_rule":False}]})
        accepted.append(labeled)
        outcome_methods[method]+=1

    return {
        "schema_version":1,"cases":accepted,
        "review_audit":{
            "submitted":len(document["cases"]),
            "accepted_for_replay":len(accepted),
            "excluded":dict(sorted(excluded.items())),
            "accepted_by_process":dict(sorted(outcome_methods.items())),
            "asserted_reviewer_independence_not_verified":True,
            "evidence_authenticity_not_verified":True,
            "model_predictions_not_used_as_ground_truth":True,
            "bot_account_count":None,
            "automatic_deduction":0,
        },
    }
