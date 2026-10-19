"""Local, explicitly entered context notes for interpreting reaction time-series.

Context can explain a burst, but is not independent proof of legitimacy.
No actor-level observations, tokens or auto-deductions are stored.
"""
from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from research_quality import parse_utc
from reaction_history import DEFAULT_DB, LOCK, connection, ensure

PAGE = re.compile(r"^[0-9]{4,30}$")
OBJECT = re.compile(r"^(?:[0-9]{4,30}|[0-9]{4,30}_[0-9]{4,30})$")
TYPES = {
    "organizer_announcement": "Ban tổ chức kêu gọi bình chọn",
    "creator_share": "Người sáng tạo hoặc cộng đồng chia sẻ",
    "paid_advertisement": "Quảng cáo có trả phí",
    "media_coverage": "Báo chí hoặc người nổi tiếng nhắc đến",
    "other_known_event": "Sự kiện hợp lệ khác được ghi nhận",
}
MAX_WINDOW_DAYS = 31


def valid_ids(page_id, object_id):
    if not isinstance(page_id, str) or PAGE.fullmatch(page_id) is None:
        raise ValueError("Page ID không hợp lệ")
    if not isinstance(object_id, str) or OBJECT.fullmatch(object_id) is None:
        raise ValueError("Object ID không hợp lệ")


def init(path=DEFAULT_DB):
    ensure(path)
    with LOCK, closing(connection(path)) as db, db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS reaction_context_events(
          id TEXT PRIMARY KEY,
          page_id TEXT NOT NULL,
          object_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          start_utc TEXT NOT NULL,
          end_utc TEXT NOT NULL,
          evidence_ref TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        )""")
        db.execute("""CREATE INDEX IF NOT EXISTS idx_context_object
            ON reaction_context_events(page_id,object_id,start_utc)""")


def validate_event(item):
    if not isinstance(item, dict):
        raise ValueError("Thông tin bối cảnh không hợp lệ")
    pid = item.get("page_id")
    oid = item.get("object_id")
    valid_ids(pid, oid)
    kind = item.get("event_type")
    if kind not in TYPES:
        raise ValueError("Loại bối cảnh không hợp lệ")
    a, b = parse_utc(item.get("start_utc")), parse_utc(item.get("end_utc"))
    if not a or not b or b <= a or (b-a).total_seconds() > MAX_WINDOW_DAYS*86400:
        raise ValueError("Thời gian không hợp lệ; khoảng tối đa 31 ngày")
    reference = item.get("evidence_ref", "")
    note = item.get("note", "")
    if not isinstance(reference, str) or len(reference)>120 or any(ord(c)<32 for c in reference):
        raise ValueError("Mã tham chiếu không hợp lệ")
    if reference.strip().lower().startswith(("http://","https://")):
        raise ValueError("Hãy dùng mã hồ sơ nội bộ, không nhập URL cá nhân")
    if not isinstance(note, str) or len(note)>500 or any(ord(c)<32 and c not in "\n\t" for c in note):
        raise ValueError("Ghi chú không hợp lệ")
    return {"page_id":pid, "object_id":oid, "event_type":kind,
            "start_utc":a.isoformat(), "end_utc":b.isoformat(),
            "evidence_ref":reference.strip(), "note":note.strip()}


def add(item, path=DEFAULT_DB):
    data=validate_event(item)
    init(path)
    key=uuid.uuid4().hex
    with LOCK, closing(connection(path)) as db, db:
        db.execute("""INSERT INTO reaction_context_events
            (id,page_id,object_id,event_type,start_utc,end_utc,evidence_ref,note,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (key,data["page_id"],data["object_id"],data["event_type"],
             data["start_utc"],data["end_utc"],data["evidence_ref"],data["note"],
             datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return key


def listing(page_id, object_id, path=DEFAULT_DB):
    valid_ids(page_id, object_id)
    if not Path(path).is_file():
        return []
    init(path)
    with LOCK, closing(connection(path)) as db:
        rows=db.execute("""SELECT id,event_type,start_utc,end_utc,evidence_ref,note,created_at
            FROM reaction_context_events WHERE page_id=? AND object_id=?
            ORDER BY start_utc DESC LIMIT 250""", (page_id,object_id)).fetchall()
    return [dict(row) for row in rows]


def remove(event_id, page_id, object_id, path=DEFAULT_DB):
    valid_ids(page_id, object_id)
    if not isinstance(event_id,str) or re.fullmatch(r"[0-9a-f]{32}",event_id) is None:
        raise ValueError("Event ID không hợp lệ")
    init(path)
    with LOCK, closing(connection(path)) as db, db:
        count=db.execute("""DELETE FROM reaction_context_events
             WHERE id=? AND page_id=? AND object_id=?""",
             (event_id,page_id,object_id)).rowcount
    return count>0


def overlaps(intervals, events):
    """Decorate flags with overlapping contextual events. Never suppress flags."""
    result=[]
    for item in intervals:
        a=parse_utc(item.get("from"))
        b=parse_utc(item.get("to"))
        if a is None or b is None or b<=a:
            result.append({**item, "context_event_ids":[]})
            continue
        ids=[]
        for e in events:
            start=parse_utc(e.get("start_utc"))
            end=parse_utc(e.get("end_utc"))
            if start and end and max(a,start)<min(b,end):
                ids.append(e["id"])
        result.append({**item, "context_event_ids":ids})
    return result
