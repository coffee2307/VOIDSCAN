"use strict";
const $=id=>document.getElementById(id);
const fmt=n=>new Intl.NumberFormat("vi-VN").format(Number(n)||0);
const labels={live:"Đọc được từ Meta",matched:"Đối chiếu CSV mới",unavailable:"Chưa đủ dữ liệu"};
const sourceLabels={meta_graph_api:"Meta Graph API",local_csv:"Dữ liệu chủ động nhập",none:"Không có nguồn"};
let toastTimer=0;
function el(tag,value,cls){const x=document.createElement(tag);if(value!=null)x.textContent=String(value);if(cls)x.className=cls;return x}
function notify(message){const b=$("toast");b.textContent=message;b.classList.add("visible");clearTimeout(toastTimer);toastTimer=setTimeout(()=>b.classList.remove("visible"),4500)}
function text(id,value){$(id).textContent=String(value)}
async function api(path,options={}){const response=await fetch(path,{...options,headers:{"Content-Type":"application/json",...(options.headers||{})}});let body;try{body=await response.json()}catch{throw Error("Máy chủ trả về phản hồi không hợp lệ")}if(!response.ok)throw Error(body.error||"Lỗi truy cập");return body}
function goto(name){document.querySelectorAll(".nav-item").forEach(x=>x.classList.toggle("active",x.dataset.view===name));document.querySelectorAll(".panel-view").forEach(x=>x.classList.toggle("active",x.id==="view-"+name));text("breadcrumb",({overview:"Scan bài đăng",history:"Lịch sử phân tích",sources:"Nguồn dữ liệu",method:"Phương pháp"})[name]);window.scrollTo({top:0,behavior:"smooth"})}
function td(row,value){const c=el("td");if(value instanceof Node)c.append(value);else c.textContent=String(value);row.append(c);return c}
function badge(status){const b=el("span",labels[status]||status,"flag "+(status==="unavailable"?"unverified":status==="live"?"keep":""));return b}
function historyRow(x,summary=false){const tr=el("tr");td(tr,x.created_at.slice(0,19).replace("T"," "));if(!summary){const url=el("span",x.post_url);url.className="history-url";td(tr,url);}td(tr,sourceLabels[x.source]||x.source);td(tr,badge(x.status));td(tr,fmt(x.evidence_count));if(!summary)td(tr,fmt(x.signal_count));tr.tabIndex=0;tr.addEventListener("click",()=>detail(x.id));tr.addEventListener("keydown",e=>{if(e.key==="Enter")detail(x.id)});return tr}
function renderStatus(data){const m=data.stats||{};for(const k of ["scans","live","flagged","unavailable"])text("metric-"+k,fmt(m[k]));const ready=data.connectors?.meta===true;text("meta-state",ready?"Có token":"Chưa cấu hình");text("meta-state-detail",ready?"Có token — chưa kiểm tra quyền":"Chưa cấu hình token");text("source-explainer",ready?"Đã nhận cấu hình token, nhưng quyền truy cập chỉ được xác minh khi chạy Scan thực tế.":"Chưa thiết lập token Meta Page; chỉ có thể đối chiếu với nguồn mới được bạn nhập.");const history=data.history||[];const recent=$("recent-table");recent.replaceChildren();history.forEach(x=>recent.append(historyRow(x,true)));if(history.length===0){const row=el("tr"),cell=td(row,"Chưa có lượt Scan nào. Hãy nhập URL để bắt đầu.");cell.colSpan=4;cell.className="empty";recent.append(row)}text("live-status", "● Đã kết nối")}
async function loadStatus(){try{const result=await api("/api/status");renderStatus(result)}catch(e){text("live-status","● LỖI KẾT NỐI");notify(e.message)}}
async function loadHistory(){try{const data=await api("/api/scans");const table=$("history-table");table.replaceChildren();data.items.forEach(x=>table.append(historyRow(x)));if(!data.items.length){const tr=el("tr"),c=td(tr,"Chưa có kết quả được lưu.");c.colSpan=6;c.className="empty";table.append(tr)}text("history-foot",fmt(data.items.length)+" kết quả gần nhất · Lịch sử tổng hợp lưu 90 ngày")}catch(e){notify(e.message)}}
function rows(parent,entries){const dl=el("dl");for(const [key,val] of entries){const row=el("div",null,"detail-row");row.append(el("dt",key),el("dd",val==null?"—":val));dl.append(row)}parent.append(dl)}
async function detail(scanId){try{const r=await api("/api/scans/"+scanId);const box=$("history-detail");box.replaceChildren();rows(box,[["Thời gian UTC",r.created_at],["Đường dẫn",r.post_url],["Trạng thái",labels[r.status]||r.status],["Nguồn",sourceLabels[r.source]||r.source],["Mẫu quan sát",r.evidence_count],["Số loại tín hiệu",r.signal_count],["Lưu ý",r.result.message]]);if(r.result.signals?.length){box.append(el("h3","Tín hiệu được lưu"));renderSignals(box,r.result.signals)}$("history-dialog").showModal()}catch(e){notify(e.message)}}
function renderSignals(parent,signals){const table=el("table");const header=el("tr");["TÍN HIỆU","SỐ LƯỢNG","DIỄN GIẢI"].forEach(t=>header.append(el("th",t)));table.append(header);for(const x of signals){const tr=el("tr");td(tr,x.label);td(tr,fmt(x.count));td(tr,x.explanation);table.append(tr)}const scroll=el("div",null,"table-scroll");scroll.append(table);parent.append(scroll)}
function renderResult(data){const box=$("scan-result");box.className="scan-result";$("scan-details").replaceChildren();const parts=[];if(data.status==="live"){parts.push("ĐÃ TRUY CẬP META GRAPH API (MẪU GIỚI HẠN)");parts.push("Bình luận quan sát: "+fmt(data.comments)+" · Comment lặp nguyên văn: "+fmt(data.suspicious));}else if(data.status==="matched"){parts.push("TÌM THẤY DỮ LIỆU MỚI ĐƯỢC NHẬP");parts.push("Bản ghi: "+fmt(data.total)+" · Bản ghi lặp cùng lớp: "+fmt(data.duplicates)+" · Thiếu ID: "+fmt(data.unverified));}else{parts.push("CHƯA THỂ ĐÁNH GIÁ BÀI ĐĂNG");box.classList.add("error")}parts.push(data.message||"Không đủ dữ liệu để đánh giá.");if(data.page?.name)parts.push("Page: "+data.page.name+" · Đã xác minh nguồn bài viết");if(data.coverage?.comment_sample_capped)parts.push("CẢNH BÁO: API còn trang bình luận chưa đọc, kết quả chỉ là mẫu.");if(data.scan_id)parts.push("Scan ID: "+data.scan_id.slice(0,12));box.textContent=parts.join("\n");if(data.signals?.length){const area=$("scan-details");area.append(el("h2","Tín hiệu quan sát được"));renderSignals(area,data.signals);if(data.examples?.length){area.append(el("h2","Bản ghi gợi ý rà soát (hiển thị tạm thời)"));const table=el("table");for(const item of data.examples.slice(0,20)){const tr=el("tr");td(tr,item.class);td(tr,item.name);td(tr,item.profile_id);td(tr,item.signal);table.append(tr)}const scroll=el("div",null,"table-scroll");scroll.append(table);area.append(scroll)}}}
async function scan(){const url=$("scan-url").value.trim();if(!url){text("scan-result","Vui lòng nhập URL bài Facebook.");return}const btn=$("scan-button");btn.disabled=true;text("scan-result","Đang xác minh nguồn và thực hiện phân tích...");$("scan-details").replaceChildren();try{const data=await api("/api/scan",{method:"POST",body:JSON.stringify({url,page_id:$("managed-page").value||null})});renderResult(data);await loadStatus();}catch(e){$("scan-result").className="scan-result error";text("scan-result",e.message)}finally{btn.disabled=false}}
async function importFiles(files){const selected=Array.from(files);if(!selected.length)return;if(selected.length>40||selected.some(x=>!x.name.toLowerCase().endsWith(".csv")||x.size>6*1024*1024)){notify("Chỉ chấp nhận tối đa 40 CSV, mỗi file tối đa 6 MB.");return}if(selected.reduce((a,x)=>a+x.size,0)>18*1024*1024){notify("Tổng dung lượng mỗi lần nhập không quá 18 MB.");return}text("upload-feedback","Đang nhập dữ liệu mới...");try{const out=[];for(const file of selected){const raw=new Uint8Array(await file.arrayBuffer());let binary="";for(let i=0;i<raw.length;i+=16384)binary+=String.fromCharCode(...raw.slice(i,i+16384));out.push({name:file.name,content:btoa(binary)})}const response=await api("/api/import",{method:"POST",body:JSON.stringify({files:out})});text("upload-feedback","Đã nhập "+response.files+" file và "+fmt(response.rows)+" bản ghi mới. Quay lại trang Scan để đối chiếu.");notify("Nhập thành công")}catch(e){text("upload-feedback",e.message)}finally{$("file-picker").value=""}}
document.querySelectorAll("[data-view]").forEach(x=>x.addEventListener("click",()=>{goto(x.dataset.view);if(x.dataset.view==="history")loadHistory()}));
document.querySelectorAll("[data-goto]").forEach(x=>x.addEventListener("click",()=>{goto(x.dataset.goto);if(x.dataset.goto==="history")loadHistory()}));
$("scan-button").addEventListener("click",scan);$("scan-url").addEventListener("keydown",e=>{if(e.key==="Enter")scan()});
$("refresh").addEventListener("click",()=>{loadStatus();if($("view-history").classList.contains("active"))loadHistory()});
$("close-dialog").addEventListener("click",()=>$("history-dialog").close());
$("export-history").addEventListener("click",()=>{location.href="/api/export-history.csv"});
$("select-files").addEventListener("click",()=>$("file-picker").click());
$("file-picker").addEventListener("change",e=>importFiles(e.target.files).catch(x=>notify(x.message)));
const drop=$("upload-card");["dragover","dragenter"].forEach(name=>drop.addEventListener(name,e=>{e.preventDefault();drop.classList.add("dragging")}));["drop","dragleave"].forEach(name=>drop.addEventListener(name,e=>{e.preventDefault();drop.classList.remove("dragging")}));drop.addEventListener("drop",e=>importFiles(e.dataTransfer.files).catch(x=>notify(x.message)));
loadStatus();

