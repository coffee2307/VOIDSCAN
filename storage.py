"""Local scan history: SQLite, private, aggregate-only and versioned."""
from __future__ import annotations
import json
import os
import sqlite3
from contextlib import contextmanager
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

DEFAULT_DB = Path(os.environ.get("VOIDSCAN_DATA_DIR", str(Path(__file__).resolve().parent / "data"))).resolve() / "voidscan.sqlite3"
_lock = threading.RLock()
SCHEMA_VERSION = 1

def _connect(path=DEFAULT_DB):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 10000")
    return db

@contextmanager
def connected(path):
    db = _connect(path)
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize(path=DEFAULT_DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock, connected(path) as db:
        db.executescript("""
          CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS scan_jobs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            post_url TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            result_json TEXT NOT NULL,
            evidence_count INTEGER NOT NULL DEFAULT 0,
            signal_count INTEGER NOT NULL DEFAULT 0
          );
          CREATE INDEX IF NOT EXISTS ix_scan_jobs_created ON scan_jobs(created_at DESC);
        """)
        db.execute("INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('version', ?)",
                   (str(SCHEMA_VERSION),))

def canonical_url(url):
    parsed = urlsplit(url)
    allowed = {}
    qs = parse_qs(parsed.query)
    for key in ("story_fbid", "fbid", "id"):
        if key in qs:
            allowed[key] = qs[key][0][:80]
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(("https", "www.facebook.com", path, urlencode(allowed), ""))

def persist_scan(url, result, path=DEFAULT_DB):
    """Save evidence summaries only, not user identifiers or raw comments."""
    from scan import validate_url
    validate_url(url)
    initialize(path)
    purge_expired(90, path)
    clean = {
        "status": result.get("status", "unavailable"),
        "source": result.get("source", "none"),
        "message": str(result.get("message", ""))[:1200],
        "comments": int(result.get("comments", 0)),
        "total": int(result.get("total", 0)),
        "duplicates": int(result.get("duplicates", 0)),
        "unverified": int(result.get("unverified", 0)),
        "suspicious": int(result.get("suspicious", 0)),
        "signals": [
            {"label": str(x.get("label", ""))[:140],
             "count": int(x.get("count", 0)),
             "explanation": str(x.get("explanation", ""))[:450],
             "level": str(x.get("level", "info")) if x.get("level") in ("info", "review") else "info"}
            for x in result.get("signals", [])[:12]
        ],
    }
    evidence = clean["comments"] or clean["total"]
    signal_count = sum(1 for item in clean["signals"] if item["count"] > 0 and item["level"] == "review")
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    scan_id = uuid.uuid4().hex
    with _lock, connected(path) as db:
        db.execute(
            "INSERT INTO scan_jobs(id,created_at,post_url,source,status,result_json,evidence_count,signal_count)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (scan_id, created, canonical_url(url), clean["source"], clean["status"],
             json.dumps(clean, ensure_ascii=False), evidence, signal_count))
    return {"id": scan_id, "created_at": created, **clean}

def list_scans(limit=50, path=DEFAULT_DB):
    initialize(path)
    n = max(1, min(100, int(limit))) if limit is not None else None
    with _lock, connected(path) as db:
        if n is None:
            rows = db.execute("SELECT id,created_at,post_url,source,status,evidence_count,signal_count FROM scan_jobs ORDER BY created_at DESC,id DESC").fetchall()
        else:
            rows = db.execute("SELECT id,created_at,post_url,source,status,evidence_count,signal_count FROM scan_jobs ORDER BY created_at DESC,id DESC LIMIT ?", (n,)).fetchall()
    return [dict(row) for row in rows]

def get_scan(scan_id, path=DEFAULT_DB):
    initialize(path)
    if len(scan_id) != 32 or not all(c in "0123456789abcdef" for c in scan_id):
        return None
    with _lock, connected(path) as db:
        row = db.execute("SELECT * FROM scan_jobs WHERE id=?", (scan_id,)).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["result"] = json.loads(data.pop("result_json"))
    return data

def stats(path=DEFAULT_DB):
    initialize(path)
    with _lock, connected(path) as db:
        row = db.execute("""
           SELECT COUNT(*) AS scans,
           COALESCE(SUM(CASE WHEN status='live' THEN 1 ELSE 0 END),0) AS live,
           COALESCE(SUM(CASE WHEN status='matched' THEN 1 ELSE 0 END),0) AS local,
           COALESCE(SUM(CASE WHEN status='unavailable' THEN 1 ELSE 0 END),0) AS unavailable,
           COALESCE(SUM(CASE WHEN signal_count>0 THEN 1 ELSE 0 END),0) AS flagged
           FROM scan_jobs
        """).fetchone()
    return dict(row)

def purge_expired(days=90, path=DEFAULT_DB):
    initialize(path)
    days = min(3650, max(1, int(days)))
    cutoff = (datetime.now(timezone.utc)-timedelta(days=days)).isoformat(timespec="seconds")
    with _lock, connected(path) as db:
        count = db.execute("DELETE FROM scan_jobs WHERE created_at < ?",(cutoff,)).rowcount
    return count
