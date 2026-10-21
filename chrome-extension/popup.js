(() => {
"use strict";
const $=id=>document.getElementById(id);
const STORE="voidscan_reactions_v1";
const PHOTO_STORE="voidscan_photo_links_v1";
const setStatus=text=>{$("status").textContent=text;};
const api=window.VoidscanAudit;

async function fetchRows(){
  const data=await chrome.storage.local.get(STORE);
  return Array.isArray(data[STORE])?data[STORE]:[];
}
async function refresh(){
  const rows=await fetchRows();
  $("records").textContent=rows.length.toLocaleString("vi-VN");
  $("photos").textContent=new Set(rows.map(r=>r.photoId)).size.toLocaleString("vi-VN");
}
async function saveDownload(filename,text,mime){
  const blob=new Blob([text],{type:mime});
  const address=URL.createObjectURL(blob);
  try{
    await chrome.downloads.download({url:address,filename,saveAs:true,
      conflictAction:"uniquify"});
    setStatus("Đã gửi yêu cầu lưu tệp. Không tải lên máy chủ.");
  }finally{setTimeout(()=>URL.revokeObjectURL(address),30000);}
}
function stamp(){return new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);}
async function activate(){
  const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
  if(!tab||!api.fbUrl(tab.url)){setStatus("Mở một tab Facebook trước khi bật công cụ.");return;}
  await chrome.scripting.executeScript({target:{tabId:tab.id},files:["lib.js","content.js"]});
  setStatus("Đã mở bảng điều khiển ở góc phải trang Facebook.");
}
async function exportPhotoLinks(){
 const data=await chrome.storage.local.get(PHOTO_STORE);
 const items=Array.isArray(data[PHOTO_STORE])?data[PHOTO_STORE]:[];
 if(!items.length){setStatus("Chưa lưu link ảnh. Mở bài nhiều ảnh và bấm nút lưu link trong bảng thu thập.");return;}
 await saveDownload("VOIDSCAN_photo_links_"+stamp()+".csv",api.csv(items,["photoId","photoUrl"]),"text/csv;charset=utf-8");
}
async function exportData(kind){
  const rows=await fetchRows();
  if(!rows.length){setStatus("Chưa có reaction đã thu thập để xuất.");return;}
  const basename="VOIDSCAN_reactions_"+stamp();
  if(kind==="json"){
    const payload={schema_version:1,source:"user_visible_facebook_reaction_dialog",
      observation_type:"visible_only_not_complete",exported_at:new Date().toISOString(),
      records:rows};
    await saveDownload(basename+".json",JSON.stringify(payload,null,2),"application/json;charset=utf-8");
  }else if(kind==="summary"){
    const agg=api.aggregate(rows);
    await saveDownload(basename+"_summary.csv",api.csv(agg,["photoId","photoUrl","LIKE","LOVE","CARE","HAHA","WOW","observedRows"]),
      "text/csv;charset=utf-8");
  }else{
    await saveDownload(basename+".csv",api.csv(rows,["photoId","photoUrl","profileUrl","reaction","capturedAt"]),
      "text/csv;charset=utf-8");
  }
}
$("activate").addEventListener("click",()=>activate().catch(()=>setStatus("Không thể bật công cụ. Hãy tải lại tab Facebook.")));
for(const kind of ["csv","summary","json"]){
  $(kind).addEventListener("click",()=>exportData(kind).catch(()=>setStatus("Xuất file thất bại; kiểm tra quyền tải xuống.")));
}
$("photo-links").addEventListener("click",()=>exportPhotoLinks().catch(()=>setStatus("Xuất link ảnh thất bại.")));
$("clear").addEventListener("click",async()=>{
  if(!confirm("Xóa toàn bộ URL hồ sơ đã thu thập trong Chrome này? Không thể hoàn tác."))return;
  await chrome.storage.local.remove([STORE,PHOTO_STORE]);
  await refresh();
  setStatus("Đã xóa bộ dữ liệu cục bộ.");
});
chrome.storage.onChanged.addListener((changes,area)=>{if(area==="local"&&changes[STORE])refresh().catch(()=>{});});
refresh().catch(()=>setStatus("Không đọc được dữ liệu cục bộ."));
})();