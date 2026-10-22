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
 ["status","access","usable","reason","checkedAt","expiresAt"].sort());
assert.equal(publicSignal.status,"chưa đủ dữ liệu");
assert.equal(publicSignal.usable,true);
assert(!JSON.stringify(publicSignal).includes("school"));
assert(!JSON.stringify(publicSignal).includes("09999"));
assert(!JSON.stringify(publicSignal).includes("example.org"));
const inaccessible=privacy.decide({access:"restricted",region:"local"},base);
assert.equal(inaccessible.usable,false);
const url="https://www.facebook.com/profile.php?id=100000000121";
assert.equal(privacy.prune({[url]:publicSignal},base+3600000).records[url].usable,true);
assert.equal(Object.keys(privacy.prune({[url]:publicSignal},base+privacy.TTL_MS+1).records).length,0);
assert.equal(privacy.prune({[url]:{...publicSignal,access:"sneaky",expiresAt:publicSignal.expiresAt}},base).expired,1);
console.log("VOIDSCAN privacy audit transient decision, field minimization, expiry: PASS");
