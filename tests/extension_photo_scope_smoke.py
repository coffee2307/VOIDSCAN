"""Regression for per-photo storage, display, and default CSV export.

Fully synthetic Chrome and Facebook DOM. No network requests or real accounts.
"""
from __future__ import annotations
import csv
import io
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/"chrome-extension"
A="2030957244381534"
B="2030957077714884"
def u(id):return "https://www.facebook.com/photo/?fbid="+id
HTML="""<!doctype html><html lang="vi"><head><meta charset="utf-8"><style>
[role=dialog]{position:fixed;top:30px;left:30px;width:450px;height:410px;background:white}
[role=listitem]{height:80px;display:flex;align-items:center}
[role=listitem] a{padding:10px}
</style></head><body><div role="dialog" aria-label="Người đã bày tỏ cảm xúc"><div id="reaction-list" role="list"></div></div></body></html>"""
MOCK="""() => {
 window.__db={};
 window.chrome={storage:{local:{
 get:async keys=>{const out={};for(const k of (Array.isArray(keys)?keys:[keys]))if(k in window.__db)out[k]=window.__db[k];return out;},
 set:async items=>{Object.assign(window.__db,items);},
 remove:async keys=>{for(const k of (Array.isArray(keys)?keys:[keys]))delete window.__db[k];}
 }}};
 window.rebuild=(name)=>{
   const list=document.querySelector("#reaction-list");
   list.replaceChildren();
   const row=document.createElement("div");row.setAttribute("role","listitem");
   const a=document.createElement("a");a.href="https://www.facebook.com/"+name+"/";
   a.setAttribute("aria-label",name+" đã thích");a.textContent=name;
   row.append(a);list.append(row);
 };
 window.rebuild("photo.one");
}"""
POPUP_MOCK="""(data) => {
window.__db=data;window.__downloads=[];
window.chrome={storage:{
 local:{
  get:async keys=>{const result={};for(const key of (Array.isArray(keys)?keys:[keys]))if(key in window.__db)result[key]=window.__db[key];return result;},
  set:async data=>{Object.assign(window.__db,data);},
  remove:async keys=>{for(const k of (Array.isArray(keys)?keys:[keys]))delete window.__db[k];}
 },
 onChanged:{addListener:()=>{}}
},downloads:{
 download:async args=>{
   const payload=await fetch(args.url).then(x=>x.text());
   window.__downloads.push({filename:args.filename,csv:payload});return 1;
 }
},tabs:{query:async()=>[],create:async()=>({})},runtime:{getURL:()=>""}};
}"""
class ScopeSmoke(unittest.TestCase):
 def test_navigation_keeps_photo_ids_and_current_csv(self):
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel="chrome",headless=True)
   try:
    page=browser.new_page(accept_downloads=True)
    page.route("**/*",lambda r:r.fulfill(status=200,body=HTML,content_type="text/html")
       if r.request.is_navigation_request() else r.abort())
    page.goto(u(A));page.evaluate(MOCK)
    page.add_script_tag(path=str(ROOT/"lib.js"));page.add_script_tag(path=str(ROOT/"content.js"))
    panel=page.locator("#voidscan-reaction-audit-root")
    panel.locator("#vcurrent").click()
    page.wait_for_function("""() => !document.querySelector('#voidscan-reaction-audit-root')
      .shadowRoot.getElementById('vcurrent').disabled""",timeout=30000)
    self.assertEqual(panel.locator("#vcount").inner_text(),"1")
    page.evaluate("(url)=>{history.pushState({},'',url);window.rebuild('photo.two');}",u(B))
    page.wait_for_function("""() => {
      const r=document.querySelector('#voidscan-reaction-audit-root').shadowRoot;
      return r.getElementById('vphoto').value==='2030957077714884';
    }""",timeout=5000)
    self.assertEqual(panel.locator("#vcount").inner_text(),"0")
    panel.locator("#vcurrent").click()
    page.wait_for_function("""() => !document.querySelector('#voidscan-reaction-audit-root')
      .shadowRoot.getElementById('vcurrent').disabled""",timeout=30000)
    rows=page.evaluate("window.__db.voidscan_reactions_v1")
    self.assertEqual(len(rows),2)
    self.assertEqual([x["photoId"] for x in rows],[A,B])
    self.assertEqual(panel.locator("#vcount").inner_text(),"1")
    self.assertEqual(panel.locator("#vall").inner_text(),"1")
    with page.expect_download(timeout=12000) as download:panel.locator("#vcsv").click()
    content=download.value.path().read_text(encoding="utf-8-sig")
    parsed=list(csv.DictReader(io.StringIO(content)))
    self.assertEqual(len(parsed),1)
    self.assertEqual(parsed[0]["photoId"],B)
    self.assertIn("PHOTO",download.value.suggested_filename.upper() if "PHOTO" in download.value.suggested_filename.upper() else "PHOTO")
   finally:browser.close()

 def test_popup_photo_one_190_photo_two_110_all_300(self):
  records=[]
  for i in range(190):
   records.append({ "photoId":A,"photoUrl":u(A),
     "profileUrl":"https://www.facebook.com/profile.php?id="+str(100000000000+i),"reaction":"LIKE"})
  for i in range(110):
   records.append({"photoId":B,"photoUrl":u(B),
     "profileUrl":"https://www.facebook.com/profile.php?id="+str(100000000000+i),"reaction":"LOVE"})
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel="chrome",headless=True)
   try:
    page=browser.new_page()
    page.set_content((ROOT/"popup.html").read_text(encoding="utf-8"))
    page.evaluate(POPUP_MOCK,{"voidscan_reactions_v1":records,"voidscan_active_photo_v1":B})
    for script in ("lib.js","review-lib.js","popup.js"):
     page.add_script_tag(path=str(ROOT/script))
    page.wait_for_function('document.getElementById("records").textContent==="110"',timeout=18000)
    self.assertEqual(page.locator("#photo-scope").input_value(),B)
    page.locator("#csv").click()
    page.wait_for_function("window.__downloads.length===1")
    exported=page.evaluate("window.__downloads[0]")
    self.assertEqual(len(list(csv.DictReader(io.StringIO(exported["csv"].lstrip("\ufeff"))))),110)
    self.assertIn(B,exported["filename"])
    page.locator("#photo-scope").select_option(A)
    page.wait_for_function('document.getElementById("records").textContent==="190"')
    page.locator("#photo-scope").select_option("all")
    page.wait_for_function('document.getElementById("records").textContent==="300"')
    page.locator("#csv").click()
    page.wait_for_function("window.__downloads.length===2")
    self.assertEqual(len(list(csv.DictReader(io.StringIO(
     page.evaluate("window.__downloads[1].csv").lstrip("\ufeff"))))),300)
   finally:browser.close()

if __name__=="__main__":unittest.main()
