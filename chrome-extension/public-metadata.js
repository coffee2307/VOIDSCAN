/* Public metadata reader for opted-in Facebook profiles.
 * No session cookies, authentication data, internal APIs, contact details,
 * friend networks, or hidden GraphQL endpoints. */
(function(root,factory){
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanPublicMetadata=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
"use strict";
const HOST="www.facebook.com";
function safeUrl(raw){
 try{const u=new URL(raw);
  if(u.protocol!=="https:"||u.hostname!==HOST)return null;
  if(/^\/(?:login|checkpoint|recovery|groups|pages|search|photo)/i.test(u.pathname))return null;
  const clean=new URL(u.origin+u.pathname);
  if(u.pathname==="/profile.php"){
    const id=u.searchParams.get("id");
    if(!id||!/^\d{5,30}$/.test(id))return null;
    clean.searchParams.set("id",id);
  }
  return clean.href;
 }catch{return null;}
}
function locality(value){
 const s=String(value||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
 if(/(?:di an|binh duong|ho chi minh|tp\.?\s*hcm|hcm|sai gon|saigon)/i.test(s))return "local";
 return s?"other":"unknown";
}
function extract(html,actualUrl,Parser){
 if(typeof html!=="string"||!Parser)return {access:"unavailable",region:"unknown",reason:"Không đọc được HTML"};
 const doc=new Parser().parseFromString(html,"text/html");
 const title=(doc.title||"").toLowerCase();
 if(/log in to facebook|đăng nhập facebook|security check|checkpoint/i.test(title))
   return {access:"restricted",region:"unknown",reason:"Facebook yêu cầu đăng nhập hoặc xác minh"};
 const meta=(key)=>doc.querySelector('meta[property="'+key+'"]')?.getAttribute("content")||"";
 const description=meta("og:description");
 const profileTitle=meta("og:title");
 if(!profileTitle||/^(facebook|đăng nhập)/i.test(profileTitle))
   return {access:"insufficient",region:"unknown",reason:"Không tìm thấy metadata hồ sơ cụ thể"};
 // Only accept explicit 'lives in/current city' patterns, not any unrelated city mention.
 const location=description.match(/(?:lives in|living in|sống tại|hiện sống tại|current city|nơi sống)\s*[:：]?\s*([^.;\n|]{2,90})/i);
 const city=location?locality(location[1]):"unknown";
 const hasBio=/(?:^|[.;\n])\s*(?:bio|giới thiệu|intro)\s*[:：]/i.test(description);
 return {access:"public_metadata",region:city,
   regionEvidence:location?"explicit_public_location":"not_present_in_public_metadata",
   hasBio:hasBio?true:null,
   // Avoid persisting raw display name, description and city text.
   reason:location?"Có thông tin nơi ở tự khai trong metadata công khai":
     "Metadata công khai không hiển thị địa điểm rõ ràng"};
}
async function get(url,fetcher=fetch,Parser=DOMParser,signal){
 const target=safeUrl(url);
 if(!target)return {access:"invalid",region:"unknown",reason:"URL không hỗ trợ"};
 try{
  const response=await fetcher(target,{method:"GET",credentials:"omit",
   redirect:"follow",headers:{"Accept":"text/html"},signal});
  if(response.status===429)return {access:"rate_limited",region:"unknown",reason:"Giới hạn truy cập"};
  if(response.status===401||response.status===403)return {access:"restricted",region:"unknown",reason:"Không có quyền truy cập"};
  if(!response.ok)return {access:"http_error",region:"unknown",reason:"HTTP "+response.status};
  const final=new URL(response.url||target);
  if(final.hostname!==HOST||/^\/(?:login|checkpoint|recovery)/i.test(final.pathname))
    return {access:"restricted",region:"unknown",reason:"Chuyển đến đăng nhập/kiểm tra"};
  if((response.headers?.get("content-length")||"")&&
     Number(response.headers.get("content-length"))>2000000)
    return {access:"large",region:"unknown",reason:"Trang lớn vượt giới hạn"};
  const body=await response.text();
  if(body.length>2000000)return {access:"large",region:"unknown",reason:"HTML quá lớn"};
  return extract(body,target,Parser);
 }catch(e){
  if(signal?.aborted)return {access:"cancelled",region:"unknown",reason:"Đã dừng"};
  return {access:"network_error",region:"unknown",reason:"Không truy cập được metadata công khai"};
 }
}
return {safeUrl,locality,extract,get};
});