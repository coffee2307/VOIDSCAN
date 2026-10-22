"use strict";
const assert=require("node:assert/strict");
const tabAudit=require("./tab-audit.js");
const url=id=>"https://www.facebook.com/profile.php?id="+id;
(async()=>{
 tabAudit.config.settleMs=0;
 const seen=[];
 let current=null,removed=false,redirect=false;
 const fake={
  tabs:{
   async create(o){seen.push("create:"+o.url);current={id:77,status:"complete",url:o.url};return current;},
   async update(id,o){seen.push("update:"+o.url);assert.equal(id,77);
     current={id:77,status:"complete",url:redirect?"https://www.facebook.com/login/?next=profile":o.url};
     return current;},
   async get(id){assert.equal(id,77);return current;},
   async remove(id){assert.equal(id,77);removed=true;},
   onUpdated:{addListener(){},removeListener(){}}
  },
  scripting:{
   async executeScript(o){assert.equal(o.target.tabId,77);
    return [{result:{access:"page_visible",avatarSeen:true}}];
   }
  }
 };
 const a=await tabAudit.scan(url("100000000123"),null,fake);
 assert.equal(a.access,"page_visible");
 assert.equal(a.avatarSeen,true);
 assert.equal(a.tabId,77);
 const b=await tabAudit.scan(url("100000000124"),a.tabId,fake);
 assert.equal(b.access,"page_visible");
 assert.equal(seen.filter(s=>s.startsWith("create:")).length,1);
 assert.equal(seen.filter(s=>s.startsWith("update:")).length,1);
 redirect=true;
 const c=await tabAudit.scan(url("100000000125"),b.tabId,fake);
 assert.equal(c.access,"auth_required");
 assert(!tabAudit.isAllowed("https://evil.test/profile.php?id=100000000123"));
 await tabAudit.close(77,fake);
 assert.equal(removed,true);
 console.log("VOIDSCAN single Chrome tab sequential navigation, auth stop, close: PASS");
})().catch(e=>{console.error(e);process.exitCode=1;});
