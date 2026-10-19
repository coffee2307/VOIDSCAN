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
            ref["path"] == other["path"] and
            any(prefix in ref["path"] for prefix in ("/posts/", "/reel/", "/videos/", "/permalink/"))):
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
        "signals": [
            {"label": "Trùng Profile ID trong cùng lớp", "count": sum(x["duplicate"] for x in result),
             "explanation": "Lặp định danh trong một lớp; không phải bằng chứng tài khoản ảo.",
             "level": "review" if any(x["duplicate"] for x in result) else "info"},
            {"label": "Bản ghi thiếu Profile ID", "count": sum(not x["has_identity"] for x in result),
             "explanation": "Không có định danh để đối chiếu; cần rà soát thủ công.",
             "level": "info"},
            {"label": "Xuất hiện ở nhiều lớp", "count": sum(x["cross_class"] for x in result),
             "explanation": "Có thể là người thật chia sẻ nhiều bài; không tự động loại.",
             "level": "info"}
        ],
        "examples": [
            {"name": x["name"] or "(không tên)", "class": x["class"],
             "signal": x["reason"], "profile_id": x["profile_id"]}
            for x in result if x["duplicate"] or not x["has_identity"]
        ][:20],
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
         "explanation": "Ít nhất 3 bình luận có cùng nội dung từ 8 ký tự trở lên; có thể là hành vi bình thường.",
         "level": "review" if duplicated_count else "info"},
        {"label": "Mật độ bình luận cao nhất / 60 giây", "count": max_burst,
         "explanation": "Mật độ cao chỉ là mô tả, không đủ kết luận là bot hoặc gian lận.",
         "level": "info"}
    ]
    return signals, duplicated_count

def graph_scan(url, page_id=None):
    """Scan ONLY a post verified through its owner's managed Page posts edge.

    Fail closed on permission and unverified URL ownership. Never fetch input URL.
    """
    from meta_pages import MetaAccessError, graph_get, resolve_page_and_post
    try:
        page, post, post_list_partial = resolve_page_and_post(url, page_id)
    except MetaAccessError as exc:
        result = {"status": "unavailable", "source": "none",
                  "message": exc.public()["message"],
                  "diagnostic": exc.public(),
                  "ownership_verified": False}
        if exc.kind == "not_found":
            result["message"] += (
                " URL phải khớp một bài mà Graph API liệt kê trong danh sách "
                "bài gần đây của Page đã chọn; Reel và một số định dạng "
                "khác có thể chưa được hỗ trợ."
            )
        return result

    comments = []
    cursor = None
    capped = False
    try:
        for page_number in range(3):
            params = {"fields": "id,message,created_time", "limit": 100}
            if cursor:
                params["after"] = cursor
            payload = graph_get(post["id"] + "/comments", params, page["token"])
            batch = payload.get("data", [])
            if not isinstance(batch, list):
                raise MetaAccessError("response")
            comments.extend(x for x in batch if isinstance(x, dict))
            cursor = (payload.get("paging", {}).get("cursors") or {}).get("after")
            if not cursor or len(batch) < 100:
                cursor = None
                break
        capped = bool(cursor)
    except MetaAccessError as exc:
        return {"status": "unavailable", "source": "none",
                "message": "Đã xác minh bài viết thuộc Page đã chọn, nhưng không đọc được bình luận. "
                           + exc.public()["message"],
                "diagnostic": exc.public(), "ownership_verified": True,
                "page": {"id": page["id"], "name": page["name"]},
                "post": {"id": post["id"], "url": post["url"]}}

    signals, repeated_count = flags(comments)
    normalized = [re.sub(r"\s+", " ", str(x.get("message", "")).strip()).casefold()
                  for x in comments]
    frequency = Counter(t for t in normalized if 8 <= len(t) <= 300)
    repeated = {t for t, count in frequency.items() if count >= 3}
    examples = [
        {"name": "Mẫu bình luận " + str(index + 1), "class": "Meta API",
         "signal": "Trùng nội dung, không xác định danh tính",
         "profile_id": str(comment.get("message", ""))[:150]}
        for index, comment in enumerate(comments)
        if normalized[index] in repeated
    ][:20]
    return {
        "status": "live", "source": "meta_graph_api",
        "comments": len(comments), "suspicious": repeated_count,
        "signals": signals, "examples": examples,
        "ownership_verified": True,
        "page": {"id": page["id"], "name": page["name"]},
        "post": {"id": post["id"], "url": post["url"]},
        "coverage": {"observed_comments": len(comments),
                     "comment_sample_capped": capped,
                     "post_catalog_partial": post_list_partial,
                     "all_engagement_accessible": False},
        "message": "Đã xác minh bài viết thuộc Page mà token cho phép quản lý. "
                   "Chỉ phân tích bình luận được Graph API cung cấp (tối đa 300). "
                   "Không truy cập được toàn bộ danh tính người like/share hoặc "
                   "xác định ai là tài khoản giả."
    }

def scan(url, records, page_id=None):
    reference(url)
    has_token = bool(os.environ.get("META_USER_ACCESS_TOKEN", "").strip() or
                     os.environ.get("META_PAGE_ACCESS_TOKEN", "").strip())
    online = graph_scan(url, page_id) if has_token else None
    if online and online["status"] == "live":
        return online
    local = local_match(url, records)
    if local:
        if online:
            local["message"] += " Không lấy được dữ liệu Graph API cho Page đã chọn."
        return local
    return online or {
        "status": "unavailable", "source": "none",
        "message": "Chưa cấu hình Meta Page token. Hãy mở Nguồn dữ liệu để xem "
                   "hướng dẫn kết nối Page bạn quản trị. Không thể quét tương tác "
                   "mới chỉ từ URL khi thiếu quyền chính thức."
    }
