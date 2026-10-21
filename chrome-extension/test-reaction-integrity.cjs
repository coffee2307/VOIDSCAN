"use strict";
const assert=require("node:assert/strict");
const audit=require("./reaction-integrity.js").audit;
const profile=i=>"https://www.facebook.com/profile.php?id="+(100000000000+i);
const id="2030958097714782";
const rows=[
 {photoId:id,profileUrl:profile(1),reaction:"LIKE",capturedAt:"2026-10-21T10:00:00Z"},
 {photoId:id,profileUrl:profile(1),reaction:"LOVE",capturedAt:"2026-10-21T11:00:00Z"},
 {photoId:id,profileUrl:profile(2),reaction:"LOVE"},
 {photoId:id,profileUrl:profile(3),reaction:"UNKNOWN"},
 {photoId:id,profileUrl:"https://invalid.test/id",reaction:"LIKE"},
 {photoId:id,profileUrl:profile(4),reaction:"ANGRY"},
];
const r=audit(rows,{[id]:{LIKE:{displayedCount:10},LOVE:{displayedCount:10}}});
assert.equal(r.totals.duplicates,1);
assert.equal(r.totals.conflicts,1);
assert.equal(r.totals.unknown,1);
assert.equal(r.totals.excluded,1);
assert.equal(r.totals.invalid,1);
assert.equal(r.photos.length,1);
assert.equal(r.photos[0].counts.LOVE,2);
assert.equal(r.photos[0].counts.LIKE,0);
assert.equal(r.photos[0].uniqueAccounts,2);
assert.equal(r.photos[0].coverage.LOVE.ratio,.2);
assert.equal(audit([],{}).totals.uniquePhotoReactions,0);
const alternate=[{photoId:id,profileUrl:profile(5),reaction:"LIKE"},
 {photoId:id,profileUrl:"https://www.facebook.com/people/A-User/100000000005/",reaction:"LIKE"}];
assert.equal(audit(alternate,{}).photos[0].uniqueAccounts,1);
assert.equal(audit(alternate,{}).totals.duplicates,1);
const unresolved=audit([{photoId:id,profileUrl:profile(8),reaction:"LIKE"},
 {photoId:id,profileUrl:profile(8),reaction:"LOVE"}],{});
assert.equal(unresolved.photos[0].ambiguousAccounts,1);
assert.equal(unresolved.photos[0].uniqueAccounts,0);
const mismatch=audit([{photoId:id,photoUrl:"https://www.facebook.com/photo/?fbid=2030958097714783",profileUrl:profile(9),reaction:"LOVE"}],{});
assert.equal(mismatch.totals.invalid,1);
console.log("VOIDSCAN unique reaction count and coverage: PASS");
