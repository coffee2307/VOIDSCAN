/* VOIDSCAN privacy-by-design decision records. No personal fields, raw page HTML,
 * friend graph, contact data, post text, school name or avatar URL retained. */
(function(root,factory){
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanPrivacyAudit=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
"use strict";
const TTL_MS=24*60*60*1000;
const ACCESS=new Set(["public_metadata","insufficient","restricted","rate_limited",
  "network_error","http_error","large","invalid","cancelled","unknown"]);
function decide(observation,now=Date.now()){
 const access=ACCESS.has(observation?.access)?observation.access:"unknown";
 const usable=access==="public_metadata"&&
   (["local","other"].includes(observation.region)||observation.hasBio===true);
 // No data in this reader substantiates either "real" or "bot".
 const reason=access!=="public_metadata"?"no_access":
   usable?"limited_public_signals":"no_profile_signals";
 return {status:"chưa đủ dữ liệu",access,usable,reason,
   checkedAt:new Date(now).toISOString(),
   expiresAt:new Date(now+TTL_MS).toISOString()};
}
function prune(raw,now=Date.now()){
 const saved=raw&&typeof raw==="object"?raw:{}, records={};
 let expired=0;
 for(const [url,original] of Object.entries(saved)){
  const checked=Date.parse(original?.checkedAt||"");
  const expires=Date.parse(original?.expiresAt||"");
  if(!Number.isFinite(checked)||!Number.isFinite(expires)||
     expires>checked+TTL_MS||expires<=now||checked>now+60000||
     !ACCESS.has(original.access)||original.status!=="chưa đủ dữ liệu"){
    expired++;continue;
  }
  records[url]={status:"chưa đủ dữ liệu",access:original.access,
    usable:original.usable===true,
    reason:["no_access","limited_public_signals","no_profile_signals"].includes(original.reason)?
      original.reason:"no_access",
    checkedAt:new Date(checked).toISOString(),expiresAt:new Date(expires).toISOString()};
 }
 return {records,expired};
}
function describe(record){
 return record?.reason==="limited_public_signals"?
  "Đã kiểm tra metadata công khai: có tín hiệu giới hạn; không đủ để xác minh thật/giả":
  record?.reason==="no_profile_signals"?
  "Đã thử metadata công khai nhưng không có tín hiệu đánh giá tài khoản":
  "Không có metadata hồ sơ đủ để kết luận";
}
return {TTL_MS,decide,prune,describe};
});
