"""R0: provenance and continuity audit for aggregate reaction observations.

Quality metrics describe observability, NOT probability of bot activity.
Never interpolate unobserved reaction counts or merge missing measurements.
"""
from __future__ import annotations

from datetime import datetime, timezone
from reaction_collector import REACTIONS

EXPECTED_MINUTES = 10.0
MAX_GAP_MULTIPLIER = 1.5


def parse_utc(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None


def audit_series(points, kind="LOVE", expected_minutes=EXPECTED_MINUTES, now=None):
    """Audit source readings without manufacturing positive/negative labels.

    Each interval must have *adjacent* observations, positive elapsed time,
    and a bounded gap. No rejoining across a missing/corrupt observation.
    """
    if kind not in REACTIONS:
        raise ValueError("Unsupported reaction type")
    if not isinstance(expected_minutes, (int, float)) or not 1 <= expected_minutes <= 60:
        raise ValueError("Expected interval must be 1–60 minutes")
    data = list(points)
    parsed = []
    for row in data:
        dt = parse_utc(row.get("observed_at"))
        counts = row.get("counts") or {}
        count = counts.get(kind) if isinstance(counts, dict) else None
        valid = type(count) is int and count >= 0
        parsed.append((dt, count if valid else None))
    good = [(t, v) for t, v in parsed if t is not None and v is not None]
    eligible, missing, invalid_times, repeats, big_gaps, disorder = 0, 0, 0, 0, 0, 0
    run, longest, corrections = 0, 0, 0
    for t, v in parsed:
        if v is None:
            missing += 1
        if t is None:
            invalid_times += 1
    for (a, prev), (b, current) in zip(parsed, parsed[1:]):
        if a is None or b is None:
            run = 0
            continue
        seconds = (b - a).total_seconds()
        if seconds <= 0:
            run = 0
            if seconds == 0:
                repeats += 1
            else:
                disorder += 1
            continue
        if seconds > expected_minutes * MAX_GAP_MULTIPLIER * 60:
            run = 0
            big_gaps += 1
            continue
        if prev is not None and current is not None and current < prev:
            corrections += 1
            run = 0
            continue
        if prev is not None and current is not None and seconds >= 12:
            eligible += 1
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    latest = good[-1][0] if good else None
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    age_minutes = round((now - latest).total_seconds() / 60, 2) if latest else None
    stale = age_minutes is not None and age_minutes > 3 * expected_minutes
    known = len(good)
    return {
        "kind": kind,
        "total_snapshots": len(data),
        "valid_snapshots": known,
        "missing_counts": missing,
        "invalid_timestamps": invalid_times,
        "repeated_timestamps": repeats,
        "out_of_order": disorder,
        "long_gaps": big_gaps,
        "negative_corrections": corrections,
        "eligible_adjacent_intervals": eligible,
        "longest_contiguous_intervals": longest,
        "missing_fraction": round(missing / len(data), 4) if data else None,
        "latest_sample_at": latest.isoformat() if latest else None,
        "latest_sample_age_minutes": age_minutes,
        "stale": stale,
        "min_intervals_for_review": 6,
        "ready_for_review": longest >= 6 and known >= 7,
        "actor_level_data_available": False,
        "calibrated_bot_probability_available": False,
        "notes": "Chất lượng đo không xác minh tài khoản, gian lận hoặc khả năng dự báo.",
    }
