"""End-to-end offline Chrome test for CSV upload, live scanning and styled XLSX.

Uses synthetic IDs. No remote requests or Facebook authentication.
"""
from __future__ import annotations
import csv
import io
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from playwright.sync_api import sync_playwright

EXT=Path(__file__).resolve().parents[1]/"chrome-extension"
PHOTOIDS=["20309572443815"+str(30+i) for i in range(10)]
def url(i):return "https://www.facebook.com/profile.php?id="+str(100000000000+i)
def photo(i):return "https://www.facebook.com/photo/?fbid="+PHOTOIDS[i]
HEAD=["photoId","photoUrl","profileUrl","reaction","displayName","friendsCount","followingCount"]
def fixture():
  output=io.StringIO(newline="")
  writer=csv.writer(output)
  writer.writerow(HEAD)
  for i in range(10):
    writer.writerow([PHOTOIDS[i],photo(i),url(1),"LIKE","Case A","",""])
    writer.writerow([PHOTOIDS[i],photo(i),url(100+i),"LOVE","Case other","",""])
  writer.writerow([PHOTOIDS[0],photo(0),url(1),"CARE","Case A","",""])
  writer.writerow([PHOTOIDS[2],photo(2),url(600),"UNKNOWN","Case unknown","",""])
  writer.writerow([PHOTOIDS[0],photo(0),url(700),"LIKE","Case high count",3000,3500])
  return ("\ufeff"+output.getvalue()).encode("utf-8")

MOCK="""() => {
  window.__auditStorage={
    voidscan_reactions_v1:[
      {photoId:"2030957244381530",photoUrl:"https://www.facebook.com/photo/?fbid=2030957244381530",
       profileUrl:"https://www.facebook.com/local.test/",reaction:"LIKE"}
    ]
  };
  window.chrome={storage:{
    local:{
      get:async keys=>{
        const out={};
        for(const key of (Array.isArray(keys)?keys:[keys]))if(key in window.__auditStorage)out[key]=window.__auditStorage[key];
        return out;
      },
      set:async o=>{Object.assign(window.__auditStorage,o);},
      remove:async keys=>{for(const k of (Array.isArray(keys)?keys:[keys]))delete window.__auditStorage[k];}
    }
  }};
}"""

class ImportedCsvBrowser(unittest.TestCase):
 def test_upload_scan_live_counts_and_xlsx(self):
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel="chrome",headless=True)
   try:
    page=browser.new_page(accept_downloads=True,viewport={"width":1250,"height":900})
    page.set_content((EXT/"review.html").read_text(encoding="utf-8"))
    page.evaluate(MOCK)
    for name in ("lib.js","file-audit.js","xlsx-export.js","review.js"):
     page.add_script_tag(path=str(EXT/name))
    page.wait_for_function('document.getElementById("total").textContent==="1"',timeout=12000)
    self.assertEqual(page.locator("#total").inner_text(),"1")
    page.locator("#upload").set_input_files({
      "name":"VOIDSCAN_reactions_test.csv","mimeType":"text/csv","buffer":fixture()
    })
    page.wait_for_function('document.getElementById("progress-title").textContent==="Hoàn tất phân tích CSV (chưa xác minh profile)"',timeout=20000)
    self.assertNotEqual(page.locator("#photo-scope").input_value(),"all")
    self.assertEqual(page.locator("#total").inner_text(),"2") # two records on last image? one of each class
    page.locator("#photo-scope").select_option("all")
    page.wait_for_function('document.getElementById("total").textContent==="13"',timeout=20000)
    self.assertEqual(page.locator("#total").inner_text(),"13")
    self.assertEqual(page.locator("#flagged").inner_text(),"1") # friendsCount alone is not evidence of an empty profile
    self.assertEqual(page.locator("#nosignal").inner_text(),"12")
    self.assertEqual(page.locator("#checked").inner_text(),"13")
    self.assertEqual(page.locator("#photos").inner_text(),"10")
    self.assertEqual(page.locator("#progress-number").inner_text(),"13 / 13 tài khoản")
    self.assertEqual(page.locator(".queuebutton").count(),1)
    self.assertIn("Nghi vấn",page.locator(".queuebutton").first.inner_text())
    self.assertEqual(page.locator("#progress-track").get_attribute("aria-valuenow"),"100")
    with page.expect_download(timeout=15000) as get_csv:
      page.locator("#csvall").click()
    text=get_csv.value.path().read_text(encoding="utf-8-sig")
    self.assertTrue(get_csv.value.suggested_filename.endswith(".csv"))
    self.assertIn("Trạng thái",text.splitlines()[0])
    self.assertIn("nghi vấn",text)
    self.assertIn("không có dấu hiệu",text)
    with page.expect_download(timeout=15000) as get_xlsx:
      page.locator("#xlsxall").click()
    workbook=get_xlsx.value.path()
    self.assertTrue(get_xlsx.value.suggested_filename.endswith(".xlsx"))
    with zipfile.ZipFile(workbook) as z:
      self.assertIsNone(z.testzip())
      st=z.read("xl/styles.xml").decode("utf-8")
      sheet=z.read("xl/worksheets/sheet1.xml").decode("utf-8")
      self.assertIn("FF2158AD",st)
      self.assertIn("FFFDE8E8",st)
      self.assertIn("FFE4F5E8",st)
      self.assertIn('state="frozen"',sheet)
      self.assertIn("<autoFilter",sheet)
      self.assertIn('s="1"',sheet)
      self.assertIn('s="2"',sheet)
      self.assertIn('s="3"',sheet)
      self.assertIn("không có dấu hiệu",sheet)
      self.assertIn("<hyperlinks>",sheet)
      links=z.read("xl/worksheets/_rels/sheet1.xml.rels").decode("utf-8")
      self.assertIn('TargetMode="External"',links)
      self.assertIn("https://www.facebook.com/",links)
      ET.fromstring(links)
      ET.fromstring(sheet)
      ET.fromstring(st)
    # Show complete unfiltered list without losing original input order.
    page.locator("#filter").select_option("all")
    self.assertEqual(page.locator(".queuebutton").count(),13)
   finally:browser.close()

if __name__=="__main__":
 unittest.main()
