"""Headless Chrome smoke for the local automatic triage review dashboard.

The HTML and records are synthetic. No Facebook or user accounts accessed.
"""
from __future__ import annotations
import json
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

EXT=Path(__file__).resolve().parents[1]/"chrome-extension"
PHOTO_IDS=["20309572443815"+str(i+30) for i in range(10)]
def photo(pid):return "https://www.facebook.com/photo/?fbid="+pid
def profile(uid):return "https://www.facebook.com/profile.php?id="+str(100000000000+uid)

def fixture():
    rows=[]
    for i,pid in enumerate(PHOTO_IDS):
        rows.append(dict(photoId=pid,photoUrl=photo(pid),profileUrl=profile(1),reaction="LOVE"))
        rows.append(dict(photoId=pid,photoUrl=photo(pid),profileUrl=profile(50+i),reaction="LIKE"))
    rows.append(dict(photoId=PHOTO_IDS[2],photoUrl=photo(PHOTO_IDS[2]),profileUrl=profile(1),reaction="HAHA"))
    return rows

INIT_SCRIPT="""(data) => {
  const state={"voidscan_reactions_v1":data,"voidscan_screening_reviews_v1":{}};
  window.__auditDb=state;
  window.chrome={storage:{
    local:{
      get:async keys=>{
        const result={};
        for(const key of (Array.isArray(keys)?keys:[keys])){
          if(key in state)result[key]=state[key];
        }
        return result;
      },
      set:async obj=>{Object.assign(state,obj);return;},
      remove:async keys=>{
        for(const key of (Array.isArray(keys)?keys:[keys]))delete state[key];
      }
    },
    onChanged:{addListener:()=>{}}
  }};
}"""

class ReviewBrowserSmoke(unittest.TestCase):
    def test_dashboard_auto_selects_only_flagged_and_csv(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="chrome",headless=True)
            try:
                page=browser.new_page(viewport={"width":1250,"height":900},accept_downloads=True)
                page.set_content((EXT/"review.html").read_text(encoding="utf-8"))
                page.evaluate(INIT_SCRIPT,fixture())
                for script in ("lib.js","review-lib.js","review.js"):
                    page.add_script_tag(path=str(EXT/script))
                page.wait_for_function("document.getElementById('total').textContent==='11'",timeout=10000)
                self.assertEqual(page.locator("#total").inner_text(),"11")
                self.assertEqual(page.locator("#flagged").inner_text(),"1")
                self.assertEqual(page.locator("#nosignal").inner_text(),"10")
                self.assertEqual(page.locator(".queuebutton").count(),1)
                self.assertEqual(page.locator("#nphotos").inner_text(),"10")
                self.assertIn("nhiều loại reaction",page.locator("#reasons").inner_text())
                with page.expect_download(timeout=10000) as downloaded:
                    page.locator("#csvflag").click()
                self.assertTrue(downloaded.value.suggested_filename.endswith(".csv"))
                page.locator("#decision").select_option("needs_review")
                page.locator("#notes").fill("Test: đối chiếu phản ứng theo thời gian")
                page.locator("#save").click()
                page.wait_for_function("""() =>
                  window.__auditDb.voidscan_screening_reviews_v1 &&
                  Object.values(window.__auditDb.voidscan_screening_reviews_v1)
                    .some(r=>r.status==="needs_review")""",timeout=10000)
                self.assertEqual(page.locator("#checked").inner_text(),"1")
                page.locator("#filter").select_option("all")
                self.assertEqual(page.locator(".queuebutton").count(),11)
                self.assertEqual(page.locator("#total").inner_text(),"11")
                self.assertIn("Không tự kết luận bot",page.locator("#notice").inner_text()
                    if "Không tự kết luận bot" in page.locator("#notice").inner_text() else
                    page.locator("header").inner_text())
            finally:
                browser.close()

if __name__=="__main__":
    unittest.main()
