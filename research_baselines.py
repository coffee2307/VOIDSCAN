"""R1: comparison of transparent statistical baselines on aggregate reactions.

No actor identity, no ML classifier, and no calibrated fraud probability.
All thresholds are research candidates, NOT validated sanctions criteria.
"""
from __future__ import annotations

import math
import statistics
from collections import deque

from reaction_collector import REACTIONS
from research_quality import parse_utc, EXPECTED_MINUTES, MAX_GAP_MULTIPLIER

METHODS = ("robust_mad", "rolling_p95", "mean_5sigma")
DISPLAY = {
    "robust_mad": "Trung vị + MAD",
    "rolling_p95": "Phân vị lịch sử",
    "mean_5sigma": "Trung bình + độ lệch chuẩn",
}
PRIOR_MIN = 5
PRIOR_MAX = 36
MIN_DELTA = 20
MIN_RATE = 4.0


def percentile(values, quantile):
    """No dependence on numpy; interpolate between ordered observations."""
    sorted_values = sorted(values)
    if not sorted_values:
        return None
    k = quantile * (len(sorted_values) - 1)
    low = math.floor(k)
    high = math.ceil(k)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (k - low)


def thresholds(prior):
    median = statistics.median(prior)
    mad = statistics.median(abs(x - median) for x in prior)
    mean = statistics.fmean(prior)
    std = statistics.pstdev(prior)
    p95 = percentile(prior, .95)
    return {
        "robust_mad": max(MIN_RATE, 4 * max(median, .1), median + 6 * 1.4826 * mad),
        "rolling_p95": max(MIN_RATE, 3 * p95),
        "mean_5sigma": max(MIN_RATE, 4 * mean, mean + 5 * std),
    }


def compare(points, kind="LOVE"):
    """Run candidate baselines on the *original*, ordered snapshot stream.

    Duplicates/failed readings/time gaps invalidate the affected interval.
    The baseline is reset after gaps; no interpolation across unobserved time.
    """
    if kind not in REACTIONS:
        raise ValueError("Unsupported reaction type")
    rows = list(points)
    priors = deque(maxlen=PRIOR_MAX)
    summary = {m: {"flagged_intervals": 0, "flagged_growth": 0,
                   "excess_above_reference": 0} for m in METHODS}
    eligible = 0
    compared = 0
    agree = 0
    disagreements = 0
    flagged_details = []
    for before, after in zip(rows, rows[1:]):
        t0 = parse_utc(before.get("observed_at"))
        t1 = parse_utc(after.get("observed_at"))
        c0 = (before.get("counts") or {}).get(kind)
        c1 = (after.get("counts") or {}).get(kind)
        elapsed = (t1 - t0).total_seconds() / 60 if t0 and t1 else 0
        if (type(c0) is not int or type(c1) is not int or c0 < 0 or c1 < 0
                or elapsed < .2 or elapsed > EXPECTED_MINUTES * MAX_GAP_MULTIPLIER):
            priors.clear()
            continue
        change = c1 - c0
        if change < 0:
            # Deleted/revised reactions: never mark removed votes as suspicious.
            priors.clear()
            continue
        eligible += 1
        rate = change / elapsed
        if len(priors) >= PRIOR_MIN:
            compared += 1
            t = thresholds(list(priors))
            flags = {
                m: change >= MIN_DELTA and rate >= MIN_RATE and rate > t[m]
                for m in METHODS
            }
            flag_count = sum(flags.values())
            agree += flag_count >= 2
            disagreements += 0 < flag_count < len(METHODS)
            if flag_count:
                base_rate = statistics.median(priors)
                excess = max(0, math.floor(change - base_rate * elapsed))
                flagged_details.append({
                    "from": before["observed_at"], "to": after["observed_at"],
                    "growth": change, "per_minute": round(rate, 3),
                    "excess_above_reference": excess,
                    "flag_count": flag_count,
                    "methods": [m for m in METHODS if flags[m]],
                })
            for m in METHODS:
                if flags[m]:
                    summary[m]["flagged_intervals"] += 1
                    summary[m]["flagged_growth"] += change
                    summary[m]["excess_above_reference"] += max(
                        0, math.floor(change - statistics.median(priors) * elapsed)
                    )
        priors.append(rate)
    return {
        "status": "experimental_unvalidated" if compared else "insufficient_history",
        "reaction_type": kind,
        "eligible_intervals": eligible,
        "evaluated_intervals": compared,
        "method_results": {m: {"name": DISPLAY[m], **summary[m]} for m in METHODS},
        "multi_method_agreement_intervals": agree,
        "disagreement_intervals": disagreements,
        "examples": flagged_details[-100:],
        "bot_probability_pct": None,
        "confirmed_fake_reactions": None,
        "automatic_deduction": 0,
        "warning": (
            "Các thuật toán cùng sử dụng một chuỗi số đếm: đồng thuận KHÔNG "
            "phải các bằng chứng độc lập và KHÔNG phải tỷ lệ chắc chắn gian lận. "
            "Phần vượt mức tham chiếu không phải số tài khoản ảo."
        ),
    }
