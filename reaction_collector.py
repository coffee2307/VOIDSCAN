"""Reaction auditing for owned Page posts and attached photo objects.

This module never guesses actor identities. Only Graph response counts with explicit
summary.total_count are treated as observed counts; unsupported fields are null.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from meta_pages import MetaAccessError, graph_get, managed_pages, page_posts
from scan import reference, validate_url

# Meta groups CARE with LIKE for some endpoints; do not claim independent CARE.
REACTIONS = ("LIKE", "LOVE", "WOW", "HAHA", "SAD", "ANGRY")
MAX_ATTACHMENTS = 40
MAX_OBJECTS = 100

def verify_page(page_id):
    pages = managed_pages()
    key = str(page_id or "")
    if key not in pages:
        raise MetaAccessError("permission")
    return pages[key]

def select_post(page, post_id=None, url=None):
    """Resolve only a post listed under the authorized Page's posts edge."""
    catalog = page_posts(page)
    found = None
    candidate_id = str(post_id or "")
    if candidate_id:
        for item in catalog["items"]:
            if item["id"] == candidate_id:
                found = item
                break
    if found is None and url:
        validate_url(url)
        r = reference(url)
        for item in catalog["items"]:
            if not item.get("url"):
                continue
            try:
                candidate = reference(item["url"])
            except ValueError:
                continue
            if (r["post_id"] and r["post_id"] == candidate["post_id"]) or (
                r["path"] and r["path"] == candidate["path"] and
                "/share/" not in r["path"]):
                found = item
                break
    if found is None:
        # For old contests a Page post can be older than the current catalog.
        # Direct Graph lookup is allowed ONLY when the author's Page ID matches.
        token=str(post_id or "")
        if not token and url:
            r=reference(url)
            if any(part in r["path"] for part in ("/posts/","/permalink/")):
                token=r.get("post_id") or ""
        candidate=token if token.startswith(page["id"]+"_") else (
            page["id"]+"_"+token if re.fullmatch(r"[0-9]{4,30}",token) else "")
        if candidate and re.fullmatch(
                re.escape(page["id"])+r"_[0-9]{4,30}",candidate):
            try:
                result=graph_get(candidate,{
                    "fields":"id,from{id},permalink_url,created_time,message"},page["token"])
                if str(result.get("id",""))==candidate and str(
                    (result.get("from") or {}).get("id",""))==page["id"]:
                    found={"id":candidate,"url":str(result.get("permalink_url","")),
                           "created_time":str(result.get("created_time","")),
                           "excerpt":str(result.get("message",""))[:130]}
            except MetaAccessError:
                pass
        if found is None:
            raise MetaAccessError("not_found")
    return found, catalog["partial"]

def attached_objects(page, post):
    """Best-effort: use official attachment target IDs; do not infer Photo IDs."""
    result = {"items": [], "status": "unavailable", "error": None}
    try:
        payload = graph_get(post["id"], {
            "fields": "id,attachments{media_type,target,url,subattachments{media_type,target,url}}"
        }, page["token"])
    except MetaAccessError as exc:
        result["error"] = exc.public()
        return result
    candidates = []
    root = (payload.get("attachments") or {}).get("data") or []
    for attachment in root[:MAX_ATTACHMENTS]:
        if not isinstance(attachment, dict):
            continue
        candidates.append(attachment)
        for sub in ((attachment.get("subattachments") or {}).get("data") or [])[:MAX_ATTACHMENTS]:
            if isinstance(sub, dict):
                candidates.append(sub)
    seen = set()
    for item in candidates:
        target = item.get("target") or {}
        oid = str(target.get("id", ""))
        if not re.fullmatch(r"[0-9]{4,30}", oid) or oid in seen:
            continue
        seen.add(oid)
        raw_url = str(item.get("url", ""))
        hostname = (urlsplit(raw_url).hostname or "").casefold()
        public_url = raw_url if hostname in ("facebook.com", "www.facebook.com", "m.facebook.com") and raw_url.startswith("https://") else ""
        result["items"].append({
            "id": oid, "parent_id": post["id"],
            "media_type": str(item.get("media_type", "unknown"))[:35],
            "url": public_url,
            "label": str(item.get("media_type", "Ảnh đính kèm"))[:35] + " · " + oid[-7:]
        })
        if len(result["items"]) >= MAX_ATTACHMENTS:
            break
    result["status"] = "ok" if result["items"] else "none"
    return result

def page_photos(page, max_photos=200):
    """Official Page /photos?type=uploaded; each returned ID belongs to that Page."""
    items=[]
    cursor=None
    capped=False
    for _ in range(4):
        params={"type":"uploaded","fields":"id,link,created_time,name","limit":50}
        if cursor:
            params["after"]=cursor
        payload=graph_get(page["id"]+"/photos",params,page["token"])
        batch=payload.get("data",[])
        if not isinstance(batch,list):
            raise MetaAccessError("response")
        for item in batch:
            if not isinstance(item,dict):
                continue
            photo_id=str(item.get("id",""))
            if not re.fullmatch(r"[0-9]{4,30}",photo_id):
                continue
            url=str(item.get("link",""))
            if (urlsplit(url).hostname or "").lower() not in (
                    "facebook.com","www.facebook.com","m.facebook.com"):
                url=""
            items.append({"id":photo_id,"url":url,
               "created_time":str(item.get("created_time","")),
               "excerpt":str(item.get("name",""))[:110]})
            if len(items)>=max_photos:
                capped=True
                break
        cursor=(payload.get("paging",{}).get("cursors") or {}).get("after")
        if capped or not cursor or len(batch)<50:
            break
    return {"items":items, "partial":bool(cursor) or capped,
            "source":"page_photos_uploaded"}

