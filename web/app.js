"use strict";
const $=id=>document.getElementById(id);
const nf=n=>new Intl.NumberFormat("vi-VN").format(n);
const setText=(id,s)=>{$(id).textContent=String(s)};
const el=(tag,c="",s)=>{const n=document.createElement(tag);n.className=c;if(s!==undefined)n.textContent=String(s);return n};
const TYPES={LOVE:"Love / Tim",LIKE:"Like (có thể gồm Care)",HAHA:"Haha",WOW:"Wow",SAD:"Sad",ANGRY:"Angry"};
let state={page:"",pageName:"",target:null,source:[],sourceKind:"",report:null,watchId:null,busy:false};
async function req(url,options={}){
 const res=await fetch(url,{...options,headers:{"Content-Type":"application/json",...(options.headers||{})}});
 let data;try{data=await res.json()}catch{throw Error("Máy chủ trả về phản hồi không hợp lệ.")};
 if(!res.ok)throw Error(typeof data.error==="string"?data.error:data.error?.message||"Lỗi truy cập.");
 return data;
}
function notice(message,error=false){const n=$("activity-message");n.textContent=message;n.style.color=error?"#ae3e47":""}
function busy(flag,msg="Đang quét..."){state.busy=flag;const btn=$("scan-btn");btn.disabled=flag||!state.page;btn.firstElementChild.textContent=flag?msg:"Quét & phân tích tương tác"}
function clearTarget(clearURL=false){
 state.target=null;state.report=null;state.watchId=null;$("result").hidden=true;$("selected-target").hidden=true;
 if(clearURL)$("target-url").value="";
}
function chooseTarget(objectId,postId,title,url=""){
 clearTarget();state.target={objectId:String(objectId),postId:String(postId),title};
 $("selected-target").hidden=false;setText("target-description",title);
 if(url)$("target-url").value=url;
 $("source-browser").hidden=true;
 notice("Đã chọn "+title+". Nhấn “Quét & phân tích tương tác”.");
}
function connection(kind,message){
 const label=$("connection-label");
 label.className="connection "+(kind==="ok"?"":kind==="loading"?"checking":"error");
 label.textContent=kind==="ok"?"● Meta đã kết nối":kind==="loading"?"Đang xác minh Meta...":kind==="expired"?"● Token Meta hết hạn":"● Cần kiểm tra kết nối";
 const warning=$("auth-warning");warning.hidden=kind==="ok"||kind==="loading";
 warning.textContent=kind==="expired"?"Meta thông báo token hết hạn. Mở F:\\VOIDSCAN\\setup-voidscan-token.bat, lưu token mới rồi nhấn ↻.":(message||"Chưa có quyền truy cập Page phù hợp.");
}
async function loadPages(){
 connection("loading","");const select=$("page-select");
 const previous=state.page;select.replaceChildren(new Option("Đang kiểm tra Page...",""));
 try{
  const data=await req("/api/meta/pages");const pages=data.pages||[];
  select.replaceChildren(new Option("— Chọn Facebook Page —",""));
  pages.forEach(p=>{if(/^\d+$/.test(p.id))select.add(new Option(p.name,p.id))});
  const saved=localStorage.getItem("voidscan:selected-page");
  const chosen=pages.find(p=>p.id===previous)||pages.find(p=>p.id===saved)||(pages.length===1?pages[0]:null);
  state.page=chosen?.id||"";state.pageName=chosen?.name||"";
  if(chosen)select.value=chosen.id;
  connection(data.status==="ready"&&pages.length?"ok":data.error?.kind==="expired"?"expired":"error",data.error?.message||data.message);
  setText("page-help",pages.length?nf(pages.length)+" Page được Meta trả về.":"Không có Page khả dụng, hãy kiểm tra quyền.");
 }catch(e){state.page="";select.replaceChildren(new Option("Không tải được Page",""));connection("error",e.message);setText("page-help",e.message)}
 $("choose-photos").disabled=!state.page;$("choose-posts").disabled=!state.page;busy(false);
}
function pageChanged(){
 state.page=$("page-select").value;state.pageName=$("page-select").selectedOptions[0]?.textContent||"";
 try{localStorage.setItem("voidscan:selected-page",state.page)}catch(_){}
 clearTarget(true);$("source-browser").hidden=true;
 $("choose-photos").disabled=!state.page;$("choose-posts").disabled=!state.page;busy(false);
 notice(state.page?"Đã chọn Page. Tiếp theo hãy chọn ảnh hoặc dán đường dẫn.":"Hãy chọn Page trước.",!state.page);
}
function rowOption(label,subtitle,click,isPost=false){
 const b=el("button","source-option");b.type="button";
 const icon=el("span","thumb",isPost?"▤":"▧");
 const content=el("span");content.append(el("strong","",label),el("small","",subtitle));
 b.append(icon,content);b.addEventListener("click",click);return b;
}
function renderSource(){
 const q=$("source-filter").value.trim().toLocaleLowerCase("vi-VN");
 const root=$("source-list");root.replaceChildren();
 const items=state.source.filter(x=>(x.excerpt+" "+x.id+" "+(x.created_time||"")).toLocaleLowerCase("vi-VN").includes(q));
 if(!items.length){root.append(el("p","empty","Không tìm thấy mục phù hợp."));return}
 for(const item of items.slice(0,75)){
  const title=(item.excerpt||"Đối tượng Facebook").slice(0,100);
  root.append(rowOption(title,(item.created_time||"").slice(0,10)+" · ID "+item.id.slice(-10),async()=>{
   if(state.sourceKind==="photos")chooseTarget(item.id,item.id,"Ảnh dự thi · "+item.id,item.url||"");
   else if(state.sourceKind==="posts")await inspectPost(item);
   else chooseTarget(item.id,item.postId,"Ảnh trong bài · "+item.id,item.url||"");
  },state.sourceKind==="posts"));
 }
}
async function listSource(kind){
 if(!state.page)return notice("Chọn Page trước.",true);
 const btn=$(kind==="photos"?"choose-photos":"choose-posts");btn.disabled=true;
 notice("Đang đọc danh sách từ Meta...");
 try{
  const path=(kind==="photos"?"/api/reactions/photos?page_id=":"/api/meta/posts?page_id=")+encodeURIComponent(state.page);
  const data=await req(path);
  if(data.status!=="ready")throw Error(data.error?.message||"Meta không cấp quyền cho nguồn này.");
  state.source=(data.items||[]).map(x=>({...x,excerpt:x.excerpt||"",created_time:x.created_time||""}));
  state.sourceKind=kind;$("source-browser").hidden=false;$("source-filter").value="";
  setText("source-title",kind==="photos"?"Chọn ảnh từ Page":"Chọn bài đăng");
  setText("source-foot",nf(state.source.length)+" mục trong phạm vi Meta cho phép."+(data.partial?" Có thể còn mục cũ chưa tải.":""));
  renderSource();
  notice(state.source.length?"Đã tải danh sách. Hãy chọn ảnh/bài cần kiểm tra.":"Không tìm thấy đối tượng.");
 }catch(e){notice(e.message,true)}
 finally{btn.disabled=false}
}
async function inspectPost(post){
 notice("Đang kiểm tra các ảnh trong bài...");
 try{
  const data=await req("/api/reactions/objects?"+new URLSearchParams({page_id:state.page,post_id:post.id}));
  if(data.status!=="ready")throw Error(data.error?.message||"Không đọc được bài đăng.");
  await inspectAttachments(data.post,data.attachments||{});
 }catch(e){notice(e.message,true)}
}
async function inspectAttachments(post,attachments){
 const objects=(attachments.items||[]).filter(x=>/^\d+$/.test(x.id));
 if(!objects.length){
  chooseTarget(post.id,post.id,"Bài đăng mẹ · "+post.id,post.url||"");
  if(attachments.status==="unavailable")notice("Meta chưa cho đọc ảnh trong bài; chỉ đang chọn bài mẹ, không suy ra số của ảnh con.",true);
  return true;
 }
 state.source=objects.map(x=>({id:x.id,postId:post.id,excerpt:x.label||"Ảnh đính kèm",url:x.url||"",created_time:""}));
 state.sourceKind="attachments";$("source-browser").hidden=false;
 $("source-filter").value="";setText("source-title","Chọn ảnh dự thi trong bài");
 setText("source-foot","Có "+nf(objects.length)+" ảnh/tệp đính kèm. Không tự sử dụng số reaction của bài mẹ.");
 renderSource();notice("Hãy chọn đúng ảnh trong danh sách để tiếp tục.");
 return false;
}
async function resolveLink(){
 const url=$("target-url").value.trim();if(!url)throw Error("Bạn chưa chọn ảnh hoặc nhập đường dẫn.");
 const data=await req("/api/reactions/resolve-share?"+new URLSearchParams({page_id:state.page,url}));
 if(data.status!=="ready")throw Error(data.error?.message||data.message||"Không xác minh được đường dẫn; hãy dùng “Chọn ảnh đã đăng”.");
 if(data.kind==="photo"){chooseTarget(data.object_id,data.post_id,"Ảnh · "+data.object_id,url);return true}
 const result=await req("/api/reactions/objects?"+new URLSearchParams({page_id:state.page,post_id:data.post_id}));
 if(result.status!=="ready")throw Error(result.error?.message||"Meta không trả về đối tượng.");
 return inspectAttachments(result.post,result.attachments||{});
}
async function scan(){
 if(state.busy)return;if(!state.page)return notice("Chọn Page để bắt đầu.",true);
 busy(true,"Đang lấy reaction...");
 try{
  if(!state.target){const resolved=await resolveLink();if(!resolved)return}
  const target=state.target;
  const snap=await req("/api/reactions/snapshot",{method:"POST",body:JSON.stringify({
    page_id:state.page,post_id:target.postId,object_id:target.objectId
  })});
  await loadReport(target);
  notice(snap.snapshot_id?"Đã lưu mốc mới và cập nhật báo cáo.":"Meta không trả số reaction mới; đang xem lịch sử sẵn có.",!snap.snapshot_id);
 }catch(e){notice(e.message,true)}
 finally{busy(false)}
}
async function loadReport(target=state.target){
 if(!target)return;
 const query=new URLSearchParams({page_id:state.page,object_id:target.objectId,type:$("reaction-kind").value});
 const data=await req("/api/reactions/report?"+query);state.report=data;
 const a=data.assessment;
 $("result").hidden=false;setText("result-title",a.headline);
 setText("result-detail",state.pageName+" · "+target.title+" · "+TYPES[a.reaction_type]);
 setText("total-reactions",a.current_reactions===null?"—":nf(a.current_reactions));
 setText("flagged-reactions",a.suspicious_window_reactions===null?"—":nf(a.suspicious_window_reactions));
 setText("flagged-percentage",a.suspicious_share_pct===null?"—":a.suspicious_share_pct.toLocaleString("vi-VN")+"%");
 setText("bot-probability","Chưa xác định");
 const quality=a.data_quality||{};
 setText("sample-count",nf(a.observed_snapshots)+" mốc đo · "+nf(quality.eligible_adjacent_intervals||0)+"/6 khoảng đủ điều kiện"+(quality.stale?" · Số liệu đã cũ":""));
 const review=a.evidence_status==="có_chỉ_báo",ok=a.evidence_status==="chưa_phát_hiện";
 $("evidence-badge").className="pill "+(review?"warn":ok?"good":"");
 setText("evidence-badge",review?"Cần rà soát":ok?"Chưa có cảnh báo":"Chưa đủ dữ liệu");
 const verdict=$("verdict");verdict.replaceChildren();verdict.className="verdict "+(review?"warn":"");
 verdict.append(el("strong","",review?"Có khoảng tăng nghi vấn, chưa xác nhận được bot":ok?"Chưa phát hiện đột biến theo mô hình hiện tại":"Chưa đủ lịch sử để đánh giá"));
 verdict.append(el("span","",review?nf(a.suspicious_window_reactions)+" lượt tăng trong "+nf(a.flagged_intervals)+" khoảng đáng rà soát. Không tự trừ số này khỏi điểm cuộc thi.":ok?"Không có cảnh báo không có nghĩa mọi tài khoản đều là người thật.":"VOIDSCAN cần tối thiểu 7 mốc reaction có giá trị. Cuộc thi cũ không thể tự tái dựng lịch sử đã mất."));
 if(quality.missing_counts||quality.long_gaps||quality.repeated_timestamps||quality.invalid_timestamps||quality.negative_corrections){
  verdict.append(el("p","", "Chất lượng dữ liệu: "+nf(quality.missing_counts||0)+" mốc thiếu số · "+nf(quality.long_gaps||0)+" khoảng đo gián đoạn · "+nf(quality.repeated_timestamps||0)+" timestamp trùng · "+nf(quality.invalid_timestamps||0)+" timestamp không hợp lệ · "+nf(quality.negative_corrections||0)+" lần số reaction giảm hoặc được sửa. Không suy diễn số bot từ các khoảng này."));
 }
 if(quality.stale)verdict.append(el("p","","Lần quan sát mới nhất đã cũ. Cần quét lại để cập nhật tổng reaction."));
 plot(data.observations||[]);intervals(a.intervals||[]);
 renderR1Comparison(data.r1_research_comparison);
 await syncWatch();
 $("result").scrollIntoView({behavior:"smooth",block:"start"});
}
function renderR1Comparison(data){
 const root=$("r1-baselines");root.replaceChildren();
 if(!data||data.status!=="experimental_unvalidated"){
   root.append(el("p","empty","Chưa đủ các khoảng thời gian hợp lệ để đối chiếu thuật toán. Bật theo dõi định kỳ để có chuỗi dữ liệu."));
   return;
 }
 const intro=el("p","field-help","Đã so sánh "+nf(data.evaluated_intervals)+" khoảng với 3 mô hình cùng dùng một nguồn dữ liệu Meta. Các con số chỉ là chỉ báo nghiên cứu; không dùng để trừ điểm.");
 root.append(intro);
 for(const [name,m] of Object.entries(data.method_results)){
   const row=el("div","evidence-row");
   const description=el("span","",m.name);
   const result=el("strong","",nf(m.flagged_intervals)+" khoảng · "+nf(m.flagged_growth)+" lượt tăng nằm trong khoảng bị gắn cờ");
   row.append(description,result);root.append(row);
 }
 root.append(el("p","field-help","Đồng thuận từ 2/3 phương pháp: "+nf(data.multi_method_agreement_intervals)+" khoảng. Đồng thuận KHÔNG đồng nghĩa xác suất gian lận. Các phương pháp cùng đọc một chuỗi reaction, nên không cung cấp bằng chứng độc lập."));
 root.append(el("p","field-help","Phần tăng vượt baseline chỉ là ước tính thống kê, không phải số tài khoản ảo hay lượt cần trừ."));
}
function intervals(values){
 const root=$("flagged-intervals");root.replaceChildren();const flagged=values.filter(x=>x.flagged);
 if(!flagged.length){root.append(el("p","empty","Chưa có khoảng tăng trưởng đủ điều kiện gắn cờ."));return}
 flagged.forEach(x=>{const row=el("div","evidence-row");
  row.append(el("span","",x.from.replace("T"," ").slice(0,16)+" → "+x.to.replace("T"," ").slice(0,16)+" UTC"),
             el("strong","",nf(x.delta)+" lượt tăng · "+x.per_minute+"/phút"));
  root.append(row);
 });
}
function plot(rows){
 const root=$("trend-chart");root.replaceChildren();
 const values=rows.map(x=>({t:Date.parse(x.observed_at),v:x.value})).filter(x=>Number.isFinite(x.t)&&Number.isInteger(x.v)&&x.v>=0);
 if(values.length<2){root.append(el("p","","Chưa đủ hai mốc hợp lệ để vẽ đồ thị. Bật theo dõi để tích lũy dữ liệu."));return}
 const w=680,h=170,p=24;
 const t0=Math.min(...values.map(x=>x.t)),t1=Math.max(...values.map(x=>x.t));
 const v0=Math.min(...values.map(x=>x.v)),v1=Math.max(...values.map(x=>x.v));
 const X=x=>p+(w-2*p)*(x.t-t0)/Math.max(1,t1-t0),Y=x=>h-p-(h-2*p)*(x.v-v0)/Math.max(1,v1-v0);
 const ns="http://www.w3.org/2000/svg";
 const svg=document.createElementNS(ns,"svg");svg.setAttribute("viewBox","0 0 "+w+" "+h);
 svg.setAttribute("role","img");svg.setAttribute("aria-label","Reaction theo thời gian");
 const node=(tag,attrs)=>{const z=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))z.setAttribute(k,String(v));return z};
 svg.append(node("line",{x1:p,y1:h-p,x2:w-p,y2:h-p,stroke:"#d4dbeb","stroke-width":1}));
 svg.append(node("polyline",{points:values.map(x=>X(x)+","+Y(x)).join(" "),stroke:"#644bc3","stroke-width":3,fill:"none"}));
 values.slice(-35).forEach(x=>{const z=node("circle",{cx:X(x),cy:Y(x),r:3,fill:"#644bc3"});const tip=node("title",{});tip.textContent=nf(x.v)+" reaction, "+new Date(x.t).toLocaleString("vi-VN");z.append(tip);svg.append(z)});
 root.append(svg);
}
async function syncWatch(){
 if(!state.target)return;
 try{
  const d=await req("/api/reactions/watches");
  const w=(d.items||[]).find(x=>x.active&&x.page_id===state.page&&x.object_id===state.target.objectId);
  state.watchId=w?.id||null;setText("watch-btn",w?"Dừng theo dõi định kỳ":"Bật theo dõi định kỳ");
  setText("watch-note",w?"Đang ghi số liệu theo chu kỳ khi server chạy.":"Thao tác này giúp VOIDSCAN có lịch sử để nhận diện tăng đột biến.");
 }catch{state.watchId=null}
}
async function toggleWatch(){
 if(!state.target)return notice("Chọn ảnh trước khi theo dõi.",true);
 $("watch-btn").disabled=true;
 try{
  if(state.watchId){await req("/api/reactions/toggle",{method:"POST",body:JSON.stringify({id:state.watchId,active:false})});notice("Đã dừng theo dõi.") }
  else{const t=state.target;const x=await req("/api/reactions/watch",{method:"POST",body:JSON.stringify({page_id:state.page,post_id:t.postId,object_id:t.objectId})});if(!x.watch_id)throw Error("Meta không có dữ liệu đủ điều kiện theo dõi.");notice("Đã bật theo dõi. Giữ server hoạt động để ghi các mốc tiếp theo.")}
  await syncWatch();
 }catch(e){notice(e.message,true)}finally{$("watch-btn").disabled=false}
}
function exportCSV(){if(!state.target)return notice("Chưa có ảnh để xuất.",true);location.href="/api/reactions/export.csv?"+new URLSearchParams({page_id:state.page,object_id:state.target.objectId})}
function navigate(name){
 document.querySelectorAll(".nav-button").forEach(x=>x.classList.toggle("active",x.dataset.view===name));
 document.querySelectorAll(".view").forEach(x=>x.classList.toggle("active",x.id==="view-"+name));
 setText("top-title",({scan:"Quét tương tác",history:"Theo dõi & lịch sử",method:"Hiểu kết quả"})[name]);
 if(name==="history")loadHistory();window.scrollTo({top:0,behavior:"smooth"});
}
async function loadHistory(){
 const watches=$("watch-list"),scans=$("scan-list");watches.replaceChildren();scans.replaceChildren();
 try{
  const [wh,sh]=await Promise.all([req("/api/reactions/watches"),req("/api/scans")]);
  for(const item of (wh.items||[]).slice(0,40)){
   const row=el("div","history-item"),left=el("div");
   left.append(el("b","",item.active?"● Đang theo dõi":"○ Đã dừng"),el("p","","Đối tượng "+item.object_id+" · Lần đo: "+(item.last_checked?.slice(0,19)||"Chưa có")));
   const actions=el("div","history-actions"),viewBtn=el("button","btn secondary small","Xem báo cáo"),toggle=el("button","btn quiet small",item.active?"Dừng":"Bật lại");
   viewBtn.addEventListener("click",async()=>{
    state.page=item.page_id;const select=$("page-select");if([...select.options].some(x=>x.value===item.page_id))select.value=item.page_id;
    state.pageName=select.selectedOptions[0]?.textContent||"Page";chooseTarget(item.object_id,item.post_id,"Đối tượng đã theo dõi · "+item.object_id);
    navigate("scan");try{await loadReport()}catch(e){notice(e.message,true)}
   });
   toggle.addEventListener("click",async()=>{try{await req("/api/reactions/toggle",{method:"POST",body:JSON.stringify({id:item.id,active:!item.active})});await loadHistory()}catch(e){notice(e.message,true)}});
   actions.append(viewBtn,toggle);row.append(left,actions);watches.append(row);
  }
  if(!watches.children.length)watches.append(el("p","empty","Chưa theo dõi ảnh nào. Quay lại trang Quét và bật theo dõi định kỳ."));
  (sh.items||[]).slice(0,20).forEach(x=>{const row=el("div","history-item"),body=el("div");body.append(el("b","",x.created_at?.slice(0,19).replace("T"," ")||"Lần quét"),el("p","",(x.post_url||"")+" · "+(x.status||"")));row.append(body);scans.append(row)});
  if(!scans.children.length)scans.append(el("p","empty","Chưa có lịch sử quét bài đăng."));
 }catch(e){notice(e.message,true)}
}
$("page-select").addEventListener("change",pageChanged);
$("choose-photos").addEventListener("click",()=>listSource("photos"));
$("choose-posts").addEventListener("click",()=>listSource("posts"));
$("close-sources").addEventListener("click",()=>{$("source-browser").hidden=true});
$("source-filter").addEventListener("input",renderSource);
$("clear-target").addEventListener("click",()=>clearTarget(true));
$("target-url").addEventListener("input",()=>{if(state.target)clearTarget()});
$("target-url").addEventListener("keydown",e=>{if(e.key==="Enter")scan()});
$("reaction-kind").addEventListener("change",async()=>{if(state.report&&state.target){try{await loadReport()}catch(e){notice(e.message,true)}}});
$("scan-btn").addEventListener("click",scan);
$("watch-btn").addEventListener("click",toggleWatch);
$("export-btn").addEventListener("click",exportCSV);
$("refresh-all").addEventListener("click",loadPages);
$("history-refresh").addEventListener("click",loadHistory);
$("history-export").addEventListener("click",()=>location.href="/api/export-history.csv");
document.querySelectorAll(".nav-button").forEach(b=>b.addEventListener("click",()=>navigate(b.dataset.view)));
loadPages();
