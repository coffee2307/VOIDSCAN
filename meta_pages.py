"""Permissioned Facebook Page connector. Tokens never leave the process or enter history.

Use META_USER_ACCESS_TOKEN (me/accounts) or META_PAGE_ACCESS_TOKEN (me page).
All outgoing requests are read-only to a fixed graph.facebook.com HTTPS origin.
"""
from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scan import API_VERSION, reference

PAGE_ID = re.compile(r"^[0-9]{4,30}$")
GRAPH_BASE = "https://graph.facebook.com/" + API_VERSION + "/"
MAX_MANAGED_PAGES = 100
MAX_POSTS = 200

class MetaAccessError(Exception):
    def __init__(self, kind, code=None, subcode=None):
        super().__init__(kind)
        self.kind = kind
        self.code = code
        self.subcode = subcode
    def public(self):
        messages = {
            "permission": "Meta từ chối quyền truy cập. Kiểm tra Page tasks và quyền của ứng dụng.",
            "expired": "Token Meta hết hạn hoặc không hợp lệ. Hãy tạo token mới.",
            "rate_limit": "Meta đã giới hạn tần suất. Hãy thử lại sau.",
            "network": "Không kết nối được Meta Graph API.",
            "response": "Meta Graph API trả về dữ liệu không hợp lệ.",
            "not_found": "Không xác minh được tài nguyên này trên Page.",
            "configuration": "Chưa có Page token hoặc User token phù hợp.",
        }
        return {"kind": self.kind, "code": self.code, "subcode": self.subcode,
                "message": messages.get(self.kind, "Không thể truy cập dữ liệu từ Meta.")}

def graph_get(path, params, token):
    if not token or not isinstance(token, str):
        raise MetaAccessError("configuration")
    # Fixed base and no dynamic domain: path is server-authored.
    if not re.fullmatch(r"[A-Za-z0-9_./-]{1,100}", path) or path.startswith("/") or ".." in path:
        raise ValueError("Invalid Graph API path")
    query = urlencode(params)
    req = Request(GRAPH_BASE + path + ("?" + query if query else ""),
                  headers={"Authorization": "Bearer " + token,
                           "Accept": "application/json", "User-Agent": "VOIDSCAN/2.1"})
    try:
        with urlopen(req, timeout=12) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise MetaAccessError("response")
        return result
    except HTTPError as exc:
        try:
            raw = exc.read(4096)
            info = json.loads(raw).get("error", {})
            code = int(info.get("code", exc.code))
            sub = info.get("error_subcode")
        except (ValueError, TypeError, AttributeError):
            code, sub = exc.code, None
        if code in (190,):
            kind = "expired"
        elif code in (4, 17, 32, 613):
            kind = "rate_limit"
        elif code in (10, 200, 3, 100):
            kind = "permission"
        else:
            kind = "not_found"
        raise MetaAccessError(kind, code, sub) from None
    except (URLError, TimeoutError, ConnectionError):
        raise MetaAccessError("network") from None
    except (ValueError, UnicodeError):
        raise MetaAccessError("response") from None

def configured_mode():
    if os.environ.get("META_USER_ACCESS_TOKEN", "").strip():
        return "user"
    if os.environ.get("META_PAGE_ACCESS_TOKEN", "").strip():
        return "page"
    return "none"

def managed_pages():
    """Returns private page-token mapping; never serialize this mapping to client."""
    mode = configured_mode()
    if mode == "none":
        return {}
    if mode == "page":
        token = os.environ["META_PAGE_ACCESS_TOKEN"].strip()
        info = graph_get("me", {"fields": "id,name,category"}, token)
        page_id = str(info.get("id", ""))
        expected = os.environ.get("META_PAGE_ID", "").strip()
        if not PAGE_ID.fullmatch(page_id) or not expected or expected != page_id or not info.get("category"):
            raise MetaAccessError("permission")
        return {page_id: {"id": page_id,
                          "name": str(info.get("name", "Facebook Page"))[:140],
                          "tasks": [], "token": token}}
    token = os.environ["META_USER_ACCESS_TOKEN"].strip()
    pages = {}
    cursor = None
    for _ in range(3):
        params = {"fields": "id,name,tasks,access_token", "limit": 50}
        if cursor:
            params["after"] = cursor
        response = graph_get("me/accounts", params, token)
        data = response.get("data", [])
        if not isinstance(data, list):
            raise MetaAccessError("response")
        for p in data:
            if not isinstance(p, dict):
                continue
            page_id = str(p.get("id", ""))
            page_token = p.get("access_token")
            if PAGE_ID.fullmatch(page_id) and isinstance(page_token, str) and page_token.strip():
                pages[page_id] = {"id": page_id, "name": str(p.get("name", ""))[:140],
                                  "tasks": [str(t) for t in p.get("tasks", [])[:15]],
                                  "token": page_token}
            if len(pages) >= MAX_MANAGED_PAGES:
                break
        if len(pages) >= MAX_MANAGED_PAGES or len(data) < 50:
            break
        cursor = (response.get("paging", {}).get("cursors") or {}).get("after")
        if not cursor:
            break
    return pages

def public_pages(pages):
    return [{"id": p["id"], "name": p["name"], "tasks": p["tasks"]} for p in pages.values()]

def page_posts(page, max_posts=MAX_POSTS):
    """Read published posts with a verifiable permalink under an authorized Page."""
    posts = []
    cursor = None
    capped = False
    for _ in range(4):
        params = {"fields": "id,permalink_url,created_time,message", "limit": 50}
        if cursor:
            params["after"] = cursor
        data = graph_get(page["id"] + "/posts", params, page["token"])
        batch = data.get("data", [])
        if not isinstance(batch, list):
            raise MetaAccessError("response")
        for p in batch:
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id", ""))
            url = p.get("permalink_url")
            if not re.fullmatch(r"[0-9]+_[0-9]+", pid) or not pid.startswith(page["id"] + "_"):
                continue
            if not isinstance(url, str):
                url = ""
            posts.append({"id": pid, "url": url, "created_time": str(p.get("created_time", "")),
                          "excerpt": str(p.get("message", ""))[:130]})
            if len(posts) >= max_posts:
                capped = True
                break
        cursor = (data.get("paging", {}).get("cursors") or {}).get("after")
        if capped or not cursor or len(batch) < 50:
            break
    return {"items": posts, "limited_to": min(max_posts, MAX_POSTS), "partial": bool(cursor) or capped}

def match_owned_post(url, page, posts):
    """Fail closed: a post must be returned by the Page's own posts edge."""
    incoming = reference(url)
    for post in posts:
        if not post["url"]:
            continue
        try:
            existing = reference(post["url"])
        except ValueError:
            continue
        if (incoming["post_id"] and existing["post_id"] and
            incoming["post_id"] == existing["post_id"]):
            return post
        if incoming["path"] and incoming["path"] == existing["path"]:
            return post
    return None

def resolve_page_and_post(url, page_id=None):
    pages = managed_pages()
    if not pages:
        raise MetaAccessError("configuration")
    if not page_id:
        if len(pages) == 1:
            page_id = next(iter(pages))
        else:
            raise MetaAccessError("configuration")
    page_id = str(page_id)
    if page_id not in pages:
        raise MetaAccessError("permission")
    page = pages[page_id]
    posts = page_posts(page)
    post = match_owned_post(url, page, posts["items"])
    if post is None:
        raise MetaAccessError("not_found")
    return page, post, posts["partial"]
