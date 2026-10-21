(() => {
"use strict";
const $=id=>document.getElementById(id);
const REACTIONS="voidscan_reactions_v1",DECISIONS="voidscan_screening_reviews_v1";
const lib=window.VoidscanAudit,review=window.VoidscanReview;
let analysis={accounts:[],observedPhotos:0,rawRows:0,validReactions:0};
let selections=[],active="",reviewMap={};
const labelStatus={unreviewed:"Chưa kiểm tra",needs_review:"Cần kiểm tra thêm",
  provisional_pass:"Tạm chấp nhận",inconclusive:"Không đủ dữ liệu"};
const labelPriority={review_first:"Ưu tiên cao",review:"Cần rà soát",no_signal:"Chưa có tín hiệu"};
const format=x=>Number(x||0).toLocaleString("vi-VN");
const toast=text=>{$("toast").textContent=text;};
const filterValue=()=>String($("filter").value);
function filtered(){
 const q=$("search").value.trim().toLowerCase(),mode=filterValue();
 return analysis.accounts.filter(x=>{
   if(mode==="flagged"&&x.priority==="no_signal"&&x.status!=="needs_review")return false;
   if(mode==="checked"&&x.status==="unreviewed")return false;
   return !q||(x.profileUrl+" "+x.username+" "+x.userId).toLowerCase().includes(q);
 });
}
function textEl(tag,text,className){
 const el=document.createElement(tag);
 if(className)el.className=className;
 el.textContent=String(text);
 return el;
}
function refreshQueue(){
 selections=filtered();
 $("listcount").textContent=format(selections.length)+" hồ sơ phù hợp bộ lọc"+
   (selections.length>250?" · đang hiển thị 250 hồ sơ đầu":"");
 const area=$("queue");area.replaceChildren();
 if(!selections.length){
   area.append(textEl("p",filterValue()==="flagged"?
     "Chưa có hồ sơ cần rà soát từ dữ liệu hiện có. Đây không phải xác nhận các tài khoản khác là thật.":
     "Chưa có dữ liệu phù hợp bộ lọc.","small"));
   $("editor").hidden=true;$("empty").hidden=false;return;
 }
 for(const profile of selections.slice(0,250)){
   const b=document.createElement("button");
   b.type="button";b.className="queuebutton"+(profile.profileUrl===active?" selected":"");
   const title=textEl("strong",profile.username||profile.userId||profile.profileUrl);
   const info=textEl("small",labelPriority[profile.priority]+" · "+
      format(profile.photoCount)+" ảnh · "+labelStatus[profile.status]);
   b.append(title,info);b.addEventListener("click",()=>select(profile.profileUrl));
   area.appendChild(b);
 }
 if(!selections.some(x=>x.profileUrl===active))select(selections[0].profileUrl,false);
}
function select(url,rerender=true){
 const item=analysis.accounts.find(x=>x.profileUrl===url);
 if(!item)return;
 active=url;$("editor").hidden=false;$("empty").hidden=true;
 $("username").textContent=item.username||item.userId||"Tài khoản";
 $("profile-link").href=item.profileUrl;
 $("profile-link").textContent=item.profileUrl+" ↗";
 $("level").textContent=labelPriority[item.priority]||"Không rõ";
 $("nphotos").textContent=format(item.photoCount);
 $("nfields").textContent=format(item.metadataFields)+"/4";
 $("reasons").replaceChildren(...item.reasons.map(x=>textEl("p",x)));
 $("decision").value=item.status;$("notes").value=item.notes||"";
 if(rerender)refreshQueue();
}
function refreshMetrics(){
 const s=review.summary(analysis);
 $("total").textContent=format(s.total);
 $("flagged").textContent=format(s.reviewFirst+s.review);
 $("nosignal").textContent=format(s.noSignal);
 $("checked").textContent=format(s.checked);
 $("photos").textContent=format(analysis.observedPhotos);
 const flagged=s.reviewFirst+s.review;
 const flaggedChecked=analysis.accounts.filter(
   x=>(x.priority!=="no_signal"||x.status==="needs_review")&&x.status!=="unreviewed").length;
 const pct=flagged?Math.min(100,flaggedChecked/flagged*100):0;
 $("notice").textContent="Đã đọc "+format(analysis.validReactions)+
   " reaction hợp lệ từ "+format(analysis.observedPhotos)+" ảnh. "+
   format(flagged)+" hồ sơ được ưu tiên kiểm tra; "+format(s.noSignal)+
   " chưa có tín hiệu bất thường từ các trường đang có. Không tự xác nhận bot, không loại phiếu.";
 $("notice").setAttribute("data-observation","incomplete");
 document.documentElement.style.setProperty("--review-progress",pct+"%");
}
async function load(){
 const data=await chrome.storage.local.get([REACTIONS,DECISIONS]);
 const raw=Array.isArray(data[REACTIONS])?data[REACTIONS]:[];
 reviewMap=data[DECISIONS]&&typeof data[DECISIONS]==="object"?data[DECISIONS]:{};
 analysis=review.analyse(raw,reviewMap);
 refreshMetrics();refreshQueue();
 toast("Tự sàng lọc "+format(analysis.accounts.length)+" hồ sơ · Không tự truy cập profile.");
}
async function save(){
 if(!active)return;
 const status=$("decision").value,notes=$("notes").value.trim().slice(0,220);
 if(!review.STATUSES.includes(status))return;
 reviewMap[active]={status,notes,reviewedAt:new Date().toISOString()};
 await chrome.storage.local.set({[DECISIONS]:reviewMap});
 const updated=review.analyse((await chrome.storage.local.get(REACTIONS))[REACTIONS]||[],reviewMap);
 analysis=updated;refreshMetrics();refreshQueue();
 toast("Đã lưu kết quả. Chỉ ghi quyết định và ghi chú của người kiểm tra.");
}
function next(){
 const shown=filtered();
 const i=shown.findIndex(p=>p.profileUrl===active);
 if(i>=0&&i<shown.length-1)select(shown[i+1].profileUrl);
 else toast("Đã tới cuối danh sách theo bộ lọc.");
}
function downloadRows(flaggedOnly){
 const rows=review.csvRows(analysis,flaggedOnly);
 if(!rows.length){toast("Không có hồ sơ trong danh sách xuất.");return;}
 const csv=lib.csv(rows,review.CSV_COLUMNS);
 const file=new Blob([csv],{type:"text/csv;charset=utf-8"});
 const href=URL.createObjectURL(file);
 const a=document.createElement("a");
 a.href=href;a.download="VOIDSCAN_screening_"+(flaggedOnly?"review_":"all_")+
   new Date().toISOString().replace(/[:.]/g,"-").slice(0,19)+".csv";
 document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(href),30000);
 toast("Đã xuất "+format(rows.length)+" hồ sơ. Nhãn bot tự động luôn là NOT_DETERMINED.");
}
$("refresh").addEventListener("click",()=>load().catch(()=>toast("Không thể tải bộ nhớ Chrome.")));
$("search").addEventListener("input",refreshQueue);
$("filter").addEventListener("change",refreshQueue);
$("save").addEventListener("click",()=>save().catch(()=>toast("Lỗi lưu đánh giá.")));
$("next").addEventListener("click",next);
$("csvflag").addEventListener("click",()=>downloadRows(true));
$("csvall").addEventListener("click",()=>downloadRows(false));
chrome.storage.onChanged.addListener((changes,area)=>{
 if(area==="local"&&changes[REACTIONS])load().catch(()=>{});
});
load().catch(()=>toast("Chưa có dữ liệu từ extension hoặc không đọc được bộ nhớ."));
})();