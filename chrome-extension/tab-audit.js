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
 // Only emit coarse observations; never return names, raw text, friend lists,
 // school names, exact dates, locations, or contact fields.
 const visible=(document.body?.innerText||"").slice(0,32000);
 const lines=visible.split(/[\r\n]+/).map(x=>x.trim()).filter(Boolean);
 const hasLine=regex=>lines.some(line=>regex.test(line));
 const locationListed=hasLine(/^(?:sống tại|hiện sống tại|lives in|living in|đang sống tại)\s+.{2,85}$/i);
 const schoolListed=hasLine(/^(?:học tại|đã học tại|studies at|studied at|went to)\s+.{2,90}$/i);
 const bioListed=hasLine(/^(?:tiểu sử|giới thiệu|bio|about me)\s*[:：]\s*.{3,100}$/i);
 // Only count visibly labeled summaries; 0 means an explicit displayed zero,
 // while 'unknown' means Facebook did not expose a count.
 const numberFromLabel=regex=>{
   const match=visible.match(regex);
   if(!match)return null;
   const parsed=Number(match[1].replace(/[.,\s]/g,""));
   return Number.isSafeInteger(parsed)&&parsed>=0&&parsed<=10000000?parsed:null;
 };
 const band=n=>n===null?"unknown":n===0?"0":n<50?"1-49":n<200?"50-199":n<1000?"200-999":"1000+";
 const friends=numberFromLabel(/(?:^|\n)\s*([\d.,]{1,11})\s*(?:bạn bè|friends)(?:\s|$)/i);
 const mutual=numberFromLabel(/(?:^|\n)\s*([\d.,]{1,11})\s*(?:bạn chung|mutual friends)(?:\s|$)/i);
 const dates=[...document.querySelectorAll('article time[datetime], [role="article"] time[datetime]')]
  .slice(0,20).map(el=>Date.parse(el.getAttribute("datetime")||""))
  .filter(Number.isFinite).filter(t=>t<=Date.now()+86400000);
 const ageDays=dates.length?Math.floor((Date.now()-Math.max(...dates))/86400000):null;
 const postRecency=ageDays===null?"unknown":ageDays<90?"within_90d":ageDays<365?"90_to_364d":"365d_plus";
 const joinedText=visible.match(/(?:đã tham gia facebook\s*(?:vào\s*)?(?:năm\s*)?|joined facebook\s*(?:in\s*)?)(20\d{2})/i);
 const joinedYear=joinedText?Number(joinedText[1]):null;
 const year=new Date().getFullYear();
 const joinedEra=joinedYear===null||joinedYear>year?"unknown":
   joinedYear>=year-2?"within_2y":joinedYear>=year-5?"2_to_5y":"5y_plus";
 return {access:"page_visible",avatarSeen,locationListed,schoolListed,bioListed,
   friendsBand:band(friends),mutualBand:band(mutual),
   postRecency,joinedEra,visiblePostDates:dates.length?Math.min(10,dates.length):0};
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
  // Coarse, non-identifying signals only. Never return page text.
  return {tabId,access:observation.access,avatarSeen:observation.avatarSeen===true,
    locationListed:observation.locationListed===true,
    schoolListed:observation.schoolListed===true,
    bioListed:observation.bioListed===true,
    friendsBand:observation.friendsBand||"unknown",
    mutualBand:observation.mutualBand||"unknown",
    postRecency:observation.postRecency||"unknown",
    joinedEra:observation.joinedEra||"unknown",
    visiblePostDates:Number(observation.visiblePostDates)||0};
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
