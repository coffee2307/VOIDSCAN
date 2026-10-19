"""VOIDSCAN local-only web server. Start: python server.py"""
from __future__ import annotations
import base64
import csv
import io
import json
import logging
import mimetypes
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from engine import analyze, parse_export, safe_csv_cell
from scan import scan
from meta_pages import MetaAccessError, managed_pages, public_pages, page_posts, configured_mode
import storage

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "web"
DATA = Path(os.environ.get("VOIDSCAN_DATA_DIR", str(ROOT / "data"))).resolve()
IMPORTS = DATA / "imports"
REVIEWS = DATA / "reviews.json"
PORT = int(os.environ.get("VOIDSCAN_PORT", "3000"))
HOST = "127.0.0.1"
BODY_LIMIT = 25 * 1024 * 1024
state_lock = threading.RLock()
analysis = {}
reviews = {}

def load():
    global analysis, reviews
    DATA.mkdir(exist_ok=True)
    IMPORTS.mkdir(exist_ok=True, parents=True)
    with state_lock:
        analysis = analyze(DATA / "sources", IMPORTS)
        try:
            reviews = json.loads(REVIEWS.read_text(encoding="utf-8")) if REVIEWS.exists() else {}
            if not isinstance(reviews, dict):
                reviews = {}
        except (ValueError, OSError):
            reviews = {}

def save_reviews():
    temp = DATA / "reviews.tmp"
    temp.write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(REVIEWS)

def decorated_records():
    for item in analysis["records"]:
        row = dict(item)
        row["decision"] = reviews.get(item["id"], "unreviewed")
        yield row

def selected_rows(params):
    cls = (params.get("class", [""])[0] or "").casefold()
    status = (params.get("status", ["all"])[0] or "all").casefold()
    decision = (params.get("decision", ["all"])[0] or "all").casefold()
    query = (params.get("q", [""])[0] or "").casefold().strip()[:120]
    items = decorated_records()
    if cls:
        items = (x for x in items if x["class"].casefold() == cls)
    if status != "all":
        items = (x for x in items if x["status"] == status or
                 (status == "cross_class" and x["cross_class"]))
    if decision != "all":
        items = (x for x in items if x["decision"] == decision)
    if query:
        items = (x for x in items if query in (x["name"] + " " + x["profile_id"] + " " + x["class"]).casefold())
    return list(items)

def overview():
    with state_lock:
        result = {k: analysis[k] for k in ("summary", "files", "errors", "counts", "timeline")}
        result = dict(result)
        result["counts"] = dict(result["counts"])
        result["counts"]["excluded"] = sum(
            1 for x in analysis["records"] if reviews.get(x["id"]) == "exclude"
        )
        result["counts"]["approved"] = sum(
            1 for x in analysis["records"] if reviews.get(x["id"]) == "keep"
        )
        result["counts"]["eligible"] = sum(
            1 for x in analysis["records"] if not x["duplicate"] and reviews.get(x["id"]) != "exclude"
        )
        return result

