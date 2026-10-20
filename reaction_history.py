"""SQLite reaction snapshots, human-review-only anomaly evidence and monitoring targets.

No per-user data are collected or stored. Snapshots cannot identify fake actors.
"""
from __future__ import annotations
import json
import math
import os
import statistics
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import closing
import sqlite3

from reaction_collector import REACTIONS
from research_quality import parse_utc, EXPECTED_MINUTES, MAX_GAP_MULTIPLIER
from storage import DEFAULT_DB

LOCK = threading.RLock()
MIN_POLL_SECONDS = 300

def connection(path=DEFAULT_DB):
    db=sqlite3.connect(str(path), timeout=10)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    return db

def ensure(path=DEFAULT_DB):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with LOCK, closing(connection(path)) as db, db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS reaction_snapshots(
          id TEXT PRIMARY KEY,
          page_id TEXT NOT NULL,
          post_id TEXT NOT NULL,
          object_id TEXT NOT NULL,
          object_type TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          counts_json TEXT NOT NULL,
          status TEXT NOT NULL,
          source TEXT NOT NULL DEFAULT 'meta_graph_api'
        );
        CREATE INDEX IF NOT EXISTS idx_reaction_times
          ON reaction_snapshots(page_id,object_id,observed_at,id);
        CREATE TABLE IF NOT EXISTS reaction_watches(
          id TEXT PRIMARY KEY,
          page_id TEXT NOT NULL,
          post_id TEXT NOT NULL,
          object_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          last_checked TEXT,
          last_status TEXT,
          active INTEGER NOT NULL DEFAULT 1,
          UNIQUE(page_id,object_id)
        );
        """)

def store_observation(record, path=DEFAULT_DB):
    reaction=record["reaction"]
    if reaction["status"] not in ("ok","partial") or not any(
        type(v) is int and v>=0 for v in reaction["counts"].values()
    ):
        return None
    ensure(path)
    data={key: reaction["counts"].get(key) for key in REACTIONS}
    time=record["observed_at"]
    snapshot_id=uuid.uuid4().hex
    with LOCK, closing(connection(path)) as db, db:
        db.execute("""INSERT INTO reaction_snapshots
        (id,page_id,post_id,object_id,object_type,observed_at,counts_json,status)
        VALUES(?,?,?,?,?,?,?,?)""",
        (snapshot_id, record["page"]["id"], record["post"]["id"],
         record["object"]["id"],record["object"]["type"],time,
         json.dumps(data,ensure_ascii=False),reaction["status"]))
    return snapshot_id

def history(page_id, object_id, limit=250, path=DEFAULT_DB):
    ensure(path)
    n=max(1,min(500,int(limit)))
    with LOCK, closing(connection(path)) as db:
        rows=db.execute("""SELECT id,post_id,object_id,object_type,observed_at,counts_json,status
        FROM reaction_snapshots WHERE page_id=? AND object_id=?
        ORDER BY observed_at DESC,id DESC LIMIT ?""",(page_id,object_id,n)).fetchall()
    result=[]
    for r in reversed(rows):
        item=dict(r)
        item["counts"]=json.loads(item.pop("counts_json"))
        result.append(item)
    return result

def anomaly_report(points, reaction_kind="LOVE"):
    """Robust historical-only rule; NEVER a fake-actor estimate.

    Current interval is compared only with earlier intervals. Require >=5
    prior intervals for any automatic review flag. No future leakage.
    """
    if reaction_kind not in REACTIONS:
        raise ValueError("Reaction kind unsupported")
    segments=[]
    historical_rates=[]
    eligible_intervals=0
    # Reject a missing scheduled poll: for 10-minute cadence, any gap
    # longer than 15 minutes is not an observed 10-minute growth burst.
    max_gap_minutes=EXPECTED_MINUTES * MAX_GAP_MULTIPLIER
    for before,after in zip(points,points[1:]):
        previous=before["counts"].get(reaction_kind)
        current=after["counts"].get(reaction_kind)
        if type(previous) is not int or type(current) is not int:
            historical_rates.clear()
            continue
        a=parse_utc(before.get("observed_at"))
        b=parse_utc(after.get("observed_at"))
        if a is None or b is None:
            historical_rates.clear()
            continue
        mins=(b-a).total_seconds()/60.0
        if mins < .2 or mins > max_gap_minutes:
            historical_rates.clear()
            continue
        delta=current-previous
        if delta>=0:
            eligible_intervals += 1
        rate=delta/mins if delta>=0 else 0.0
        median=statistics.median(historical_rates) if len(historical_rates)>=5 else None
        mad=statistics.median(abs(x-median) for x in historical_rates) if median is not None else None
        threshold=max(4.0*max(median or 0,0.1), (median or 0)+6*1.4826*(mad or 0), 1.0) if median is not None else None
        # Conservative minimum of 20 net reactions and >4/min, independent of baseline.
        flagged=(threshold is not None and delta>=20 and rate>=4 and rate>threshold)
        segments.append({
           "from":before["observed_at"], "to":after["observed_at"],
           "delta":delta, "minutes":round(mins,2), "per_minute":round(rate,3),
           "baseline_rate":round(median,3) if median is not None else None,
           "threshold":round(threshold,3) if threshold is not None else None,
           "flagged":flagged,
           "reason":("Tăng vượt mức lịch sử: cần rà soát, KHÔNG phải số bot"
                     if flagged else ("Thiếu lịch sử đối chiếu" if threshold is None else
                                      "Chưa đủ tín hiệu để gắn cờ"))
        })
        if delta>=0:
            historical_rates.append(rate)
        else:
            historical_rates.clear()
    flagged_delta=sum(max(0,x["delta"]) for x in segments if x["flagged"])
    return {
        "reaction_type":reaction_kind,
        "intervals":segments[-100:],
        "flagged_net_increase":flagged_delta,
        "flagged_intervals":sum(x["flagged"] for x in segments),
        "sample_size":len(points),
        "eligible_intervals":eligible_intervals,
        "status":"review" if flagged_delta else ("insufficient_history" if len(historical_rates)<6 else "no_anomaly_detected"),
        "not_fake_count":True,
        "deductible_reactions":0,
        "disclaimer":"Chỉ là gia tăng ròng trong khoảng bất thường; không xác định tài khoản bot hoặc số tương tác phải trừ."
    }

def watch(page_id, post_id, object_id, path=DEFAULT_DB):
    ensure(path)
    with LOCK, closing(connection(path)) as db, db:
        prev=db.execute("SELECT id FROM reaction_watches WHERE page_id=? AND object_id=?",
                        (page_id,object_id)).fetchone()
        token=prev["id"] if prev else uuid.uuid4().hex
        db.execute("""INSERT INTO reaction_watches
        (id,page_id,post_id,object_id,created_at,active)
        VALUES(?,?,?,?,?,1)
        ON CONFLICT(page_id,object_id) DO UPDATE SET active=1,post_id=excluded.post_id""",
        (token,page_id,post_id,object_id,datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return token

def watch_list(path=DEFAULT_DB):
    ensure(path)
    with LOCK, closing(connection(path)) as db:
        return [dict(x) for x in db.execute(
            """SELECT id,page_id,post_id,object_id,created_at,last_checked,last_status,active
            FROM reaction_watches ORDER BY created_at DESC LIMIT 250""").fetchall()]

def set_watch(id_,active,path=DEFAULT_DB):
    ensure(path)
    with LOCK, closing(connection(path)) as db, db:
        return db.execute("UPDATE reaction_watches SET active=? WHERE id=?",
                          (1 if active else 0,str(id_))).rowcount>0

def update_watch(id_, status, path=DEFAULT_DB):
    ensure(path)
    with LOCK, closing(connection(path)) as db, db:
        db.execute("UPDATE reaction_watches SET last_checked=?,last_status=? WHERE id=?",
                   (datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    str(status)[:30],id_))

def _watch_is_due(row, path, now, poll_seconds):
    """Avoid duplicate API measurements after a recent scan or recent poll."""
    if not 300 <= poll_seconds <= 3600:
        raise ValueError("Invalid reaction polling cadence")
    timestamps=[parse_utc(row.get("last_checked"))]
    with LOCK, closing(connection(path)) as db:
        most_recent=db.execute("""SELECT MAX(observed_at) AS observed
            FROM reaction_snapshots WHERE page_id=? AND object_id=?""",
            (row["page_id"],row["object_id"])).fetchone()
    timestamps.append(parse_utc(most_recent["observed"]) if most_recent else None)
    timestamps=[t for t in timestamps if t is not None]
    if not timestamps:
        return True
    return (now-max(timestamps)).total_seconds() >= poll_seconds


def poll_active_once(path=DEFAULT_DB, *, due_only=False, poll_seconds=600, now=None):
    """Bounded polling; never turn missing Meta data into zero reactions.

    due_only=True is for the scheduler. Manual/test callers default to one
    explicit attempt; the scheduler must not poll a freshly scanned object.
    """
    from reaction_collector import collect_once
    if not 300 <= poll_seconds <= 3600:
        raise ValueError("Invalid reaction polling cadence")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Expected timezone-aware current time")
    watches=[row for row in watch_list(path) if row["active"]][:20]
    outcomes=[]
    for w in watches:
        if due_only and not _watch_is_due(w,path,now,poll_seconds):
            continue
        try:
            sample=collect_once(w["page_id"],w["post_id"],w["object_id"])
            saved=store_observation(sample,path)
            api_error=sample["reaction"].get("api_error") or {}
            status=sample["reaction"]["status"] if saved else str(api_error.get("kind") or "unavailable")[:30]
            update_watch(w["id"],status,path)
            outcomes.append({"id":w["id"],"status":status})
        except Exception as exc:
            # Persist only a known error category, never an API token or raw response.
            from meta_pages import MetaAccessError
            failure=exc.kind if isinstance(exc,MetaAccessError) else "error"
            update_watch(w["id"],failure,path)
            outcomes.append({"id":w["id"],"status":failure})
    return outcomes
