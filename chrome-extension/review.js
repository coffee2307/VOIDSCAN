(() => {
"use strict";
const $=id=>document.getElementById(id);
const FILE=window.VoidscanFileAudit,LIB=window.VoidscanAudit, XLSX=window.VoidscanXlsx;
const STORAGE_REACTIONS="voidscan_reactions_v1",STORAGE_PENDING="voidscan_pending_reactions_v1";
const STORAGE_DECISIONS="voidscan_screening_reviews_v1",MAX_CSV_BYTES=15*1024*1024;
let scanToken=0,source=[],allSource=[],sourceOrigin="",profiles=[],results=[],byUrl=new Map(),chosen="",decisionMap={};
let sourceLabel="Dữ liệu trong Chrome";
let currentProgress={done:0,total:0,flagged:0,clear:0};
const fmt=n=>Number(n||0).toLocaleString("vi-VN");
const msg=text=>{$("toast").textContent=text;};
const busy=flag=>{
 $("stop").disabled=!flag;
 $("source-local").disabled=flag;
 $("upload").disabled=flag;
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
 $("checked").textContent=fmt(currentProgress.done);
 $("progress-number").textContent=fmt(currentProgress.done)+" / "+fmt(currentProgress.total)+" tài khoản";
 const pc=currentProgress.total?Math.round(currentProgress.done/currentProgress.total*100):0;
 $("progress-bar").style.width=pc+"%";
 $("progress-track").setAttribute("aria-valuenow",pc);
}
function listFiltered(){
 const q=$("search").value.trim().toLowerCase(),mode=$("filter").value;
 return results.filter(p=>{
  if(mode==="flagged"&&p.status!==FILE.LABEL_SUSPECT)return false;
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
  item.append(safeText("small",(p.status===FILE.LABEL_SUSPECT?"● Nghi vấn":"● Không có dấu hiệu")+
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
 $("level").className="pill "+(p.status===FILE.LABEL_SUSPECT?"suspect":"clear");
 $("nphotos").textContent=fmt(p.photoCount);
 $("nunknown").textContent=fmt(p.unknownRows);
 $("nfields").textContent=fmt(p.availableInfoPoints)+"/6";
 $("reasons").replaceChildren(safeText("p",p.evidence));
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
  profiles=prepared.profiles;
  currentProgress={total:profiles.length,done:0,flagged:0,clear:0};
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
   "Không kiểm tra bio, địa phương, bạn bè hoặc hoạt động nếu CSV không cung cấp; chưa xác minh tính thật/giả.";
  $("progress-title").textContent="Đang phân tích dữ liệu CSV — không mở profile Facebook";
  const decisions=await chrome.storage.local.get(STORAGE_DECISIONS);
  decisionMap=decisions[STORAGE_DECISIONS]&&typeof decisions[STORAGE_DECISIONS]==="object"?
    decisions[STORAGE_DECISIONS]:{};
  for(let i=0;i<profiles.length;i++){
   if(ticket!==scanToken){$("progress-title").textContent="Đã dừng.";return;}
   const row=FILE.scoreProfile(profiles[i],prepared.photoTotal,decisionMap);
   results.push(row);byUrl.set(row.profileUrl,row);
   currentProgress.done++;
   if(row.status===FILE.LABEL_SUSPECT)currentProgress.flagged++;
   else currentProgress.clear++;
   updateCounter();
   setLast(row);
   // Yield regularly so Chrome paints counters and n/n progress mid-scan.
   if(i%8===7)await sleep(8);
  }
  if(ticket!==scanToken)return;
  $("progress-title").textContent="Hoàn tất phân tích CSV (chưa xác minh profile)";
  drawQueue();
  msg("Hoàn thành "+fmt(currentProgress.done)+" URL trong CSV của phạm vi đã chọn. "+
   fmt(currentProgress.flagged)+" có tín hiệu cần rà soát; "+fmt(currentProgress.clear)+
   " chưa thấy tín hiệu trong CSV. Số hồ sơ Facebook thực sự được mở/kiểm tra: 0.");
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
 const chosen=options.some(p=>p.photoId===active)?active:(options.at(-1)?.photoId||"all");
 select.value=chosen;
 await scanScope();
}
async function scanScope(){
 const photo=$("photo-scope").value;
 $("scope-hint").textContent=photo==="all"?
   "Đang TỔNG HỢP TẤT CẢ ẢNH — chuyển về Photo ID để tách riêng.":
   "Chỉ phân tích ảnh "+photo+"; các ảnh còn lại không bị cộng vào.";
 const valid=FILE.normaliseRows(allSource).rows;
 await scan(photo==="all"?valid:LIB.scopedRows(valid,photo),sourceOrigin+
  (photo==="all"?" · Tất cả ảnh":" · Ảnh "+photo));
}
async function loadFromChrome(){
 const saved=await chrome.storage.local.get([STORAGE_REACTIONS,STORAGE_PENDING]);
 const classified=Array.isArray(saved[STORAGE_REACTIONS])?saved[STORAGE_REACTIONS]:[];
 const pending=Array.isArray(saved[STORAGE_PENDING])?saved[STORAGE_PENDING]:[];
 const known=new Set(classified.map(r=>r.photoId+"|"+r.profileUrl));
 const merged=[...classified,...pending.filter(r=>!known.has(r.photoId+"|"+r.profileUrl))];
 await useSource(merged,"Dữ liệu trong Chrome · "+fmt(merged.length)+" dòng reaction");
}
async function loadFile(file){
 if(!file)return;
 if(file.size>MAX_CSV_BYTES)throw Error("File vượt 15 MB; hãy chia nhỏ để quét.");
 if(!/\.csv$/i.test(file.name)&&file.type!=="text/csv"&&file.type!=="text/plain")
   throw Error("Chỉ hỗ trợ file .csv. Xuất CSV từ popup VOIDSCAN trước.");
 const fileText=await file.text();
 const parsed=FILE.parseCSV(fileText);
 await useSource(parsed.rows,file.name+" · "+fmt(parsed.rows.length)+" dòng · không tải lên máy chủ");
}
function allRows(flaggedOnly){
 return results.filter(p=>!flaggedOnly||p.status===FILE.LABEL_SUSPECT);
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
   // Human disagreement triggers manual-review label, with explanation.
   p.status=FILE.LABEL_SUSPECT;
   p.evidence+=" | Được người duyệt đánh dấu cần xem kỹ hơn";
   currentProgress.flagged++;currentProgress.clear--;
   updateCounter();
 }
 drawQueue();msg("Đã lưu đánh giá của người kiểm tra. Không tự loại phiếu.");
}
function nextProfile(){
 const queue=listFiltered();
 const ix=queue.findIndex(x=>x.profileUrl===chosen);
 if(ix>=0&&ix<queue.length-1)select(queue[ix+1].profileUrl);
 else msg("Đã đến cuối danh sách trong bộ lọc hiện tại.");
}
$("source-local").addEventListener("click",()=>loadFromChrome().catch(e=>msg("Lỗi đọc dữ liệu Chrome: "+e.message)));
$("photo-scope").addEventListener("change",()=>scanScope().catch(e=>msg("Lỗi thay đổi phạm vi ảnh: "+e.message)));
$("upload").addEventListener("change",e=>{
 const file=e.target.files?.[0];
 if(file)loadFile(file).catch(e=>msg("Không nhập được CSV: "+e.message));
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
 if(file)loadFile(file).catch(error=>msg("Lỗi nhập CSV: "+error.message));
});
$("stop").addEventListener("click",()=>{
 scanToken++;busy(false);$("progress-title").textContent="Đã dừng theo yêu cầu";
 drawQueue();msg("Đã dừng. Kết quả phân tích được giữ đến thời điểm dừng.");
});
$("search").addEventListener("input",drawQueue);
$("filter").addEventListener("change",drawQueue);
$("csvall").addEventListener("click",()=>exportFile("csv"));
$("xlsxall").addEventListener("click",()=>exportFile("xlsx"));
$("save").addEventListener("click",()=>saveReview().catch(e=>msg(e.message)));
$("next").addEventListener("click",nextProfile);
$("copy").addEventListener("click",()=>{
 const p=byUrl.get(chosen);
 if(!p)return;
 navigator.clipboard?.writeText(p.profileUrl).then(()=>msg("Đã sao chép URL hồ sơ.")).
  catch(()=>msg("Không thể sao chép; hãy dùng liên kết hồ sơ bên trên."));
});
// No external fetch(), profile visits, tracking or upload. Optional initial scan
// uses only local extension records. User-imported file remains memory-only.
loadFromChrome().catch(e=>msg("Chưa có dữ liệu local. Chọn CSV từ popup: "+e.message));
})();