/* One-tab navigator for authorized browsing. Returns only minimal page-access
 * signals. Does not extract names, schools, friend lists, posts or contact data. */
(function(root,factory){
 const api=factory(root.VoidscanAudit||(typeof require==="function"?require("./lib.js"):null));
 if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanTabAudit=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(lib){
"use strict";
const MAX_WAIT_MS=25000,config={settleMs:1400};
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function isAllowed(raw){
 const normalized=lib?.normalizeProfile(raw);
 return normalized&&normalized===raw?normalized:null;
}
function probePage(){
 const url=location.href,title=(document.title||"").slice(0,200);
 const lower=title.toLowerCase();
 if(/\/login|\/checkpoint|\/recover|\/two_step_verification/.test(location.pathname)||
    /log in to facebook|đăng nhập facebook|security check|bảo mật|checkpoint/.test(lower))
   return {access:"auth_required",avatarSeen:false};
 if(/content isn't available|nội dung này hiện không có|page isn't available|trang này hiện không có|không tìm thấy nội dung/i.test(title))
   return {access:"unavailable",avatarSeen:false};
 const imgs=[...document.querySelectorAll("img[alt],img[aria-label]")].slice(0,150);
 const avatarSeen=imgs.some(el=>{
   const label=(el.alt||"")+" "+(el.getAttribute("aria-label")||"");
   return /profile picture|profile photo|ảnh đại diện|ảnh hồ sơ/i.test(label);
 });
 return {access:"page_visible",avatarSeen};
}
async function loaded(browser,tabId,signal,timeout=MAX_WAIT_MS){
 if(signal?.aborted)throw Error("cancelled");
 const current=await browser.tabs.get(tabId);
 if(current.status==="complete")return current;
 return new Promise((resolve,reject)=>{
   let finished=false;
   const done=(error,value)=>{
     if(finished)return;finished=true;
     clearTimeout(timer);
     browser.tabs.onUpdated.removeListener(onUpdate);
     signal?.removeEventListener("abort",onAbort);
     error?reject(error):resolve(value);
   };
   const onUpdate=(id,change,tab)=>{
     if(id===tabId&&change.status==="complete")done(null,tab);
   };
   const onAbort=()=>done(Error("cancelled"));
   const timer=setTimeout(()=>done(Error("timeout")),timeout);
   browser.tabs.onUpdated.addListener(onUpdate);
   signal?.addEventListener("abort",onAbort,{once:true});
   if(signal?.aborted)onAbort();
 });
}
function isFB(raw){
 try{
  const url=new URL(raw);
  return url.protocol==="https:"&&
   ["www.facebook.com","facebook.com","m.facebook.com","web.facebook.com"].includes(url.hostname);
 }catch{return false;}
}
async function scan(url,priorId,browser=chrome,signal){
 const safe=isAllowed(url);
 if(!safe)return {tabId:priorId,access:"invalid",avatarSeen:false};
 if(signal?.aborted)return {tabId:priorId,access:"cancelled",avatarSeen:false};
 let tabId=priorId;
 try{
  let tab;
  if(tabId===null||tabId===undefined){
    tab=await browser.tabs.create({url:safe,active:false});
    tabId=tab.id;
  }else{
    try{tab=await browser.tabs.update(tabId,{url:safe,active:false});}
    catch{tab=await browser.tabs.create({url:safe,active:false});tabId=tab.id;}
  }
  tab=await loaded(browser,tabId,signal);
  if(signal?.aborted)return {tabId,access:"cancelled",avatarSeen:false};
  if(!isFB(tab.url||safe))return {tabId,access:"restricted",avatarSeen:false};
  const path=new URL(tab.url||safe).pathname;
  if(/^\/(?:login|checkpoint|recover|two_step_verification)(?:\/|$)/i.test(path))
   return {tabId,access:"auth_required",avatarSeen:false};
  await wait(config.settleMs);
  if(signal?.aborted)return {tabId,access:"cancelled",avatarSeen:false};
  const read=await browser.scripting.executeScript({target:{tabId},func:probePage});
  const observation=read?.[0]?.result;
  if(!observation||!["page_visible","auth_required","unavailable"].includes(observation.access))
    return {tabId,access:"insufficient",avatarSeen:false};
  return {tabId,access:observation.access,avatarSeen:observation.avatarSeen===true};
 }catch(error){
   const msg=String(error?.message||"");
   return {tabId,access:signal?.aborted||msg==="cancelled"?"cancelled":
       msg==="timeout"?"timeout":"navigation_error",avatarSeen:false};
 }
}
async function close(tabId,browser=chrome){
 if(tabId===null||tabId===undefined)return;
 try{await browser.tabs.remove(tabId);}catch{}
}
return {scan,close,isAllowed,probePage,loaded,config};
});
