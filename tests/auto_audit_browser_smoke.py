"""VOIDSCAN unattended opt-in public metadata queue - mocked and offline."""
from pathlib import Path
from playwright.sync_api import sync_playwright
EXT=Path(__file__).resolve().parents[1]/"chrome-extension"
PHOTO="2030957244381534"
def url(i):return "https://www.facebook.com/profile.php?id="+str(100000000000+i)
DATA=("photoId,profileUrl,reaction\n"+"".join(PHOTO+","+url(i)+",LIKE\n" for i in range(1,5))).encode("utf-8")
MOCK="""() => {
 window.__stored={};
 window.chrome={
   permissions:{request:async()=>true},
   tabs:{
     create:async o=>{
       window.__lastVisited=o.url;window.__tabCreateCount=(window.__tabCreateCount||0)+1;
       window.__tested=(window.__tested||0)+1;
       return {id:77,url:o.url,status:"complete"};
     },
     update:async (id,o)=>{
       if(id!==77)throw Error("Wrong reused tab");
       window.__lastVisited=o.url;window.__tested=(window.__tested||0)+1;
       return {id:77,url:o.url,status:"complete"};
     },
     get:async id=>({id,url:window.__lastVisited,status:"complete"}),
     remove:async id=>{window.__tabCloseCount=(window.__tabCloseCount||0)+1;},
     onUpdated:{addListener:()=>{},removeListener:()=>{}}
   },
   scripting:{executeScript:async o=>[{result:{access:"page_visible",avatarSeen:true}}]},
   storage:{
     local:{get:async keys=>{
       const out={};for(const k of Array.isArray(keys)?keys:[keys])
         if(k in window.__stored)out[k]=window.__stored[k];return out;
     },set:async update=>Object.assign(window.__stored,update),
            remove:async keys=>{for(const k of (Array.isArray(keys)?keys:[keys]))delete window.__stored[k];}},
     onChanged:{addListener:()=>{}}
   }
 };
}"""
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel="chrome",headless=True)
 try:
  page=browser.new_page(accept_downloads=True)
  page.set_content((EXT/"review.html").read_text(encoding="utf-8"))
  page.evaluate(MOCK)
  for name in ["lib.js","file-audit.js","profile-import.js","public-metadata.js",
               "auto-audit.js","auto-coverage.js","privacy-audit.js","tab-audit.js","reaction-integrity.js","xlsx-export.js","review.js"]:
   page.add_script_tag(path=str(EXT/name))
  page.evaluate("""() => {
    window.VoidscanAutoAudit.WAIT_MS=0;
    window.VoidscanTabAudit.config.settleMs=0;
  }""")
  page.locator("#upload").set_input_files({"name":"reactions.csv","mimeType":"text/csv","buffer":DATA})
  page.wait_for_function('document.getElementById("total").textContent==="4"',timeout=15000)
  page.locator("#auto-start").click()
  page.wait_for_function('document.getElementById("auto-state").textContent==="Hoàn thành"',timeout=25000)
  saved=page.evaluate("window.__stored.voidscan_auto_tab_state_v1")
  assert saved["index"]==4,saved
  assert saved["usable"]==4,saved
  assert saved["urls"] and len(saved["urls"])==4,saved
  assert page.evaluate("window.__tested")==4
  assert page.evaluate("window.__tabCreateCount")==1
  assert page.evaluate("window.__tabCloseCount")==1
  page.wait_for_function('document.getElementById("insufficient").textContent==="4"',timeout=15000)
  record=page.evaluate("window.__stored.voidscan_ephemeral_tab_audit_v1")
  assert len(record)==4,record
  assert not page.evaluate("window.__stored.voidscan_profile_observations_v1")
  assert all(set(x)=={"status","access","usable","reason","checkedAt","expiresAt"} for x in record.values())
  assert all(x["status"]=="chưa đủ dữ liệu" and x["access"]=="page_visible"
             for x in record.values())
  assert not any("local" in str(x) or "bio" in str(x) for x in record.values())
  assert page.locator("#auto-progress").inner_text().startswith("4/4 URL")
  assert page.locator("#evidence-coverage").inner_text()=="0 / 4"
  assert "4 URL đã thử" in page.locator("#metadata-status").inner_text()
  with page.expect_download(timeout=15000) as exported:
   page.locator("#auto-export").click()
  txt=exported.value.path().read_text(encoding="utf-8-sig")
  assert txt.count("https://www.facebook.com/profile.php?id=")==4
  assert "with_evidence" in txt
  # Resuming completed queues is intentionally a new pass; existing metadata means no new requests.
  page.locator("#auto-start").click()
  page.wait_for_function('document.getElementById("auto-state").textContent==="Hoàn thành"',timeout=20000)
  assert page.evaluate("window.__tested")==4
  removed=[]
  page.expose_function("recordRemovedAuditKeys",lambda keys:removed.extend(keys))
  page.evaluate("""() => {
    const original=window.chrome.storage.local.remove;
    window.chrome.storage.local.remove=async keys=>{
      await window.recordRemovedAuditKeys(keys);return original(keys);
    };
  }""")
  page.locator("#privacy-erase").click()
  page.wait_for_timeout(350)
  assert {"voidscan_ephemeral_tab_audit_v1","voidscan_auto_tab_state_v1",
          "voidscan_reactions_v1","voidscan_profile_observations_v1",
          "voidscan_tab_audit_attempts_v1"}.issubset(set(removed)),removed
  print("VOIDSCAN automatic privacy audit, no raw persistence and wipe button: PASS")
 finally:browser.close()
