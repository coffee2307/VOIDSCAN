"use strict";
const assert=require("node:assert/strict");
const f=require("./file-audit.js"),base=require("./lib.js"),xlsx=require("./xlsx-export.js");
const pic=i=>"20309572443815"+String(30+i);
const profile=i=>"https://www.facebook.com/profile.php?id="+String(100000000000+i);
const rows=[];
for(let i=0;i<10;i++){
 rows.push({photoId:pic(i),profileUrl:profile(1),reaction:i?"LIKE":"LOVE"});
 rows.push({photoId:pic(i),profileUrl:profile(100+i),reaction:"LIKE"});
}
rows.push({photoId:pic(0),profileUrl:profile(1),reaction:"CARE"});
rows.push({photoId:pic(0),profileUrl:profile(500),reaction:"UNKNOWN"});
rows.push({photoId:pic(1),profileUrl:profile(501),reaction:"LOVE",friendsCount:"3000",
 followingCount:"3500",hasBio:"0",hasWork:"0"});
const prepared=f.prepare(rows);
assert.equal(prepared.photoTotal,10);
assert.equal(prepared.profiles.length,13);
const scored=prepared.profiles.map(p=>f.scoreProfile(p,prepared.photoTotal,{}));
const one=scored.find(x=>x.profileUrl===profile(1));
assert.equal(one.status,"nghi vấn");
assert(one.evidence.includes("Nhiều loại reaction"));
const empty=scored.find(x=>x.profileUrl===profile(500));
assert.equal(empty.status,"nghi vấn");
assert(empty.evidence.includes("reaction chưa xác định loại"));
assert.equal(empty.unknownRows,1);
const large=scored.find(x=>x.profileUrl===profile(501));
assert.equal(large.status,"nghi vấn");
assert(large.evidence.includes("số bạn bè/theo dõi cao"));
const colliding=f.prepare([
 {photoId:pic(0),profileUrl:profile(603),reaction:"LIKE",displayName:"Nguyễn Liên"},
 {photoId:pic(0),profileUrl:profile(604),reaction:"LOVE",displayName:"Nguyễn Liên"},
 {photoId:pic(1),profileUrl:profile(605),reaction:"LOVE",displayName:"Nguyễn Liên"},
]);
const signals=colliding.profiles.map(x=>f.scoreProfile(x,colliding.photoTotal,{}));
assert.equal(signals.filter(x=>x.status==="nghi vấn").length,2);
assert(signals.every(x=>x.botConfirmed==="CHƯA_XÁC_MINH"));
const regular=scored.find(x=>x.profileUrl===profile(100));
assert.equal(regular.status,"không có dấu hiệu");
assert.equal(f.scoreProfile(prepared.profiles[0],10,{[profile(1)]:{status:"needs_review"}}).status,"nghi vấn");
assert(!f.COLUMNS.some(x=>/birth|phone|email|gender/i.test(x.key)));
assert(f.COLUMNS.find(x=>x.key==="status").label==="Trạng thái");
const commaCsv='\ufeffprofileUrl,photoId,reaction,displayName\r\n'+
  '"https://www.facebook.com/alex.test/","'+pic(0)+'",LIKE,"Alice, Test"\r\n';
const parsed=f.parseCSV(commaCsv);
assert.equal(parsed.rows.length,1);
assert.equal(parsed.rows[0].displayName,"Alice, Test");
const semicolon=f.parseCSV("profileUrl;photoId;reaction\n"+profile(1)+";"+pic(1)+";LOVE\n");
assert.equal(semicolon.rows[0].reaction,"LOVE");
assert.throws(()=>f.parseCSV("username,reaction\nalex,LIKE\n"),/profileUrl/);
assert.throws(()=>f.parseCSV("profileUrl,reaction\n\"bad\n"),/ngoặc kép/);
assert.equal(f.prepare([{photoId:pic(0),profileUrl:"https://evil.test/",reaction:"LIKE"}]).profiles.length,0);
const mismatch=f.prepare([{photoId:pic(0),photoUrl:"https://www.facebook.com/photo/?fbid="+pic(1),
  profileUrl:profile(6),reaction:"LOVE"}]);
assert.equal(mismatch.rows.length,0);
assert.equal(mismatch.warnings.photoMismatch,1);
const unknownMeta=f.prepare([{photoId:pic(0),profileUrl:profile(77),reaction:"LIKE",
  friendsCount:"5000",followingCount:"3000"}]);
assert.equal(f.scoreProfile(unknownMeta.profiles[0],1,{}).status,"không có dấu hiệu");
assert.equal(f.scoreProfile(unknownMeta.profiles[0],1,{}).profileInfoFieldsObserved,0);
const byte=xlsx.workbook(scored,f.COLUMNS);
assert(byte instanceof Uint8Array&&byte.byteLength>5000);
assert.equal(new DataView(byte.buffer).getUint32(0,true),0x04034b50);
assert(xlsx.widths(scored,f.COLUMNS).every(w=>w>=12&&w<=68));
const headerNames=f.COLUMNS.map(c=>c.label);
const csvRows=scored.map(row=>Object.fromEntries(f.COLUMNS.map(col=>[col.label,row[col.key]??""])));
const csv=base.csv(csvRows,headerNames);
assert(csv.startsWith("\ufeff"));
assert(csv.includes("nghi vấn"));
assert(csv.includes("không có dấu hiệu"));
console.log("VOIDSCAN imported-CSV triage and formatted Excel writer: PASS");
