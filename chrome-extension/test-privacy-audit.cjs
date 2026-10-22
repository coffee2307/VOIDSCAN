"use strict";
const assert=require("node:assert/strict");
const privacy=require("./privacy-audit.js");
const base=Date.parse("2026-10-22T00:00:00Z");
const publicSignal=privacy.decide({
 access:"public_metadata",region:"local",hasBio:true,
 name:"Person",email:"name@example.org",phone:"0999988888",
 school:"Private School",birthday:"2008-01-01",html:"<main>Personal data</main>"
},base);
assert.deepEqual(Object.keys(publicSignal).sort(),
 ["status","access","usable","reason","signalCount","signals","checkedAt","expiresAt"].sort());
assert.equal(publicSignal.status,"chưa đủ dữ liệu");
assert.equal(publicSignal.usable,true);
assert(!JSON.stringify(publicSignal).includes("Private School"));
assert(!JSON.stringify(publicSignal).includes("09999"));
assert(!JSON.stringify(publicSignal).includes("example.org"));
const tabSignals=privacy.decide({
  access:"page_visible",avatarSeen:true,locationListed:true,
  schoolListed:true,bioListed:false,friendsBand:"200-999",mutualBand:"1-49",
  postRecency:"within_90d",joinedEra:"5y_plus",
  schoolName:"Trường không được lưu",email:"secret@example.test",
  friendNames:["người A","người B"],postBody:"Nội dung riêng"
},base);
assert.equal(tabSignals.signalCount,7);
assert.equal(tabSignals.usable,true);
assert.equal(tabSignals.status,"chưa đủ dữ liệu");
assert.equal(tabSignals.signals.friendsBand,"200-999");
assert.equal(tabSignals.signals.postAge,"within_90d");
assert(!JSON.stringify(tabSignals).includes("secret"));
assert(!JSON.stringify(tabSignals).includes("Trường không"));
assert(!JSON.stringify(tabSignals).includes("người A"));
const reloaded=privacy.prune({"https://www.facebook.com/profile.php?id=100000000121":tabSignals},base+1000);
assert.equal(Object.values(reloaded.records)[0].signalCount,7);
const inaccessible=privacy.decide({access:"restricted",region:"local"},base);
assert.equal(inaccessible.usable,false);
const url="https://www.facebook.com/profile.php?id=100000000121";
assert.equal(privacy.prune({[url]:publicSignal},base+3600000).records[url].usable,true);
assert.equal(Object.keys(privacy.prune({[url]:publicSignal},base+privacy.TTL_MS+1).records).length,0);
assert.equal(privacy.prune({[url]:{...publicSignal,access:"sneaky",expiresAt:publicSignal.expiresAt}},base).expired,1);
console.log("VOIDSCAN privacy audit transient decision, field minimization, expiry: PASS");