/* Managed Page connector: only metadata crosses the browser boundary. */
let pageRefreshInProgress=false;
async function loadManagedPages(){
  if(pageRefreshInProgress)return;
  pageRefreshInProgress=true;
  const button=$("check-meta-pages");
  button.disabled=true;
  const picker=$("managed-page");
  const oldSelection=picker.value;
  text("page-access-note","Đang xác minh với Meta...");
  try{
    const data=await api("/api/meta/pages");
    picker.replaceChildren(new Option("Chọn Trang Facebook",""));
    for(const page of data.pages||[]){
      if(/^\d+$/.test(page.id))picker.add(new Option(page.name+" · "+page.id,page.id));
    }
    const choices=Array.from(picker.options).map(opt=>opt.value);
    if(choices.includes(oldSelection))picker.value=oldSelection;
    else if(choices.length===2)picker.value=choices[1];
    const isReady=data.status==="ready"&&picker.options.length>1;
    $("load-page-posts").disabled=!isReady;
    const note=data.error?.message||data.message||"Không có Page khả dụng.";
    text("page-access-note",note);
    text("page-diagnostics",isReady?"Meta đã trả về "+(picker.options.length-1)+" Page hợp lệ. Token chỉ lưu trong tiến trình server.":note);
    if(!isReady)$("page-posts").replaceChildren();
  }catch(e){
    picker.replaceChildren(new Option("Lỗi kết nối Meta",""));
    $("load-page-posts").disabled=true;
    text("page-access-note",e.message);
    text("page-diagnostics",e.message);
  }finally{
    pageRefreshInProgress=false;
    button.disabled=false;
  }
}
async function showManagedPosts(){
  const pageId=$("managed-page").value;
  const area=$("page-posts");
  area.replaceChildren();
  if(!pageId){text("page-access-note","Chọn một Page được xác minh trước.");return;}
  $("load-page-posts").disabled=true;
  text("page-access-note","Đang đọc danh sách bài viết được Meta cho phép...");
  try{
    const data=await api("/api/meta/posts?page_id="+encodeURIComponent(pageId));
    const posts=data.items||[];
    if(!posts.length){area.append(el("div","Không tìm thấy bài có permalink trong phạm vi Graph API trả về.","empty"));return;}
    const lead=el("p","Chọn một bài để điền URL vào ô Scan. Hiển thị tối đa "+posts.length+" bài gần đây"+(data.partial?"; có thể còn những bài khác.":"."));
    area.append(lead);
    for(const item of posts.slice(0,25)){
      if(!item.url)continue;
      const control=el("button",(item.created_time||"").slice(0,10)+" · "+(item.excerpt||item.id),"post-option");
      control.type="button";
      control.addEventListener("click",()=>{
        $("scan-url").value=item.url;
        $("scan-url").focus();
        text("page-access-note","Đã chọn bài thuộc Page. Nhấn Scan để kiểm tra.");
      });
      area.append(control);
    }
    text("page-access-note",posts.length+" bài đọc được từ Meta Page.");
  }catch(e){text("page-access-note",e.message)}finally{$("load-page-posts").disabled=false;}
}
$("managed-page").addEventListener("change",()=>{
  $("page-posts").replaceChildren();
  $("load-page-posts").disabled=!$("managed-page").value;
});
$("check-meta-pages").addEventListener("click",loadManagedPages);
$("load-page-posts").addEventListener("click",showManagedPosts);
loadManagedPages();

/* Accessible user-selected appearance; default is a high-contrast light theme. */
(function setupAppearance(){
  const key="voidscan:appearance";
  let saved="light";
  try{saved=localStorage.getItem(key)==="dark"?"dark":"light"}catch(_){}
  const root=document.documentElement;
  const button=document.getElementById("theme-toggle");
  function apply(mode){
    root.dataset.theme=mode;
    if(button){
      const isDark=mode==="dark";
      button.textContent=isDark?"☀":"☾";
      button.setAttribute("aria-label",isDark?"Chuyển sang nền sáng":"Chuyển sang nền tối");
      button.setAttribute("aria-pressed",String(isDark));
      button.title=isDark?"Chuyển sang nền sáng":"Chuyển sang nền tối";
    }
  }
  apply(saved);
  button?.addEventListener("click",()=>{
    const next=root.dataset.theme==="dark"?"light":"dark";
    apply(next);
    try{localStorage.setItem(key,next)}catch(_){}
  });
})();
