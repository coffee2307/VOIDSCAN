"""R1.6 local monitoring/readiness diagnostics, independent of Meta credentials.

This answers whether enough aggregate observations exist to *begin* applying
research heuristics. It does NOT certify a detector or authenticate a bot.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from reaction_collector import REACTIONS
from research_quality import audit_series, parse_utc
from storage import DEFAULT_DB

PROBLEM_STATUSES={"expired","configuration","permission","rate_limit",
                  "network","not_found","response","error","unavailable"}


def _elapsed(now, iso):
    dt=parse_utc(iso) if iso else None
    return max(0, round((now-dt).total_seconds())) if dt is not None else None


def _empty():
    return {
        "status":"no_data",
        "snapshots":0,
        "historical_objects":0,
        "total_watches":0,
        "active_watches":0,
        "active_stale":0,
        "active_errors":0,
        "objects_with_usable_history":0,
        "series_with_usable_history":0,
        "latest_snapshot_at":None,
        "latest_snapshot_age_seconds":None,
        "latest_monitor_check_at":None,
        "latest_monitor_check_age_seconds":None,
        "last_monitor_errors":{},
        "polling_requires_server_online":True,
        "meta_token_validated":False,
        "bot_probability_validated":False,
        "automatic_deduction":0,
        "instructions":["Chọn Page và ảnh được Meta cấp quyền, nhấn Quét, sau đó bật theo dõi định kỳ."]
    }


def readiness(path=DEFAULT_DB, now=None, poll_seconds=600):
    """Inspect local SQLite without API calls, DDL, write operations, or exposing IDs."""
    if not 300 <= poll_seconds <= 3600:
        raise ValueError("Invalid polling interval")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now needs a timezone")
    result=_empty()
    if not Path(path).is_file():
        return result

    # Database in normal read-only URI mode. Does not change user data.
    uri=Path(path).resolve().as_uri()+"?mode=ro"
    with closing(sqlite3.connect(uri,uri=True,timeout=5)) as db:
        db.row_factory=sqlite3.Row
        n=db.execute("SELECT COUNT(*) FROM reaction_snapshots").fetchone()[0]
        o=db.execute("""SELECT COUNT(*) FROM (
            SELECT 1 FROM reaction_snapshots GROUP BY page_id, object_id)""").fetchone()[0]
        last=db.execute("SELECT MAX(observed_at) FROM reaction_snapshots").fetchone()[0]
        watches=[dict(r) for r in db.execute(
            "SELECT page_id, object_id, last_checked, last_status, active "
            "FROM reaction_watches ORDER BY created_at DESC LIMIT 250")]
        result.update(snapshots=n,historical_objects=o,total_watches=len(watches),
                      latest_snapshot_at=last,
                      latest_snapshot_age_seconds=_elapsed(now,last))
        active=[w for w in watches if w["active"]]
        result["active_watches"]=len(active)
        checks=[w["last_checked"] for w in active if w["last_checked"]]
        latest_checked=max(checks,default=None)
        result["latest_monitor_check_at"]=latest_checked
        result["latest_monitor_check_age_seconds"]=_elapsed(now,latest_checked)
        statuses={}
        complete_objects=0
        series_ready=0
        for w in active:
            kind=str(w["last_status"] or "not_checked")
            if kind in PROBLEM_STATUSES:
                result["active_errors"]+=1
                statuses[kind]=statuses.get(kind,0)+1
            check_age=_elapsed(now,w["last_checked"])
            if check_age is None or check_age > max(2.5 * poll_seconds, 1800):
                result["active_stale"]+=1
            records=db.execute("""
               SELECT observed_at, counts_json FROM reaction_snapshots
               WHERE page_id=? AND object_id=? ORDER BY observed_at DESC, id DESC LIMIT 500
            """,(w["page_id"],w["object_id"])).fetchall()
            points=[]
            for r in reversed(records):
                try:
                    data=json.loads(r["counts_json"])
                except (ValueError,TypeError):
                    data={}
                points.append({"observed_at":r["observed_at"],
                               "counts":data if isinstance(data,dict) else {}})
            valid_types=0
            for reaction in REACTIONS:
                if audit_series(points,reaction,now=now)["ready_for_review"]:
                    series_ready+=1
                    valid_types+=1
            if valid_types:
                complete_objects+=1
        result["last_monitor_errors"]=statuses
        result["objects_with_usable_history"]=complete_objects
        result["series_with_usable_history"]=series_ready

    recommendations=[]
    if not active:
        result["status"]="not_monitoring" if result["snapshots"] else "no_data"
        recommendations.append("Chưa theo dõi ảnh nào: chọn ảnh dự thi, quét và bấm Bật theo dõi định kỳ.")
    elif result["active_errors"]:
        result["status"]="monitor_errors"
        if statuses.get("expired"):
            recommendations.append("Meta token đã hết hạn ở lần theo dõi gần đây; cần lưu token mới trên máy.")
        else:
            recommendations.append("Có lỗi thu thập; kiểm tra kết nối, quyền Page hoặc giới hạn Meta.")
    elif result["active_stale"]==len(active):
        result["status"]="monitor_stale"
        recommendations.append("Không ghi nhận lượt kiểm tra gần đây; cần giữ VOIDSCAN chạy và kiểm tra Meta.")
    elif complete_objects:
        result["status"]="observing_with_history"
        recommendations.append("Đã đủ mốc cho phân tích thống kê trên một số chuỗi. Vẫn chưa có xác suất bot được kiểm định.")
    else:
        result["status"]="collecting"
        recommendations.append("Đang thu thập: cần ít nhất 7 mốc liên tiếp hợp lệ trên mỗi loại reaction.")
    result["instructions"]=recommendations
    return result
