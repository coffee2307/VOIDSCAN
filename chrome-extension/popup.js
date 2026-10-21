(() => {
"use strict";
const $=id=>document.getElementById(id);
const STORE="voidscan_reactions_v1", PHOTO_STORE="voidscan_photo_links_v1";
const COUNT_STORE="voidscan_visible_reaction_counts_v2";
const api=window.VoidscanAudit;
function status(s){$("status").textContent=s;}
async function rows(){
 const d=await chrome.storage.local.get(STORE);
 return api.dedupe(Array.isArray(d[STORE])?d[STORE]:[]);
}
async function refresh(){
 const all=await rows();
 $("records").textContent=all.length.toLocaleString("vi-VN");
 $("photos").textContent=new Set(all.map(x=>x.photoId)).size.toLocaleString("vi-VN");
 const review=window.VoidscanReview;
 if(review){const result=review.analyse(all,{});const stats=review.summary(result);
   $("screening-flagged").textContent=(stats.reviewFirst+stats.review).toLocaleString("vi-VN");
   $("screening-total").textContent=stats.total.toLocaleString("vi-VN");
 }
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
async function exportPhotos(){
 const result=await chrome.storage.local.get(PHOTO_STORE);
 const data=Array.isArray(result[PHOTO_STORE])?result[PHOTO_STORE]:[];
 if(!data.length){status("Chưa có ảnh được ghi. Mở album rồi bấm Lưu link ảnh.");return;}
 await download("VOIDSCAN_photos_"+stamp()+".csv",api.csv(data,["photoId","photoUrl"]),"text/csv;charset=utf-8");
}
async function exportData(mode){
 const all=await rows();
 if(!all.length){status("Chưa có dữ liệu reaction để xuất.");return;}
 const base="VOIDSCAN_reactions_"+stamp();
 if(mode==="json"){
   const counts=(await chrome.storage.local.get(COUNT_STORE))[COUNT_STORE]||{};
   const payload={schema_version:2,source:"facebook_visible_reaction_dialog",
     limitation:"May be partial. User metadata only when visible in current reaction list.",
     capturedAt:new Date().toISOString(),records:all,displayedCounts:counts};
   await download(base+".json",JSON.stringify(payload,null,2),"application/json;charset=utf-8");
 }else if(mode==="summary"){
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
   await download(base+".csv",api.csv(all,columns),"text/csv;charset=utf-8");
 }
}
function home(){
 $("home-view").hidden=false;
 $("fields-view").hidden=true;
 status("Home · Sẵn sàng.");
}
$("home").addEventListener("click",home);
$("screening").addEventListener("click",async()=>{
 try{await chrome.tabs.create({url:chrome.runtime.getURL("review.html")});}
 catch{status("Không mở được trang sàng lọc.");}
});
$("details").addEventListener("click",()=>{$("home-view").hidden=true;$("fields-view").hidden=false;});
$("back").addEventListener("click",home);
$("activate").addEventListener("click",()=>activate().catch(()=>status("Không mở được bảng thu thập. Tải lại tab Facebook.")));
for(const type of ["csv","summary","json"]){
 $(type).addEventListener("click",()=>exportData(type).catch(()=>status("Lỗi xuất tệp. Hãy kiểm tra quyền tải xuống.")));
}
$("photo-links").addEventListener("click",()=>exportPhotos().catch(()=>status("Không xuất được danh sách ảnh.")));
$("clear").addEventListener("click",async()=>{
 if(!confirm("Xóa toàn bộ dữ liệu reaction, số hiển thị và link ảnh trên Chrome?"))return;
 await chrome.storage.local.remove([STORE,PHOTO_STORE,COUNT_STORE]);
 await refresh();
 status("Đã xóa dữ liệu cục bộ.");
});
chrome.storage.onChanged.addListener((changes,area)=>{
 if(area==="local"&&changes[STORE])refresh().catch(()=>{});
});
refresh().catch(()=>status("Không đọc được dữ liệu cục bộ."));
})();