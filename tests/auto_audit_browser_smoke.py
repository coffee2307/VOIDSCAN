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
   storage:{
     local:{get:async keys=>{
       const out={};for(const k of Array.isArray(keys)?keys:[keys])
         if(k in window.__stored)out[k]=window.__stored[k];return out;
     },set:async update=>Object.assign(window.__stored,update)},
     onChanged:{addListener:()=>{}}
   }
 };
}"""
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel="chrome",headless=True)
 try:
  page=browser.new_page()
  page.set_content((EXT/"review.html").read_text(encoding="utf-8"))
  page.evaluate(MOCK)
  for name in ["lib.js","file-audit.js","profile-import.js","public-metadata.js",
               "auto-audit.js","reaction-integrity.js","xlsx-export.js","review.js"]:
   page.add_script_tag(path=str(EXT/name))
  page.evaluate("""() => {
    window.VoidscanAutoAudit.WAIT_MS=0;
    window.VoidscanPublicMetadata.get=async (url)=>{
      window.__tested=(window.__tested||0)+1;
      return {access:"public_metadata",region:url.includes("001")?"local":"unknown",hasBio:true};
    };
  }""")
  page.locator("#upload").set_input_files({"name":"reactions.csv","mimeType":"text/csv","buffer":DATA})
  page.wait_for_function('document.getElementById("total").textContent==="4"',timeout=15000)
  page.locator("#auto-start").click()
  page.wait_for_function('document.getElementById("auto-state").textContent==="Hoàn thành"',timeout=25000)
  saved=page.evaluate("window.__stored.voidscan_auto_audit_state_v1")
  assert saved["index"]==4,saved
  assert saved["usable"]==4,saved
  assert saved["urls"] and len(saved["urls"])==4,saved
  assert page.evaluate("window.__tested")==4
  page.wait_for_function('document.getElementById("insufficient").textContent==="0"',timeout=15000)
  assert page.locator("#auto-progress").inner_text().startswith("4/4 URL")
  # Resuming completed queues is intentionally a new pass; existing metadata means no new requests.
  page.locator("#auto-start").click()
  page.wait_for_function('document.getElementById("auto-state").textContent==="Hoàn thành"',timeout=20000)
  assert page.evaluate("window.__tested")==4
  print("VOIDSCAN auto audit from CSV to completed queue, persistence, duplicate suppression: PASS")
 finally:browser.close()
