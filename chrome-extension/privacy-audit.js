/* VOIDSCAN privacy-by-design decision records. No personal fields, raw page HTML,
 * friend graph, contact data, post text, school name or avatar URL retained. */
(function(root,factory){
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanPrivacyAudit=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
"use strict";
const TTL_MS=24*60*60*1000;
const ACCESS=new Set(["public_metadata","page_visible","auth_required","unavailable","timeout","navigation_error","insufficient","restricted","rate_limited",
  "network_error","http_error","large","invalid","cancelled","unknown"]);
const COUNT_BANDS=new Set(["0","1-49","50-199","200-999","1000+"]);
const POST_AGES=new Set(["within_90d","90_to_364d","365d_plus"]);
const JOIN_ERAS=new Set(["within_2y","2_to_5y","5y_plus"]);
function signals(observation){
 // False means not observed, NEVER proof that the attribute does not exist.
 const o=observation||{};
 const marker=key=>o[key]===true;
 const raw={
  avatar:marker("avatarSeen"),
  localityField:marker("locationListed"),
  schoolField:marker("schoolListed"),
  bioField:marker("bioListed"),
  friendsBand:COUNT_BANDS.has(o.friendsBand)?o.friendsBand:"unknown",
  mutualBand:COUNT_BANDS.has(o.mutualBand)?o.mutualBand:"unknown",
  postAge:POST_AGES.has(o.postRecency)?o.postRecency:"unknown",
  joinedEra:JOIN_ERAS.has(o.joinedEra)?o.joinedEra:"unknown"
 };
 const count=["avatar","localityField","schoolField","bioField"].filter(k=>raw[k]).length+
  ["friendsBand","mutualBand","postAge","joinedEra"].filter(k=>raw[k]!=="unknown").length;
 return {raw,count};
}
function decide(observation,now=Date.now()){
 const access=ACCESS.has(observation?.access)?observation.access:"unknown";
 const {raw,count}=access==="page_visible"?signals(observation):
   {raw:signals({}).raw,count:0};
 const usable=count>0||(access==="public_metadata"&&
   (["local","other"].includes(observation.region)||observation.hasBio===true));
 // Sparse profile attributes cannot validate authenticity or establish a bot.
 const reason=!["public_metadata","page_visible"].includes(access)?"no_access":
   usable?"limited_public_signals":"no_profile_signals";
 return {status:"chưa đủ dữ liệu",access,usable,reason,
   signalCount:count,signals:raw,
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
  const minimal=signals({
    avatarSeen:original?.signals?.avatar,
    locationListed:original?.signals?.localityField,
    schoolListed:original?.signals?.schoolField,
    bioListed:original?.signals?.bioField,
    friendsBand:original?.signals?.friendsBand,
    mutualBand:original?.signals?.mutualBand,
    postRecency:original?.signals?.postAge,
    joinedEra:original?.signals?.joinedEra
  });
  records[url]={status:"chưa đủ dữ liệu",access:original.access,
    usable:original.usable===true,
    reason:["no_access","limited_public_signals","no_profile_signals"].includes(original.reason)?
      original.reason:"no_access",
    signalCount:minimal.count,signals:minimal.raw,
    checkedAt:new Date(checked).toISOString(),expiresAt:new Date(expires).toISOString()};
 }
 return {records,expired};
}
function describe(record){
 return record?.reason==="limited_public_signals"?
  "Đã quan sát được một số tín hiệu tổng hợp trên tab Chrome; chưa đủ để xác minh thật/giả":
  record?.reason==="no_profile_signals"?
  "Đã mở trang nhưng chưa quan sát được tín hiệu tổng hợp cần thiết":
  "Không có metadata hồ sơ đủ để kết luận";
}
return {TTL_MS,decide,prune,describe,signals};
});
