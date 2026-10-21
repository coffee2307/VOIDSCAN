/* Local-only deterministic triage. This does not determine bot identity. */
(function(root,factory){
  const base=root.VoidscanAudit||(typeof require==="function"?require("./lib.js"):null);
  const api=factory(base);
  if(typeof module==="object"&&module.exports)module.exports=api;
  root.VoidscanReview=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(base){
"use strict";
const STATUSES=["unreviewed","provisional_pass","needs_review","inconclusive"];
function normalizeDecision(item){
  const value=item&&typeof item==="object"?item:{};
  return {status:STATUSES.includes(value.status)?value.status:"unreviewed",
    notes:typeof value.notes==="string"?value.notes.slice(0,220):"",
    reviewedAt:typeof value.reviewedAt==="string"?value.reviewedAt:""};
}
function analyse(input, decisions){
  const records=Array.isArray(input)?input:[];
  const accounts=new Map(), photos=new Set(), eventTypes=new Map();
  for(const item of records){
    if(!item||!base.cleanReaction(item.reaction))continue;
    const id=base.photoId(item.photoUrl),meta=base.profileMeta(item.profileUrl);
    if(!id||id!==item.photoId||!meta)continue;
    photos.add(id);
    const row=accounts.get(meta.profileUrl)||{
      profileUrl:meta.profileUrl,username:meta.username,userId:meta.userId,
      photoIds:new Set(),events:0,metadata:new Set(),reactionTypes:new Set(),
      conflictingPhotos:new Set(),reasons:[]};
    row.photoIds.add(id);
    row.reactionTypes.add(base.cleanReaction(item.reaction));
    row.events++;
    for(const [name,value] of [["avatar",item.avatarUrl],["username",meta.username],
      ["userId",meta.userId],["mutualCount",item.mutualFriendsNumber]]){
      if(value!==null&&value!==undefined&&value!=="")row.metadata.add(name);
    }
    const key=id+"|"+meta.profileUrl;
    const last=eventTypes.get(key);
    if(last&&last!==item.reaction)row.conflictingPhotos.add(id);
    eventTypes.set(key,item.reaction);
    accounts.set(meta.profileUrl,row);
  }
  const denominator=photos.size;
  const all=[...accounts.values()].map(account=>{
    const photoCount=account.photoIds.size;
    const repeats=account.events-photoCount;
    const reasons=[];
    let priority="no_signal";
    if(account.conflictingPhotos.size){
      priority="review_first";
      reasons.push("Dữ liệu ghi nhận nhiều loại reaction trên cùng ảnh: cần đối chiếu thời điểm thu thập, có thể là thay đổi cảm xúc hợp lệ");
    }
    if(denominator>=8&&photoCount>=Math.max(6,Math.ceil(denominator*.70))){
      if(priority!=="review_first")priority="review";
      reasons.push("Tương tác trên tỷ lệ lớn các ảnh đã quan sát ("+photoCount+"/"+denominator+"); có thể là bình chọn hợp lệ");
    }
    if(repeats>0){
      reasons.push("Có "+repeats+" bản ghi lặp trong dữ liệu xuất; sẽ chỉ tính một reaction cho mỗi ảnh");
    }
    if(reasons.length===0)reasons.push("Không thấy tín hiệu bất thường trong dữ liệu reaction hiện có; chưa xác minh hồ sơ");
    const dec=normalizeDecision(decisions&&decisions[account.profileUrl]);
    return {...dec,profileUrl:account.profileUrl,username:account.username,userId:account.userId,
      photos:[...account.photoIds].sort(),photoCount,reactionTypes:[...account.reactionTypes].sort(),
      metadataFields:account.metadata.size,priority,reasons,observedReactions:photoCount};
  });
  const order={review_first:0,review:1,no_signal:2};
  all.sort((a,b)=>order[a.priority]-order[b.priority]||a.profileUrl.localeCompare(b.profileUrl));
  return {accounts:all,observedPhotos:denominator,rawRows:records.length,
    validReactions:eventTypes.size};
}
function summary(result){
  const list=result&&Array.isArray(result.accounts)?result.accounts:[];
  const counters={total:list.length,reviewFirst:0,review:0,noSignal:0,
    checked:0,provisionalPass:0,needsReview:0,inconclusive:0,
    automaticBotLabels:0,automaticDisqualifications:0};
  for(const item of list){
    if(item.priority==="review_first")counters.reviewFirst++;
    else if(item.priority==="review")counters.review++;
    else counters.noSignal++;
    if(item.status!=="unreviewed")counters.checked++;
    if(item.status==="provisional_pass")counters.provisionalPass++;
    if(item.status==="needs_review")counters.needsReview++;
    if(item.status==="inconclusive")counters.inconclusive++;
  }
  return counters;
}
function csvRows(result, flaggedOnly){
  const list=result&&Array.isArray(result.accounts)?result.accounts:[];
  return list.filter(x=>!flaggedOnly||x.priority!=="no_signal"||x.status==="needs_review")
    .map(x=>({
      profileUrl:x.profileUrl,userId:x.userId,username:x.username,
      photoCount:x.photoCount,photoIds:x.photos.join(" | "),
      reactionTypes:x.reactionTypes.join(" | "),metadataFieldsAvailable:x.metadataFields,
      screeningPriority:x.priority,screeningReasons:x.reasons.join(" | "),
      humanReviewStatus:x.status,reviewerNotes:x.notes,reviewedAt:x.reviewedAt,
      automatedBotVerdict:"NOT_DETERMINED"}));
}
const CSV_COLUMNS=["profileUrl","userId","username","photoCount","photoIds",
  "reactionTypes","metadataFieldsAvailable","screeningPriority","screeningReasons",
  "humanReviewStatus","reviewerNotes","reviewedAt","automatedBotVerdict"];
return {STATUSES,normalizeDecision,analyse,summary,csvRows,CSV_COLUMNS};
});