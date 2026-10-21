/* Capture only explicitly visible fields on the Facebook profile the user opened.
   Does not navigate, request data, or access cookies/friend graphs. */
(function(root){
"use strict";
root.VoidscanCaptureCurrentProfile=async function(){
 const lib=root.VoidscanAudit;
 const meta=lib?.profileMeta(location.href);
 if(!meta) return {saved:false,reason:"Hãy mở đúng trang hồ sơ Facebook."};
 const title=String(document.title||"");
 if(/log in|đăng nhập|checkpoint|security check/i.test(title))
   return {saved:false,reason:"Trang yêu cầu đăng nhập hoặc xác minh."};
 const photoPattern=/(profile (?:picture|photo)|ảnh đại diện|anh dai dien|ảnh hồ sơ)/i;
 const avatar=[...document.querySelectorAll("img[src],img[srcset]")].find(img=>{
  const label=[img.alt,img.getAttribute("aria-label")].filter(Boolean).join(" ");
  const box=img.getBoundingClientRect();
  return photoPattern.test(label)&&box.width>=60&&box.height>=60&&
    lib.avatarUrl(img.currentSrc||img.src);
 });
 const visibleText=(document.body?.innerText||"").slice(0,18000);
 const lines=visibleText.split(/[\r\n]+/).map(v=>v.trim()).filter(Boolean);
 let locationText="";
 for(const line of lines){
   const match=line.match(/^(?:sống tại|hiện sống tại|lives in|living in|đang sống tại)\s+(.{2,85})$/i);
   if(!match)continue;
   const candidate=match[1].trim();
   if(candidate.length>2&&candidate.length<85&&!/https?:|@|\d{5,}/.test(candidate)){
     locationText=candidate;break;
   }
 }
 if(!avatar&&!locationText)return {saved:false,reason:"Trang đang mở chưa hiển thị avatar hoặc nơi ở rõ ràng; không tự suy đoán."};
 const key="voidscan_profile_observations_v1";
 const old=(await chrome.storage.local.get(key))[key]||{};
 const previous=old[meta.profileUrl]||{};
 const record={...previous,profileUrl:meta.profileUrl,source:"observed_open_profile",observedAt:new Date().toISOString()};
 if(avatar)record.hasAvatar="1";
 if(locationText)record.currentCity=locationText;
 const records=Object.keys(old).length;
 if(records>=2000&&!old[meta.profileUrl])
  return {saved:false,reason:"Đã đạt giới hạn 2.000 hồ sơ được ghi nhận cục bộ."};
 old[meta.profileUrl]=record;
 await chrome.storage.local.set({[key]:old});
 return {saved:true,hasAvatar:!!avatar,hasCurrentCity:!!locationText};
};
})(typeof globalThis!=="undefined"?globalThis:this);