"use strict";
const assert=require("node:assert/strict");
const meta=require("./public-metadata.js");
const url="https://www.facebook.com/profile.php?id=100000000123";
assert.equal(meta.safeUrl(url),url);
assert.equal(meta.safeUrl("https://evil.example/profile.php?id=100000000123"),null);
assert.equal(meta.safeUrl("https://www.facebook.com/login/"),null);
assert.equal(meta.locality("Dĩ An, Bình Dương"),"local");
assert.equal(meta.locality("Bắc Ninh"),"other");
assert.equal(meta.locality(""),"unknown");
(async()=>{
 let called=false;
 const rate=await meta.get(url,async()=>({status:429}),class {});
 assert.equal(rate.access,"rate_limited");
 const restricted=await meta.get(url,async()=>({
   status:200,ok:true,url:"https://www.facebook.com/login/",headers:{get:()=>null},text:async()=>"<html></html>"
 }),class {});
 assert.equal(restricted.access,"restricted");
 const invalid=await meta.get("https://evil.example/",async()=>{called=true;},class{});
 assert.equal(invalid.access,"invalid");assert.equal(called,false);
 console.log("VOIDSCAN public metadata respects host, access restrictions and 429: PASS");
})().catch(e=>{console.error(e);process.exitCode=1});
