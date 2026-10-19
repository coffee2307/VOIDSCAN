"""R1.5: reproducible event-level replay on externally reviewed aggregate histories.

The tool computes detection flags FROM the frozen VOIDSCAN algorithms; reviewers
provide evidence-backed event labels separately. No false bot-count claims.
"""
from __future__ import annotations

from datetime import datetime
from research_baselines import compare, METHODS
from research_quality import parse_utc
from research_validation import evaluate, load_cases

MAX_CASES=5000
MAX_OBSERVATIONS=500


def replay(document):
    if not isinstance(document,dict) or document.get("schema_version")!=1:
        raise ValueError("Expected schema_version=1")
    cases=document.get("cases")
    if not isinstance(cases,list) or len(cases)>MAX_CASES:
        raise ValueError("Too many cases")
    # Validate all independent labels, contests, timestamps and evidence IDs
    # without accepting a manually supplied prediction flag.
    base=[]
    events=[]
    for index,raw in enumerate(cases):
        if not isinstance(raw,dict):
            raise ValueError("Each case must be an object")
        normalized={k:v for k,v in raw.items() if k!="flagged_by_frozen_rule"}
        normalized["flagged_by_frozen_rule"]=False
        base.append(normalized)
        typ=raw.get("reaction_type")
        if typ not in ("LIKE","LOVE","WOW","HAHA","SAD","ANGRY"):
            raise ValueError(f"Invalid reaction type at {index}")
        observations=raw.get("observations")
        if not isinstance(observations,list) or not 2 <= len(observations) <= MAX_OBSERVATIONS:
            raise ValueError(f"Invalid observation count at {index}")
        previous=None
        normalized_rows=[]
        for row in observations:
            if not isinstance(row,dict):
                raise ValueError("Observation must be object")
            timestamp=parse_utc(row.get("observed_at"))
            raw_counts=row.get("counts")
            if timestamp is None or not isinstance(raw_counts,dict):
                raise ValueError("Observation needs UTC time and reaction counts")
            if previous is not None and timestamp <= previous:
                raise ValueError("Observations must be strictly increasing")
            previous=timestamp
            count=raw_counts.get(typ)
            if count is not None and (type(count) is not int or count < 0):
                raise ValueError("Reaction count must be integer >= 0 or null")
            normalized_rows.append({"observed_at":timestamp.isoformat(),
                                    "counts":{typ:count}})
        observed_at=parse_utc(raw.get("event_time"))
        if observed_at is None or previous != observed_at:
            raise ValueError("Event time must exactly match last observation")
        events.append((typ,normalized_rows))
    load_cases({"schema_version":1,"cases":base})
    prepared={m:[] for m in (*METHODS,"consensus_2_of_3")}
    ignored=0
    for original,(reaction,history) in zip(base,events):
        result=compare(history,reaction)
        if not result["last_interval_evaluated"]:
            ignored+=1
            continue
        flags=set(result["last_interval_flags"])
        for m in METHODS:
            prepared[m].append({**original,"flagged_by_frozen_rule":m in flags})
        prepared["consensus_2_of_3"].append({
            **original, "flagged_by_frozen_rule":len(flags)>=2})
    reports={method:evaluate({"schema_version":1,"cases":data})
             for method,data in prepared.items()}
    return {
        "schema_version":1,
        "method":"point_in_time_historical_only_event_replay",
        "input_cases":len(cases),
        "eligible_cases":len(cases)-ignored,
        "skipped_insufficient_or_broken_history":ignored,
        "metrics":reports,
        "calibrated_bot_probability":None,
        "fake_account_count":None,
        "automatic_deduction":0,
        "caution":"Labels must be independently verified by humans. This code "
                  "cannot verify evidence. A legitimate viral burst can mimic "
                  "manipulation on aggregate timelines.",
    }
