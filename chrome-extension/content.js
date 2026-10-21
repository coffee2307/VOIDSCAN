(() => {
"use strict";
const lib=window.VoidscanAudit;
if(window.__voidscanAuditActive||!lib)return;
window.__voidscanAuditActive=true;
const STORE="voidscan_reactions_v1";
const PHOTO_STORE="voidscan_photo_links_v1";
const COUNT_STORE="voidscan_visible_reaction_counts_v2";
const PENDING_STORE="voidscan_pending_reactions_v1";
const MAX_STEPS=180,WAIT_MS=850,MAX_RUN_MS=10*60*1000;
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const root=document.createElement("div");
root.id="voidscan-reaction-audit-root";
root.style.cssText="position:fixed;right:16px;top:85px;z-index:2147483646";
const shadow=root.attachShadow({mode:"open"});
const style=document.createElement("style");
style.textContent=[
"*{box-sizing:border-box}.panel{width:370px;max-width:calc(100vw - 20px);max-height:calc(100vh - 18px);overflow:auto;background:white;color:#1d2a42;font:13px system-ui,Segoe UI,sans-serif;border:1px solid #cad5e8;border-radius:15px;box-shadow:0 14px 45px #0a193c66}",
"header{background:#192c50;color:white;padding:12px 13px;display:flex;align-items:center;gap:7px;cursor:grab;touch-action:none}header:active{cursor:grabbing}header strong{font-size:15px;flex:1;pointer-events:none}",
"button{font:inherit;cursor:pointer;padding:8px 10px;border:1px solid #d2dced;background:white;color:#20395f;border-radius:8px;font-weight:650}button:hover{background:#eef3fe}button:disabled{opacity:.45;cursor:not-allowed}",
"header button{padding:5px 8px;border:1px solid #7184a7;background:#ffffff16;color:#fff;cursor:pointer;touch-action:auto}header button:hover{background:#ffffff33}",
"main{padding:12px 13px}h3{font-size:13px;margin:0 0 8px}.info{padding:10px;border-radius:9px;background:#f0f4fb;color:#426080;line-height:1.55;margin:9px 0}.small{font-size:11px;line-height:1.55;color:#61728d}",
".metrics{display:flex;gap:8px;margin:10px 0}.metrics>div{flex:1;background:#f4f6fb;border:1px solid #e3e9f1;border-radius:10px;padding:10px;font-size:11px;color:#64748b}.metrics strong{display:block;color:#182e51;font-size:23px}",
".actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:10px 0}.actions .primary{grid-column:1/-1;background:#315eb9;border:0;color:white}",
"label{display:block;font-size:12px;margin:10px 0 5px}input{width:100%;font:inherit;border:1px solid #cdd8e9;border-radius:8px;padding:8px}",
"#vstatus{font-size:12px;color:#315c94;line-height:1.6;min-height:25px;white-space:pre-wrap}.hidden{display:none}.progress{height:6px;background:#e4ebf4;border-radius:5px;overflow:hidden}.progress div{height:100%;background:#3e72dd;width:0;transition:width .2s}",
"button:focus-visible,input:focus-visible{outline:2px solid #4178de;outline-offset:2px}"
].join("");
const panel=document.createElement("section");panel.className="panel";
panel.innerHTML=[
'<header id="vdrag"><strong>VOIDSCAN · REACTIONS</strong><button id="vhome" title="Home" type="button">⌂</button><button id="vcsv" title="Xuất CSV" type="button">CSV</button><button id="vmin" title="Thu nhỏ" type="button">−</button><button id="vclose" title="Đóng" type="button">×</button></header>',
'<main id="vmain"><h3 id="vheading">Thu thập reaction tự động</h3>',
'<div class="info">Mở ảnh Facebook, nhấn vào <b>số lượt cảm xúc</b> để hiện danh sách. Bấm <b>Quét tất cả cảm xúc</b>: extension tự chuyển từng tab và cuộn.</div>',
'<label for="vphoto">Photo ID (tự nhận khi mở ảnh riêng)</label><input id="vphoto" inputmode="numeric" placeholder="Photo ID từ URL ảnh" maxlength="30">',
'<div class="actions"><button id="vauto" class="primary">Quét tự động cả 5 loại cảm xúc</button><button id="vcurrent">Quét tab đang mở</button><button id="vlinks">Lưu link ảnh album</button><button id="vstop">Dừng quét</button><button id="vexport">Xuất CSV</button><button id="vdiag">Kiểm tra nhận diện</button></div>',
'<div class="progress"><div id="vbar"></div></div>',
'<div class="metrics"><div><strong id="vcount">0</strong>Đã phân loại</div><div><strong id="vall">0</strong>Tổng hợp lệ</div><div><strong id="vpending">0</strong>Chưa rõ loại</div></div>',
'<p id="vstatus" role="status">Đã sẵn sàng.</p>',
'<p class="small">User ID, username, avatar, trạng thái bạn bè/theo dõi và số bạn chung chỉ lấy khi hiển thị ngay trong danh sách. Không tự truy cập trang cá nhân. Giới hạn quét 10 phút/lượt.</p></main>'
].join("");
shadow.append(style,panel);
document.documentElement.appendChild(root);
const $=id=>shadow.getElementById(id);
let running=false,stopped=false,minimized=false,lastPhoto="",saving=Promise.resolve();
const report=message=>{$("vstatus").textContent=message;};
const progress=x=>{$("vbar").style.width=Math.max(0,Math.min(100,x))+"%";};
const iso=()=>new Date().toISOString();
const imageUrl=id=>"https://www.facebook.com/photo/?fbid="+id;
function currentPhoto(){
 const fromUrl=lib.photoId(location.href);
 if(fromUrl&&document.activeElement!==$("vphoto"))$("vphoto").value=fromUrl;
 const value=$("vphoto").value.trim();
 return /^\d{5,30}$/.test(value)?value:null;
}
async function dataRows(){
 const data=(await chrome.storage.local.get(STORE))[STORE];
 return Array.isArray(data)?data:[];
}
async function updateMetrics(){
 const all=await dataRows(),id=currentPhoto();
 $("vcount").textContent=all.filter(r=>r.photoId===id).length.toLocaleString("vi-VN");
 $("vall").textContent=all.length.toLocaleString("vi-VN");
 const unclassified=(await chrome.storage.local.get(PENDING_STORE))[PENDING_STORE]||[];
 $("vpending").textContent=unclassified.length.toLocaleString("vi-VN");
}
function dialogInfo(){
 const boxes=[...document.querySelectorAll('[role="dialog"]')].filter(d=>{
  const r=d.getBoundingClientRect();
  return r.width>180&&r.height>180&&!root.contains(d);
 });
 const ranked=boxes.map(dialog=>{
  const text=((dialog.getAttribute("aria-label")||"")+" "+(dialog.innerText||"").slice(0,260)).toLowerCase();
  const profiles=[...dialog.querySelectorAll("a[href]")].filter(a=>lib.normalizeProfile(a.href)).length;
  const tabs=dialog.querySelectorAll('[role="tab"],[aria-selected]').length;
  const hasKeyword=/reaction|cảm xúc|người đã|thích|thương thương|love|haha|wow|like/.test(text);
  return {dialog,score:profiles+tabs*3+(hasKeyword?5:0),valid:tabs>0||(hasKeyword&&profiles>0)};
 });
 return ranked.filter(r=>r.valid).sort((a,b)=>b.score-a.score)[0]?.dialog||null;
}
function candidates(dialog){
 // Facebook may put role="tab" on the button OR on a wrapper.
 // Limit candidates to the tab/header region; never click profile actions.
 const top=dialog.getBoundingClientRect().top;
 const selector='[role="tab"],[role="tablist"] button,[role="tablist"] [role="button"],[role="tablist"] [aria-label],[aria-selected]';
 const all=[...dialog.querySelectorAll(selector)]
  .filter((el,i,array)=>array.indexOf(el)===i&&el.getClientRects().length>0&&
    el.getBoundingClientRect().top<top+Math.min(330,dialog.clientHeight*.60)&&
    !el.closest('[role="listitem"],li'));
 return all.map(el=>{
   const children=[...el.querySelectorAll('img[alt],svg[aria-label],[role="img"][aria-label]')].slice(0,5);
   const labels=[el.getAttribute("aria-label")||"",el.getAttribute("title")||"",
    el.getAttribute("data-tooltip-content")||"",(el.innerText||"").slice(0,90),
    ...children.map(x=>x.getAttribute("alt")||x.getAttribute("aria-label")||"")];
   const kind=labels.map(label=>lib.reactionFromLabel(label)).find(Boolean)||null;
   const selected=el.getAttribute("aria-selected")==="true"||
    el.getAttribute("aria-pressed")==="true"||el.getAttribute("aria-current")==="true"||
    el.getAttribute("data-state")==="active"||
    !!el.querySelector('[aria-selected="true"],[aria-pressed="true"],[data-state="active"]');
   return {el,kind,selected,label:labels.join(" ")};
 }).filter(x=>x.kind);
}
function rowContainer(anchor,dialog){
 let cur=anchor;
 for(let i=0;i<6&&cur&&cur!==dialog;i++,cur=cur.parentElement){
  if(cur.getAttribute("role")==="listitem"||cur.tagName==="LI")return cur;
  if(i>=2){
    const profiles=[...cur.querySelectorAll("a[href]")].filter(a=>lib.normalizeProfile(a.href));
    const text=(cur.innerText||"");
    if(profiles.length===1&&text.length<380&&(cur.querySelector("img")||i>=4))return cur;
  }
 }
 return anchor.parentElement||anchor;
}
function visibleCards(dialog){
 const found=new Map();
 for(const anchor of dialog.querySelectorAll("a[href]")){
  const meta=lib.profileMeta(anchor.href);
  if(!meta||!anchor.getClientRects().length)continue;
  const box=anchor.getBoundingClientRect();
  if(box.width===0||box.height===0)continue;
  const row=rowContainer(anchor,dialog);
  const text=(row.innerText||"").slice(0,380);
  const named=[...row.querySelectorAll("img[alt],svg[aria-label]")].slice(0,15).map(node=>({
    node,kind:lib.reactionFromLabel(node.getAttribute("alt")||node.getAttribute("aria-label")||"")
  }));
  const reactionIcon=named.find(v=>{
    if(!v.kind)return false;
    const dim=v.node.getBoundingClientRect();
    return dim.width>0&&dim.width<=42&&dim.height>0&&dim.height<=42;
  });
  const img=[...row.querySelectorAll("img[src]")].find(el=>{
    const dim=el.getBoundingClientRect();
    return dim.width>=30&&dim.height>=30&&dim.width<=160&&dim.height<=160&&lib.avatarUrl(el.src);
  });
  const friend=/(?:\bfriends?\b|bạn bè)/i.test(text)
     ? (/(?:thêm bạn bè|add friend|kết bạn)/i.test(text)?"not_friend":"friends") : "";
  const following=/(?:đang theo dõi|following)/i.test(text)?"following":
     (/(?:^|\s)(?:theo dõi|follow)(?:\s|$)/i.test(text)?"not_following":"");
  const mutualMatch=text.match(/(\d+(?:[.,]\d+)?)\s*(?:bạn chung|mutual friends?)/i);
  const mutual=mutualMatch?Number(mutualMatch[1].replace(/[.,]/g,"")):null;
  const displayName=(anchor.innerText||"").trim().replace(/\s+/g," ").slice(0,120);
  found.set(meta.profileUrl,{...meta,displayName,
    avatarUrl:img?lib.avatarUrl(img.src):"",friendshipStatus:friend,subscribeStatus:following,
    mutualFriendsNumber:Number.isInteger(mutual)?mutual:null,
    reactionIcon:reactionIcon?.kind||null});
 }
 return [...found.values()];
}
function scrollElement(dialog){
 return [dialog,...dialog.querySelectorAll("*")].filter(node=>{
  if(node.clientHeight<70||node.scrollHeight-node.clientHeight<70)return false;
  const rect=node.getBoundingClientRect();
  if(rect.width<70||rect.height<70)return false;
  return ["auto","scroll"].includes(getComputedStyle(node).overflowY)||
    node.getAttribute("role")==="list"||node===dialog;
 }).sort((a,b)=>{
   const count=el=>[...el.querySelectorAll("a[href]")].filter(x=>lib.normalizeProfile(x.href)).length;
   return count(b)-count(a)||((b.scrollHeight-b.clientHeight)-(a.scrollHeight-a.clientHeight));
 })[0]||null;
}
function selectedType(dialog){
 const selected=candidates(dialog).filter(x=>x.selected);
 return selected.length===1?selected[0].kind:null;
}
async function saveCards(id,mode,cards){
 saving=saving.catch(()=>{}).then(async()=>{
  const all=await dataRows();
  const raw=(await chrome.storage.local.get(PENDING_STORE))[PENDING_STORE];
  const pending=Array.isArray(raw)?raw:[];
  const index=new Map(all.map((r,i)=>[r.photoId+"|"+r.profileUrl,i]));
  const pendingKeys=new Set(pending.map(r=>r.photoId+"|"+r.profileUrl));
  let added=0,skipped=0,changed=false;
  for(const card of cards){
    // A confirmed single-reaction tab is more reliable than decorative icons.
    const type=lib.cleanReaction(mode)||lib.cleanReaction(card.reactionIcon);
    const key=id+"|"+card.profileUrl;
    if(!type){
      if(!index.has(key)&&!pendingKeys.has(key)){
        pending.push({photoId:id,photoUrl:imageUrl(id),profileUrl:card.profileUrl,
          userId:card.userId,username:card.username,displayName:card.displayName,
          reaction:"UNKNOWN",capturedAt:iso()});
        pendingKeys.add(key);skipped++;
      }
      continue;
    }
    const rec={photoId:id,photoUrl:imageUrl(id),profileUrl:card.profileUrl,userId:card.userId,
      username:card.username,displayName:card.displayName,avatarUrl:card.avatarUrl,
      friendshipStatus:card.friendshipStatus,subscribeStatus:card.subscribeStatus,
      mutualFriendsNumber:card.mutualFriendsNumber,reaction:type,capturedAt:iso()};
    const ix=index.get(key);
    if(ix===undefined){index.set(key,all.length);all.push(rec);added++;changed=true;}
    else {
      const old=all[ix];
      const merged={...old,...Object.fromEntries(Object.entries(rec).filter(([k,v])=>
        k==="reaction"||k==="capturedAt"||(v!==""&&v!==null&&v!==undefined)))};
      all[ix]=merged;changed=true;
    }
  }
  const retained=pending.filter(r=>!index.has(r.photoId+"|"+r.profileUrl));
  if(changed||skipped||retained.length!==pending.length){
    await chrome.storage.local.set({[STORE]:all,[PENDING_STORE]:retained});
  }
  return {added,skipped};
 });
 return saving;
}
async function saveDisplayedCount(photo,type,label){
 const match=String(label||"").match(/(\d[\d.,]*\s*[kKmM]?)/);
 const count=match?lib.parseCount(match[1]):null;
 if(count===null)return;
 const storage=(await chrome.storage.local.get(COUNT_STORE))[COUNT_STORE]||{};
 const prev=storage[photo]||{};
 prev[type]={displayedCount:count,recordedAt:iso(),basis:"visible_facebook_reaction_tab"};
 storage[photo]=prev;
 await chrome.storage.local.set({[COUNT_STORE]:storage});
}
async function snapshot(dialog,mode){
 const id=currentPhoto();
 if(!id)throw Error("Không nhận được Photo ID. Hãy mở ảnh riêng.");
 const cards=visibleCards(dialog);
 if(!cards.length)return {added:0,shown:0,skipped:0};
 const result=await saveCards(id,mode,cards);
 await updateMetrics();
 return {...result,shown:cards.length};
}
async function runType(type,tab,start,id){
 if(stopped)return {added:0,steps:0,skipped:0};
 let beforeSignature="";
 if(tab){
   const prior=dialogInfo();
   beforeSignature=prior?visibleCards(prior).map(x=>x.profileUrl).sort().slice(0,25).join("|"):"";
   tab.el.click();
   await delay(1100);
 }
 const dialog=dialogInfo();
 if(!dialog)throw Error("Hộp thoại reaction đã đóng hoặc không tải được.");
 const selected=selectedType(dialog);
 // Facebook sometimes updates the visible list but omits aria-selected.
 // A verified change of profile rows after a specific tab click is supporting
 // evidence; never infer type from the "All" list or a failed click.
 const afterSignature=tab?visibleCards(dialog).map(x=>x.profileUrl).sort().slice(0,25).join("|"):"";
 const changed=Boolean(tab&&beforeSignature&&afterSignature&&beforeSignature!==afterSignature);
 const mode=tab?(selected===type||(!selected&&changed)?type:null):selected;
 if(tab&&!mode){
   report("Facebook chưa xác nhận tab "+type+" đã chuyển. URL sẽ được lưu riêng dạng chưa phân loại.");
 }
 const activeTab=candidates(dialog).find(x=>x.selected&&x.kind===type);
 if(mode&&activeTab)await saveDisplayedCount(id,mode,activeTab.label);
 const scroll=scrollElement(dialog);
 if(scroll)scroll.scrollTop=0;
 let added=0,skipped=0,steps=0,idle=0,lastTop=-1;
 for(let i=0;i<MAX_STEPS&&!stopped;i++){
   if(Date.now()-start>MAX_RUN_MS){report("Dừng vì đạt giới hạn 10 phút.");break;}
   const live=dialogInfo();
   if(!live||currentPhoto()!==id)break;
   const result=await snapshot(live,mode);
   added+=result.added;
   skipped+=result.skipped;
   steps++;
   const sc=scrollElement(live);
   if(!sc){idle++;if(idle>=4)break;await delay(WAIT_MS);continue;}
   const before=sc.scrollTop;
   sc.scrollTop=Math.min(sc.scrollHeight,sc.scrollTop+Math.max(280,Math.round(sc.clientHeight*.73)));
   const reachedBottom=sc.scrollTop>=sc.scrollHeight-sc.clientHeight-4;
   if(result.added===0&&(reachedBottom||sc.scrollTop<=before+1||sc.scrollTop===lastTop))idle++;
   else idle=0;
   lastTop=sc.scrollTop;
   report("Đang quét "+(type||"All")+" · "+steps+" lượt cuộn · "+added+" hồ sơ mới"+
    (skipped?" · "+skipped+" không rõ loại":""));
   progress(100*Math.min(steps/MAX_STEPS,1));
   if(idle>=5)break;
   await delay(WAIT_MS);
 }
 const last=dialogInfo();
 if(last&&!stopped&&currentPhoto()===id)added+=(await snapshot(last,mode)).added;
 return {added,skipped,steps};
}
async function beginScan(allTypes){
 if(running)return;
 const id=currentPhoto();
 if(!id){report("Hãy mở ảnh riêng hoặc nhập đúng Photo ID.");return;}
 const dialog=dialogInfo();
 if(!dialog){report("Hãy mở danh sách reaction của ảnh trên Facebook trước.");return;}
 running=true;stopped=false;lastPhoto=id;
 $("vauto").disabled=true;$("vcurrent").disabled=true;$("vphoto").disabled=true;
 const start=Date.now();let total=0,attempted=0;
 try{
   if(allTypes){
     const detected=candidates(dialog).filter(x=>lib.types.includes(x.kind));
     if(!detected.length){
       const result=await runType(null,null,start,id);
       total+=result.added;
       report("Danh sách chung: "+result.added+" reaction được phân loại; "+result.skipped+
         " URL mới chờ xác định loại. Không đếm lặp khi cuộn. Nếu không thấy 5 tab cảm xúc, bấm Kiểm tra nhận diện.");
     }else{
       for(const type of lib.types){
         if(stopped)break;
         const live=dialogInfo();
         if(!live)break;
         const tab=candidates(live).find(x=>x.kind===type);
         if(!tab)continue;
         const result=await runType(type,tab,start,id);
         total+=result.added;attempted++;
         progress(attempted/lib.types.length*100);
       }
       report((stopped?"Đã dừng. ":"Đã hoàn tất các tab có thể đọc. ")+
         "Thu được "+total+" hồ sơ mới. Danh sách có thể chưa đầy đủ.");
     }
   }else{
     const result=await runType(selectedType(dialog),null,start,id);
     total=result.added;
     report((stopped?"Đã dừng. ":"Đã hoàn thành tab. ")+total+" hồ sơ mới"+
       (result.skipped?"; đã lưu "+result.skipped+" URL chưa rõ loại (không đếm lặp).":""));
   }
 }catch(e){report("Lỗi thu thập: "+(e.message||"không rõ"));}
 finally{
   running=false;stopped=false;
   $("vauto").disabled=false;$("vcurrent").disabled=false;$("vphoto").disabled=false;
   await updateMetrics();progress(0);
 }
}
async function recordPhotoLinks(){
 const raw=(await chrome.storage.local.get(PHOTO_STORE))[PHOTO_STORE];
 const urls=new Map((Array.isArray(raw)?raw:[]).map(x=>[x.photoId,x]));
 let added=0;
 for(const a of document.querySelectorAll("a[href]")){
  const u=lib.fbUrl(a.href),id=lib.photoId(a.href);
  if(!u||!id||(u.searchParams.get("set")||"").startsWith("pcb.")===false)continue;
  if(!urls.has(id))added++;
  urls.set(id,{photoId:id,photoUrl:imageUrl(id)});
 }
 await chrome.storage.local.set({[PHOTO_STORE]:[...urls.values()]});
 report("Đã thêm "+added+" link ảnh; tổng "+urls.size+
   ". Hãy mở rộng album nếu còn ảnh ẩn.");
}
async function exportCSV(){
 const records=lib.dedupe(await dataRows());
 const raw=(await chrome.storage.local.get(PENDING_STORE))[PENDING_STORE];
 const existing=new Set(records.map(r=>r.photoId+"|"+r.profileUrl));
 const pending=(Array.isArray(raw)?raw:[]).filter(r=>!existing.has(r.photoId+"|"+r.profileUrl));
 if(!records.length&&!pending.length){report("Chưa có URL để xuất.");return;}
 const columns=["photoId","photoUrl","profileUrl","userId","username","displayName",
  "reaction","avatarUrl","friendshipStatus","subscribeStatus","mutualFriendsNumber","capturedAt"];
 const csv=lib.csv([...records,...pending],columns);
 const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});
 const url=URL.createObjectURL(blob);
 const anchor=document.createElement("a");
 anchor.href=url;anchor.download="VOIDSCAN_reactions_"+iso().replace(/[:.]/g,"-").slice(0,19)+".csv";
 root.appendChild(anchor);anchor.click();anchor.remove();
 setTimeout(()=>URL.revokeObjectURL(url),30000);
 report("Đã xuất "+records.length+" reaction xác định và "+pending.length+" URL chưa rõ cảm xúc.");
}
function home(){
 if(minimized){$("vmain").classList.remove("hidden");minimized=false;}
 $("vheading").textContent="Thu thập reaction tự động";
 report("Home · Sẵn sàng.");
}
function diagnostic(){
 const dialog=dialogInfo();
 if(!dialog){report("Không tìm thấy hộp thoại reaction. Hãy bấm vào số cảm xúc của ảnh.");return;}
 const tabs=candidates(dialog),rows=visibleCards(dialog);
 const selected=selectedType(dialog)||"Không rõ / Tất cả";
 const icons=rows.filter(x=>x.reactionIcon).length;
 report("Chẩn đoán: "+tabs.length+" tab có tên cảm xúc, tab chọn: "+selected+
   ", "+rows.length+" URL đang hiển thị, "+icons+" biểu tượng nhận dạng được. "+
   (tabs.length===0&&icons===0?"Facebook không hiển thị dấu hiệu phân loại; URL sẽ lưu dạng UNKNOWN. Hãy gửi ảnh chụp thanh tab cảm xúc để điều chỉnh.":"Hãy chọn Quét tự động cả 5 loại cảm xúc."));
}
$("vdiag").addEventListener("click",diagnostic);
$("vauto").addEventListener("click",()=>beginScan(true));
$("vcurrent").addEventListener("click",()=>beginScan(false));
$("vlinks").addEventListener("click",()=>recordPhotoLinks().catch(()=>report("Không lưu được link ảnh.")));
$("vstop").addEventListener("click",()=>{stopped=true;report("Đang dừng sau bước hiện tại...");});
$("vexport").addEventListener("click",()=>exportCSV().catch(()=>report("Xuất CSV thất bại.")));
$("vcsv").addEventListener("click",()=>exportCSV().catch(()=>report("Xuất CSV thất bại.")));
$("vhome").addEventListener("click",home);
$("vmin").addEventListener("click",()=>{
 minimized=!minimized;
 $("vmain").classList.toggle("hidden",minimized);
});
$("vclose").addEventListener("click",()=>{
 stopped=true;
 root.remove();
 window.__voidscanAuditActive=false;
});
$("vphoto").addEventListener("change",()=>updateMetrics().catch(()=>{}));
// The browser-action popup cannot be dragged; the panel IN THE FACEBOOK PAGE
// can be freely repositioned by dragging its title bar.
const handle=$("vdrag");
let gesture=null;
handle.addEventListener("pointerdown",event=>{
 if(event.button!==0||event.target.closest("button"))return;
 const rect=root.getBoundingClientRect();
 gesture={pointerId:event.pointerId,dx:event.clientX-rect.left,dy:event.clientY-rect.top};
 root.style.left=rect.left+"px";root.style.top=rect.top+"px";root.style.right="auto";
 handle.setPointerCapture(event.pointerId);
 event.preventDefault();
});
handle.addEventListener("pointermove",event=>{
 if(!gesture||gesture.pointerId!==event.pointerId)return;
 const width=root.getBoundingClientRect().width;
 const height=root.getBoundingClientRect().height;
 const x=Math.max(0,Math.min(innerWidth-width,event.clientX-gesture.dx));
 const y=Math.max(0,Math.min(innerHeight-Math.min(height,65),event.clientY-gesture.dy));
 root.style.left=x+"px";root.style.top=y+"px";
});
function stopDrag(event){
 if(gesture&&gesture.pointerId===event.pointerId)gesture=null;
}
handle.addEventListener("pointerup",stopDrag);
handle.addEventListener("pointercancel",stopDrag);
const watcher=setInterval(()=>{
 if(!document.documentElement.contains(root)){clearInterval(watcher);return;}
 const id=lib.photoId(location.href);
 if(id&&id!==lastPhoto&&!running){
   lastPhoto=id;$("vphoto").value=id;updateMetrics().catch(()=>{});
 }
},1300);
const initial=lib.photoId(location.href);
if(initial){lastPhoto=initial;$("vphoto").value=initial;}
updateMetrics().catch(()=>report("Không đọc được bộ nhớ extension."));
})();
