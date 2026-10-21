"use strict";
const assert=require("node:assert/strict");
const cov=require("./auto-coverage.js");
const file=require("./file-audit.js");
const make=i=>"https://www.facebook.com/profile.php?id="+String(100000000000+i);
const urls=Array.from({length:369},(_,i)=>make(i+1));
const blank=cov.assess(urls,{},{});
assert.equal(blank.counters.total,369);
assert.equal(blank.counters.unattempted,369);
assert.equal(blank.attemptedTotal,0);
assert.equal(blank.coverage,0);
assert(blank.diagnosis.includes("Chưa chạy"));
const attempts=Object.fromEntries(urls.map((u,i)=>[u,{status:i<340?"insufficient":
 i<359?"network_error":"http_error",at:"2026-10-22T00:00:00Z"}]));
const failed=cov.assess(urls,attempts,{});
assert.equal(failed.attemptedTotal,369);
assert.equal(failed.counters.missingFields,340);
assert.equal(failed.counters.errors,29);
assert.equal(failed.counters.withEvidence,0);
assert.equal(failed.counters.unattempted,0);
assert(failed.diagnosis.includes("chưa có bằng chứng"));
const observations={
 [urls[0]]:{profileUrl:urls[0],regionContext:"local",source:"public_metadata"},
 [urls[1]]:{profileUrl:urls[1],hasBio:"1",source:"public_metadata"}
};
const partly=cov.assess(urls,attempts,observations);
assert.equal(partly.counters.withEvidence,2);
assert.equal(partly.attemptedTotal,369);
assert.equal(partly.coverage,0.5);
const reactions=urls.map((u,i)=>({
 photoId:"2030957244381534",profileUrl:u,reaction:i<7?"UNKNOWN":"LOVE"
}));
const p=file.prepare(reactions);
const scores=p.profiles.map(x=>file.scoreProfile(x,p.photoTotal,{}));
assert.equal(scores.filter(x=>x.status===file.LABEL_SUSPECT).length,0);
assert.equal(scores.filter(x=>x.status===file.LABEL_INSUFFICIENT).length,369);
assert.equal(scores.filter(x=>x.needsReactionCheck).length,7);
console.log("VOIDSCAN 369 URL no usable profile evidence / 7 unknown reaction: PASS");
