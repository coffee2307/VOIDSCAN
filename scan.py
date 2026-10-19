"""Facebook post scan providers: local CSV evidence and permissioned Meta Graph API."""
from __future__ import annotations
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import Request, urlopen

ALLOWED_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com"}
API_VERSION = "v26.0"

def validate_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("URL không hợp lệ")
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port:
        raise ValueError("Chỉ chấp nhận URL HTTPS chính thức của facebook.com")
    return parsed

def reference(value):
    parsed = validate_url(value)
    path = re.sub(r"/+", "/", parsed.path).rstrip("/").lower()
    params = parse_qs(parsed.query)
    identifier = None
    patterns = [
        r"/posts/([0-9]+)$", r"/reel/([0-9]+)$",
        r"/videos/([0-9]+)$", r"/permalink/([0-9]+)$",
        r"/photos/(?:a\.[0-9]+/)?([0-9]+)$"
    ]
    for pattern in patterns:
        m = re.search(pattern, path)
        if m:
            identifier = m.group(1)
            break
    if "story_fbid" in params and re.fullmatch(r"[0-9]{4,30}", params["story_fbid"][0]):
        identifier = params["story_fbid"][0]
    if "fbid" in params and re.fullmatch(r"[0-9]{4,30}", params["fbid"][0]):
        identifier = params["fbid"][0]
    return {"path": path, "post_id": identifier}

def local_match(url, records):
    ref = reference(url)
    result = []
    for rec in records:
        source = rec.get("share_url", "")
        if not source:
            continue
        try:
            other = reference(source)
        except ValueError:
            continue
        if (ref["post_id"] and ref["post_id"] == other["post_id"]) or (
            ref["path"] == other["path"] and ref["path"] not in ("", "/")):
            result.append(rec)
    if not result:
        return None
    classes = sorted({x["class"] for x in result})
    return {
        "status": "matched", "source": "local_csv",
        "total": len(result),
        "duplicates": sum(x["duplicate"] for x in result),
        "unverified": sum(not x["has_identity"] for x in result),
        "classes": classes, "class": classes[0] if len(classes) == 1 else "",
        "message": "Đây là dữ liệu CSV đã nhập, không phải dữ liệu Facebook được thu thập mới. "
                   "Số liệu chỉ phản ánh bản ghi xuất hiện trong các file liên quan."
    }

def parse_datetime(s):
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None

def flags(comments):
    nonempty = [re.sub(r"\s+", " ", str(x.get("message", "")).strip()).casefold() for x in comments]
    common = Counter(t for t in nonempty if len(t) >= 8 and len(t) <= 300)
    repeated = {t for t, n in common.items() if n >= 3}
    duplicated_count = sum(1 for t in nonempty if t in repeated)
    dated = sorted(d for x in comments if (d := parse_datetime(x.get("created_time"))))
    max_burst = 0
    left = 0
    for right, time in enumerate(dated):
        while time - dated[left] > timedelta(seconds=60):
            left += 1
        max_burst = max(max_burst, right - left + 1)
    signals = [
        {"label": "Bình luận lặp nguyên văn", "count": duplicated_count,
         "explanation": "Ít nhất 3 bình luận có cùng nội dung từ 8 ký tự trở lên; có thể là hành vi bình thường."},
        {"label": "Mật độ bình luận cao nhất / 60 giây", "count": max_burst,
         "explanation": "Mật độ cao chỉ là tín hiệu cần kiểm tra, không đủ kết luận là bot."}
    ]
    return signals, duplicated_count

def graph_scan(url):
    token = os.environ.get("META_PAGE_ACCESS_TOKEN", "").strip()
    if not token:
        return None
    post_id = reference(url)["post_id"]
    if not post_id:
        return {"status": "unavailable", "message":
            "Đã cấu hình Meta API nhưng không suy ra được Post ID từ URL này. "
            "Hãy thử URL dạng /posts/<id>, /reel/<id> hoặc ?story_fbid=<id>."}
    # All network calls use a hard-coded host; the input URL is never fetched.
    endpoint = ("https://graph.facebook.com/" + API_VERSION + "/" + quote(post_id, safe="") +
                "/comments?fields=id,message,created_time&limit=100")
    comments = []
    cursor = None
    for _ in range(3):
        link = endpoint + (("&after=" + quote(cursor, safe="")) if cursor else "")
        req = Request(link, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=14) as response:
                payload = json.load(response)
        except HTTPError as exc:
            try:
                body = json.loads(exc.read(4096).decode("utf-8"))
                info = body.get("error", {})
                code = info.get("code", exc.code)
            except Exception:
                code = exc.code
            return {"status": "unavailable",
                    "message": f"Meta Graph API từ chối truy cập (mã {code}). "
                    "Kiểm tra quyền Page, Post ID, phạm vi truy cập của app và thời hạn token."}
        except (URLError, TimeoutError, ValueError):
            return {"status": "unavailable", "message": "Không kết nối được Meta Graph API. Hãy kiểm tra mạng và cấu hình."}
        comments.extend(payload.get("data", []))
        cursor = (payload.get("paging", {}).get("cursors", {}) or {}).get("after")
        if not cursor or len(payload.get("data", [])) < 100:
            break
    signals, repeated = flags(comments)
    return {
        "status": "live", "source": "meta_graph_api", "comments": len(comments),
        "suspicious": repeated, "signals": signals,
        "message": "Chỉ phân tích các comment mà token được phép đọc (tối đa 300 trên mỗi lần scan). "
                   "Các số liệu không đại diện cho toàn bộ like/share hay danh tính người tương tác; "
                   "mẫu có thể chưa đầy đủ."
    }

def scan(url, records):
    reference(url)
    online = graph_scan(url)
    if online and online["status"] == "live":
        return online
    local = local_match(url, records)
    if local:
        if online and online["status"] == "unavailable":
            local["message"] += " Meta API hiện chưa truy cập được bài này."
        return local
    return online or {
        "status": "unavailable",
        "message": "Không tìm thấy URL này trong dữ liệu đã nhập. Quét bài đăng trực tiếp cần "
                   "META_PAGE_ACCESS_TOKEN và quyền đọc nội dung Page phù hợp. "
                   "VOIDSCAN không thể tự truy cập mọi bài Facebook chỉ từ một đường link. "
                   "Bạn cũng có thể nhập CSV chứa danh sách tương tác qua mục Nguồn dữ liệu."
    }
