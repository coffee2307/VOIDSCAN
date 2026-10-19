"""Best-effort public Facebook share-link redirect resolution.

No login, cookies, credential forwarding, browser automation or page scraping.
Strict official Facebook host allowlist; unresolved links remain unresolved.
"""
from __future__ import annotations
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin,urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from scan import validate_url

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def resolve_shortlink(url, max_hops=4):
    parsed=validate_url(url)
    if not parsed.path.startswith("/share/"):
        return {"status":"already_canonical","url":url,"hops":0}
    opener=build_opener(NoRedirect())
    current=url
    seen=set()
    for i in range(min(4,max(1,int(max_hops)))):
        if current in seen:
            break
        seen.add(current)
        try:
            req=Request(current,method="HEAD",
                        headers={"User-Agent":"VOIDSCAN/2.3 (link-resolution-only)"})
            with opener.open(req,timeout=6) as response:
                # Public redirect may not be supplied: never attempt private HTML access.
                status=response.status
                location=response.headers.get("Location")
        except HTTPError as exc:
            status=exc.code
            location=exc.headers.get("Location")
            exc.close()
        except (URLError,TimeoutError,ValueError,UnicodeError):
            break
        if status not in (301,302,303,307,308) or not location:
            break
        candidate=urljoin(current,location)
        try:
            validate_url(candidate)
        except ValueError:
            break
        current=candidate
        if not urlsplit(current).path.startswith("/share/"):
            return {"status":"resolved","url":current,"hops":i+1}
    return {"status":"unresolved","url":None,"hops":len(seen),
            "message":"Meta không cung cấp chuyển hướng công khai cho link này. Hãy chọn ảnh từ danh sách Page."}
