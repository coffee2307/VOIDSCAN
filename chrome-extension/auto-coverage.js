/* Explain evidence coverage and public-metadata attempts without inferring authenticity. */
(function(root,factory){
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanCoverage=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
"use strict";
const CATEGORIES=["public_metadata","page_visible","auth_required","unavailable",
 "timeout","navigation_error","insufficient","restricted","rate_limited",
 "network_error","http_error","large","invalid","cancelled","unknown"];
function category(attempt){
 const s=String(attempt?.status||"");
 return CATEGORIES.includes(s)?s:"unknown";
}
function assess(urls,attempts,profileMap){
 const counters={total:0,withEvidence:0,attempted:0,unattempted:0,
  publicMetadataNoEvidence:0,denied:0,errors:0,missingFields:0,skipped:0};
 const outcomes={};
 const rows=[];
 const seen=new Set();
 for(const url of Array.isArray(urls)?urls:[]){
  if(typeof url!=="string"||seen.has(url))continue;
  seen.add(url);counters.total++;
  const record=profileMap?.[url];
  const att=attempts?.[url];
  const status=record?"with_evidence":att?category(att):"not_attempted";
  if(record)counters.withEvidence++;
  else if(att){
   counters.attempted++;
   if(status==="public_metadata")counters.publicMetadataNoEvidence++;
   else if(["restricted","rate_limited","auth_required"].includes(status))counters.denied++;
   else if(["network_error","navigation_error","timeout","http_error","large","invalid"].includes(status))counters.errors++;
   else if(status==="insufficient")counters.missingFields++;
  } else counters.unattempted++;
  outcomes[status]=(outcomes[status]||0)+1;
  rows.push({profileUrl:url,status,attemptedAt:att?.at||"",
   hasUsableEvidence:Boolean(record)});
 }
 // attempted here excludes urls now with evidence, which are counted separately.
 const attemptedTotal=counters.attempted+rows.filter(r=>r.hasUsableEvidence&&r.attemptedAt).length;
 const coverage=counters.total?Math.round(1000*counters.withEvidence/counters.total)/10:0;
 const diagnosis=!counters.total?"Chưa có danh sách hồ sơ.":
   counters.withEvidence===0?
    (counters.unattempted===counters.total?
      "Chưa chạy đọc metadata hồ sơ; mới chuẩn hóa danh sách CSV.":
      "Đã thử đọc một phần hoặc toàn bộ URL nhưng chưa có bằng chứng hồ sơ dùng được. Không thể kết luận tài khoản thật hay bot."):
    "Chỉ các hồ sơ có dữ liệu bổ sung thực tế mới có thể nhận diện một số tín hiệu.";
 return {counters,outcomes,rows,coverage,attemptedTotal,diagnosis};
}
return {assess,category};
});
