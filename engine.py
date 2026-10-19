"""VOIDSCAN: local, explainable analysis of Facebook share exports.

No account authenticity inference or network scraping occurs in this module.
"""
from __future__ import annotations
import csv
import hashlib
import io
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HEADER_KEYS = {"profile id", "profile name"}
DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%y %H:%M:%S",
)
MAX_CSV_BYTES = 6 * 1024 * 1024

def normalize(value):
    return " ".join(str(value or "").strip().split())

def normalize_id(value):
    value = normalize(value)
    if value.endswith(".0") and value[:-2].isdigit():
        value = value[:-2]
    return value.casefold()

def parse_date(value):
    value = normalize(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).isoformat(timespec="seconds")
        except ValueError:
            pass
    return None

def canonical_class(name):
    return re.sub(r"\s*\(\d+\)$", "", Path(name).stem, flags=re.I).strip()

def decode_csv(data):
    for encoding in ("utf-8-sig", "utf-8", "cp1258", "cp1252"):
        try:
            return data.decode(encoding), encoding
        except UnicodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"

def parse_export(data, filename, record_scope=None):
    if len(data) > MAX_CSV_BYTES:
        raise ValueError(f"{filename}: file lớn hơn giới hạn 6 MB")
    text, encoding = decode_csv(data)
    found = []
    for delim in (",", ";"):
        try:
            rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delim))
        except csv.Error:
            continue
        for i, row in enumerate(rows[:30]):
            normalized = {normalize(c).casefold() for c in row}
            if HEADER_KEYS.issubset(normalized):
                found.append((len(normalized), rows, i, delim))
                break
    if not found:
        raise ValueError(f"{filename}: không tìm thấy cột Profile Name và Profile ID")
    _, rows, header_idx, delimiter = max(found, key=lambda item: item[0])
    columns = [normalize(x).casefold() for x in rows[header_idx]]
    def cell(row, col):
        return normalize(row[columns.index(col)]) if col in columns and columns.index(col) < len(row) else ""
    source_url = ""
    for row in rows[:header_idx]:
        if len(row) >= 2 and normalize(row[0]).casefold() == "source url":
            source_url = normalize(row[1])
            break
    records = []
    for line, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        pid = cell(row, "profile id")
        name = cell(row, "profile name")
        if not pid and not name:
            continue
        identity = normalize_id(pid)
        # Display names are NOT reliable identities and must never be used for deduplication.
        message = cell(row, "message")
        record_id = hashlib.sha256(f"{record_scope or filename}\x00{line}\x00{pid}\x00{message}".encode("utf-8")).hexdigest()[:20]
        records.append({
            "id": record_id, "file": filename, "class": canonical_class(filename),
            "line": line, "name": name, "profile_id": pid,
            "identity": identity, "date": cell(row, "date"),
            "timestamp": parse_date(cell(row, "date")), "message": message[:600],
            "share_url": source_url, "has_identity": bool(identity),
            "duplicate": False, "cross_class": False, "reason": "",
            "status": "unique",
        })
    return records, {"file": filename, "encoding": encoding, "delimiter": delimiter,
                     "rows": len(records), "source_url": source_url}

def analyze(directory, extra_directory=None):
    paths = sorted(directory.glob("*.csv"), key=lambda p: p.name.casefold())
    if extra_directory and extra_directory.is_dir():
        paths += sorted(extra_directory.rglob("*.csv"), key=lambda p: str(p).casefold())
    all_records, files, errors = [], [], []
    for path in paths:
        try:
            is_import = bool(extra_directory and extra_directory in path.parents)
            display_name = re.sub(r"^\d+_", "", path.name) if is_import else path.name
            scope = str(path.relative_to(extra_directory)) if is_import else path.name
            records, detail = parse_export(path.read_bytes(), display_name, scope)
            all_records.extend(records)
            files.append(detail)
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append(str(exc))
    # Duplicate exports of the same profile in the SAME CLASS can be deterministically
    # deduplicated. Sharing different classes is not proof of fraud.
    seen = {}
    class_names_by_identity = defaultdict(set)
    for item in all_records:
        if item["identity"]:
            class_names_by_identity[item["identity"]].add(item["class"])
            k = (item["class"].casefold(), item["identity"])
            if k in seen:
                item["duplicate"] = True
                item["status"] = "duplicate"
                item["reason"] = "Trùng Profile ID trong cùng lớp"
            else:
                seen[k] = item["id"]
        else:
            item["status"] = "unverified"
            item["reason"] = "Không có Profile ID để đối chiếu"
    for item in all_records:
        if item["identity"] and len(class_names_by_identity[item["identity"]]) > 1:
            item["cross_class"] = True
    classes = defaultdict(list)
    for item in all_records:
        classes[item["class"]].append(item)
    summary = []
    for name, items in classes.items():
        total = len(items)
        dupes = sum(x["duplicate"] for x in items)
        unknown = sum(not x["has_identity"] for x in items)
        across = sum(x["cross_class"] and not x["duplicate"] for x in items)
        dated = sum(bool(x["timestamp"]) for x in items)
        summary.append({
            "name": name, "total": total, "unique": total - dupes, "duplicates": dupes,
            "unverified": unknown, "cross_class": across, "dated": dated,
            "duplicate_rate": round(100 * dupes / total, 1) if total else 0,
        })
    summary.sort(key=lambda x: (-x["unique"], x["name"].casefold()))
    timeline = Counter()
    for item in all_records:
        if item["timestamp"]:
            timeline[item["timestamp"][:10]] += 1
    counts = {
        "total": len(all_records), "unique": sum(not x["duplicate"] for x in all_records),
        "duplicates": sum(x["duplicate"] for x in all_records),
        "unverified": sum(not x["has_identity"] for x in all_records),
        "cross_class": sum(x["cross_class"] and not x["duplicate"] for x in all_records),
        "classes": len(summary), "files": len(files), "errors": len(errors)
    }
    return {"summary": summary, "records": all_records, "files": files,
            "errors": errors, "counts": counts,
            "timeline": [{"date": d, "count": n} for d, n in sorted(timeline.items())]}

def safe_csv_cell(value):
    s = str(value if value is not None else "")
    if s.lstrip().startswith(("=", "+", "-", "@")) or s.startswith(("\t", "\r", "\n")):
        return "'" + s
    return s
