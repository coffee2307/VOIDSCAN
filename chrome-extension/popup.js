(() => {
"use strict";
const $=id=>document.getElementById(id);
const STORE="voidscan_reactions_v1", PHOTO_STORE="voidscan_photo_links_v1";
const COUNT_STORE="voidscan_visible_reaction_counts_v2";
const PENDING_STORE="voidscan_pending_reactions_v1";
const ACTIVE_PHOTO_STORE="voidscan_active_photo_v1";
const PROFILE_STORE="voidscan_profile_observations_v1",ATTEMPT_STORE="voidscan_public_metadata_attempts_v1";
let manualScope=null;
const api=window.VoidscanAudit;
function status(s){$("status").textContent=s;}
async function rows(){
 const d=await chrome.storage.local.get(STORE);
 return api.dedupe(Array.isArray(d[STORE])?d[STORE]:[]);
}
async function refresh(){
 const all=await rows();
 const storage=await chrome.storage.local.get([PENDING_STORE,ACTIVE_PHOTO_STORE]);
 const pendingValue=storage[PENDING_STORE];
 const pending=Array.isArray(pendingValue)?pendingValue:[];
 const photos=api.photoCounts([...all,...pending]);
 const chooser=$("photo-scope"),previous=manualScope??"";
 const active=String(storage[ACTIVE_PHOTO_STORE]||"");
 const preferred=previous||((photos.some(x=>x.photoId===active)&&active)||photos.at(-1)?.photoId||"all");
 chooser.replaceChildren();
 const make=(value,label)=>{const op=document.createElement("option");op.value=value;op.textContent=label;chooser.append(op);};
 for(const item of photos)make(item.photoId,"Ảnh "+item.photoId+" · "+item.count+" URL");
 make("all","Tất cả ảnh (tổng hợp toàn cuộc thi)");
 const scope=photos.some(x=>x.photoId===preferred)||preferred==="all"?preferred:(photos.at(-1)?.photoId||"all");
 chooser.value=scope;
 const scoped=api.scopedRows(all,scope);
 const unknown=api.scopedRows(pending,scope);
 $("pending-count").textContent=unknown.length.toLocaleString("vi-VN");
 $("records").textContent=scoped.length.toLocaleString("vi-VN");
 $("photos").textContent=(scope==="all"?photos.length:photos.length?1:0).toLocaleString("vi-VN");
 $("scope-note").textContent=scope==="all"?
  "Đang xem TẤT CẢ ảnh. Dữ liệu sẽ cộng gộp; chọn từng ảnh để xuất riêng.":
  "Chỉ đang xem và xuất dữ liệu của ảnh "+scope+"; các ảnh khác được giữ nguyên, không gộp.";
 const rawProfiles=(await chrome.storage.local.get(PROFILE_STORE))[PROFILE_STORE]||{};
 const reviewed=window.VoidscanProfileImport.enrich([...scoped,...unknown],Object.values(rawProfiles)).rows;
 const analysis=window.VoidscanFileAudit.prepare(reviewed);
 const scores=analysis.profiles.map(p=>window.VoidscanFileAudit.scoreProfile(p,analysis.photoTotal,{}));
 $("screening-flagged").textContent=scores.filter(x=>x.status===window.VoidscanFileAudit.LABEL_SUSPECT).length.toLocaleString("vi-VN");
 $("screening-insufficient").textContent=scores.filter(x=>x.status===window.VoidscanFileAudit.LABEL_INSUFFICIENT).length.toLocaleString("vi-VN");
 $("screening-total").textContent=scores.length.toLocaleString("vi-VN");
}
async function download(name,data,type){
 const blob=new Blob([data],{type});
 const url=URL.createObjectURL(blob);
 try{
   await chrome.downloads.download({url,filename:name,saveAs:true,conflictAction:"uniquify"});
   status("Đã gửi yêu cầu lưu tệp xuống máy.");
 }finally{setTimeout(()=>URL.revokeObjectURL(url),30000);}
}
const stamp=()=>new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);
async function activate(){
 const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
 if(!tab||!api.fbUrl(tab.url)){status("Bạn cần mở tab Facebook trước.");return;}
 await chrome.scripting.executeScript({target:{tabId:tab.id},files:["lib.js","content.js"]});
 status("Đã mở bảng kéo thả trên Facebook. Có nút Home và CSV ngay trong bảng.");
}
async function captureCurrentProfile(){
 const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
 if(!tab?.id||!api.profileMeta(tab.url||"")){
   status("Hãy mở trang cá nhân Facebook cần kiểm tra, rồi nhấn nút này.");
   return;
 }
 await chrome.scripting.executeScript({target:{tabId:tab.id},files:["lib.js","profile-capture.js"]});
 const value=await chrome.scripting.executeScript({
   target:{tabId:tab.id},func:()=>window.VoidscanCaptureCurrentProfile()
 });
 const response=value?.[0]?.result||{};
 status(response.saved?
   "Đã lưu quan sát trên hồ sơ đang mở: avatar "+(response.hasAvatar?"có":"chưa rõ")+
   "; địa điểm "+(response.hasCurrentCity?"có":"chưa rõ")+
   ". Mở lại trang kiểm toán để cập nhật.":
   response.reason||"Trang Facebook chưa có dữ liệu công khai đọc được.");
}
async function exportPhotos(){
 const result=await chrome.storage.local.get(PHOTO_STORE);
 const data=Array.isArray(result[PHOTO_STORE])?result[PHOTO_STORE]:[];
 if(!data.length){status("Chưa có ảnh được ghi. Mở album rồi bấm Lưu link ảnh.");return;}
 await download("VOIDSCAN_photos_"+stamp()+".csv",api.csv(data,["photoId","photoUrl"]),"text/csv;charset=utf-8");
}
async function exportData(mode){
 const photo=$("photo-scope").value;
 if(!photo){status("Chưa chọn Photo ID.");return;}
 const all=api.scopedRows(await rows(),photo);
 const raw=(await chrome.storage.local.get(PENDING_STORE))[PENDING_STORE];
 const known=new Set(all.map(r=>r.photoId+"|"+r.profileUrl));
 const pending=api.scopedRows((Array.isArray(raw)?raw:[]),photo).filter(r=>!known.has(r.photoId+"|"+r.profileUrl));
 if(!all.length&&!pending.length){status("Ảnh này chưa có URL để xuất.");return;}
 const base="VOIDSCAN_"+(photo==="all"?"ALL_PHOTOS":"PHOTO_"+photo)+"_reactions_"+stamp();
 if(mode==="json"){
   const counts=(await chrome.storage.local.get(COUNT_STORE))[COUNT_STORE]||{};
   const payload={schema_version:2,source:"facebook_visible_reaction_dialog",
     limitation:"May be partial. User metadata only when visible in current reaction list.",
     capturedAt:new Date().toISOString(),photoScope:photo,records:all,unclassifiedRecords:pending,displayedCounts:photo==="all"?counts:{[photo]:counts[photo]||{}}};
   await download(base+".json",JSON.stringify(payload,null,2),"application/json;charset=utf-8");
 }else if(mode==="summary"){
   if(!all.length){status("Chỉ có URL chưa rõ cảm xúc; chưa thể tính bảng điểm reaction.");return;}
   const summary=api.aggregate(all);
   const display=(await chrome.storage.local.get(COUNT_STORE))[COUNT_STORE]||{};
   for(const row of summary){
     const listed=display[row.photoId]||{};
     for(const kind of api.types){
       row[kind+"_displayed"]=listed[kind]?.displayedCount??"";
     }
     row.completeness="PARTIAL_UNLESS_VERIFIED";
   }
   const cols=["photoId","photoUrl","LIKE","LOVE","CARE","HAHA","WOW",
     "LIKE_displayed","LOVE_displayed","CARE_displayed","HAHA_displayed","WOW_displayed",
     "observedRows","points_observed","completeness"];
   await download(base+"_summary.csv",api.csv(summary,cols),"text/csv;charset=utf-8");
 }else{
   const columns=["photoId","photoUrl","profileUrl","userId","username",
     "displayName","reaction","avatarUrl","friendshipStatus","subscribeStatus",
     "mutualFriendsNumber","capturedAt"];
   await download(base+".csv",api.csv([...all,...pending],columns),"text/csv;charset=utf-8");
 }
}
function home(){
 $("home-view").hidden=false;
 $("fields-view").hidden=true;
 status("Home · Sẵn sàng.");
}
$("home").addEventListener("click",home);
$("photo-scope").addEventListener("change",()=>{
 manualScope=$("photo-scope").value;
 refresh().catch(()=>status("Lỗi hiển thị phạm vi ảnh."));
});
$("screening").addEventListener("click",async()=>{
 try{await chrome.tabs.create({url:chrome.runtime.getURL("review.html")});}
 catch{status("Không mở được trang sàng lọc.");}
});
$("capture-profile").addEventListener("click",()=>captureCurrentProfile().catch(e=>status("Không ghi nhận được hồ sơ: "+e.message)));
$("details").addEventListener("click",()=>{$("home-view").hidden=true;$("fields-view").hidden=false;});
$("back").addEventListener("click",home);
$("activate").addEventListener("click",()=>activate().catch(()=>status("Không mở được bảng thu thập. Tải lại tab Facebook.")));
for(const type of ["csv","summary","json"]){
 $(type).addEventListener("click",()=>exportData(type).catch(()=>status("Lỗi xuất tệp. Hãy kiểm tra quyền tải xuống.")));
}
$("photo-links").addEventListener("click",()=>exportPhotos().catch(()=>status("Không xuất được danh sách ảnh.")));
$("clear").addEventListener("click",async()=>{
 if(!confirm("Xóa toàn bộ dữ liệu reaction, link ảnh và hồ sơ đã ghi nhận trên Chrome?"))return;
 await chrome.storage.local.remove([STORE,PHOTO_STORE,COUNT_STORE,PENDING_STORE,PROFILE_STORE,ATTEMPT_STORE]);
 await refresh();
 status("Đã xóa dữ liệu cục bộ.");
});
chrome.storage.onChanged.addListener((changes,area)=>{
 if(area==="local"&&(changes[STORE]||changes[PENDING_STORE]||changes[ACTIVE_PHOTO_STORE]||changes[PROFILE_STORE]))refresh().catch(()=>{});
});
refresh().catch(()=>status("Không đọc được dữ liệu cục bộ."));
})();