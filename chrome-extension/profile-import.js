/* Explicitly supplied profile evidence; no requests to Facebook profiles. */
(function(root,factory){
 const lib=root.VoidscanAudit||(typeof require==="function"?require("./lib.js"):null);
 const api=factory(lib);
 if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanProfileImport=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(lib){
"use strict";
function key(x){return String(x??"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/đ/gi,"d").toLowerCase().replace(/[^a-z0-9]/g,"");}
function normalizeRow(raw){
 const m={};for(const [k,v] of Object.entries(raw||{}))m[key(k)]=v;
 const first=(...keys)=>{for(const k of keys){const value=m[key(k)];if(value!==undefined&&String(value).trim()!=="")return String(value).trim();}return "";};
 return {
  profileUrl:first("profileUrl","profileLink","url","urlTaiKhoan","facebookUrl"),
  userId:first("userId","id"),
  currentCity:first("currentCity","location","city","noiO","diaDiem"),
  avatarUrl:first("avatarUrl"), hasAvatar:first("hasAvatar"),
  bio:first("bio"),hasBio:first("hasBio"),
  work:first("work"),hasWork:first("hasWork"),
  education:first("education"),hasEducation:first("hasEducation"),
  hometown:first("hometown"),hasHometown:first("hasHometown"),
  category:first("category"),hasCategory:first("hasCategory"),
  friendsCount:first("friendsCount"),followingCount:first("followingCount")
 };
}
function region(v){
 const s=String(v||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/đ/g,"d").toLowerCase().replace(/[^a-z0-9]+/g," ").trim();
 if(!s)return "unknown";
 if(/\b(di an|binh duong|ho chi minh|tp hcm|hcm|sai gon|saigon)\b/.test(s))return "local";
 return "other";
}
function flag(raw,yes){
 if(raw==="1"||/^(true|yes|co|có)$/i.test(String(raw)))return "1";
 if(raw==="0"||/^(false|no|khong|không)$/i.test(String(raw)))return "0";
 return yes?"1":"";
}
function observe(c){
 const url=lib.profileMeta(c.profileUrl||( /^\d{5,30}$/.test(c.userId)?"https://www.facebook.com/profile.php?id="+c.userId:""));
 if(!url)return null;
 const city=region(c.currentCity);
 const avatar=flag(c.hasAvatar,Boolean(c.avatarUrl));
 const result={
  profileUrl:url.profileUrl,userId:url.userId,regionContext:city,
  profileDataSource:"uploaded_profile_csv",hasAvatar:avatar,
  avatarEvidence:avatar==="1"?"present":avatar==="0"?"absent_observed":"unknown",
  locationEvidence:city==="unknown"?"unknown":"declared_in_source",
  hasCurrentCity:city==="unknown"?"":"1",
  hasBio:flag(c.hasBio,Boolean(c.bio)),
  hasWork:flag(c.hasWork,Boolean(c.work)),
  hasEducation:flag(c.hasEducation,Boolean(c.education)),
  hasHometown:flag(c.hasHometown,Boolean(c.hometown)),
  hasCategory:flag(c.hasCategory,Boolean(c.category)),
  friendsCount:c.friendsCount||"",followingCount:c.followingCount||""
 };
 return result;
}
function importProfiles(rows){
 const map=new Map();let skipped=0;
 for(const raw of Array.isArray(rows)?rows:[]){
  const value=observe(normalizeRow(raw));
  if(!value){skipped++;continue;}
  map.set(value.profileUrl,value);
  if(value.userId)map.set("id:"+value.userId,value);
 }
 return {map,sourceAccounts:new Set([...map.values()].map(v=>v.profileUrl)).size,skipped};
}
function enrich(reactionRows,sourceRows){
 const loaded=importProfiles(sourceRows);
 let matched=0;
 const rows=(Array.isArray(reactionRows)?reactionRows:[]).map(r=>{
  const meta=lib.profileMeta(r?.profileUrl);
  const supplied=meta&&(loaded.map.get(meta.profileUrl)||(meta.userId&&loaded.map.get("id:"+meta.userId)));
  const intrinsicFields=["currentCity","location","city","hasAvatar","hasBio","hasWork","hasEducation","hasHometown","avatarUrl"];
  const hasIntrinsic=intrinsicFields.some(k=>r&&r[k]!==undefined&&String(r[k]??"").trim()!=="");
  const intrinsic=!supplied&&hasIntrinsic?observe(normalizeRow(r)):null;
  const evidence=supplied||intrinsic;
  if(!evidence)return {...r};
  if(intrinsic)evidence.profileDataSource="reaction_csv_fields";
  matched++;
  const merged={...r};
  for(const [k,v] of Object.entries(evidence)){
   if(["profileUrl","userId"].includes(k))continue;
   if(v!==""&&v!==undefined)merged[k]=v;
  }
  return merged;
 });
 return {rows,matchedRows:matched,sourceAccounts:loaded.sourceAccounts,skippedAccounts:loaded.skipped};
}
return {normalizeRow,region,flag,observe,importProfiles,enrich};
});