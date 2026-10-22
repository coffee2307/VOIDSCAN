(() => {
"use strict";
const $=id=>document.getElementById(id);
const FILE=window.VoidscanFileAudit,LIB=window.VoidscanAudit, XLSX=window.VoidscanXlsx,INTEGRITY=window.VoidscanIntegrity,PROFILE=window.VoidscanProfileImport,PUBLIC=window.VoidscanPublicMetadata,AUTO=window.VoidscanAutoAudit,COVERAGE=window.VoidscanCoverage,PRIVACY=window.VoidscanPrivacyAudit,TAB=window.VoidscanTabAudit;
const STORAGE_REACTIONS="voidscan_reactions_v1",STORAGE_PENDING="voidscan_pending_reactions_v1";
const STORAGE_DECISIONS="voidscan_screening_reviews_v1",STORAGE_COUNTS="voidscan_visible_reaction_counts_v2",PROFILE_STORE="voidscan_profile_observations_v1",MAX_CSV_BYTES=15*1024*1024;
let scanToken=0,source=[],allSource=[],sourceOrigin="",profiles=[],results=[],byUrl=new Map(),chosen="",decisionMap={};
let sourceLabel="Dữ liệu trong Chrome",integrityReport=null,profileSource=[];
let metadataBusy=false,metadataStop=false;const ATTEMPT_STORE="voidscan_tab_audit_attempts_v1";
const AUTO_STORE="voidscan_auto_tab_state_v1",AUDIT_STORE="voidscan_ephemeral_tab_audit_v1";
let autoBusy=false,autoAbort=null,autoPauseRequested=false,autoSession=null;
let reviewTabId=null,reviewTabTarget="";
const stateText=t=>{$("manual-review-state").textContent=t;};
let currentProgress={done:0,total:0,flagged:0,clear:0,insufficient:0,quality:0};
const fmt=n=>Number(n||0).toLocaleString("vi-VN");
const msg=text=>{$("toast").textContent=text;};
const busy=flag=>{
 $("stop").disabled=!flag;
 $("source-local").disabled=flag;
 $("upload").disabled=flag;
 $("profile-upload").disabled=flag;
};
const words={unreviewed:"Chưa duyệt",provisional_pass:"Tạm chấp nhận",
 needs_review:"Cần xem kỹ hơn",inconclusive:"Không đủ dữ liệu"};
function safeText(tag,text,className){
 const el=document.createElement(tag);
 el.textContent=String(text??"");
 if(className)el.className=className;
 return el;
}
function updateCounter(){
 $("total").textContent=fmt(currentProgress.total);
 $("flagged").textContent=fmt(currentProgress.flagged);
 $("nosignal").textContent=fmt(currentProgress.clear);
 $("insufficient").textContent=fmt(currentProgress.insufficient);
 $("quality-review").textContent=fmt(currentProgress.quality);
 $("checked").textContent=fmt(currentProgress.done);
 $("progress-number").textContent=fmt(currentProgress.done)+" / "+fmt(currentProgress.total)+" tài khoản";
 const pc=currentProgress.total?Math.round(currentProgress.done/currentProgress.total*100):0;
 $("progress-bar").style.width=pc+"%";
 $("progress-track").setAttribute("aria-valuenow",pc);
}
function listFiltered(){
 const q=$("search").value.trim().toLowerCase(),mode=$("filter").value;
 return results.filter(p=>{
  if(mode==="attention"&&p.status!==FILE.LABEL_SUSPECT&&!p.needsReactionCheck)return false;
  if(mode==="flagged"&&p.status!==FILE.LABEL_SUSPECT)return false;
  if(mode==="quality"&&!p.needsReactionCheck)return false;
  if(mode==="insufficient"&&p.status!==FILE.LABEL_INSUFFICIENT)return false;
  if(mode==="clear"&&p.status!==FILE.LABEL_CLEAR)return false;
  if(mode==="checked"&&p.reviewerStatus==="unreviewed")return false;
  return !q||[p.profileUrl,p.username,p.userId].some(v=>String(v||"").toLowerCase().includes(q));
 });
}
function drawQueue(){
 const filtered=listFiltered(),q=$("queue");q.replaceChildren();
 $("listcount").textContent=fmt(filtered.length)+" tài khoản"+
   (filtered.length>250?" · đang hiển thị 250 đầu tiên":"");
 if(!filtered.length){
   q.append(safeText("p",currentProgress.done===0?"Chưa có kết quả sàng lọc.":
     "Không có tài khoản phù hợp bộ lọc. Điều này không xác nhận tính hợp lệ của toàn bộ danh sách.","small"));
   $("empty").hidden=false;$("editor").hidden=true;
   return;
 }
 for(const p of filtered.slice(0,250)){
  const item=document.createElement("button");item.type="button";item.className="queuebutton"+
   (chosen===p.profileUrl?" selected":"");
  item.append(safeText("strong",p.username||p.userId||p.profileUrl));
  item.append(safeText("small",(p.status===FILE.LABEL_SUSPECT?"● Nghi vấn":
    p.status===FILE.LABEL_INSUFFICIENT?"● Chưa đủ dữ liệu":"● Chưa thấy dấu hiệu")+
    (p.needsReactionCheck?" · Cần kiểm tra reaction":"")+
    " · "+fmt(p.photoCount)+" ảnh · "+words[p.reviewerStatus]));
  item.addEventListener("click",()=>select(p.profileUrl));
  q.append(item);
 }
 if(!filtered.some(x=>x.profileUrl===chosen))select(filtered[0].profileUrl,false);
}
function select(url,redraw=true){
 const p=byUrl.get(url);if(!p)return;
 chosen=url;$("empty").hidden=true;$("editor").hidden=false;
 $("username").textContent=p.username||p.userId||"Tài khoản";
 $("profile-link").href=p.profileUrl;
 $("profile-link").textContent=p.profileUrl+" ↗";
 $("level").textContent=p.status;
 $("level").className="pill "+(p.status===FILE.LABEL_SUSPECT?"suspect":
   p.status===FILE.LABEL_INSUFFICIENT?"inconclusive":"clear");
 $("nphotos").textContent=fmt(p.photoCount);
 $("nunknown").textContent=fmt(p.unknownRows);
 $("nfields").textContent=fmt(p.availableInfoPoints)+"/6";
 $("avatar-state").textContent=p.avatarEvidence==="present"?"Có URL/đã ghi nhận":
   p.avatarEvidence==="absent_observed"?"Đã kiểm tra: không thấy":"Chưa thu thập";
 $("location-state").textContent=p.regionContext==="local"?"Khớp khu vực ưu tiên":
   p.regionContext==="other"?"Địa điểm ngoài khu vực":"Chưa thu thập";
 $("profile-evidence-source").textContent=p.profileDataSource==="uploaded_profile_csv"?"CSV hồ sơ nhập":
   p.profileDataSource==="observed_open_profile"?"Trang Facebook đang mở":p.profileDataSource==="public_metadata"?"Metadata công khai":"Không có";
 $("mutual-observed").textContent=p.mutualFriendsNumber===""?"Chưa thấy":fmt(p.mutualFriendsNumber);
 $("postdate-observed").textContent=p.latestVisiblePostAt||"Chưa thấy";
 $("school-observed").textContent=p.educationObserved||"Chưa thấy";
 $("friends-observed").textContent=p.friendsCount===""?"Chưa thấy":fmt(p.friendsCount);
 $("joined-observed").textContent=p.joinedYear||"Chưa thấy";
 $("reasons").replaceChildren(safeText("p",p.evidence));
 if(p.dataQuality)$("reasons").append(safeText("p","Chất lượng dữ liệu (không phải bằng chứng bot): "+p.dataQuality,"small"));
 $("decision").value=p.reviewerStatus;
 $("notes").value=p.reviewNotes||"";
 if(redraw)drawQueue();
}
function setLast(p){
 const short=p.username||p.userId||p.profileUrl.split("/").filter(Boolean).at(-1)||"Hồ sơ";
 $("last-scanned").textContent="Vừa phân tích dòng CSV: "+short+" — "+p.status;
 $("last-scanned").style.color=p.status===FILE.LABEL_SUSPECT?"#ffb1bd":"#9cedbd";
}
async function sleep(ms){return new Promise(resolve=>setTimeout(resolve,ms));}
async function showIntegrity(records,origin){
 const isChrome=origin.startsWith("Dữ liệu trong Chrome");
 const stored=isChrome?await chrome.storage.local.get(STORAGE_COUNTS):{};
 const report=INTEGRITY.audit(records,isChrome?(stored[STORAGE_COUNTS]||{}):{});
 integrityReport=report;
 $("duplicate-rows").textContent=fmt(report.totals.duplicates);
 $("unknown-rows").textContent=fmt(report.totals.unknown);
 const table=$("integrity-rows");table.replaceChildren();
 for(const p of report.photos){
  const tr=document.createElement("tr");
  const cells=[p.photoId,...LIB.types.map(k=>p.counts[k]),p.uniqueAccounts];
  const measured=LIB.types.map(k=>p.coverage[k]).filter(Boolean);
  const comparable=measured.reduce((a,v)=>a+v.displayed,0);
  const seen=measured.reduce((a,v)=>a+v.observed,0);
  const ratio=measured.length?fmt(seen)+" / "+fmt(comparable)+
    (comparable?" ("+Math.round(100*seen/comparable)+"%)":""):
    "Chưa có số gốc";
  cells.push(ratio);
  for(const value of cells)tr.append(safeText("td",value));
  table.append(tr);
 }
 if(!report.photos.length){const tr=document.createElement("tr");const td=safeText("td","Không có URL reaction hợp lệ.");td.colSpan=8;tr.append(td);table.append(tr);}
 $("integrity-explanation").textContent="Đếm "+fmt(report.totals.uniquePhotoReactions)+
   " tương tác có loại xác định (URL duy nhất trong từng ảnh), "+fmt(report.totals.duplicates)+
   " dòng trùng, "+fmt(report.totals.conflicts)+" xung đột loại reaction (chưa rõ thời điểm sẽ không cộng vào loại cụ thể); "+
   fmt(report.totals.unknown)+" dòng chưa rõ loại không được cộng điểm. "+
   (isChrome?"Chỉ đối soát số hiển thị khi Chrome đã lưu số đó.":"CSV tải lên không cung cấp số reaction hiển thị để đối soát.")+
   " Đây KHÔNG phải số tài khoản ảo hay tỷ lệ phát hiện bot.";
 return report;
}
async function scan(data,origin){
 const ticket=++scanToken;
 source=data;
 results=[];profiles=[];byUrl=new Map();chosen="";
 sourceLabel=origin;
 busy(true);
 $("progress-title").textContent="Đang chuẩn hóa CSV...";
 $("source-label").textContent=origin;
 $("last-scanned").textContent="Đang đọc dữ liệu...";
 try{
  const prepared=FILE.prepare(data);
  await showIntegrity(prepared.rows,origin);
  profiles=prepared.profiles;
  const observedAvatar=profiles.filter(p=>["present","absent_observed"].includes(p.avatarEvidence)).length;
  const observedLocality=profiles.filter(p=>["local","other"].includes(p.regionContext)).length;
  const historyProfiles=profiles.filter(p=>p.photoIds.size>=2).length;
  currentProgress={total:profiles.length,done:0,flagged:0,clear:0,insufficient:0,quality:0};
  $("inspected-count").textContent=fmt(profiles.filter(p=>p.profileDataSource==="observed_open_profile").length);
  $("photos").textContent=fmt(prepared.photoTotal);
  updateCounter();
  $("notice").textContent="PHẠM VI: "+($("photo-scope").value==="all"?"TẤT CẢ ẢNH":("CHỈ ẢNH "+$("photo-scope").value))+
   ". Đây là phân tích dữ liệu CSV, KHÔNG truy cập hồ sơ Facebook. 0 nghi vấn chỉ có nghĩa 0 tín hiệu từ các cột đã nhập, KHÔNG chứng minh các tài khoản đều thật. Đọc "+fmt(prepared.rows.length)+" dòng hợp lệ. "+
   (prepared.warnings.invalidProfile?
    fmt(prepared.warnings.invalidProfile)+" dòng thiếu URL hồ sơ đã được bỏ qua. ":"")+
   (prepared.warnings.unknownReaction?
    fmt(prepared.warnings.unknownReaction)+" reaction chưa xác định loại. ":"")+
   (prepared.warnings.photoMismatch?
    fmt(prepared.warnings.photoMismatch)+" dòng có Photo ID mâu thuẫn với Photo URL bị loại. ":"")+
   "ĐỘ BAO PHỦ DỮ LIỆU: avatar "+fmt(observedAvatar)+"/"+fmt(profiles.length)+
   " hồ sơ; địa điểm "+fmt(observedLocality)+"/"+fmt(profiles.length)+
   "; có lịch sử từ ít nhất hai ảnh "+fmt(historyProfiles)+"/"+fmt(profiles.length)+
   ". Các trường chỉ được sử dụng khi CSV thực sự cung cấp. Trùng tên và reaction UNKNOWN chỉ là vấn đề chất lượng dữ liệu, không phải dấu hiệu tài khoản ảo.";
  $("progress-title").textContent="Đang phân tích dữ liệu CSV — không mở profile Facebook";
  const decisions=await chrome.storage.local.get([STORAGE_DECISIONS,AUDIT_STORE]);
  decisionMap=decisions[STORAGE_DECISIONS]&&typeof decisions[STORAGE_DECISIONS]==="object"?
    decisions[STORAGE_DECISIONS]:{};
  const minimalAudit=PRIVACY?PRIVACY.prune(decisions[AUDIT_STORE]).records:{};
  for(let i=0;i<profiles.length;i++){
   if(ticket!==scanToken){$("progress-title").textContent="Đã dừng.";return;}
   const row=FILE.scoreProfile(profiles[i],prepared.photoTotal,decisionMap);
   const audit=minimalAudit[row.profileUrl];
   if(audit){
     row.privacyAccess=audit.access;
     row.privacyCheckedAt=audit.checkedAt;
     row.privacyDecision=audit.status;
     row.evidence+=" | "+PRIVACY.describe(audit);
   }
   results.push(row);byUrl.set(row.profileUrl,row);
   currentProgress.done++;
   if(row.status===FILE.LABEL_SUSPECT)currentProgress.flagged++;
   else if(row.status===FILE.LABEL_INSUFFICIENT)currentProgress.insufficient++;
   else currentProgress.clear++;
   if(row.needsReactionCheck)currentProgress.quality++;
   updateCounter();
   setLast(row);
   // Yield regularly so Chrome paints counters and n/n progress mid-scan.
   if(i%8===7)await sleep(8);
  }
  if(ticket!==scanToken)return;
  $("progress-title").textContent="Hoàn tất phân tích CSV (chưa xác minh profile)";
  const supplied=results.filter(p=>p.evidenceQuality==="profile_observed").length;
  $("evidence-coverage").textContent=fmt(supplied)+" / "+fmt(results.length);
  $("auto-diagnosis").textContent=supplied===0&&results.length?
    "CẢNH BÁO DỮ LIỆU: 0/"+fmt(results.length)+
    " hồ sơ có trường bổ sung để đánh giá. "+
    fmt(currentProgress.insufficient)+" hồ sơ đang CHƯA ĐỦ DỮ LIỆU, không phải "+
    fmt(currentProgress.insufficient)+" tài khoản bình thường. "+
    fmt(currentProgress.quality)+" hồ sơ có reaction cần kiểm tra lại. "+
    "Auto Audit thử metadata công khai không đồng nghĩa đã xem hoạt động của hồ sơ.":
    "Đã có trường bổ sung để đánh giá "+fmt(supplied)+"/"+fmt(results.length)+
    " hồ sơ; những hồ sơ còn thiếu dữ liệu vẫn cần đối chiếu.";
  drawQueue();
  msg("Hoàn thành "+fmt(currentProgress.done)+" URL trong CSV của phạm vi đã chọn. "+
   fmt(currentProgress.flagged)+" có tín hiệu hồ sơ; "+
   fmt(currentProgress.quality)+" cần kiểm tra lại loại reaction; "+
   fmt(currentProgress.insufficient)+" chưa đủ dữ liệu; "+
   fmt(currentProgress.clear)+" chưa thấy tín hiệu khi đã có dữ liệu. "+
   "Đã có quan sát từ trang mở: "+$("inspected-count").textContent+".");
 }catch(e){
   $("progress-title").textContent="Lỗi phân tích";
   msg("Không thể phân tích: "+(e.message||"lỗi không xác định"));
 }finally{if(ticket===scanToken)busy(false);}
}
async function useSource(data,origin){
 allSource=data;
 sourceOrigin=origin;
 const valid=FILE.normaliseRows(data).rows;
 const options=LIB.photoCounts(valid),select=$("photo-scope");
 const storage=await chrome.storage.local.get("voidscan_active_photo_v1");
 const active=String(storage.voidscan_active_photo_v1||"");
 select.replaceChildren();
 const add=(id,label)=>{const op=document.createElement("option");op.value=id;op.textContent=label;select.append(op);};
 for(const p of options)add(p.photoId,"Ảnh "+p.photoId+" · "+p.count+" URL");
 add("all","Tất cả ảnh — chỉ chọn khi cần tổng hợp");
 const chosen=options.length>1?"all":(options.some(p=>p.photoId===active)?active:(options.at(-1)?.photoId||"all"));
 select.value=chosen;
 await scanScope();
 await showCoverageReport();
}
async function scanScope(){
 const photo=$("photo-scope").value;
 $("scope-hint").textContent=photo==="all"?
   "Đang TỔNG HỢP TẤT CẢ ẢNH — chuyển về Photo ID để tách riêng.":
   "Chỉ phân tích ảnh "+photo+"; các ảnh còn lại không bị cộng vào.";
 const valid=FILE.normaliseRows(allSource).rows;
 const scoped=photo==="all"?valid:LIB.scopedRows(valid,photo);
 const saved=await chrome.storage.local.get(PROFILE_STORE);
 const observations=Object.values(saved[PROFILE_STORE]||{});
 const match=PROFILE.enrich(scoped,[...observations,...profileSource]);
 $("profile-source").textContent=profileSource.length?
   "Đã nạp "+fmt(profileSource.length)+" dòng hồ sơ; ghép "+fmt(match.matchedRows)+" dòng reaction trong phạm vi đang chọn":
   "Chưa có nguồn hồ sơ · không suy từ cột thiếu.";
 await scan(match.rows,sourceOrigin+
  (photo==="all"?" · Tất cả ảnh":" · Ảnh "+photo)+
  (profileSource.length?" · có dữ liệu hồ sơ bổ sung":""));
}
async function showCoverageReport(){
 if(!COVERAGE)return;
 const saved=await chrome.storage.local.get([AUTO_STORE,PROFILE_STORE,ATTEMPT_STORE,AUDIT_STORE]);
 const state=saved[AUTO_STORE]||{};
 const urls=allSource.length?AUTO.plan(FILE.normaliseRows(allSource).rows):state.urls||[];
 const derived=PRIVACY?PRIVACY.prune(saved[AUDIT_STORE]).records:{};
 const usable=Object.fromEntries(Object.entries(derived).filter(([,v])=>v.usable));
 const summary=COVERAGE.assess(urls,saved[ATTEMPT_STORE]||{},
   {...(saved[PROFILE_STORE]||{}),...usable});
 const {counters:c,outcomes}=summary;
 $("metadata-status").textContent="Tiến độ tab Facebook: "+fmt(summary.attemptedTotal)+
   " URL đã thử · "+fmt(c.withEvidence)+" có tín hiệu trang · "+fmt(c.unattempted)+
   " chưa thử · "+fmt(c.denied)+" bị từ chối/giới hạn · "+
   fmt(c.errors)+" lỗi truy cập · "+fmt(c.missingFields)+" HTML thiếu trường dùng được."+
   " Chi tiết: "+Object.entries(outcomes).map(([k,v])=>k+": "+fmt(v)).join("; ");
}
function exportAutoLog(){
 if(!COVERAGE){msg("Không có mô-đun nhật ký.");return;}
 chrome.storage.local.get([AUTO_STORE,PROFILE_STORE,ATTEMPT_STORE,AUDIT_STORE]).then(saved=>{
   const state=saved[AUTO_STORE]||{},urls=allSource.length?
      AUTO.plan(FILE.normaliseRows(allSource).rows):state.urls||[];
   const derived=PRIVACY?PRIVACY.prune(saved[AUDIT_STORE]).records:{};
   const usable=Object.fromEntries(Object.entries(derived).filter(([,v])=>v.usable));
   const report=COVERAGE.assess(urls,saved[ATTEMPT_STORE]||{},
     {...(saved[PROFILE_STORE]||{}),...usable});
   if(!report.rows.length){msg("Chưa có danh sách để xuất nhật ký.");return;}
   const headers=["URL hồ sơ","Trạng thái truy xuất","Thời điểm thử","Có dữ liệu hồ sơ"];
   const rows=report.rows.map(r=>({
     "URL hồ sơ":r.profileUrl,"Trạng thái truy xuất":r.status,
     "Thời điểm thử":r.attemptedAt,"Có dữ liệu hồ sơ":r.hasUsableEvidence?"Có":"Không"
   }));
   const blob=new Blob([LIB.csv(rows,headers)],{type:"text/csv;charset=utf-8"});
   const link=URL.createObjectURL(blob),a=document.createElement("a");
   a.href=link;a.download="VOIDSCAN_AUTO_AUDIT_NHAT_KY.csv";
   document.body.append(a);a.click();a.remove();
   setTimeout(()=>URL.revokeObjectURL(link),30000);
   msg("Đã xuất nhật ký "+fmt(report.rows.length)+" URL; không ghi dữ liệu liên hệ.");
 }).catch(e=>msg("Không xuất được nhật ký: "+e.message));
}
function showAutoProgress(state){
 const s=state||{};
 const total=Array.isArray(s.urls)?s.urls.length:0,done=Math.min(total,Number(s.index)||0);
 const pct=total?Math.round(done/total*100):0;
 $("auto-track").setAttribute("aria-valuenow",pct);
 $("auto-bar").style.width=pct+"%";
 const names={ready:"Sẵn sàng",running:"Đang chạy",paused:"Tạm dừng",
   blocked:"Đã dừng do Facebook hạn chế truy cập",complete:"Hoàn thành"};
 $("auto-state").textContent=names[s.status]||"Chưa có hàng đợi";
 $("auto-progress").textContent=total?
  fmt(done)+"/"+fmt(total)+" URL · "+pct+"% · "+
  fmt(s.usable)+" có tín hiệu ảnh đại diện · "+fmt(s.unavailable)+" chưa đủ tín hiệu/không tải được · "+
  fmt(s.skipped)+" được bỏ qua vì đã xử lý/có dữ liệu. "+
  (s.stopReason||""):
  "Nhập CSV reaction, bấm Auto Audit một lần. Tiến độ được lưu trong Chrome.";
 $("auto-pause").disabled=!autoBusy;
 $("auto-start").disabled=autoBusy;
}
async function persistAuto(queue,decisions,attempts){
 queue.updatedAt=new Date().toISOString();
 autoSession=queue;
 // Only minimal, expiring decisions and access status are persisted.
 await chrome.storage.local.set({[AUTO_STORE]:queue,[AUDIT_STORE]:decisions,[ATTEMPT_STORE]:attempts});
 showAutoProgress(queue);
 if(queue.index%10===0||queue.status!=="running")
   await showCoverageReport();
}
async function startAutoAudit(){
 if(autoBusy)return;
 if(metadataBusy){msg("Vui lòng đợi lần thử metadata 10 hồ sơ hoàn tất.");return;}
 if(!AUTO||!TAB||!PRIVACY){msg("Chưa tải được bộ điều khiển tab Chrome.");return;}
 const stored=(await chrome.storage.local.get(AUTO_STORE))[AUTO_STORE];
 const candidate=allSource.length?AUTO.plan(FILE.normaliseRows(allSource).rows):stored?.urls||[];
 if(!candidate.length){msg("Chưa có URL. Nhập CSV reaction hoặc lấy dữ liệu từ tiện ích trước.");return;}
 const approved=await chrome.permissions.request({origins:["https://www.facebook.com/*"]});
 if(!approved){msg("Cần cấp quyền trang Facebook để Chrome đọc được trạng thái trang mở.");return;}
 let q=AUTO.create(candidate,stored);
 if(q.index>=q.urls.length)q=AUTO.create(candidate,null);
 q.status="running";q.stopReason="";
 autoBusy=true;autoPauseRequested=false;autoAbort=new AbortController();
 const state=await chrome.storage.local.get([ATTEMPT_STORE,AUDIT_STORE]);
 const attempts=state[ATTEMPT_STORE]||{};
 const decisions=PRIVACY.prune(state[AUDIT_STORE]).records;
 let consecutiveNetworkErrors=0,tabId=null;
 try{
  await persistAuto(q,decisions,attempts);
  while(q.index<q.urls.length){
   if(autoPauseRequested){q.status="paused";q.stopReason="Đã tạm dừng theo yêu cầu.";break;}
   const url=q.urls[q.index],existing=decisions[url],attempt=attempts[url];
   if(existing||AUTO.reuseAttempt(attempt)){
     q.skipped++;q.index++;
     await persistAuto(q,decisions,attempts);
     continue;
   }
   // Reuse one real Chrome tab; no personal page content is extracted.
   const outcome=await TAB.scan(url,tabId,chrome,autoAbort.signal);
   tabId=outcome.tabId;
   if(outcome.access==="cancelled"||autoPauseRequested){
     q.status="paused";q.stopReason="Đã tạm dừng.";break;
   }
   attempts[url]={at:new Date().toISOString(),status:outcome.access};
   if(["navigation_error","timeout"].includes(outcome.access))consecutiveNetworkErrors++;
   else consecutiveNetworkErrors=0;
   if(["auth_required","restricted"].includes(outcome.access)||
      consecutiveNetworkErrors>=3){
     q.status="blocked";
     q.stopReason=["auth_required","restricted"].includes(outcome.access)?
       "Facebook yêu cầu đăng nhập/xác minh; Auto Audit đã dừng.":
       "Liên tiếp không tải được trang Facebook; dừng để tránh truy cập quá mức.";
     await persistAuto(q,decisions,attempts);break;
   }
   const decision=PRIVACY.decide(outcome);
   decisions[url]=decision;
   if(decision.usable)q.usable++;
   else q.unavailable++;
   q.attempted++;q.index++;
   await persistAuto(q,decisions,attempts);
   if(q.index%10===0&&allSource.length)await scanScope();
   if(q.index<q.urls.length){
     // Deliberately conservative sequential pacing; keep tab open.
     await sleep(AUTO.WAIT_MS);
   }
  }
  if(q.index>=q.urls.length){q.status="complete";q.stopReason="Đã thử toàn bộ URL trong hàng đợi.";}
  else if(q.status==="running"){q.status="paused";q.stopReason="Tạm dừng.";}
  await persistAuto(q,decisions,attempts);
  if(allSource.length)await scanScope();
  const resultText="Auto Audit Chrome: "+fmt(q.index)+"/"+fmt(q.urls.length)+" URL, "+
   fmt(q.usable)+" có ảnh đại diện nhìn thấy, "+fmt(q.unavailable)+
   " chưa đủ tín hiệu/không tải được. "+q.stopReason;
  msg(resultText);
 }catch(e){
  q.status="paused";q.stopReason="Lỗi xử lý: "+(e.message||"không xác định");
  await persistAuto(q,decisions,attempts).catch(()=>{});
  msg(q.stopReason);
 }finally{
  await TAB.close(tabId,chrome).catch(()=>{});
  autoBusy=false;autoAbort=null;
  showAutoProgress(q);
 }
}
function pauseAutoAudit(){
 if(!autoBusy)return;
 autoPauseRequested=true;
 autoAbort?.abort();
 $("auto-pause").disabled=true;
}
async function purgeExpiredAudit(){
 if(!PRIVACY)return;
 const keys=[AUDIT_STORE,ATTEMPT_STORE,AUTO_STORE,PROFILE_STORE];
 const stored=await chrome.storage.local.get(keys),now=Date.now();
 const decisions=PRIVACY.prune(stored[AUDIT_STORE],now).records;
 const attempts={};
 for(const [url,entry] of Object.entries(stored[ATTEMPT_STORE]||{})){
   const date=Date.parse(entry?.at||"");
   if(Number.isFinite(date)&&date<=now&&now-date<PRIVACY.TTL_MS)
     attempts[url]={status:String(entry.status||"unknown"),at:new Date(date).toISOString()};
 }
 const observed={};
 for(const [url,entry] of Object.entries(stored[PROFILE_STORE]||{})){
   const date=Date.parse(entry?.observedAt||"");
   if(Number.isFinite(date)&&date<=now&&now-date<PRIVACY.TTL_MS)observed[url]=entry;
 }
 await chrome.storage.local.set({
   [AUDIT_STORE]:decisions,[ATTEMPT_STORE]:attempts,[PROFILE_STORE]:observed
 });
 await chrome.storage.local.remove([
   "voidscan_public_metadata_attempts_v1","voidscan_auto_audit_state_v1",
   "voidscan_ephemeral_audit_v1"
 ]);
 const last=Date.parse(stored[AUTO_STORE]?.updatedAt||"");
 if(stored[AUTO_STORE]&&(!Number.isFinite(last)||now-last>=PRIVACY.TTL_MS))
   await chrome.storage.local.remove(AUTO_STORE);
}
async function eraseStoredAudit(){
 if(autoBusy||metadataBusy){msg("Hãy dừng Auto Audit trước khi xóa dữ liệu.");return;}
 await chrome.storage.local.remove([
  STORAGE_REACTIONS,STORAGE_PENDING,STORAGE_DECISIONS,STORAGE_COUNTS,
  PROFILE_STORE,ATTEMPT_STORE,AUTO_STORE,AUDIT_STORE,
  "voidscan_public_metadata_attempts_v1","voidscan_auto_audit_state_v1",
  "voidscan_ephemeral_audit_v1",
  "voidscan_photo_links_v1","voidscan_active_photo_v1"
 ]);
 profileSource=[];allSource=[];source=[];results=[];byUrl.clear();
 location.reload();
}
async function refreshAutoState(){
 const stored=(await chrome.storage.local.get(AUTO_STORE))[AUTO_STORE];
 if(!autoBusy&&stored?.status==="running"){
   stored.status="paused";
   stored.stopReason="Phiên trước đã đóng hoặc tải lại. Nhấn Bắt đầu để tiếp tục tại URL chưa xử lý.";
   await chrome.storage.local.set({[AUTO_STORE]:stored});
 }
 if(!autoBusy)showAutoProgress(stored);
 await showCoverageReport();
}
async function loadFromChrome(){
 const saved=await chrome.storage.local.get([STORAGE_REACTIONS,STORAGE_PENDING]);
 const classified=Array.isArray(saved[STORAGE_REACTIONS])?saved[STORAGE_REACTIONS]:[];
 const pending=Array.isArray(saved[STORAGE_PENDING])?saved[STORAGE_PENDING]:[];
 const known=new Set(classified.map(r=>r.photoId+"|"+r.profileUrl));
 const merged=[...classified,...pending.filter(r=>!known.has(r.photoId+"|"+r.profileUrl))];
 await useSource(merged,"Dữ liệu trong Chrome · "+fmt(merged.length)+" dòng reaction");
}
async function loadFiles(files){
 const selected=Array.from(files||[]);
 if(!selected.length)return;
 if(selected.length>50)throw Error("Tối đa 50 CSV cho một lần nhập.");
 const combined=[];
 for(const file of selected){
  if(file.size>MAX_CSV_BYTES)throw Error(file.name+" vượt 15 MB.");
  if(!/\.csv$/i.test(file.name)&&file.type!=="text/csv"&&file.type!=="text/plain")
    throw Error("Chỉ chấp nhận CSV.");
  const parsed=FILE.parseCSV(await file.text());
  combined.push(...parsed.rows);
 }
 await useSource(combined,selected.length===1?selected[0].name:
   fmt(selected.length)+" tệp CSV · "+fmt(combined.length)+" dòng reaction");
}
async function loadProfiles(file){
 if(!file)return;
 if(file.size>MAX_CSV_BYTES)throw Error("CSV hồ sơ vượt 15 MB.");
 const parsed=FILE.parseCSV(await file.text());
 const sourceColumns=PROFILE.inspectExportHeaders(parsed.headers);
 profileSource=parsed.rows;
 if(allSource.length)await scanScope();
 else $("profile-source").textContent="Đã nạp "+fmt(profileSource.length)+" dòng hồ sơ; chờ nhập CSV reaction.";
 msg((sourceColumns.isFriendsExporter?"Đã nhận CSV FBFriends 1.3.1. ":"Đã nhận CSV hồ sơ. ")+
   "Đã bỏ qua trường nhạy cảm; chỉ đối chiếu URL/ID và những thông tin phù hợp. Không truy cập Facebook.");
}
function allRows(flaggedOnly){
 return results.filter(p=>!flaggedOnly||p.status===FILE.LABEL_SUSPECT);
}
function exportIntegrity(){
 if(!integrityReport||!integrityReport.photos.length){msg("Chưa có dữ liệu đối soát để xuất.");return;}
 const columns=["Photo ID","LIKE","LOVE","CARE","HAHA","WOW","URL duy nhất","Trùng","Xung đột reaction","Chưa phân giải xung đột","Chưa rõ loại","Loại bị loại trừ","Đã quan sát có số gốc","Số gốc Facebook","Ghi chú"];
 const records=integrityReport.photos.map(p=>{
  const measured=LIB.types.map(k=>p.coverage[k]).filter(Boolean);
  const seen=measured.reduce((n,x)=>n+x.observed,0);
  const displayed=measured.reduce((n,x)=>n+x.displayed,0);
  const note=measured.length?(seen>displayed?"Lớn hơn số gốc; kiểm tra thời điểm ghi dữ liệu":"Số gốc và dữ liệu thu thập có thể khác thời điểm"):
   "Chưa có bộ đếm Facebook để đối soát";
  const values=[p.photoId,...LIB.types.map(k=>p.counts[k]),p.uniqueAccounts,p.duplicates,p.conflicts,p.ambiguousAccounts,p.unknown,p.excluded,measured.length?seen:"",measured.length?displayed:"",note];
  return Object.fromEntries(columns.map((k,i)=>[k,values[i]]));
 });
 const file=new Blob([LIB.csv(records,columns)],{type:"text/csv;charset=utf-8"});
 const url=URL.createObjectURL(file);
 const a=document.createElement("a");a.href=url;
 a.download="VOIDSCAN_DOI_SOAT_ANH_"+new Date().toISOString().replace(/[:.]/g,"-").slice(0,19)+".csv";
 document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),30000);
 msg("Đã tạo bảng đối soát "+fmt(records.length)+" ảnh. Không suy diễn số tài khoản ảo.");
}
function exportFile(filetype,flaggedOnly=false){
 const rows=allRows(flaggedOnly);
 if(!rows.length){msg("Chưa có kết quả để xuất.");return;}
 const cols=FILE.COLUMNS;
 const date=new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);
 const name="VOIDSCAN_KIEM_TOAN_"+(flaggedOnly?"NGHI_VAN_":"TAT_CA_")+date;
 let bytes,filename,type;
 if(filetype==="xlsx"){
  bytes=XLSX.workbook(rows,cols);
  filename=name+".xlsx";
  type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
 }else{
  const data=rows.map(r=>Object.fromEntries(cols.map(c=>[c.label,r[c.key]??""])));
  bytes=LIB.csv(data,cols.map(c=>c.label));
  filename=name+".csv";type="text/csv;charset=utf-8";
 }
 const blob=new Blob([bytes],{type}),url=URL.createObjectURL(blob);
 const a=document.createElement("a");a.href=url;a.download=filename;
 document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),30000);
 msg("Đã tạo "+filename+" ("+fmt(rows.length)+" tài khoản). "+
   (filetype==="csv"?"CSV không lưu định dạng màu/viền.":"Excel có tiêu đề xanh, viền, lọc và màu trạng thái."));
}
async function saveReview(){
 if(!chosen)return;
 const status=$("decision").value,notes=$("notes").value.trim().slice(0,220);
 if(!["unreviewed","provisional_pass","needs_review","inconclusive"].includes(status))return;
 decisionMap[chosen]={status,notes,reviewedAt:new Date().toISOString()};
 await chrome.storage.local.set({[STORAGE_DECISIONS]:decisionMap});
 const p=byUrl.get(chosen);
 p.reviewerStatus=status;p.reviewNotes=notes;
 if(status==="needs_review"&&p.status!==FILE.LABEL_SUSPECT){
   if(p.status===FILE.LABEL_INSUFFICIENT)currentProgress.insufficient--;
   else currentProgress.clear--;
   p.status=FILE.LABEL_SUSPECT;
   p.evidence+=" | Được người duyệt đánh dấu cần xem kỹ hơn";
   currentProgress.flagged++;
   updateCounter();
 }
 drawQueue();msg("Đã lưu đánh giá của người kiểm tra. Không tự loại phiếu.");
}
async function openManualProfile(url){
 const candidate=LIB.profileMeta(url);
 if(!candidate)throw Error("URL hồ sơ Facebook không hợp lệ.");
 let tab=null;
 if(reviewTabId!==null){
   try{tab=await chrome.tabs.update(reviewTabId,{url:candidate.profileUrl,active:true});}
   catch{reviewTabId=null;}
 }
 if(!tab)tab=await chrome.tabs.create({url:candidate.profileUrl,active:true});
 reviewTabId=tab.id;reviewTabTarget=candidate.profileUrl;
 stateText("Đã mở hồ sơ trong tab Chrome. Xem trang, sau đó quay về VOIDSCAN bấm Ghi nhận trang đã mở.");
}
async function captureManualProfile(){
 if(reviewTabId===null||!reviewTabTarget){stateText("Hãy bấm Mở trong tab Chrome trước.");return;}
 const granted=await chrome.permissions.request({origins:["https://www.facebook.com/*"]});
 if(!granted){stateText("Chưa cấp quyền đọc trang Facebook đang mở.");return;}
 try{
  const info=await chrome.tabs.get(reviewTabId);
  if(LIB.normalizeProfile(info.url||"")!==LIB.normalizeProfile(reviewTabTarget)){
    stateText("Tab đã chuyển URL; hãy mở lại đúng hồ sơ từ VOIDSCAN.");return;
  }
  await chrome.scripting.executeScript({target:{tabId:reviewTabId},files:["lib.js","profile-capture.js"]});
  const rv=await chrome.scripting.executeScript({
    target:{tabId:reviewTabId},func:()=>window.VoidscanCaptureCurrentProfile()
  });
  const output=rv?.[0]?.result||{};
  stateText(output.saved?"Đã lưu thông tin hiển thị. Tiếp tục hồ sơ sau khi kiểm tra kết quả.":
    output.reason||"Không ghi nhận được thông tin; trường chưa thấy vẫn để trống.");
  if(output.saved&&allSource.length){
    const inspected=chosen;
    await scanScope();
    if(byUrl.has(inspected))select(inspected);
  }
 }catch(err){stateText("Không đọc được trang: "+err.message);}
}
function nextProfile(){
 const queue=listFiltered();
 const ix=queue.findIndex(x=>x.profileUrl===chosen);
 if(ix>=0&&ix<queue.length-1)select(queue[ix+1].profileUrl);
 else msg("Đã đến cuối danh sách trong bộ lọc hiện tại.");
}
chrome.storage.onChanged?.addListener((changes,area)=>{
 if(area==="local"&&changes[PROFILE_STORE]&&allSource.length&&!autoBusy)
   scanScope().catch(e=>msg("Không cập nhật được dữ liệu hồ sơ: "+e.message));
});
$("auto-start").addEventListener("click",()=>startAutoAudit().catch(e=>msg("Auto Audit không chạy: "+e.message)));
$("auto-pause").addEventListener("click",pauseAutoAudit);
$("auto-export").addEventListener("click",exportAutoLog);
$("privacy-erase").addEventListener("click",()=>eraseStoredAudit().catch(e=>msg("Lỗi xóa dữ liệu: "+e.message)));
$("source-local").addEventListener("click",()=>loadFromChrome().catch(e=>msg("Lỗi đọc dữ liệu Chrome: "+e.message)));
$("photo-scope").addEventListener("change",()=>scanScope().catch(e=>msg("Lỗi thay đổi phạm vi ảnh: "+e.message)));
$("profile-upload").addEventListener("change",e=>{
 const file=e.target.files?.[0];
 if(file)loadProfiles(file).catch(err=>msg("Lỗi CSV hồ sơ: "+err.message));
 e.target.value="";
});
$("upload").addEventListener("change",e=>{
 const files=e.target.files;
 if(files?.length)loadFiles(files).catch(e=>msg("Không nhập được CSV: "+e.message));
 e.target.value="";
});
const drop=$("upload").closest(".upload");
for(const event of ["dragenter","dragover"]){
 drop.addEventListener(event,e=>{e.preventDefault();drop.classList.add("dragover");});
}
for(const event of ["dragleave","drop"]){
 drop.addEventListener(event,e=>{e.preventDefault();drop.classList.remove("dragover");});
}
drop.addEventListener("drop",e=>{
 const file=e.dataTransfer?.files?.[0];
 if(file)loadFiles([file]).catch(error=>msg("Lỗi nhập CSV: "+error.message));
});
$("stop").addEventListener("click",()=>{
 scanToken++;busy(false);$("progress-title").textContent="Đã dừng theo yêu cầu";
 drawQueue();msg("Đã dừng. Kết quả phân tích được giữ đến thời điểm dừng.");
});
$("search").addEventListener("input",drawQueue);
$("filter").addEventListener("change",drawQueue);
$("csvall").addEventListener("click",()=>exportFile("csv"));
$("export-integrity").addEventListener("click",exportIntegrity);
$("xlsxall").addEventListener("click",()=>exportFile("xlsx"));
$("save").addEventListener("click",()=>saveReview().catch(e=>msg(e.message)));
$("next").addEventListener("click",nextProfile);
$("open-review-tab").addEventListener("click",()=>openManualProfile(chosen).catch(e=>stateText(e.message)));
$("capture-review-tab").addEventListener("click",()=>captureManualProfile().catch(e=>stateText(e.message)));
$("open-next-tab").addEventListener("click",()=>{
 const current=results.findIndex(x=>x.profileUrl===chosen);
 const upcoming=results[current+1];
 if(!upcoming){stateText("Đã đến cuối danh sách trong phạm vi này.");return;}
 select(upcoming.profileUrl);
 openManualProfile(upcoming.profileUrl).catch(e=>stateText(e.message));
});
$("copy").addEventListener("click",()=>{
 const p=byUrl.get(chosen);
 if(!p)return;
 navigator.clipboard?.writeText(p.profileUrl).then(()=>msg("Đã sao chép URL hồ sơ.")).
  catch(()=>msg("Không thể sao chép; hãy dùng liên kết hồ sơ bên trên."));
});
// No external fetch(), profile visits, tracking or upload. Optional initial scan
// uses only local extension records. User-imported file remains memory-only.
purgeExpiredAudit().then(loadFromChrome).then(refreshAutoState)
  .catch(e=>msg("Không tải được dữ liệu Chrome; hãy chọn CSV để bắt đầu: "+e.message));
})();