"use strict";
const assert=require("node:assert/strict");
const file=require("./file-audit.js");
const importProfile=require("./profile-import.js");
const PHOTO="2030957244381534";
const myurl=id=>"https://www.facebook.com/profile.php?id="+id;
const csv=[
"ID,Name,Gender,Birthday,Location,Bio,Category,Email,Phone Number,Websites,Profile URL,Avatar URL",
'100000000111,Minh Nguyen,,,Dĩ An Bình Dương,Học sinh THPT Dĩ An,Personal Blog,,,,"https://www.facebook.com/minh.vanity","https://images.example.com/a.jpg"',
'100000000222,Lan,,,,,,,,,"https://www.facebook.com/profile.php?id=100000000222",',
'100000000333,Other,,,Hà Nội,,,,,,"https://www.facebook.com/profile.php?id=100000000333",'
].join("\n");
const parsed=file.parseCSV(csv);
const shape=importProfile.inspectExportHeaders(parsed.headers);
assert.equal(shape.isFriendsExporter,true);
assert.equal(shape.hasLocation,true);
assert.equal(shape.hasAvatar,true);
assert.deepEqual(shape.skippedSensitiveHeaders,["email","phonenumber","birthday","gender","websites"]);
const reactions=[
 {photoId:PHOTO,profileUrl:myurl("100000000111"),reaction:"LIKE"},
 {photoId:PHOTO,profileUrl:myurl("100000000222"),reaction:"LOVE"},
 {photoId:PHOTO,profileUrl:myurl("100000000999"),reaction:"CARE"}
];
const out=importProfile.enrich(reactions,parsed.rows);
assert.equal(out.matchedRows,2);
assert.equal(out.sourceAccounts,3);
assert.equal(out.rows[0].displayName,"Minh Nguyen");
assert.equal(out.rows[0].regionContext,"local");
assert.equal(out.rows[0].avatarEvidence,"present");
assert.equal(out.rows[1].avatarEvidence,"unknown");
assert.equal(out.rows[2].profileDataSource,undefined);
const raw=JSON.stringify(out.rows);
for(const field of ["gender","birthday","Email","Phone Number","Websites"])
  assert(!raw.includes('"'+field+'":'),field+" leaked");
const classified=file.prepare(out.rows).profiles.map(p=>file.scoreProfile(p,1,{}));
assert.equal(classified[0].status,"không có dấu hiệu");
assert.equal(classified[1].status,"chưa đủ dữ liệu");
assert.equal(classified[2].status,"chưa đủ dữ liệu");
console.log("VOIDSCAN FBFriends 1.3.1 CSV compatibility: PASS");
