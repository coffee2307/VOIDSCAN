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
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from engine import analyze, parse_export, safe_csv_cell
from scan import scan
from meta_pages import MetaAccessError, managed_pages, public_pages, page_posts, configured_mode
import storage
import reaction_collector
import reaction_history
from reaction_assessment import assess
from share_resolver import resolve_shortlink
from scan import reference, validate_url
from secret_store import TokenStoreError, synchronize_meta_token, credential_source

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "web"
DATA = Path(os.environ.get("VOIDSCAN_DATA_DIR", str(ROOT / "data"))).resolve()
IMPORTS = DATA / "imports"
REVIEWS = DATA / "reviews.json"
PORT = int(os.environ.get("VOIDSCAN_PORT", "3000"))
REACTION_POLL_SECONDS = max(300,min(3600,int(os.environ.get("VOIDSCAN_REACTION_INTERVAL_SECONDS","600"))))
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
    server_version = "VOIDSCAN/3.0"
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
            if u.path.startswith("/api/"):
                synchronize_meta_token()
            if u.path == "/api/status":
                return self.json({"stats": storage.stats(), "history": storage.list_scans(8),
                                  "connectors": {"meta": configured_mode() != "none",
                                                 "meta_mode": configured_mode(),
                                                 "credential_source": credential_source(),
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

            if u.path == "/api/reactions/objects":
                try:
                    pid = args.get("page_id", [""])[0]
                    page = reaction_collector.verify_page(pid)
                    post, limited = reaction_collector.select_post(
                        page,post_id=args.get("post_id",[""])[0],
                        url=args.get("url",[""])[0] or None)
                    children = reaction_collector.attached_objects(page,post)
                    return self.json({"status":"ready","post":post,
                                      "catalog_partial":limited,"attachments":children})
                except MetaAccessError as exc:
                    return self.json({"status":"unavailable","error":exc.public()})
            if u.path == "/api/reactions/photos":
                try:
                    page_id=args.get("page_id",[""])[0]
                    page=reaction_collector.verify_page(page_id)
                    return self.json({"status":"ready","page_id":page_id,
                                      **reaction_collector.page_photos(page)})
                except MetaAccessError as exc:
                    return self.json({"status":"unavailable","error":exc.public()})

            if u.path == "/api/reactions/resolve-share":
                page_id=args.get("page_id",[""])[0]
                raw_url=args.get("url",[""])[0]
                validate_url(raw_url)
                try:
                    page=reaction_collector.verify_page(page_id)
                    resolved=resolve_shortlink(raw_url)
                    if resolved.get("status")=="unresolved":
                        return self.json(resolved)
                    target_url=resolved["url"]
                    ref=reference(target_url)
                    photo_id=ref.get("post_id")
                    if photo_id:
                        try:
                            matched,_=reaction_collector.verify_photo(page,photo_id)
                            return self.json({"status":"ready","kind":"photo",
                                              "object_id":matched["id"],
                                              "post_id":matched["id"],
                                              "url":target_url,
                                              "verified_source":"verified_page_photo"})
                        except MetaAccessError:
                            pass
                    try:
                        post,_=reaction_collector.select_post(page,url=target_url)
                        return self.json({"status":"ready","kind":"post",
                                          "object_id":post["id"],"post_id":post["id"],
                                          "url":target_url,"verified_source":"page_posts"})
                    except MetaAccessError:
                        return self.json({"status":"unresolved","url":target_url,
                                          "message":"Link được phân giải nhưng đối tượng không khớp ảnh/bài được Page trả về."})
                except MetaAccessError as exc:
                    return self.json({"status":"unavailable","error":exc.public()})
            if u.path == "/api/reactions/report":
                pid = args.get("page_id", [""])[0]
                oid = args.get("object_id", [""])[0]
                kind = args.get("type", ["LOVE"])[0].upper()
                if not pid.isdigit() or not (4 <= len(pid) <= 30) or not (
                    oid.isdigit() or oid.count("_") == 1 and all(x.isdigit() for x in oid.split("_"))
                ) or len(oid) > 64:
                    raise ValueError("ID Page/ảnh không hợp lệ.")
                records = reaction_history.history(pid, oid, 500)
                return self.json({"assessment": assess(records, kind),
                                  "observations": [
                                     {"observed_at": r["observed_at"],
                                      "value": r["counts"].get(kind)}
                                     for r in records
                                  ],
                                  "source": "meta_graph_api_aggregate_snapshots",
                                  "unverified_individuals": True})
            if u.path == "/api/reactions/history":
                pid = args.get("page_id", [""])[0]
                oid = args.get("object_id", [""])[0]
                kind = args.get("type", ["LOVE"])[0].upper()
                if not (reaction_collector.PAGE_ID.fullmatch(pid) if hasattr(reaction_collector,"PAGE_ID") else
                        pid.isdigit()) or not oid or len(oid)>64:
                    raise ValueError("ID không hợp lệ")
                records = reaction_history.history(pid,oid)
                return self.json({"snapshots": records,
                     "analysis":reaction_history.anomaly_report(records,kind),
                     "scope":"aggregate_only","authoritative_bot_count":None})
            if u.path == "/api/reactions/watches":
                return self.json({"items":reaction_history.watch_list(),
                                  "interval_seconds":REACTION_POLL_SECONDS,
                                  "server_must_remain_online":True})
            if u.path == "/api/reactions/export.csv":
                pid = args.get("page_id", [""])[0]
                oid = args.get("object_id", [""])[0]
                if not pid.isdigit() or len(pid)>30 or not oid or len(oid)>64:
                    raise ValueError("ID không hợp lệ")
                recs=reaction_history.history(pid,oid,500)
                buffer=io.StringIO(newline="")
                writer=csv.writer(buffer)
                writer.writerow(["UTC","Page ID","Post ID","Object ID","Object type",
                                 "LIKE (incl. CARE)","LOVE","WOW","HAHA","SAD","ANGRY",
                                 "Source","Status"])
                for item in recs:
                    counts=item["counts"]
                    writer.writerow([item["observed_at"],pid,item["post_id"],oid,
                         item["object_type"], *[(counts.get(k) if counts.get(k) is not None else "")
                         for k in reaction_collector.REACTIONS],"meta_graph_api",item["status"]])
                return self.respond(200, ("\ufeff"+buffer.getvalue()).encode("utf-8"),
                    "text/csv; charset=utf-8", "voidscan-reaction-evidence.csv")
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
            synchronize_meta_token()
            origin = self.headers.get("Origin", "")
            if origin and origin not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
                return self.json({"error": "Origin không được phép"}, 403)
            if u.path == "/api/reload":
                load()
                return self.json(overview())

            if u.path == "/api/reactions/snapshot" or u.path == "/api/reactions/watch":
                data=self.body_json()
                page_id=str(data.get("page_id",""))
                post_id=str(data.get("post_id",""))
                obj_id=str(data.get("object_id") or post_id)
                entry=reaction_collector.collect_once(page_id, post_id, obj_id)
                snapshot_id=reaction_history.store_observation(entry)
                entry["snapshot_id"]=snapshot_id
                if u.path == "/api/reactions/watch":
                    if not snapshot_id:
                        return self.json({"error":"Meta chưa trả về số reaction hợp lệ; chưa thể theo dõi tự động.","result":entry},422)
                    existing=reaction_history.watch_list()
                    if len([x for x in existing if x["active"]])>=5 and not any(
                        x["page_id"]==page_id and x["object_id"]==obj_id for x in existing):
                        return self.json({"error":"Tối đa 5 đối tượng được theo dõi tự động."},409)
                    entry["watch_id"]=reaction_history.watch(page_id,post_id,obj_id)
                    entry["poll_interval_seconds"]=REACTION_POLL_SECONDS
                return self.json(entry)
            if u.path == "/api/reactions/toggle":
                data=self.body_json()
                if data.get("active") not in (True,False):
                    raise ValueError("Trạng thái không hợp lệ")
                updated=reaction_history.set_watch(str(data.get("id","")),data["active"])
                return self.json({"updated":updated},200 if updated else 404)
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
        except MetaAccessError as exc:
            return self.json({"error":exc.public()["message"],"detail":exc.public()},403)
        except (ValueError, TypeError, KeyError) as exc:
            return self.json({"error": str(exc)}, 400)
        except Exception:
            logging.exception("POST failed")
            return self.json({"error": "Lỗi máy chủ"}, 500)

def reaction_monitor_loop():
    # Never collect when the server is not configured with a token.
    # The thread stops with the local server process; it is not a cloud service.
    while True:
        time.sleep(REACTION_POLL_SECONDS)
        try:
            synchronize_meta_token()
            if configured_mode()=="none":
                continue
            outcome=reaction_history.poll_active_once()
            if outcome:
                logging.info("Reaction monitor: %d tracked objects checked",len(outcome))
        except Exception:
            logging.exception("Reaction monitor failed")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from secret_store import load_saved_meta_token_into_process
    try:
        if load_saved_meta_token_into_process():
            logging.info("Meta token mã hóa đã được nạp cho phiên chạy này.")
    except TokenStoreError as exc:
        logging.warning("Không nạp được token mã hóa: %s", exc)
    load()
    storage.initialize()
    storage.purge_expired(90)
    reaction_history.ensure()
    threading.Thread(target=reaction_monitor_loop, daemon=True, name="reaction-monitor").start()
    print(f"VOIDSCAN ready: http://localhost:{PORT}  |  records: {analysis['counts']['total']}  |  classes: {analysis['counts']['classes']}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
