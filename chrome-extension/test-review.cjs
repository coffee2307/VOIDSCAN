"use strict";
const assert=require("node:assert/strict");
const base=require("./lib.js");
const rev=require("./review-lib.js");
const p=id=>"https://www.facebook.com/photo/?fbid="+id;
const u=i=>"https://www.facebook.com/profile.php?id="+String(100000000000+i);
const rows=[];
const photos=Array.from({length:10},(_,i)=>"20309572443815"+String(i+30));
for(let i=0;i<10;i++){
 rows.push({photoId:photos[i],photoUrl:p(photos[i]),profileUrl:u(1),reaction:"LIKE",
   avatarUrl:i%2?"":"https://scontent.fsgn2-1.fna.fbcdn.net/test.jpg"});
 rows.push({photoId:photos[i],photoUrl:p(photos[i]),profileUrl:u(i+200),reaction:"LOVE"});
}
rows.push({photoId:photos[1],photoUrl:p(photos[1]),profileUrl:u(1),reaction:"WOW"});
rows.push({photoId:photos[2],photoUrl:p(photos[2]),profileUrl:u(200),reaction:"ANGRY"});
rows.push({photoId:photos[2],photoUrl:p(photos[2]),profileUrl:"https://other.example/no",reaction:"LIKE"});
rows.push({photoId:photos[2],photoUrl:p(photos[2]),profileUrl:u(600),reaction:"LOVE",capturedAt:"2026-10-21T08:22:11Z"});
const decision={ [u(1)]:{status:"needs_review",notes:"Cần so sánh ảnh với thời điểm reaction",
  reviewedAt:"2026-10-21T09:01:01Z"} };
const result=rev.analyse(rows,decision);
const one=result.accounts.find(a=>a.profileUrl===u(1));
const s=rev.summary(result);
assert.equal(result.observedPhotos,10);
assert.equal(result.validReactions,21);
assert.equal(one.photoCount,10);
assert.equal(one.priority,"review_first");
assert(one.reasons.some(x=>x.includes("nhiều loại reaction")));
assert.equal(one.status,"needs_review");
assert.equal(s.reviewFirst,1);
assert.equal(s.automaticBotLabels,0);
assert.equal(s.automaticDisqualifications,0);
assert(result.accounts.some(x=>x.priority==="no_signal"));
assert(rev.csvRows(result,true).every(x=>x.screeningPriority!=="no_signal"||x.humanReviewStatus==="needs_review"));
assert(rev.csvRows(result,true).every(x=>x.automatedBotVerdict==="NOT_DETERMINED"));
assert.equal(rev.normalizeDecision({status:"bot",notes:"x".repeat(300)}).status,"unreviewed");
assert.equal(rev.normalizeDecision({status:"bot",notes:"x".repeat(300)}).notes.length,220);
assert(rev.CSV_COLUMNS.includes("screeningReasons"));
assert(!rev.CSV_COLUMNS.includes("birthDate"));
assert(!rev.CSV_COLUMNS.includes("phone"));
assert(!rev.CSV_COLUMNS.includes("email"));
const exportCsv=base.csv(rev.csvRows(result,true),rev.CSV_COLUMNS);
assert(exportCsv.startsWith("\ufeff"));
assert(exportCsv.includes("NOT_DETERMINED"));
const malicious=rev.normalizeDecision({notes:'=HYPERLINK("https://evil.invalid","x")'});
assert(base.csv([{notes:malicious.notes}],["notes"]).includes("'=HYPERLINK"));
console.log("VOIDSCAN local automatic triage unit tests: PASS");