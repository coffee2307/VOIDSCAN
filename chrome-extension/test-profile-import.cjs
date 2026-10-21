"use strict";
const assert=require("node:assert/strict");
const importProfile=require("./profile-import.js");
const audit=require("./file-audit.js");
const photo="2030957244381534";
const url=n=>"https://www.facebook.com/profile.php?id="+String(100000000000+n);
const rows=[
 {photoId:photo,profileUrl:url(1),reaction:"LOVE",avatarUrl:""},
 {photoId:photo,profileUrl:url(2),reaction:"UNKNOWN",avatarUrl:""},
 {photoId:photo,profileUrl:url(3),reaction:"LIKE",avatarUrl:""}
];
let prepared=audit.prepare(rows);
let score=prepared.profiles.map(p=>audit.scoreProfile(p,1,{}));
assert(score.every(p=>p.status==="chưa đủ dữ liệu"));
assert.equal(score[0].avatarEvidence,"unknown");
assert(score[1].dataQuality.includes("UNKNOWN"));
const source=[
 {profileUrl:url(1),currentCity:"Dĩ An, Bình Dương",hasAvatar:"1",hasBio:"1"},
 {profileUrl:url(2),currentCity:"Bắc Ninh",hasAvatar:"0",hasBio:"0"},
 {profileUrl:url(3),currentCity:"TP. Hồ Chí Minh",hasAvatar:""},
 {profileUrl:"https://www.facebook.com/profile.php?id=100000000009",currentCity:"HCM"}
];
assert.equal(importProfile.region("Dĩ An, TP. Hồ Chí Minh"),"local");
assert.equal(importProfile.region("Bình Dương"),"local");
assert.equal(importProfile.region("Bắc Ninh"),"other");
assert.equal(importProfile.region(""),"unknown");
const enriched=importProfile.enrich(rows,source);
assert.equal(enriched.matchedRows,3);
assert.equal(enriched.sourceAccounts,4);
prepared=audit.prepare(enriched.rows);
score=prepared.profiles.map(p=>audit.scoreProfile(p,1,{}));
const a=score.find(x=>x.profileUrl===url(1));
const b=score.find(x=>x.profileUrl===url(2));
const c=score.find(x=>x.profileUrl===url(3));
assert.equal(a.status,"không có dấu hiệu");
assert.equal(a.regionContext,"local");
assert.equal(a.avatarEvidence,"present");
assert(a.localRuleApplied.includes("địa điểm"));
assert.equal(b.status,"nghi vấn");
assert.equal(b.avatarEvidence,"absent_observed");
assert.equal(b.regionContext,"other");
assert(b.evidence.includes("không thấy avatar"));
assert.equal(c.status,"không có dấu hiệu");
assert.equal(c.avatarEvidence,"unknown");
assert.equal(c.regionContext,"local");
assert(importProfile.enrich(rows,[]).rows.every(r=>!r.profileDataSource));
const embedded=importProfile.enrich([
 {photoId:photo,profileUrl:url(4),reaction:"LIKE",currentCity:"Bình Dương",hasAvatar:"0"}
],[]);
const embeddedScore=audit.scoreProfile(audit.prepare(embedded.rows).profiles[0],1,{});
assert.equal(embeddedScore.avatarEvidence,"absent_observed");
assert.equal(embeddedScore.regionContext,"local");
assert.equal(embeddedScore.profileDataSource,"reaction_csv_fields");
assert.equal(embeddedScore.status,"không có dấu hiệu");
const temporal=importProfile.enrich([
 {photoId:photo,profileUrl:url(5),reaction:"LIKE",friendsCount:"3500"}
],[{
 profileUrl:url(5),mutualFriendsNumber:"3",
 latestVisiblePostAt:"2024-01-01",visiblePostDateCount:"4",source:"observed_open_profile"
}]);
const temporalScore=audit.scoreProfile(audit.prepare(temporal.rows).profiles[0],1,{});
assert.equal(temporalScore.mutualFriendsNumber,3);
assert.equal(temporalScore.latestVisiblePostAt,"2024-01-01");
assert.equal(temporalScore.status,"nghi vấn");
assert(temporalScore.evidence.includes("mốc ngày cũ"));
const mergedEvidence=importProfile.enrich([
 {photoId:photo,profileUrl:url(88),reaction:"LOVE"}
],[
 {profileUrl:url(88),currentCity:"Hà Nội",hasAvatar:"1"},
 {profileUrl:url(88),education:"THPT Ví Dụ",joinedYear:"2018",source:"observed_open_profile"}
]);
assert.equal(mergedEvidence.matchedRows,1);
const annotated=audit.scoreProfile(audit.prepare(mergedEvidence.rows).profiles[0],1,{});
assert.equal(annotated.regionContext,"other");
assert.equal(annotated.avatarEvidence,"present");
assert.equal(annotated.educationObserved,"THPT Ví Dụ");
assert.equal(annotated.joinedYear,"2018");
assert.equal(annotated.profileDataSource,"observed_open_profile");
console.log("VOIDSCAN profile evidence join, region tri-state, no false absence: PASS");
