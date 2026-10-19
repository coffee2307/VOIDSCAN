"""Interpretable reaction integrity summary: provisional statistical indicators only.

Do not claim any actor is fake. Do not convert thresholds into pseudo-probabilities.
"""
from __future__ import annotations
from datetime import datetime
from reaction_collector import REACTIONS
from reaction_history import anomaly_report


def assess(points: list[dict], reaction_kind: str = "LOVE") -> dict:
    if reaction_kind not in REACTIONS:
        raise ValueError("Loại cảm xúc không được hỗ trợ.")
    usable = []
    for item in points:
        count = (item.get("counts") or {}).get(reaction_kind)
        if type(count) is int and count >= 0:
            usable.append(item)
    analysis = anomaly_report(usable, reaction_kind)
    last = usable[-1]["counts"][reaction_kind] if usable else None
    first = usable[0]["counts"][reaction_kind] if usable else None
    number = analysis["flagged_net_increase"] if last is not None else None
    flagged_count = analysis["flagged_intervals"]
    total_intervals = max(0, len(usable) - 1)
    # A high number of samples does not verify the truth of a bot accusation.
    signal_ready = total_intervals >= 6
    if not usable:
        coverage = "không_có_dữ_liệu"
        headline = "Chưa thu thập được reaction"
    elif not signal_ready:
        coverage = "chưa_đủ_lịch_sử"
        headline = "Chưa đủ lịch sử để xác định đột biến"
    elif flagged_count:
        coverage = "có_chỉ_báo"
        headline = "Phát hiện khoảng tăng trưởng đáng rà soát"
    else:
        coverage = "chưa_phát_hiện"
        headline = "Chưa phát hiện đột biến theo quy tắc hiện tại"
    ratio = round(100.0 * number / last, 1) if (
        signal_ready and last and number is not None
    ) else (0.0 if signal_ready and last == 0 and number == 0 else None)
    # Reactions can be removed; flagged net growth is not necessarily present
    # in the latest total. Do not show an impossible percentage > 100.
    if ratio is not None and ratio > 100:
        ratio = None

    dates = []
    for item in usable:
        try:
            dates.append(datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00")))
        except (KeyError, TypeError, ValueError):
            pass
    observation_hours = round((max(dates) - min(dates)).total_seconds() / 3600, 2) if len(dates) >= 2 else 0.0
    return {
        "reaction_type": reaction_kind,
        "current_reactions": last,
        "first_observed_reactions": first,
        "suspicious_window_reactions": number if signal_ready else None,
        "suspicious_share_pct": ratio,
        "flagged_intervals": flagged_count if signal_ready else None,
        "observed_intervals": total_intervals,
        "observed_snapshots": len(usable),
        "observation_hours": observation_hours,
        "evidence_status": coverage,
        "headline": headline,
        "intervals": analysis["intervals"],
        "bot_probability_pct": None,
        "confirmed_fake_reactions": None,
        "automatic_deduction": 0,
        "caveat": (
            "Số đáng nghi = mức tăng ròng trong các khoảng bị gắn cờ thống kê, "
            "KHÔNG phải số tài khoản ảo. Phần trăm là tỷ lệ của những lượt tăng đó "
            "so với tổng số reaction quan sát gần nhất, không phải xác suất gian lận."
        ),
    }
