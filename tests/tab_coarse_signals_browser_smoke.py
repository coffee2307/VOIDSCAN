"""Coarse on-tab audit: synthetic visible Facebook-like layout, no raw content retention."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/"chrome-extension"
HTML="""<!doctype html><html lang='vi'><head><title>Trang cá nhân mẫu</title></head>
<body>
 <img src='https://static.example.invalid/photo.png' alt='Ảnh đại diện của người dùng'>
 <div>Sống tại Thành phố Mẫu</div>
 <div>Học tại Trường Mẫu</div>
 <div>Tiểu sử: Công việc và cuộc sống</div>
 <div>320 bạn bè</div>
 <div>12 bạn chung</div>
 <div>Đã tham gia Facebook năm 2018</div>
 <article><time datetime='2026-10-20T10:15:00Z'>Bài đăng gần đây</time></article>
 <div id='contacts'>email-private@example.invalid - 0912345678</div>
</body></html>"""
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel="chrome",headless=True)
 try:
  page=browser.new_page()
  page.set_content(HTML)
  page.add_script_tag(path=str(ROOT/"lib.js"))
  page.add_script_tag(path=str(ROOT/"tab-audit.js"))
  page.add_script_tag(path=str(ROOT/"privacy-audit.js"))
  result=page.evaluate("window.VoidscanTabAudit.probePage()")
  assert result["access"]=="page_visible",result
  for k in ("avatarSeen","locationListed","schoolListed","bioListed"):
   assert result[k],(k,result)
  assert result["friendsBand"]=="200-999",result
  assert result["mutualBand"]=="1-49",result
  assert result["postRecency"] in ("within_90d","90_to_364d","365d_plus"),result
  assert result["joinedEra"]=="5y_plus",result
  derived=page.evaluate("obs=>window.VoidscanPrivacyAudit.decide(obs)",result)
  assert derived["signalCount"]==8,derived
  assert derived["status"]=="chưa đủ dữ liệu",derived
  for private in ("Trường Mẫu","0912345678","email-private","Thành phố Mẫu"):
   assert private not in str(result),private
   assert private not in str(derived),private
  page.set_content("<!doctype html><html><head><title>Trang cá nhân</title></head><body><p>Chưa có dữ liệu</p></body></html>")
  missing=page.evaluate("window.VoidscanTabAudit.probePage()")
  assert not missing["avatarSeen"]
  assert missing["friendsBand"]=="unknown"
  assert missing["postRecency"]=="unknown"
  assert not missing["schoolListed"]
  print("VOIDSCAN visible coarse signals only, no personally identifying text: PASS")
 finally:browser.close()
