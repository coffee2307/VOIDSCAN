"""R0 independent-label event evaluation, research-only.

No model training and no probability calibration. A reviewer-provided label
cannot be inferred from the current VOIDSCAN anomaly score.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime
from math import sqrt

from research_quality import parse_utc

LABELS = {"verified_manipulation": 1, "verified_legitimate": 0}
SOURCES = {"platform_enforcement", "consented_audit",
           "independent_documentation", "contest_evidence_review"}


def wilson(successes, total, z=1.959963984540054):
    if total == 0:
        return None
    p = successes / total
    factor = 1 + z*z/total
    center = (p + z*z/(2*total))/factor
    half = (z/factor)*sqrt((p*(1-p) + z*z/(4*total))/total)
    return [round(max(0, center-half),4),round(min(1, center+half),4)]


def load_cases(doc):
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise ValueError("Expected JSON object with schema_version=1.")
    raw = doc.get("cases")
    if not isinstance(raw, list) or len(raw)>20000:
        raise ValueError("Invalid/oversized case collection.")
    out=[]
    seen=set()
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            raise ValueError("Each case must be an object.")
        eid=row.get("case_id")
        contest=row.get("contest_id")
        when=parse_utc(row.get("event_time"))
        label=row.get("verified_label")
        source=row.get("ground_truth_source")
        evidence=row.get("evidence_ref")
        flag=row.get("flagged_by_frozen_rule")
        if (not isinstance(eid,str) or not 1<=len(eid)<=80 or eid in seen or
            not isinstance(contest,str) or not 1<=len(contest)<=80 or
            when is None or label not in LABELS or source not in SOURCES or
            not isinstance(evidence,str) or not 4<=len(evidence)<=200 or
            type(flag) is not bool):
            raise ValueError(f"Invalid case metadata/label at index {i}.")
        if evidence.lower().startswith(("http://", "https://")):
            raise ValueError("Evidence ref must be internal pseudonymous reference.")
        seen.add(eid)
        out.append({"case_id":eid,"contest_id":contest,
                    "event_time":when,"truth":LABELS[label],"flag":flag,
                    "source":source})
    return out


def evaluate(doc):
    """Frozen-rule replay with contest-group temporal holdout.

    A supplied label is only a claim. Metadata cannot independently certify
    review independence or determine a fake-reaction count.
    """
    cases=load_cases(doc)
    groups={}
    for row in cases:
        groups.setdefault(row["contest_id"],[]).append(row)
    contests=sorted(groups,key=lambda c:(min(r["event_time"] for r in groups[c]),c))
    if len(contests) < 2:
        test=[];train=contests
    else:
        cut=max(1,int(len(contests)*.7))
        cut=min(cut,len(contests)-1)
        train=contests[:cut]
        test=contests[cut:]
    held=[r for cid in test for r in groups[cid]]
    developed=[r for cid in train for r in groups[cid]]
    temporal_overlap=bool(developed and held and
                          max(r["event_time"] for r in developed) >=
                          min(r["event_time"] for r in held))
    tp=sum(r["flag"] and r["truth"]==1 for r in held)
    fp=sum(r["flag"] and r["truth"]==0 for r in held)
    fn=sum(not r["flag"] and r["truth"]==1 for r in held)
    tn=sum(not r["flag"] and r["truth"]==0 for r in held)
    precision=tp/(tp+fp) if tp+fp else None
    recall=tp/(tp+fn) if tp+fn else None
    fpr=fp/(fp+tn) if fp+tn else None
    # Conservative gate for descriptive holdout metrics, NOT for deployment.
    sufficiently_sampled=(not temporal_overlap and len(contests)>=5 and len(test)>=2 and
        len(held)>=40 and (tp+fn)>=10 and (tn+fp)>=10)
    return {
        "schema_version":1,
        "method":"frozen_binary_rule_contest_group_temporal_holdout",
        "all_cases":len(cases),"all_contests":len(contests),
        "development_contests":len(train),"heldout_contests":len(test),
        "heldout_cases":len(held),
        "temporal_overlap":temporal_overlap,
        "holdout_class_balance":{"manipulation":tp+fn,"legitimate":fp+tn},
        "confusion_matrix":{"tp":tp,"fp":fp,"fn":fn,"tn":tn},
        "precision":round(precision,4) if sufficiently_sampled and precision is not None else None,
        "precision_wilson95":wilson(tp,tp+fp) if sufficiently_sampled and precision is not None else None,
        "recall":round(recall,4) if sufficiently_sampled and recall is not None else None,
        "recall_wilson95":wilson(tp,tp+fn) if sufficiently_sampled and recall is not None else None,
        "false_positive_rate":round(fpr,4) if sufficiently_sampled and fpr is not None else None,
        "fpr_wilson95":wilson(fp,fp+tn) if sufficiently_sampled and fpr is not None else None,
        "validation_status":("overlapping_contest_periods" if temporal_overlap else
            "exploratory_holdout_descriptive" if sufficiently_sampled else
            "insufficient_independent_cases"),
        "calibrated_bot_probability_available":False,
        "deployable_for_score_deduction":False,
        "limitations":[
            "Labels are asserted by reviewer; tool cannot independently verify their truth.",
            "Test cases are events, not individual Facebook reaction accounts.",
            "No probability model is trained or calibrated by this evaluator.",
            "Frozen rule and threshold must be preregistered before collecting held-out labels.",
        ],
    }