def verify_photo(page, photo_id):
    """Verify that an uploaded photo belongs to the authorized Page."""
    if not re.fullmatch(r"[0-9]{4,30}", str(photo_id)):
        raise MetaAccessError("not_found")
    try:
        gallery=page_photos(page)
    except MetaAccessError:
        gallery={"items":[],"partial":True}
    existing=next((x for x in gallery["items"] if x["id"]==photo_id),None)
    if existing:
        return existing,gallery["partial"]
    # An old photo may be beyond the first 200 uploaded photos. The creator
    # must match the managed Page; never trust a bare guessed object ID.
    try:
        details=graph_get(photo_id,{"fields":"id,from{id},link"},page["token"])
    except MetaAccessError:
        raise MetaAccessError("not_found") from None
    if str(details.get("id",""))!=str(photo_id) or str(
        (details.get("from") or {}).get("id",""))!=page["id"]:
        raise MetaAccessError("not_found")
    u=str(details.get("link",""))
    if (urlsplit(u).hostname or "").lower() not in (
        "facebook.com","www.facebook.com","m.facebook.com"):
        u=""
    return {"id":photo_id,"url":u,"created_time":"","excerpt":""},True

def reaction_fields():
    return ",".join(
        "reactions.type(" + ("SORRY" if t == "SAD" else t) + ").limit(0).summary(total_count).as(r_" + t.lower() + ")"
        for t in REACTIONS
    )

def extract_counts(payload, requested=REACTIONS):
    """Do not turn missing or malformed graph responses into count 0."""
    output = {}
    for kind in requested:
        info = payload.get("r_" + kind.lower())
        count = (info.get("summary") or {}).get("total_count") if isinstance(info, dict) else None
        output[kind] = count if type(count) is int and count >= 0 else None
    return output

def read_reactions(object_id, page):
    if not re.fullmatch(r"(?:[0-9]{4,30}|[0-9]{4,30}_[0-9]{4,30})", object_id):
        raise ValueError("Graph object ID không hợp lệ")
    try:
        payload = graph_get(object_id, {"fields": reaction_fields()}, page["token"])
        values = extract_counts(payload)
        missing = [kind for kind, count in values.items() if count is None]
        return {"status": "ok" if not missing else "partial",
                "counts": values, "missing": missing, "api_error": None}
    except MetaAccessError as exc:
        if exc.kind in ("rate_limit","expired","network"):
            return {"status":"unavailable","counts":dict.fromkeys(REACTIONS),
                    "missing":list(REACTIONS),"api_error":exc.public()}
        # A rejected alias can invalidate the batch; retry six validated types
        # independently to salvage counts, without fabricating zeros.
        counts = dict.fromkeys(REACTIONS)
        for kind in REACTIONS:
            api_kind = "SORRY" if kind == "SAD" else kind
            fields = ("reactions.type(" + api_kind + ").limit(0)"
                      ".summary(total_count).as(r_" + kind.lower() + ")")
            try:
                response = graph_get(object_id, {"fields": fields}, page["token"])
                counts[kind] = extract_counts(response, (kind,))[kind]
            except MetaAccessError:
                continue
        missing = [name for name, number in counts.items() if number is None]
        return {"status": ("partial" if len(missing) < len(REACTIONS) else "unavailable"),
                "counts": counts, "missing": missing, "api_error": exc.public()}

def collect_once(page_id, post_id, object_id=None, url=None):
    page = verify_page(page_id)
    oid = str(object_id or post_id)
    # A standalone Page photo is verified via the Page's official uploaded photos.
    if oid and oid == str(post_id) and re.fullmatch(r"[0-9]{4,30}",oid):
        target,partial=verify_photo(page,oid)
        counts=read_reactions(oid,page)
        return {
            "page":{"id":page["id"],"name":page["name"]},
            "post":{"id":oid,"url":target["url"]},
            "object":{"id":oid,"type":"photo"},
            "observed_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "catalog_partial":partial,"reaction":counts,
            "data_scope":"aggregate_reactions_only",
            "privacy":"Không có danh sách tài khoản thả reaction; không xác minh được bot."
        }
    post, catalog_partial = select_post(page, post_id=post_id, url=url)
    oid = str(object_id or post["id"])
    if oid != post["id"]:
        attachments = attached_objects(page, post)
        if oid not in {x["id"] for x in attachments["items"]}:
            raise MetaAccessError("not_found")
        object_type = "attachment"
    else:
        object_type = "post"
    result = read_reactions(oid, page)
    return {
        "page": {"id": page["id"], "name": page["name"]},
        "post": {"id": post["id"], "url": post.get("url", "")},
        "object": {"id": oid, "type": object_type},
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "catalog_partial": catalog_partial,
        "reaction": result,
        "data_scope": "aggregate_reactions_only",
        "privacy": "Không có danh sách tài khoản thả reaction; không xác minh được bot."
    }
