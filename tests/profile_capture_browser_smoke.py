"""Mocked user-opened Facebook profile; no network requests."""
from pathlib import Path
from playwright.sync_api import sync_playwright
EXT=Path(__file__).resolve().parents[1]/"chrome-extension"
URL="https://www.facebook.com/profile.php?id=100000000123"
HTML="""<html lang="vi"><head><meta charset="utf-8"><title>Test user</title></head>
<body><img alt="Ảnh đại diện" src="https://scontent.fsgn2-1.fna.fbcdn.net/test.jpg"
style="width:120px;height:120px"><p>Sống tại Dĩ An, Bình Dương</p></body></html>"""
MOCK="""() => {
 const store={};
 window.__profileStore=store;
 window.chrome={storage:{local:{
 get:async k=>({[k]:store[k]||{}}),
 set:async v=>Object.assign(store,v)
 }}};
}"""
with sync_playwright() as p:
 browser=p.chromium.launch(channel="chrome",headless=True)
 try:
  page=browser.new_page()
  page.route("https://www.facebook.com/**",lambda route:route.fulfill(status=200,body=HTML,content_type="text/html"))
  page.goto(URL)
  page.evaluate(MOCK)
  for s in ["lib.js","profile-capture.js"]:
   page.add_script_tag(path=str(EXT/s))
  result=page.evaluate("window.VoidscanCaptureCurrentProfile()")
  assert result["saved"] is True,result
  assert result["hasAvatar"] is True,result
  assert result["hasCurrentCity"] is True,result
  record=page.evaluate("Object.values(window.__profileStore.voidscan_profile_observations_v1)[0]")
  assert record["source"]=="observed_open_profile",record
  assert record["hasAvatar"]=="1",record
  assert record["currentCity"]=="Dĩ An, Bình Dương",record
  print("VOIDSCAN user-opened profile observation browser smoke: PASS")
 finally:
  browser.close()
