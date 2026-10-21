/* Offline reaction integrity counters: never identifies bots or people. */
(function(root,factory){
 const api=factory(root.VoidscanAudit||(typeof require==="function"?require("./lib.js"):null));
 if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanIntegrity=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(lib){
"use strict";
function audit(records,visibleCounts){
 const perPhoto=new Map(),perPhotoStats=new Map();let invalid=0,excluded=0,unknown=0,duplicates=0,conflicts=0;
 for(const r of Array.isArray(records)?records:[]){
  const id=String(r?.photoId||"");
  const m=lib.profileMeta(r?.profileUrl);
  if(!/^\d{5,30}$/.test(id)||!m||(r?.photoUrl&&lib.photoId(r.photoUrl)!==id)){invalid++;continue;}
  if(!perPhoto.has(id)){perPhoto.set(id,new Map());perPhotoStats.set(id,{unknown:0,excluded:0,duplicates:0,conflicts:0});}
  const profile=perPhoto.get(id),stats=perPhotoStats.get(id),reaction=lib.cleanReaction(r?.reaction);
  if(!reaction){if(/^(SAD|ANGRY|BUỒN|PHẪN NỘ)$/i.test(String(r?.reaction))){excluded++;stats.excluded++;}
    else{unknown++;stats.unknown++;}continue;}
  const accountKey=m.userId?"id:"+m.userId:m.profileUrl;
  const previous=profile.get(accountKey);
  if(previous){
   duplicates++;stats.duplicates++;
   if(previous.reaction!==reaction){conflicts++;stats.conflicts++;}
   const old=Date.parse(previous.at||"");
   const cur=Date.parse(r.capturedAt||"");
   if(Number.isFinite(cur)&&(!Number.isFinite(old)||cur>old))
      profile.set(accountKey,{reaction,at:r.capturedAt});
   else if(previous.reaction!==reaction&&((!Number.isFinite(cur)&&!Number.isFinite(old))||cur===old))
      profile.set(accountKey,{reaction:null,at:"",ambiguous:true});
  }else profile.set(accountKey,{reaction,at:r?.capturedAt||""});
 }
 const photos=[...perPhoto.entries()].map(([photoId,accounts])=>{
  const counts=Object.fromEntries(lib.types.map(type=>[type,0]));
  for(const a of accounts.values())if(a.reaction&&Object.hasOwn(counts,a.reaction))counts[a.reaction]++;
  const observed=Object.values(counts).reduce((n,v)=>n+v,0);
  const ambiguous=[...accounts.values()].filter(v=>v.ambiguous).length;
  const displayed=visibleCounts?.[photoId]||{};
  const coverage={};
  for(const kind of lib.types){
   const v=displayed[kind];
   const n=Number(v?.displayedCount);
   coverage[kind]=v?.displayedCount!==undefined&&v?.displayedCount!==""&&Number.isFinite(n)&&n>=0?
    {observed:counts[kind],displayed:n,ratio:n?Math.min(1,counts[kind]/n):counts[kind]?null:1,
     discrepancy:counts[kind]-n}:null;
  }
  return {photoId,uniqueAccounts:observed,ambiguousAccounts:ambiguous,counts,coverage,...perPhotoStats.get(photoId)};
 });
 return {photos,totals:{photos:photos.length,uniquePhotoReactions:photos.reduce((n,x)=>n+x.uniqueAccounts,0),duplicates,conflicts,unknown,excluded,invalid},limitations:"Số đã thu thập không đồng nghĩa tổng số hiển thị; không dùng kết quả để kết luận tài khoản ảo."};
}
return {audit};
});
