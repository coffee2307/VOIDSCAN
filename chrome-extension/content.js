(() => {
"use strict";
if(window.__voidscanAuditActive)return;
const lib=window.VoidscanAudit;
if(!lib)return;
window.__voidscanAuditActive=true;
const STORE="voidscan_reactions_v1";
const PHOTO_STORE="voidscan_photo_links_v1";
const root=document.createElement("div");
root.id="voidscan-reaction-audit-root";
root.style.cssText="position:fixed;right:16px;top:90px;z-index:2147483646";
const shadow=root.attachShadow({mode:"open"});
const style=document.createElement("style");
style.textContent=[
"*{box-sizing:border-box}.panel{width:340px;max-width:calc(100vw - 28px);background:white;color:#1b2941;font:13px system-ui,Segoe UI,sans-serif;border:1px solid #cbd6e9;border-radius:14px;box-shadow:0 12px 50px #162c5366;overflow:hidden}",
"header{background:#193b72;color:#fff;padding:12px 14px;display:flex;justify-content:space-between;align-items:center}",
"header strong{font-size:15px}header button{background:transparent;color:#fff;border-color:#627aa4;padding:3px 8px}",
"main{padding:12px 14px}h4{margin:0 0 9px;font-size:13px}label{font-size:12px;display:block;margin:8px 0 4px}",
"button{font:inherit;cursor:pointer;padding:8px;border:1px solid #c8d6ed;background:#fff;border-radius:8px;color:#1d3d76;font-weight:600}button:disabled{opacity:.5}",
"input,select{padding:8px;border:1px solid #c6d2e3;border-radius:8px;width:100%;font:inherit;background:#fff;color:#14223e}",
".actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:12px 0}.actions button:first-child{grid-column:1/-1;background:#305cbb;color:#fff;border:0}",
".info{background:#f2f5fb;border-radius:9px;padding:10px;color:#375075;line-height:1.5}.small{color:#60738b;font-size:11px;line-height:1.5;margin-top:8px}",
"#vstatus{font-size:12px;margin:9px 0;line-height:1.5;color:#295b8e;min-height:16px}.metrics{display:flex;gap:8px;margin:9px 0}",
".metrics span{flex:1;padding:8px;border-radius:8px;background:#eef3fb;font-size:11px}.metrics strong{display:block;color:#16305a;font-size:20px}"
].join("");
const panel=document.createElement("section");panel.className="panel";
panel.innerHTML=[
'<header><strong>VOIDSCAN · REACTIONS</strong><button type="button" id="vclose">×</button></header>',
'<main><h4>Thu thập URL đang hiển thị</h4>',
'<div class="info">1. Mở <b>ảnh riêng</b> trên Facebook.<br>2. Nhấp số reaction và chọn tab Like/Love/Care/Haha/Wow.<br>3. Chọn đúng loại bên dưới, sau đó thu thập.</div>',
'<label for="vphoto">Photo ID (tự nhận từ URL hoặc nhập mã)</label><input id="vphoto" type="text" inputmode="numeric" placeholder="Photo ID">',
'<label for="vtype">Loại reaction đang hiển thị</label><select id="vtype">',
'<option value="LIKE">Like / Thích</option><option value="LOVE">Love / Tym</option>',
'<option value="CARE">Care / Thương thương</option><option value="HAHA">Haha</option><option value="WOW">Wow</option></select>',
'<button id="vlinks">Lưu các link ảnh đang hiển thị trong bài</button>',
'<div class="actions"><button id="vscan">Đọc danh sách đang mở</button>',
'<button id="vscroll">Cuộn & đọc (tối đa 20 lượt)</button><button id="vstop">Dừng cuộn</button></div>',
'<div class="metrics"><span><strong id="vcurrent">0</strong>Trên ảnh này</span><span><strong id="vall">0</strong>Tổng dòng đã lưu</span></div>',
'<p id="vstatus" role="status">Chưa thu thập.</p>',
'<div class="small">Chỉ đếm URL đọc được, không phải tổng reaction. Facebook có thể chưa tải toàn bộ danh sách. Không tự xác định bot.</div></main>'
].join("");
shadow.append(style,panel);
document.documentElement.appendChild(root);
const $=id=>shadow.getElementById(id);
let running=false,stopped=false,lastPhoto="";
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function report(msg){$("vstatus").textContent=msg;}
function currentPhoto(){
 const auto=lib.photoId(location.href);
 if(auto&&document.activeElement!==$("vphoto"))$("vphoto").value=auto;
 const id=$("vphoto").value.trim();
 return /^\d{5,30}$/.test(id)?id:null;
}
function imageUrl(id){return "https://www.facebook.com/photo/?fbid="+id;}
async function readRows(){
 const data=(await chrome.storage.local.get(STORE))[STORE];
 return Array.isArray(data)?data:[];
}
async function refresh(){
 const records=await readRows(),id=currentPhoto();
 $("vcurrent").textContent=records.filter(r=>r.photoId===id).length.toLocaleString("vi-VN");
 $("vall").textContent=records.length.toLocaleString("vi-VN");
}
function findDialog(){
 const dialogs=[...document.querySelectorAll('[role="dialog"]')]
  .filter(d=>d.getBoundingClientRect().width>150&&d.getBoundingClientRect().height>160);
 const candidates=dialogs.map(d=>{
  const label=((d.getAttribute("aria-label")||"")+" "+(d.innerText||"").slice(0,170)).toLowerCase();
  const count=[...d.querySelectorAll("a[href]")].filter(a=>lib.normalizeProfile(a.href)).length;
  const tabCount=d.querySelectorAll('[role="tab"],[role="tablist"]').length;
  const keyword=/react|cảm xúc|người đã|thích|thương thương|love|haha|wow|like/.test(label);
  return {d,score:count+2*tabCount+(keyword?5:0),valid:count>0&&(tabCount>0||keyword)};
 });
 return candidates.filter(x=>x.valid).sort((a,b)=>b.score-a.score)[0]?.d||null;
}
function visibleAccounts(dialog){
 const out=new Set();
 for(const a of dialog.querySelectorAll("a[href]")){
  const url=lib.normalizeProfile(a.href);
  if(url&&a.getClientRects().length){
   const rect=a.getBoundingClientRect();
   if(rect.width>0&&rect.height>0)out.add(url);
  }
 }
 return [...out];
}
let saving=Promise.resolve();
function storeBatch(id,type,accounts){
 saving=saving.catch(()=>{}).then(async()=>{
  const all=await readRows(),indices=new Map();
  for(let i=0;i<all.length;i++)indices.set(all[i].photoId+"|"+all[i].profileUrl,i);
  let added=0;
  for(const profileUrl of accounts){
   const key=id+"|"+profileUrl,at=indices.get(key);
   const record={photoId:id,photoUrl:imageUrl(id),profileUrl,reaction:type,capturedAt:new Date().toISOString()};
   if(at===undefined){indices.set(key,all.length);all.push(record);added++;}
   else if(all[at].reaction!==type)all[at]=record;
  }
  if(accounts.length)await chrome.storage.local.set({[STORE]:all});
  return added;
 });
 return saving;
}
async function capture(dialog){
 const id=currentPhoto();
 if(!id)throw new Error("Mở ảnh riêng hoặc nhập Photo ID đúng từ link ảnh.");
 if(!dialog)throw new Error("Mở danh sách người thả reaction trên Facebook trước.");
 const type=lib.cleanReaction($("vtype").value);
 const accounts=visibleAccounts(dialog);
 if(!accounts.length)throw new Error("Chưa thấy URL hồ sơ trong hộp thoại đang mở.");
 const count=await storeBatch(id,type,accounts);
 await refresh();
 return {added:count,seen:accounts.length};
}
function scroller(dialog){
 return [dialog,...dialog.querySelectorAll("*")].filter(el=>{
  if(el.scrollHeight-el.clientHeight<80||el.clientHeight<70)return false;
  const overflow=getComputedStyle(el).overflowY;
  return ["auto","scroll"].includes(overflow)||el.getAttribute("role")==="list"||el===dialog;
 }).sort((a,b)=>(b.scrollHeight-b.clientHeight)-(a.scrollHeight-a.clientHeight))[0]||null;
}
async function scanOnce(){
 if(running)return;running=true;
 try{
  const x=await capture(findDialog());
  report("Đã thêm "+x.added+" URL; quan sát "+x.seen+" URL trong danh sách.");
 }catch(e){report(e.message);}
 finally{running=false;}
}
async function scrollScan(){
 if(running)return;
 running=true;stopped=false;
 try{
  const original=findDialog();
  if(!original)throw new Error("Mở danh sách reaction trước khi cuộn.");
  const el=scroller(original);
  if(!el)throw new Error("Không tìm thấy danh sách cuộn; hãy cuộn thủ công.");
  let total=0,unchanged=0,lastTop=-1;
  for(let i=0;i<20&&!stopped;i++){
   const dialog=findDialog();
   if(!dialog)break;
   const x=await capture(dialog);total+=x.added;
   const top=el.scrollTop;
   el.scrollTop=Math.min(top+Math.max(200,el.clientHeight*.7),el.scrollHeight);
   el.dispatchEvent(new Event("scroll",{bubbles:true}));
   report("Lần "+(i+1)+"/20 · Đã thêm "+total+" URL...");
   await delay(1200);
   if(el.scrollTop<=top+2||el.scrollTop===lastTop)unchanged++;else unchanged=0;
   lastTop=el.scrollTop;if(unchanged>=3)break;
  }
  if(!stopped){const d=findDialog();if(d)total+=(await capture(d)).added;}
  report((stopped?"Đã dừng. ":"Quét hoàn thành. ")+"Thêm "+total+" URL. Có thể chưa đủ.");
 }catch(e){report(e.message);}
 finally{running=false;stopped=false;await refresh();}
}
$("vclose").addEventListener("click",()=>{stopped=true;root.remove();window.__voidscanAuditActive=false;});
async function recordPhotoLinks(){
 const raw=(await chrome.storage.local.get(PHOTO_STORE))[PHOTO_STORE];
 const urls=new Map((Array.isArray(raw)?raw:[]).map(x=>[x.photoId,x]));
 let found=0;
 for(const a of document.querySelectorAll('a[href*="fbid="]')){
  const u=lib.fbUrl(a.href),id=lib.photoId(a.href);
  if(!u||!id)continue;
  const set=u.searchParams.get("set")||"";
  if(!set.startsWith("pcb."))continue;
  urls.set(id,{photoId:id,photoUrl:imageUrl(id)});found++;
 }
 await chrome.storage.local.set({[PHOTO_STORE]:[...urls.values()]});
 report("Đã ghi "+found+" liên kết thuộc bài nhiều ảnh; tổng "+urls.size+" ảnh. Mở rộng album để tìm thêm.");
}
$("vlinks").addEventListener("click",()=>recordPhotoLinks().catch(()=>report("Không ghi được liên kết ảnh.")));
$("vscan").addEventListener("click",scanOnce);
$("vscroll").addEventListener("click",scrollScan);
$("vstop").addEventListener("click",()=>{stopped=true;report("Đang dừng...");});
$("vphoto").addEventListener("change",refresh);
const watch=setInterval(()=>{
 if(!document.documentElement.contains(root)){clearInterval(watch);return;}
 const id=lib.photoId(location.href);
 if(id&&id!==lastPhoto){lastPhoto=id;$("vphoto").value=id;refresh().catch(()=>{});}
},2000);
const startId=lib.photoId(location.href);
if(startId){$("vphoto").value=startId;lastPhoto=startId;}
refresh().catch(()=>report("Không đọc được bộ nhớ của extension."));
})();