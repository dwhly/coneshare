// Real OTP + native draft + explicit lost-distribution fixture + human browser reset.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/Users/dano/code/amforge-forks/shots/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),{execFileSync}=require('child_process');
const root=path.resolve(__dirname,'../../..'),local=root+'/deploy/chief-glue-v1/.local';
const f=JSON.parse(fs.readFileSync(local+'/fixture.json')),email=process.env.MEMBER_EMAIL;
assert.ok(email&&email.startsWith('r2-'));
const base='http://glue-v1.100-110-241-2.sslip.io',pause=ms=>new Promise(r=>setTimeout(r,ms));
function shell(code,input){return execFileSync('docker',['compose','-f','deploy/chief-glue-v1/docker-compose.yml','exec','-T','web','python','manage.py','shell','-c',code],{cwd:root,input:JSON.stringify(input),encoding:'utf8'}).trim().split('\n').at(-1)}
(async()=>{const browser=await chromium.launch();try{
 const ctx=await browser.newContext(),member=await ctx.newPage();await member.goto(base+'/view/'+f.slug,{waitUntil:'networkidle'});
 await member.locator('#name').fill('R2 Recovery Member');await member.locator('#email').fill(email);await member.getByRole('button',{name:'Send verification code'}).click();await member.locator('#code-form').waitFor({state:'visible'});
 let code;for(let n=0;n<30&&!code;n++){
  const list=await fetch('http://100.110.241.2:8785/api/v1/search?query='+encodeURIComponent('to:'+email)).then(r=>r.json());
  for(const m of (list.messages||[]).slice(0,1)){const full=await fetch('http://100.110.241.2:8785/api/v1/message/'+m.ID).then(r=>r.json());code=full.Text.match(/verification code is (\d{6})/)?.[1]}if(!code)await pause(1000);
 }assert.ok(code);await member.locator('#code').fill(code);await member.getByRole('button',{name:'Continue',exact:true}).click();await member.locator('#nda').waitFor({state:'visible'});
 await ctx.storageState({path:local+'/member-'+email.split('@')[0]+'.json'});
 const stuck=JSON.parse(shell(fs.readFileSync(__dirname+'/stuck_fixture.py','utf8'),{room_id:f.room_id,email}));
 const staff=await browser.newPage();await staff.goto(base+'/signing/',{waitUntil:'networkidle'});await staff.locator('#email').fill('admin@amforge.test');await staff.locator('#password').fill('z8QjMn4nWYK3qoXPLX2Q');await staff.getByRole('button',{name:'Sign in',exact:true}).click();
 const row=staff.getByRole('row').filter({hasText:email});await row.getByRole('button',{name:'Reset NDA'}).waitFor();
 const reset=staff.waitForResponse(r=>r.url().includes('/nda-reset/')&&r.request().method()==='POST');await row.getByRole('button',{name:'Reset NDA'}).click();const response=await reset;assert.equal(response.status(),201);const replacement=await response.json();assert.notEqual(replacement.id,stuck.workflow_id);assert.equal(replacement.member_email,email);
 const verify="import json,sys; from dealroom_sign.models import Workflow,SignCredential; from dealroom_sign.client import Documenso,SignError; d=json.load(sys.stdin); w=Workflow.objects.get(pk=d['workflow_id']); assert w.state=='cancelled'; c=Documenso(SignCredential.objects.get(owner=w.owner)); response=c.http.get('envelope/'+w.envelope_id); assert response.status_code==404, response.status_code; print('deleted')";
 assert.equal(shell(verify,stuck),'deleted');
 await staff.screenshot({path:'/Users/dano/code/chief-dealroom/docs/status/shots/C-nda-reset.png',fullPage:true});
 console.log('PASS human browser reset: real unsent Sign draft deleted, old local workflow cancelled, fresh member generation queued');
}catch(e){console.error('FAIL reset:',e.message);process.exitCode=1}finally{await browser.close()}})();
