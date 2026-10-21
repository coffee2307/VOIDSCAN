/* Sequential audit queue for opt-in, unauthenticated public metadata requests.
   Does not visit private pages or collect contact details. */
(function(root,factory){
 const lib=root.VoidscanAudit||(typeof require==="function"?require("./lib.js"):null);
 const api=factory(lib);
 if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanAutoAudit=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(lib){
"use strict";
const WAIT_MS=3500,MAX_ITEMS=2000,RECHECK_MS=86400000;
function plan(rows){
 const seen=new Set(),urls=[];
 for(const row of Array.isArray(rows)?rows:[]){
  const candidate=typeof row==="string"?row:row?.profileUrl;
  const p=lib.profileMeta(candidate);
  if(!p)continue;
  const key=p.userId?"id:"+p.userId:p.profileUrl;
  if(seen.has(key))continue;
  seen.add(key);urls.push(p.profileUrl);
  if(urls.length===MAX_ITEMS)break;
 }
 return urls;
}
function signature(urls){
 let n=2166136261;
 for(const url of urls){
  for(let j=0;j<url.length;j++)n=Math.imul(n^url.charCodeAt(j),16777619);
  n=Math.imul(n^10,16777619);
 }
 return urls.length+"-"+(n>>>0).toString(16);
}
function create(urls,prior){
 const list=Array.isArray(urls)?urls.slice(0,MAX_ITEMS):[];
 const key=signature(list);
 if(prior?.signature===key&&Array.isArray(prior?.urls)&&prior.urls.length===list.length&&
   prior.urls.every((u,i)=>u===list[i])&&Number.isInteger(prior.index)&&prior.index<=list.length){
   return {...prior,status:"paused",urls:list};
 }
 return {signature:key,urls:list,index:0,attempted:0,usable:0,unavailable:0,
   skipped:0,status:"ready",stopReason:"",updatedAt:new Date().toISOString()};
}
function reuseAttempt(attempt,now=Date.now()){
 const t=Date.parse(attempt?.at||"");
 return Number.isFinite(t)&&now-t>=0&&now-t<RECHECK_MS&&
   !["restricted","rate_limited","cancelled"].includes(attempt.status);
}
function metadata(result,url){
 if(result?.access!=="public_metadata"||
   (result.region!=="local"&&result.region!=="other"&&result.hasBio!==true))
     return null;
 return {profileUrl:url,source:"public_metadata",observedAt:new Date().toISOString(),
   regionContext:["local","other"].includes(result.region)?result.region:"unknown",
   hasBio:result.hasBio===true?"1":""};
}
function halt(access,consecutiveNetworkErrors){
 return ["restricted","rate_limited"].includes(access)||
   (access==="network_error"&&consecutiveNetworkErrors>=3);
}
return {WAIT_MS,MAX_ITEMS,RECHECK_MS,plan,signature,create,reuseAttempt,metadata,halt};
});
