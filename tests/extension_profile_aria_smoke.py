"""Regression for Facebook live accessibility-label format (synthetic profiles).

No real Facebook requests and no private data. The accessible avatar link in
Facebook's reaction dialog has an aria-label such as "A đã thích" or
"B đã cảm thấy Yêu thích"; the adjacent username anchor often overwrote
the reaction record and caused 0 recognized results.
"""
from __future__ import annotations
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]/"chrome-extension"
PHOTO="2030957244381534"
URL="https://www.facebook.com/photo/?fbid="+PHOTO
HTML="""<!doctype html><html lang="vi"><head><meta charset="utf-8"><style>
[role=dialog]{position:fixed;top:40px;left:30px;width:480px;height:500px;background:#fff}
[role=listitem]{height:78px;display:flex;gap:9px;align-items:center}
[role=listitem] img{width:45px;height:45px}
</style></head><body><div role="dialog" aria-label="Người đã bày tỏ cảm xúc">
<div><button>Tất cả</button><button>Thích</button><button>Yêu thích</button></div>
<div role="list" id="reaction-rows">
<div role="listitem">
 <a href="https://www.facebook.com/alex.example/" aria-label="Alex đã thích"><img alt="" src="https://scontent.fna.fbcdn.net/mock.jpg"></a>
 <a href="https://www.facebook.com/alex.example/">Alex</a></div>
<div role="listitem">
 <a href="https://www.facebook.com/lucy.example/" aria-label="Lucy đã cảm thấy Yêu thích"><img alt="" src="https://scontent.fna.fbcdn.net/mock.jpg"></a>
 <a href="https://www.facebook.com/lucy.example/">Lucy</a></div>
<div role="listitem">
 <a href="https://www.facebook.com/nancy.example/" aria-label="Nancy đã cảm thấy Thương thương"><img alt="" src="https://scontent.fna.fbcdn.net/mock.jpg"></a>
 <a href="https://www.facebook.com/nancy.example/">Nancy</a></div>
<div role="listitem">
 <a href="https://www.facebook.com/wow.example/" aria-label="Wow User đã cảm thấy Wow"><img alt="" src="https://scontent.fna.fbcdn.net/mock.jpg"></a>
 <a href="https://www.facebook.com/wow.example/">Wow User</a></div>
<div role="listitem">
 <a href="https://www.facebook.com/haha.example/" aria-label="Haha User đã cảm thấy Haha"><img alt="" src="https://scontent.fna.fbcdn.net/mock.jpg"></a>
 <a href="https://www.facebook.com/haha.example/">Haha User</a></div>
<div role="listitem">
 <a href="https://www.facebook.com/sad.example/" aria-label="Sad User đã cảm thấy Buồn"><img alt="" src="https://scontent.fna.fbcdn.net/mock.jpg"></a>
 <a href="https://www.facebook.com/sad.example/">Sad User</a></div>
</div></div></body></html>"""
MOCK="""() => {
 window.__db={};
 window.chrome={storage:{local:{
   get:async keys=>{const out={};for(const k of (Array.isArray(keys)?keys:[keys])){
     if(k in window.__db)out[k]=window.__db[k];
   }return out;},
   set:async items=>Object.assign(window.__db,items)
 }}};
}"""

class ActualAriaPattern(unittest.TestCase):
 def test_mixed_all_list_uses_profile_aria_without_manual_tabs(self):
  with sync_playwright() as p:
   b=p.chromium.launch(channel="chrome",headless=True)
   try:
    page=b.new_page(accept_downloads=True)
    page.route("**/*",lambda r:r.fulfill(status=200,body=HTML,content_type="text/html")
               if r.request.is_navigation_request() else r.fulfill(status=200,body=""))
    page.goto(URL);page.evaluate(MOCK)
    page.add_script_tag(path=str(ROOT/"lib.js"))
    page.add_script_tag(path=str(ROOT/"content.js"))
    panel=page.locator("#voidscan-reaction-audit-root")
    panel.locator("#vauto").click()
    page.wait_for_function("""() => !document.querySelector('#voidscan-reaction-audit-root')
      .shadowRoot.getElementById('vauto').disabled""",timeout=30000)
    rows=page.evaluate("window.__db.voidscan_reactions_v1||[]")
    self.assertEqual(len(rows),5)
    self.assertEqual(set(row["reaction"] for row in rows),
      {"LIKE","LOVE","CARE","HAHA","WOW"})
    self.assertEqual(len({row["profileUrl"] for row in rows}),5)
    unknown=page.evaluate("window.__db.voidscan_pending_reactions_v1||[]")
    self.assertEqual(len(unknown),0)  # SAD deliberately excluded, not UNKNOWN.
    self.assertEqual(panel.locator("#vcount").inner_text(),"5")
    self.assertEqual(panel.locator("#vpending").inner_text(),"0")
   finally:b.close()

if __name__=="__main__":unittest.main()
