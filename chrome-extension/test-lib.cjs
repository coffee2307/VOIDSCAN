"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const lib=require("./lib.js");
const m=JSON.parse(fs.readFileSync(path.join(__dirname,"manifest.json"),"utf8"));
assert.equal(m.manifest_version,3);
assert.deepEqual(m.permissions,["activeTab","scripting","storage","downloads"]);
assert.equal("host_permissions" in m,false);
for(const perm of ["cookies","identity","webRequest","debugger","tabs","unlimitedStorage"]){
 assert.equal(m.permissions.includes(perm),false);
}
assert.equal(lib.photoId("https://www.facebook.com/photo/?fbid=2030957244381534&set=pcb.2030979361045989"),"2030957244381534");
assert.equal(lib.photoId("https://www.facebook.com/tuoitretruongthptdian/posts/123"),null);
const scopeA="2030957244381534",scopeB="2030957077714884";
const fixtures=[];
for(let i=0;i<190;i++)fixtures.push({photoId:scopeA,photoUrl:"https://www.facebook.com/photo/?fbid="+scopeA,profileUrl:"https://www.facebook.com/profile.php?id="+(100000000001+i),reaction:"LOVE"});
for(let i=0;i<110;i++)fixtures.push({photoId:scopeB,photoUrl:"https://www.facebook.com/photo/?fbid="+scopeB,profileUrl:"https://www.facebook.com/profile.php?id="+(100000000001+i),reaction:"LIKE"});
assert.equal(lib.scopedRows(fixtures,scopeA).length,190);
assert.equal(lib.scopedRows(fixtures,scopeB).length,110);
assert.equal(lib.scopedRows(fixtures,"all").length,300);
assert.equal(lib.scopedRows(fixtures,"").length,0);
assert.deepEqual(lib.photoCounts(fixtures).map(x=>x.count),[190,110]);
assert.equal(lib.photoId("https://other.example/photo/?fbid=2030957244381534"),null);
assert.equal(lib.normalizeProfile("https://www.facebook.com/profile.php?id=1234567890123&comment_id=98"),"https://www.facebook.com/profile.php?id=1234567890123");
assert.equal(lib.normalizeProfile("https://www.facebook.com/jane.doe/?mibextid=abc"),"https://www.facebook.com/jane.doe/");
assert.equal(lib.normalizeProfile("https://www.facebook.com/people/Test-Name/1234567890123/"),"https://www.facebook.com/people/Test-Name/1234567890123/");
for(const url of ["https://www.facebook.com/photo/?fbid=11111",
"https://www.facebook.com/groups/12345","https://www.facebook.com/pages/12345",
"https://evil.facebook.com/hacker","https://facebook.com.evil.example/profile",
"https://www.facebook.com/posts/12345"]){
 assert.equal(lib.normalizeProfile(url),null,url);
}
assert.equal(lib.cleanReaction("haha"),"HAHA");
assert.equal(lib.cleanReaction("SAD"),null);
const records=[
 {photoId:"2030957244381534",photoUrl:"https://www.facebook.com/photo/?fbid=2030957244381534",profileUrl:"https://www.facebook.com/profile.php?id=1234567890123",reaction:"LOVE"},
 {photoId:"2030957244381534",photoUrl:"https://www.facebook.com/photo/?fbid=2030957244381534",profileUrl:"https://www.facebook.com/jane.doe/",reaction:"LIKE"},
 {photoId:"2030957077714884",photoUrl:"https://www.facebook.com/photo/?fbid=2030957077714884",profileUrl:"https://www.facebook.com/jane.doe/",reaction:"HAHA"},
 {photoId:"9999999999999",photoUrl:"https://www.facebook.com/tuoitretruongthptdian/posts/123",profileUrl:"https://www.facebook.com/bad/",reaction:"WOW"}
];
const summary=lib.aggregate(records);
assert.equal(summary.length,2);
assert.equal(summary[0].observedRows,2);
assert.equal(summary[0].LOVE,1);
assert.equal(summary[1].HAHA,1);
const csv=lib.csv([{col:'=HYPERLINK("evil","click")',num:12}],["col","num"]);
assert(csv.startsWith("\ufeff"));
assert(csv.includes("'=HYPERLINK"));
const content=fs.readFileSync(path.join(__dirname,"content.js"),"utf8");
const popup=fs.readFileSync(path.join(__dirname,"popup.js"),"utf8");
assert(content.includes("querySelectorAll"));
assert(content.includes("chrome.storage.local"));
assert(!content.includes("document.cookie"));
assert(!content.includes("chrome.cookies"));
assert(!content.includes("fetch("));
assert(!content.includes("XMLHttpRequest"));
assert(!content.includes("eval("));
assert(!popup.includes("fetch("));
assert.equal(lib.profileMeta("https://www.facebook.com/profile.php?id=1234567890123").userId,"1234567890123");
assert.equal(lib.profileMeta("https://www.facebook.com/jane.doe/?ref=example").username,"jane.doe");
assert.equal(lib.reactionFromLabel("Love 34"),"LOVE");
assert.equal(lib.reactionFromLabel("Thương thương 19"),"CARE");
assert.equal(lib.reactionFromLabel("Reaction: Love 27"),"LOVE");
assert.equal(lib.reactionFromLabel("Cảm xúc: Thích 1.2K"),"LIKE");
assert.equal(lib.reactionFromLabel("Like (12)"),"LIKE");
assert.equal(lib.reactionFromProfileLabel("Nguyễn A đã thích"),"LIKE");
assert.equal(lib.reactionFromProfileLabel("Nguyễn B đã thích, unseen story"),"LIKE");
assert.equal(lib.reactionFromProfileLabel("Nguyễn C đã cảm thấy Yêu thích"),"LOVE");
assert.equal(lib.reactionFromProfileLabel("Nguyễn D đã cảm thấy Thương thương"),"CARE");
assert.equal(lib.reactionFromProfileLabel("Nguyễn E đã cảm thấy Haha"),"HAHA");
assert.equal(lib.reactionFromProfileLabel("Nguyễn F đã cảm thấy Wow"),"WOW");
assert.equal(lib.reactionFromProfileLabel("Nguyễn G đã cảm thấy Buồn"),"EXCLUDED");
assert.equal(lib.reactionFromProfileLabel("Nguyễn H đã cảm thấy Phẫn nộ"),"EXCLUDED");
assert.equal(lib.reactionFromProfileLabel("Người này chỉ có tên Like"),null);
assert.equal(lib.reactionFromLabel("Sad 100"),null);
assert.equal(lib.parseCount("1.5K"),1500);
assert.equal(lib.avatarUrl("https://evil.example/photo.png"),"");
assert.equal(lib.avatarUrl("https://scontent.fsgn2-1.fna.fbcdn.net/pic.png"),"https://scontent.fsgn2-1.fna.fbcdn.net/pic.png");
const repeated=[records[0],{...records[0],avatarUrl:"https://scontent.fsgn2-1.fna.fbcdn.net/pic.png",userId:"1234567890123"}];
const compact=lib.dedupe(repeated);
assert.equal(compact.length,1);
assert.equal(compact[0].avatarUrl,"https://scontent.fsgn2-1.fna.fbcdn.net/pic.png");
assert.equal(compact[0].userId,"1234567890123");
assert(content.includes("pointerdown"),"floating panel must have drag support");
assert(content.includes("beginScan(true)"),"scan all 5 types should be wired");
assert(content.includes("MAX_STEPS"),"scanning must have hard upper bound");
assert(content.includes("stopped"),"scanning must be interruptible");
assert(!content.includes("window.open("));
console.log("VOIDSCAN Chrome extension pure logic and permission tests: PASS");