"""Chrome DOM integration smoke: synthetic Facebook reaction dialog only.

No real Facebook requests, profiles, cookies, Meta token, or login state.
Requires local Playwright + installed Chrome; run separately from CI.
"""
from __future__ import annotations
import json
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]/"chrome-extension"
PHOTO="2030957244381534"
URL="https://www.facebook.com/photo/?fbid="+PHOTO
HTML="""<!doctype html><html lang="vi"><head><style>
body{margin:0;font-family:sans-serif;background:#e4e7ea}
[role=dialog]{position:fixed;left:30px;top:40px;width:460px;height:530px;background:white;border:1px solid #ccc}
[role=tab]{padding:12px;display:inline-block;border:1px solid #aaa;cursor:pointer}
#reaction-list{height:320px;overflow:auto}
[role=listitem]{height:72px;display:flex;align-items:center;gap:12px}
[role=listitem] img{width:48px;height:48px}
</style></head><body>
<div role="dialog" aria-label="Người đã bày tỏ cảm xúc">
<div role="tablist">
<button role="tab" data-type="LIKE" aria-selected="true">Like 12</button>
<button role="tab" data-type="LOVE" aria-selected="false">Love 34</button>
<button role="tab" data-type="CARE" aria-selected="false">Care 5</button>
<button role="tab" data-type="HAHA" aria-selected="false">Haha 6</button>
<button role="tab" data-type="WOW" aria-selected="false">Wow 7</button>
</div><div id="reaction-list" role="list"></div></div>
</body></html>"""
SETUP_JS="""() => {
  window.__localExtensionDB={};
  window.chrome={storage:{local:{
    get:async key=>{let keys=typeof key==="string"?[key]:Object.keys(key);const out={};for(const k of keys)if(k in window.__localExtensionDB)out[k]=window.__localExtensionDB[k];return out;},
    set:async values=>{Object.assign(window.__localExtensionDB,values);},
    remove:async keys=>{for(const k of (Array.isArray(keys)?keys:[keys]))delete window.__localExtensionDB[k];}
  }}};
  const list=document.querySelector("#reaction-list");
  const types=["LIKE","LOVE","CARE","HAHA","WOW"];
  const renders={
     LIKE:[["alex.test","Like"],["lucy.test","Like"]],
     LOVE:[["nancy.test","Love"]],
     CARE:[["profile.php?id=1234567890123","Care"]],
     HAHA:[["people/Test-Name/1234567890124","Haha"]],
     WOW:[["peter.test","Wow"]]
  };
  const render=type=>{
    const rows=renders[type];
    list.replaceChildren();
    rows.forEach(([profile,alt])=>{
      const row=document.createElement("div");row.setAttribute("role","listitem");
      const image=document.createElement("img");image.setAttribute("alt",alt);
      image.src="https://scontent.fsgn2-1.fna.fbcdn.net/mock.png";
      const a=document.createElement("a");
      a.href="https://www.facebook.com/"+profile;
      a.textContent=profile.split("/")[0];
      const span=document.createElement("span");span.textContent="3 mutual friends";
      row.append(image,a,span);list.appendChild(row);
    });
  };
  for(const tab of document.querySelectorAll('[role="tab"]')){
    tab.addEventListener("click",()=>{
      document.querySelectorAll('[role="tab"]').forEach(x=>x.setAttribute("aria-selected",x===tab?"true":"false"));
      render(tab.dataset.type);
    });
  }
  render("LIKE");
}"""
class ExtensionBrowserSmoke(unittest.TestCase):
    def test_auto_collect_types_and_draggable_panel(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="chrome",headless=True)
            try:
                page=browser.new_page(viewport={"width":1280,"height":860},accept_downloads=True)
                page.route("**/*",lambda route:route.fulfill(status=200,body=HTML,content_type="text/html")
                           if route.request.is_navigation_request() else
                           route.fulfill(status=200,body="",content_type="image/png"))
                page.goto(URL)
                page.evaluate(SETUP_JS)
                page.add_script_tag(path=str(ROOT/"lib.js"))
                page.add_script_tag(path=str(ROOT/"content.js"))
                panel=page.locator("#voidscan-reaction-audit-root")
                self.assertEqual(panel.count(),1)
                initial=panel.locator("#vdrag").bounding_box()
                page.mouse.move(initial["x"]+50,initial["y"]+20)
                page.mouse.down()
                page.mouse.move(initial["x"]-90,initial["y"]+70,steps=5)
                page.mouse.up()
                moved=panel.locator("#vdrag").bounding_box()
                self.assertLess(moved["x"],initial["x"]-20)
                panel.locator("#vhome").click()
                panel.locator("#vauto").click()
                page.wait_for_function("""() => (window.__localExtensionDB["voidscan_reactions_v1"]||[]).length===6""",timeout=60000)
                page.wait_for_function("""() => !document.querySelector('#voidscan-reaction-audit-root').shadowRoot.getElementById('vauto').disabled""",timeout=30000)
                rows=page.evaluate("window.__localExtensionDB['voidscan_reactions_v1']")
                self.assertEqual(len(rows),6)
                self.assertEqual(set(x["reaction"] for x in rows),
                                 {"LIKE","LOVE","CARE","HAHA","WOW"})
                self.assertTrue(all(x["photoId"]==PHOTO for x in rows))
                self.assertEqual(sum(1 for x in rows if x["userId"]),2)
                self.assertTrue(all(x["profileUrl"].startswith("https://www.facebook.com/") for x in rows))
                self.assertTrue(all(x["mutualFriendsNumber"]==3 for x in rows))
                with page.expect_download(timeout=10000) as download_info:
                    panel.locator("#vcsv").click()
                self.assertTrue(download_info.value.suggested_filename.endswith(".csv"))
                panel.locator("#vmin").click()
                self.assertFalse(panel.locator("#vmain").is_visible())
                panel.locator("#vhome").click()
                self.assertTrue(panel.locator("#vmain").is_visible())
            finally:
                browser.close()

if __name__=="__main__":
    unittest.main()
