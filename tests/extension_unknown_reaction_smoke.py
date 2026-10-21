"""Regression: Facebook 'All' reaction list without per-person emoji.

The exporter must keep unique URLs as UNKNOWN rather than discard thousands
of rows and must upgrade them when a specific reaction tab can be verified.
"""
from __future__ import annotations
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]/"chrome-extension"
PHOTO="2030957244381534"
PAGE="https://www.facebook.com/photo/?fbid="+PHOTO
HTML="""<!doctype html><html><head><meta charset="utf-8"><style>
[role=dialog]{position:fixed;left:30px;top:30px;width:450px;height:500px;background:white}
[role=tab]{display:inline-block;padding:12px;cursor:pointer}
[role=listitem]{height:70px;display:flex;align-items:center}
[role=listitem] a{display:inline-block;padding:12px}
</style></head><body>
<div role="dialog" aria-label="Người đã bày tỏ cảm xúc">
<div role="tablist">
<button role="tab" id="all" aria-selected="true">Tất cả 3</button>
<button role="tab" id="like" aria-selected="false">Thích 3</button>
</div><div id="reaction-list" role="list">
<div role="listitem"><a href="https://www.facebook.com/alex.example/">Alex Example</a></div>
<div role="listitem"><a href="https://www.facebook.com/lucy.example/">Lucy Example</a></div>
<div role="listitem"><a href="https://www.facebook.com/nancy.example/">Nancy Example</a></div>
</div></div>
</body></html>"""
SETUP="""() => {
window.__db={};
window.chrome={storage:{local:{
 get:async key=>{const keys=typeof key==="string"?[key]:key;const out={};for(const k of keys)if(k in window.__db)out[k]=window.__db[k];return out;},
 set:async values=>Object.assign(window.__db,values),
 remove:async keys=>{for(const k of (Array.isArray(keys)?keys:[keys]))delete window.__db[k];}
}}};
}"""

class UnknownReactionFallback(unittest.TestCase):
 def test_preserve_unknown_and_promote_when_tab_selected(self):
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel="chrome",headless=True)
   try:
    page=browser.new_page(accept_downloads=True)
    page.route("**/*",lambda r:r.fulfill(status=200,body=HTML,content_type="text/html")
               if r.request.is_navigation_request() else r.abort())
    page.goto(PAGE);page.evaluate(SETUP)
    page.add_script_tag(path=str(ROOT/"lib.js"))
    page.add_script_tag(path=str(ROOT/"content.js"))
    panel=page.locator("#voidscan-reaction-audit-root")
    panel.locator("#vcurrent").click()
    page.wait_for_function("""() => !document.querySelector('#voidscan-reaction-audit-root')
       .shadowRoot.getElementById('vcurrent').disabled""",timeout=30000)
    pending=page.evaluate("window.__db.voidscan_pending_reactions_v1")
    self.assertEqual(len(pending),3)
    self.assertEqual(len({r["profileUrl"] for r in pending}),3)
    self.assertTrue(all(r["reaction"]=="UNKNOWN" for r in pending))
    self.assertFalse(page.evaluate("window.__db.voidscan_reactions_v1||[]"))
    self.assertIn("3",panel.locator("#vpending").inner_text())
    with page.expect_download(timeout=10000) as d:panel.locator("#vcsv").click()
    self.assertTrue(d.value.suggested_filename.endswith(".csv"))
    self.assertIn("UNKNOWN",d.value.path().read_text(encoding="utf-8-sig"))
    page.evaluate("""() => {
       document.querySelector('#all').setAttribute('aria-selected','false');
       document.querySelector('#like').setAttribute('aria-selected','true');
    }""")
    panel.locator("#vcurrent").click()
    page.wait_for_function("""() => !document.querySelector('#voidscan-reaction-audit-root')
       .shadowRoot.getElementById('vcurrent').disabled""",timeout=30000)
    classified=page.evaluate("window.__db.voidscan_reactions_v1")
    pending=page.evaluate("window.__db.voidscan_pending_reactions_v1")

    self.assertEqual(len(classified),3)
    self.assertEqual(len(pending),0)
    self.assertTrue(all(x["reaction"]=="LIKE" for x in classified))
   finally:browser.close()
if __name__=="__main__":unittest.main()
