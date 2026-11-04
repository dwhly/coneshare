// Live member isolation: real OTP, real evidence pages, no API/signature mocks.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/Users/dano/code/amforge-forks/shots/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(__dirname,'../../..'),local=root+'/deploy/chief-glue-v1/.local';
const f=JSON.parse(fs.readFileSync(local+'/fixture.json'));
const email=process.env.MEMBER_EMAIL||fs.readFileSync(local+'/r2/member-email','utf8').trim();
const base=process.env.GLUE_URL||'http://glue-v1.100-110-241-2.sslip.io';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{const browser=await chromium.launch();try{
 const subject=await browser.newContext({storageState:local+'/member-'+email.split('@')[0]+'.json'});
 const other=await browser.newContext();const page=await other.newPage();
 await page.goto(base+'/view/'+f.slug,{waitUntil:'networkidle'});
 await page.locator('#name').fill('Other Member');await page.locator('#email').fill('other@acme.test');
 await page.getByRole('button',{name:'Send verification code'}).click();await page.locator('#code-form').waitFor({state:'visible'});
 let code;for(let n=0;n<30&&!code;n++){
  const list=await fetch('http://100.110.241.2:8785/api/v1/search?query='+encodeURIComponent('to:other@acme.test')).then(r=>r.json());
  for(const m of (list.messages||[]).slice(0,1)){
   const message=await fetch('http://100.110.241.2:8785/api/v1/message/'+m.ID).then(r=>r.json());
   code=message.Text.match(/verification code is (\d{6})/)?.[1];
  }if(!code)await delay(1000);
 }
 assert.ok(code);await page.locator('#code').fill(code);await page.getByRole('button',{name:'Continue',exact:true}).click();
 await page.locator('#contents').waitFor({state:'visible',timeout:30000});
 const rooms=[];for(const ctx of [subject,other]){
  const response=await ctx.request.get(base+'/api/v1/dealroom/recipient/'+f.slug+'/room/');
  assert.equal(response.status(),200);rooms.push(await response.json());
 }
 const [mine,theirs]=rooms;
 assert.equal(mine.folders.length,1);assert.equal(theirs.folders.length,1);
 assert.notEqual(mine.folders[0].id,theirs.folders[0].id);
 assert.ok(!mine.folders.some(v=>v.name==='Agreements'));
 const own=mine.files.find(v=>v.folder_id===mine.folders[0].id);
 const foreign=theirs.files.find(v=>v.folder_id===theirs.folders[0].id);
 assert.ok(own&&foreign);
 const ownPage=await subject.request.get(base+own.page_url);assert.equal(ownPage.status(),200);
 assert.equal(ownPage.headers()['content-type'],'image/jpeg');assert.equal(ownPage.headers()['cache-control'],'private, no-store');
 assert.equal((await subject.request.get(base+foreign.page_url)).status(),403);
 assert.equal((await other.request.get(base+own.page_url)).status(),403);
 console.log('PASS two real OTP members: disjoint private NDA folders, own evidence HTTP 200, both cross-member pages HTTP 403');
}catch(e){console.error('FAIL review guards:',e.message);process.exitCode=1}finally{await browser.close()}})();