class Handler(BaseHTTPRequestHandler):
    server_version = "VOIDSCAN/2.1"
    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.address_string(), fmt % args)

    def respond(self, code, body, mime="application/json; charset=utf-8", filename=None):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def json(self, data, status=200):
        self.respond(status, json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def body_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > BODY_LIMIT:
            raise ValueError("Dung lượng request không hợp lệ (tối đa 25 MB)")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        u = urlsplit(self.path)
        args = parse_qs(u.query)
        try:
            if u.path == "/api/status":
                return self.json({"stats": storage.stats(), "history": storage.list_scans(8),
                                  "connectors": {"meta": configured_mode() != "none",
                                                 "meta_mode": configured_mode(),
                                                 "csv_import": True},
                                  "data_policy": "history_aggregates_only", "retention_days": 90})
            if u.path == "/api/meta/pages":
                if configured_mode() == "none":
                    return self.json({"status":"unconfigured","mode":"none","pages":[],
                                      "message":"Chưa cấu hình token Meta trên server."})
                try:
                    pages = managed_pages()
                    return self.json({"status":"ready" if pages else "no_pages",
                                      "mode":configured_mode(), "pages":public_pages(pages),
                                      "message":"Đã xác minh danh sách Page qua Meta." if pages else "Token chưa cấp quyền truy cập Page."})
                except MetaAccessError as exc:
                    return self.json({"status":"error","mode":configured_mode(),
                                      "pages":[],"error":exc.public()})
            if u.path == "/api/meta/posts":
                selected = args.get("page_id", [""])[0]
                try:
                    pages = managed_pages()
                    if selected not in pages:
                        return self.json({"status":"error",
                                          "error":MetaAccessError("permission").public()}, 403)
                    return self.json({"status":"ready", "page_id":selected,
                                      **page_posts(pages[selected])})
                except MetaAccessError as exc:
                    return self.json({"status":"error","error":exc.public()}, 502)
            if u.path == "/api/scans":
                return self.json({"items": storage.list_scans(100)})
            if u.path.startswith("/api/scans/"):
                item = storage.get_scan(u.path.split("/")[-1])
                return self.json(item) if item else self.json({"error": "Scan not found"}, 404)
            if u.path == "/api/export-history.csv":
                output = io.StringIO(newline="")
                writer = csv.writer(output)
                writer.writerow(["Scan ID", "Created UTC", "Facebook URL", "Source",
                                 "Status", "Evidence items", "Signals"])
                for r in storage.list_scans(None):
                    writer.writerow([safe_csv_cell(r[k]) for k in (
                        "id","created_at","post_url","source","status","evidence_count","signal_count")])
                return self.respond(200, ("\ufeff" + output.getvalue()).encode("utf-8"),
                                    "text/csv; charset=utf-8", "voidscan-history.csv")
            if u.path == "/api/health":
                return self.json({"ok": True, "app": "VOIDSCAN", "network": "local-only"})
            if u.path == "/api/overview":
                return self.json(overview())
            if u.path == "/api/records":
                with state_lock:
                    rows = selected_rows(args)
                offset = min(max(int(args.get("offset", [0])[0]), 0), 1000000)
                limit = min(max(int(args.get("limit", [50])[0]), 1), 200)
                return self.json({"total": len(rows), "offset": offset,
                                  "limit": limit, "items": rows[offset:offset + limit]})
            if u.path == "/api/export.csv":
                with state_lock:
                    rows = selected_rows(args)
                data = io.StringIO(newline="")
                writer = csv.writer(data)
                writer.writerow(["Class", "Source file", "Row", "Profile ID", "Profile Name",
                                 "Date", "Duplicate in class", "Other classes", "Identity known",
                                 "Manual decision", "Reason"])
                for r in rows:
                    writer.writerow([safe_csv_cell(v) for v in (
                        r["class"], r["file"], r["line"], r["profile_id"], r["name"],
                        r["date"], "yes" if r["duplicate"] else "no",
                        "yes" if r["cross_class"] else "no", "yes" if r["has_identity"] else "no",
                        r["decision"], r["reason"])])
                return self.respond(200, ("\ufeff" + data.getvalue()).encode("utf-8"),
                                    "text/csv; charset=utf-8", "voidscan-report.csv")
            if u.path == "/":
                file = ASSETS / "index.html"
            elif u.path in ("/app.css", "/app.js"):
                file = ASSETS / u.path.lstrip("/")
            else:
                return self.json({"error": "Not found"}, 404)
            if not file.is_file():
                return self.json({"error": "Missing asset"}, 404)
            mime = {".css": "text/css", ".js": "text/javascript", ".html": "text/html"}[file.suffix]
            return self.respond(200, file.read_bytes(), mime + "; charset=utf-8")
        except (ValueError, TypeError) as exc:
            return self.json({"error": str(exc)}, 400)
        except Exception:
            logging.exception("GET failed")
            return self.json({"error": "Lỗi máy chủ"}, 500)

    def do_POST(self):
        u = urlsplit(self.path)
        try:
            origin = self.headers.get("Origin", "")
            if origin and origin not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
                return self.json({"error": "Origin không được phép"}, 403)
            if u.path == "/api/reload":
                load()
                return self.json(overview())
            if u.path == "/api/scan":
                data = self.body_json()
                with state_lock:
                    records_snapshot = list(analysis["records"])
                result = scan(data.get("url", ""), records_snapshot, data.get("page_id"))
                stored = storage.persist_scan(data.get("url", ""), result)
                return self.json({**result, "scan_id": stored["id"], "scanned_at": stored["created_at"]})
            if u.path == "/api/review":
                data = self.body_json()
                record_id, decision = str(data.get("id", "")), data.get("decision")
                if decision not in ("keep", "exclude", "unreviewed"):
                    raise ValueError("Giá trị quyết định không hợp lệ")
                with state_lock:
                    if not any(x["id"] == record_id for x in analysis["records"]):
                        return self.json({"error": "Không tìm thấy bản ghi"}, 404)
                    if decision == "unreviewed":
                        reviews.pop(record_id, None)
                    else:
                        reviews[record_id] = decision
                    save_reviews()
                return self.json({"ok": True, "id": record_id, "decision": decision})
            if u.path == "/api/import":
                data = self.body_json()
                supplied = data.get("files", [])
                if not isinstance(supplied, list) or not 1 <= len(supplied) <= 40:
                    raise ValueError("Chọn từ 1 tới 40 file CSV")
                checked = []
                for entry in supplied:
                    name = str(entry.get("name", "")).replace("\\", "/").split("/")[-1]
                    if not name.lower().endswith(".csv") or len(name) > 120 or not name:
                        raise ValueError("Chỉ hỗ trợ file CSV")
                    content = base64.b64decode(entry.get("content", ""), validate=True)
                    recs, _ = parse_export(content, name)
                    checked.append((name, content, len(recs)))
                batch = IMPORTS / uuid.uuid4().hex[:12]
                batch.mkdir(parents=True, exist_ok=False)
                try:
                    for idx, (name, content, _) in enumerate(checked):
                        (batch / (str(idx + 1) + "_" + name)).write_bytes(content)
                except Exception:
                    for path in batch.iterdir():
                        path.unlink()
                    batch.rmdir()
                    raise
                load()
                return self.json({"ok": True, "files": len(checked),
                                  "rows": sum(n for _, _, n in checked), "overview": overview()})
            return self.json({"error": "Not found"}, 404)
        except (ValueError, TypeError, KeyError) as exc:
            return self.json({"error": str(exc)}, 400)
        except Exception:
            logging.exception("POST failed")
            return self.json({"error": "Lỗi máy chủ"}, 500)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load()
    storage.initialize()
    storage.purge_expired(90)
    print(f"VOIDSCAN ready: http://localhost:{PORT}  |  records: {analysis['counts']['total']}  |  classes: {analysis['counts']['classes']}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
