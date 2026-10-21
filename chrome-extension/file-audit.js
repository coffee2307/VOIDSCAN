/* VOIDSCAN CSV ingestion and source-limited account screening, offline only. */
(function(root,factory){
 const lib=root.VoidscanAudit||(typeof require==="function"?require("./lib.js"):null);
 const api=factory(lib);
 if(typeof module==="object"&&module.exports)module.exports=api;
 root.VoidscanFileAudit=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(lib){
"use strict";
const LABEL_SUSPECT="nghi vấn", LABEL_CLEAR="không có dấu hiệu";
const HEADER_MAP={
 profileurl:"profileUrl",profile_url:"profileUrl",profilelink:"profileUrl",urlprofile:"profileUrl",
 "url tài khoản":"profileUrl","link tài khoản":"profileUrl","facebookurl":"profileUrl",
 userid:"userId",username:"username",displayname:"displayName",reaction:"reaction",
 reactiontype:"reaction",reaction_type:"reaction",loaireaction:"reaction",
 photoid:"photoId",photourl:"photoUrl",avatarurl:"avatarUrl",
 friendshipstatus:"friendshipStatus",subscribestatus:"subscribeStatus",
 mutualfriendsnumber:"mutualFriendsNumber",captureDat:"capturedAt",capturedat:"capturedAt",
 friendscount:"friendsCount",friendcount:"friendsCount",numberoffriends:"friendsCount",
 followingcount:"followingCount",followcount:"followingCount",numberoffollowing:"followingCount",
 bio:"bio",work:"work",education:"education",hometown:"hometown",
 currentcity:"currentCity",city:"currentCity",
 hasbio:"hasBio",haswork:"hasWork",haseducation:"hasEducation",
 hashometown:"hasHometown",hascurrentcity:"hasCurrentCity",recentactivity:"recentActivity"
};
function simplified(key){return String(key||"").trim().replace(/^\uFEFF/,"").toLowerCase().replace(/[\s_\-().]/g,"");}
function headerKey(key){
 const orig=String(key||"").trim().replace(/^\uFEFF/,"");
 return HEADER_MAP[orig.toLowerCase()]||HEADER_MAP[simplified(orig)]||orig;
}
function parseCSV(text){
 if(typeof text!=="string"||!text.trim())throw Error("Tệp CSV trống.");
 const cleaned=text.replace(/^\uFEFF/,"").replace(/^sep=([,;\t])\r?\n/i,"");
 const first=(cleaned.match(/^[^\r\n]*/)||[""])[0];
 let delimiter=",";
 const countOutsideQuotes=(s,d)=>{
   let n=0,q=false;
   for(let i=0;i<s.length;i++){if(s[i]==='"'){if(q&&s[i+1]==='"')i++;else q=!q;}else if(!q&&s[i]===d)n++;}
   return n;
 };
 if(countOutsideQuotes(first,";")>countOutsideQuotes(first,","))delimiter=";";
 else if(countOutsideQuotes(first,"\t")>countOutsideQuotes(first,","))delimiter="\t";
 const rows=[];let row=[],cell="",quoted=false;
 for(let i=0;i<cleaned.length;i++){
   const c=cleaned[i];
   if(c==='"'){
     if(quoted&&cleaned[i+1]==='"'){cell+='"';i++;}
     else quoted=!quoted;
   }else if(!quoted&&c===delimiter){row.push(cell);cell="";}
   else if(!quoted&&(c==="\n"||c==="\r")){
     if(c==="\r"&&cleaned[i+1]==="\n")i++;
     row.push(cell);if(row.some(v=>v!==""))rows.push(row);
     row=[];cell="";
   }else cell+=c;
 }
 if(quoted)throw Error("CSV có dấu ngoặc kép chưa đóng.");
 row.push(cell);if(row.some(v=>v!==""))rows.push(row);
 if(rows.length<2)throw Error("CSV không có dòng dữ liệu.");
 const headers=rows.shift().map(headerKey);
 if(!headers.includes("profileUrl"))throw Error("Thiếu cột profileUrl (URL tài khoản).");
 const data=rows.map((cells,i)=>{
   const item={_sourceRow:i+2};
   headers.forEach((header,j)=>{if(!["__proto__","constructor","prototype"].includes(header))
     item[header]=cells[j]||"";});
   return item;
 });
 return {rows:data,headers,delimiter};
}
function presence(x){return x===true||x==="1"||/^(true|yes|y|có|co)$/i.test(String(x??"").trim());}
function numberOrNull(x){
 if(x===null||x===undefined||x==="")return null;
 const s=String(x).trim().replace(/\s+/g,"");
 if(!/^\d{1,8}$/.test(s))return null;
 const n=Number(s);
 return Number.isSafeInteger(n)&&n<=10000000?n:null;
}
function normaliseRows(input){
 const rows=[],warnings={invalidProfile:0,invalidPhoto:0,photoMismatch:0,unknownReaction:0};
 for(const item of input){
   const meta=lib.profileMeta(item.profileUrl||"");
   if(!meta){warnings.invalidProfile++;continue;}
   const explicitID=String(item.photoId||"").trim();
   const urlID=lib.photoId(item.photoUrl||"")||"";
   // Never silently mix two distinct photos when a malformed CSV contradicts itself.
   if(explicitID&&urlID&&explicitID!==urlID){warnings.photoMismatch++;continue;}
   const photoID=explicitID||urlID;
   const photoValid=/^\d{5,30}$/.test(photoID);
   if(!photoValid)warnings.invalidPhoto++;
   const reaction=lib.cleanReaction(item.reaction)||"UNKNOWN";
   if(reaction==="UNKNOWN")warnings.unknownReaction++;
   rows.push({
     ...item,photoId:photoValid?photoID:"",
     photoUrl:photoValid?"https://www.facebook.com/photo/?fbid="+photoID:"",
     profileUrl:meta.profileUrl,userId:meta.userId,username:meta.username,
     reaction, friendsCount:numberOrNull(item.friendsCount),
     followingCount:numberOrNull(item.followingCount)
   });
 }
 return {rows,warnings};
}
function prepare(raw){
 const {rows,warnings}=normaliseRows(raw);
 const profiles=new Map(),photos=new Set();
 for(const r of rows){
   if(r.photoId)photos.add(r.photoId);
   let item=profiles.get(r.profileUrl);
   if(!item){
     item={profileUrl:r.profileUrl,userId:r.userId,username:r.username,
       photoIds:new Set(),reactions:new Set(),perPhoto:new Map(),
       fields:new Set(),profileFlagsObserved:new Set(),friendsCount:null,followingCount:null,
       rawRows:0,unknownRows:0,sourceRows:[]};
     profiles.set(r.profileUrl,item);
   }
   if(r.photoId)item.photoIds.add(r.photoId);
   if(r.reaction==="UNKNOWN")item.unknownRows++;
   else item.reactions.add(r.reaction);
   if(r.photoId&&r.reaction!=="UNKNOWN"){
     const last=item.perPhoto.get(r.photoId)||new Set();
     last.add(r.reaction);item.perPhoto.set(r.photoId,last);
   }
   item.rawRows++;item.sourceRows.push(r._sourceRow||"");
   for(const [field,key] of [["bio","hasBio"],["currentCity","hasCurrentCity"],
     ["hometown","hasHometown"],["education","hasEducation"],["work","hasWork"],
     ["recentActivity","recentActivity"]]){
     const indicator=String(r[key]??"").trim().toLowerCase();
     if(["0","1","true","false","yes","no","có","không"].includes(indicator))
       item.profileFlagsObserved.add(field);
     const raw=String(r[field]??"").trim();
     if(presence(r[key])||(raw&&!["0","false","unknown","n/a","không rõ","không","no"].includes(raw.toLowerCase()))) {
       item.fields.add(field);item.profileFlagsObserved.add(field);
     }
   }
   if(r.friendsCount!==null)item.friendsCount=r.friendsCount;
   if(r.followingCount!==null)item.followingCount=r.followingCount;
 }
 return {rows,profiles:[...profiles.values()],photoTotal:photos.size,warnings};
}
function scoreProfile(p,photoTotal,decision){
 const photoCount=p.photoIds.size, reasons=[];
 const conflicts=[...p.perPhoto].filter(([,set])=>set.size>1);
 if(conflicts.length)reasons.push("Nhiều loại reaction được ghi trên cùng ảnh; có thể do người dùng đổi cảm xúc giữa các lần xuất");
 if(photoTotal>=8&&photoCount>=Math.max(6,Math.ceil(photoTotal*.70)))
   reasons.push("Tương tác trên "+photoCount+"/"+photoTotal+" ảnh đã thu thập; cần đối chiếu vì có thể là bình chọn hợp lệ");
 const knownFields=p.fields.size;
 if(knownFields===0&&p.profileFlagsObserved.size>=2&&
    ((p.friendsCount!==null&&p.friendsCount>=1000)||
     (p.followingCount!==null&&p.followingCount>=2000)))
   reasons.push("CSV có ít nhất hai mục hồ sơ được kiểm tra là không có thông tin, kèm số bạn bè/theo dõi cao; cần đối chiếu trực tiếp, không tự kết luận bot");
 const previous=decision&&decision[p.profileUrl]||{};
 if(previous.status==="needs_review")reasons.push("Được người kiểm duyệt đánh dấu cần kiểm tra");
 const suspected=reasons.length>0;
 return {profileUrl:p.profileUrl,userId:p.userId,username:p.username,
   photoCount,photoIds:[...p.photoIds].join(" | "),
   reactionTypes:[...p.reactions].join(" | "),reactionRows:p.rawRows,unknownRows:p.unknownRows,
   availableInfoPoints:knownFields,profileInfoFieldsObserved:p.profileFlagsObserved.size,
   profileActuallyChecked:false,friendsCount:p.friendsCount??"",
   followingCount:p.followingCount??"",sourceRows:p.sourceRows.join(" | "),
   status:suspected?LABEL_SUSPECT:LABEL_CLEAR,
   evidence:reasons.join(" | ")||(p.unknownRows>0?
      "Một số reaction chưa rõ loại; không phát hiện dấu hiệu bất thường từ các trường hiện có":
      "Chưa thấy tín hiệu bất thường trong dữ liệu CSV; không xác minh tài khoản thật"),
   reviewerStatus:previous.status||"unreviewed",
   reviewNotes:previous.notes||"",
   botConfirmed:"CHƯA_XÁC_MINH",
 };
}
const COLUMNS=[
 {key:"profileUrl",label:"URL hồ sơ"},
 {key:"userId",label:"User ID"},
 {key:"username",label:"Username"},
 {key:"status",label:"Trạng thái"},
 {key:"evidence",label:"Lý do / bằng chứng"},
 {key:"photoCount",label:"Số ảnh tương tác"},
 {key:"photoIds",label:"Photo IDs"},
 {key:"reactionTypes",label:"Loại reaction"},
 {key:"reactionRows",label:"Dòng đã nhập"},
 {key:"unknownRows",label:"Chưa rõ reaction"},
 {key:"availableInfoPoints",label:"Thông tin sẵn có (0-6)"},
 {key:"profileInfoFieldsObserved",label:"Số mục hồ sơ có dữ liệu kiểm tra"},
 {key:"profileActuallyChecked",label:"Đã truy cập kiểm tra hồ sơ"},
 {key:"friendsCount",label:"Bạn bè (nếu có)"},
 {key:"followingCount",label:"Theo dõi (nếu có)"},
 {key:"reviewerStatus",label:"Duyệt thủ công"},
 {key:"reviewNotes",label:"Ghi chú"},
 {key:"botConfirmed",label:"Kết luận bot"},
];
return {parseCSV,normaliseRows,prepare,scoreProfile,COLUMNS,LABEL_SUSPECT,LABEL_CLEAR};
});