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
 // Read only summary counts and timestamps visibly attached to public post cards.
 const mutual=visibleText.match(/(?:^|\n)\s*(\d{1,5})\s*(?:bạn chung|mutual friends?)\b/i);
 const mutualCount=mutual?Number(mutual[1]):null;
 const dates=[...document.querySelectorAll('article time[datetime], [role="article"] time[datetime]')]
   .slice(0,25).map(node=>node.getAttribute("datetime")||"")
   .map(v=>{const ts=Date.parse(v);return Number.isFinite(ts)?new Date(ts).toISOString().slice(0,10):"";})
   .filter(Boolean).sort().reverse();
 const latestVisiblePostAt=dates[0]||"";
 // Optional, strictly visible declarations on the page opened by the user.
 // The whole page is never stored. No friends list or post text is retained.
 let educationText="";
 for(const line of lines){
   const match=line.match(/^(?:đã học tại|học tại|studied at|studies at|went to)\s*[:：]?\s*(.{3,90})$/i);
   if(match&&!/@|https?:|\d{5,}/i.test(match[1])){educationText=match[1].trim();break;}
 }
 const friendsMatch=visibleText.match(/(?:^|\n)\s*([\d.,]{1,12})\s*(?:bạn bè|friends)(?:\s|$)/i);
 const parsedFriends=friendsMatch?Number(friendsMatch[1].replace(/[^\d]/g,"")):NaN;
 const friendsCount=Number.isSafeInteger(parsedFriends)&&parsedFriends>=0&&parsedFriends<=100000?parsedFriends:null;
 const joinedMatch=visibleText.match(/(?:đã tham gia facebook\s*(?:vào\s*)?(?:năm\s*)?|joined facebook\s*(?:in\s*)?)(20\d{2})/i);
 const joinedYear=joinedMatch?Number(joinedMatch[1]):null;
 if(!avatar&&!locationText&&mutualCount===null&&!latestVisiblePostAt&&!educationText&&friendsCount===null&&!joinedYear)
   return {saved:false,reason:"Trang hiện chưa hiển thị tín hiệu cần thiết; không suy đoán trường thiếu."};
 const key="voidscan_profile_observations_v1";
 const old=(await chrome.storage.local.get(key))[key]||{};
 const previous=old[meta.profileUrl]||{};
 const record={...previous,profileUrl:meta.profileUrl,source:"observed_open_profile",observedAt:new Date().toISOString()};
 if(avatar)record.hasAvatar="1";
 if(locationText)record.currentCity=locationText;
 if(mutualCount!==null)record.mutualFriendsNumber=String(mutualCount);
 if(educationText){record.education=educationText;record.hasEducation="1";}
 if(friendsCount!==null)record.friendsCount=String(friendsCount);
 if(joinedYear&&joinedYear<=new Date().getFullYear())record.joinedYear=String(joinedYear);
 if(latestVisiblePostAt){
   record.latestVisiblePostAt=latestVisiblePostAt;
   record.visiblePostDateCount=String(dates.length);
 }
 const records=Object.keys(old).length;
 if(records>=2000&&!old[meta.profileUrl])
  return {saved:false,reason:"Đã đạt giới hạn 2.000 hồ sơ được ghi nhận cục bộ."};
 old[meta.profileUrl]=record;
 await chrome.storage.local.set({[key]:old});
 return {saved:true,hasAvatar:!!avatar,hasCurrentCity:!!locationText,
   hasMutualCount:mutualCount!==null,hasVisiblePostDate:!!latestVisiblePostAt,
   hasEducation:!!educationText,hasFriendsCount:friendsCount!==null,
   hasJoinedYear:!!joinedYear};
};
})(typeof globalThis!=="undefined"?globalThis:this);