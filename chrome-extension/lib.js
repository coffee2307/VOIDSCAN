(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  root.VoidscanAudit=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
"use strict";
const types=Object.freeze(["LIKE","LOVE","CARE","HAHA","WOW"]);
const reserved=new Set(["about","ads","bookmarks","business","events","friends","gaming","groups","help","home","login","logout","marketplace","messages","notifications","pages","photo","photo.php","photos","plugins","policies","privacy","reel","reels","saved","search","settings","share","sharer","stories","story.php","watch","hashtag","recover","two_step_verification","checkpoint","posts","permalink","videos","media","watch","groups","pages","people"]);
function fbUrl(url){
  try{
    const u=new URL(url,"https://www.facebook.com/");
    return u.protocol==="https:"&&["facebook.com","www.facebook.com","m.facebook.com","web.facebook.com"].includes(u.hostname.toLowerCase())?u:null;
  }catch{return null;}
}
function photoId(url){
  const u=fbUrl(url);if(!u)return null;
  const id=u.searchParams.get("fbid");
  if(id&&/^\d{5,30}$/.test(id)&&/^\/(?:photo|photo\.php)\/?$/.test(u.pathname))return id;
  const m=u.pathname.match(/\/photos\/(?:[^/]+\/)?(\d{5,30})(?:\/|$)/);
  return m?m[1]:null;
}
function normalizeProfile(url){
  const u=fbUrl(url);if(!u)return null;
  const p=u.pathname.split("/").filter(Boolean).map(s=>{try{return decodeURIComponent(s);}catch{return s;}});
  if(!p.length)return null;
  const first=p[0].toLowerCase();
  if(first==="profile.php"){
    const id=u.searchParams.get("id");
    return id&&/^\d{5,30}$/.test(id)?"https://www.facebook.com/profile.php?id="+id:null;
  }
  if(first==="people"){
    if(p.length!==3||!/^\d{5,30}$/.test(p[2])||!p[1]||p[1].length>100)return null;
    return "https://www.facebook.com/people/"+encodeURIComponent(p[1])+"/"+p[2]+"/";
  }
  if(reserved.has(first)||first.startsWith("ajax")||first.startsWith("api"))return null;
  if(p.length!==1||!/^[\p{L}\p{N}._-]{2,100}$/u.test(p[0]))return null;
  return "https://www.facebook.com/"+encodeURIComponent(p[0])+"/";
}
function profileMeta(url){
  const normalized=normalizeProfile(url);
  if(!normalized)return null;
  const u=new URL(normalized);
  let userId="",username="";
  if(u.pathname==="/profile.php")userId=u.searchParams.get("id")||"";
  else if(u.pathname.startsWith("/people/")){
    const p=u.pathname.split("/").filter(Boolean);
    username=decodeURIComponent(p[1]||"");
    userId=p[2]||"";
  }else username=decodeURIComponent(u.pathname.split("/").filter(Boolean)[0]||"");
  return {profileUrl:normalized,userId,username};
}
function cleanReaction(value){
  const x=String(value||"").trim().toUpperCase();
  const v={
    "THÍCH":"LIKE","THICH":"LIKE","LIKE":"LIKE","👍":"LIKE",
    "YÊU THÍCH":"LOVE","YÊU":"LOVE","TYM":"LOVE","LOVE":"LOVE","❤️":"LOVE","❤":"LOVE",
    "THƯƠNG THƯƠNG":"CARE","CARE":"CARE","🥰":"CARE",
    "HAHA":"HAHA","CƯỜI":"HAHA","😆":"HAHA",
    "WOW":"WOW","NGẠC NHIÊN":"WOW","😮":"WOW"
  };
  return v[x]||null;
}
function reactionFromLabel(value){
  const str=String(value||"").trim().replace(/\u00a0/g," ");
  if(!str)return null;
  const leading=str.replace(/\s*[\d.,\sKkMm]+\s*$/,"").trim();
  const prefix=leading.replace(/^(?:reaction|cảm xúc)\s*[:：-]?\s*/i,"");
  const match=prefix.match(/^(thương thương|yêu thích|ngạc nhiên|thích|like|love|care|haha|wow)(?=$|[\s:：·(\[])/i);
  return cleanReaction(leading)||cleanReaction(prefix)||
    (match?cleanReaction(match[1]):null)||cleanReaction(str)||null;
}
function reactionFromProfileLabel(value){
  // Facebook's actual reaction dialog exposes accessibility labels:
  // "Nguyễn A đã thích", "Nguyễn B đã cảm thấy Yêu thích".
  // Only match an explicit terminal verb, never infer reactions from names
  // or from generic avatar/icon appearance.
  const label=String(value||"").replace(/\u00a0/g," ").trim();
  if(!label)return null;
  const clean=label.replace(/,\s*(?:unseen story|đang có tin|has a story).*$/i,"").trim();
  const excluded=clean.match(/\sđã\s+(?:cảm thấy\s+)?(buồn|phẫn nộ)\s*$/iu);
  if(excluded)return "EXCLUDED";
  const vi=clean.match(/\sđã\s+(?:cảm thấy\s+)?(thương thương|yêu thích|ngạc nhiên|thích|haha|wow|cười)\s*$/iu);
  if(vi)return cleanReaction(vi[1]);
  const en=clean.match(/\s(?:reacted\s+with|reacted\s+to\s+this\s+with)\s+(like|love|care|haha|wow)\s*$/i);
  if(en)return cleanReaction(en[1]);
  return null;
}
function parseCount(value){
  const s=String(value||"").trim().replace(/\s/g,"").replace(/,/g,"");
  const match=s.match(/^(\d+(?:\.\d+)?)([kKmM])?$/);
  if(match)return Math.round(Number(match[1])*(match[2]?({k:1000,m:1e6}[match[2].toLowerCase()]):1));
  return null;
}
function avatarUrl(value){
  try{
    const u=new URL(String(value||""));
    const h=u.hostname.toLowerCase();
    if(u.protocol!=="https:"||!((h==="fbcdn.net"||h.endsWith(".fbcdn.net"))||(h==="facebook.com"||h.endsWith(".facebook.com"))))return "";
    return u.href;
  }catch{return "";}
}
function csvValue(value){
  const s=String(value??"");
  const safe=/^[\t\r\n ]*[=+\-@]/.test(s)?"'"+s:s;
  return /[",\r\n]/.test(safe)?'"'+safe.replace(/"/g,'""')+'"':safe;
}
function csv(rows,cols){
  return "\ufeff"+[cols.join(","),...rows.map(r=>cols.map(k=>csvValue(r[k])).join(","))].join("\r\n");
}
function aggregate(records){
  const m=new Map();
  for(const r of records){
    if(!r||!photoId(r.photoUrl)||photoId(r.photoUrl)!==r.photoId||!cleanReaction(r.reaction)||!normalizeProfile(r.profileUrl))continue;
    let row=m.get(r.photoId);
    if(!row){row={photoId:r.photoId,photoUrl:r.photoUrl,LIKE:0,LOVE:0,CARE:0,HAHA:0,WOW:0,observedRows:0};m.set(r.photoId,row);}
    row[r.reaction]++;row.observedRows++;
  }
  return Array.from(m.values()).map(row=>({...row,points_observed:row.observedRows}));
}
function dedupe(records){
  const m=new Map();
  for(const input of records){
    if(!input||!photoId(input.photoUrl)||photoId(input.photoUrl)!==input.photoId)continue;
    const reaction=cleanReaction(input.reaction),meta=profileMeta(input.profileUrl);
    if(!reaction||!meta)continue;
    const key=input.photoId+"|"+meta.profileUrl;
    const record={...input,photoId:input.photoId,photoUrl:"https://www.facebook.com/photo/?fbid="+input.photoId,
      ...meta,reaction,avatarUrl:avatarUrl(input.avatarUrl)};
    if(m.has(key)){
      const earlier=m.get(key);
      m.set(key,{...earlier,...Object.fromEntries(Object.entries(record).filter(([,v])=>v!==""&&v!=null))});
    }else m.set(key,record);
  }
  return [...m.values()];
}
return {types,fbUrl,photoId,normalizeProfile,profileMeta,cleanReaction,reactionFromLabel,reactionFromProfileLabel,parseCount,avatarUrl,csv,aggregate,dedupe};
});