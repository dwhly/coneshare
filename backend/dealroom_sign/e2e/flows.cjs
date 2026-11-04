// Real browser acceptance; no signing/status mocks. Fixture credentials stay in ignored files.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/Users/dano/code/amforge-forks/shots/node_modules/playwright');
const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'../../..');
const fixture=JSON.parse(fs.readFileSync(root+'/deploy/chief-glue-v1/.local/fixture.json'));
const base=process.env.GLUE_URL||'http://glue-v1.100-110-241-2.sslip.io';
const shots=process.env.SHOTS||'/Users/dano/code/chief-dealroom/docs/status/shots';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function mail(to,predicate){for(let n=0;n<40;n++){const list=await fetch('http://100.110.241.2:8785/api/v1/search?query='+encodeURIComponent('to:'+to)).then(r=>r.json());for(const m of (list.messages||[]).slice(0,8)){const full=await fetch('http://100.110.241.2:8785/api/v1/message/'+m.ID).then(r=>r.json());const value=predicate(full);if(value)return value;}await sleep(1000);}throw Error('No matching Mailpit delivery');}
async function sign(p,name){
 await p.waitForLoadState('networkidle');
 await p.getByTestId('signature-pad-dialog-button').waitFor({timeout:30000});
 await p.getByTestId('signature-pad-dialog-button').click();
 await p.getByRole('tab',{name:'Type',exact:true}).click();
 await p.getByTestId('signature-pad-type-input').fill(name);
 await p.getByRole('button',{name:'Next',exact:true}).click();
 const canvas=p.locator('.konva-container').first();const bounds=await canvas.boundingBox();
 const signed=p.waitForResponse(r=>r.url().includes('/api/trpc/')&&r.url().includes('envelope.field.sign'));
 await canvas.click({position:{x:bounds.width*.275,y:bounds.height*.74}});
 const response=await signed;if(!response.ok()){console.log('Sign error body:',(await response.text()).replace(/api_[A-Za-z0-9_]+/g,'[redacted]').slice(0,400));throw Error('Sign field RPC HTTP '+response.status());}
 await p.screenshot({path:shots+'/C-signing-fields.png'});
 await p.getByRole('button',{name:'Complete',exact:true}).click();
 await p.getByRole('button',{name:'Sign',exact:true}).click();
 return Date.now();
}
(async()=>{
 const browser=await chromium.launch();
 const statePath=root+'/deploy/chief-glue-v1/.local/member-state.json';
 const context=await browser.newContext({viewport:{width:1360,height:950},...(fs.existsSync(statePath)?{storageState:statePath}:{})}),p=await context.newPage();
 p.on('pageerror',e=>console.log('PAGE ERROR:',e.message));
 p.on('request',r=>{if(r.url().includes('/api/trpc/envelope.field.sign')){const d=r.postDataJSON();const visit=o=>{if(o&&typeof o==='object')for(const[k,v]of Object.entries(o)){if(['authOptions','actionAuth','globalActionAuth','signatureLevel'].includes(k))console.log('sign auth shape',k,JSON.stringify(v));visit(v)}};visit(d)}});
 p.on('response',async r=>{if(r.status()>=400&&r.url().includes('/api/trpc/'))console.log('Sign RPC error',r.status(),new URL(r.url()).pathname)});
 try {
  await p.goto(base+'/view/'+fixture.slug,{waitUntil:'networkidle'});
  if(!fs.existsSync(statePath)){
  await p.locator('#name').fill('Jane Acme');await p.locator('#email').fill('member@acme.test');
  await p.getByRole('button',{name:'Send verification code'}).click();
  await p.locator('#code-form').waitFor({state:'visible'});
  const code=await mail('member@acme.test',m=>m.Text.match(/verification code is (\d{6})/)?.[1]);
  await p.locator('#code').fill(code);await p.getByRole('button',{name:'Continue',exact:true}).click();
  await p.locator('#nda').waitFor({state:'visible'});await context.storageState({path:statePath});}
  await p.locator('#nda').waitFor({state:'visible'});await p.screenshot({path:shots+'/C-nda-gate.png'});
  if(await p.locator('#start').isVisible())await p.locator('#start').click();
  await p.getByRole('button',{name:'Review and sign NDA'}).waitFor({timeout:60000});
  await p.getByRole('button',{name:'Review and sign NDA'}).click();
  await p.waitForURL('**/sign/**');
  const completed=await sign(p,'Jane Acme');
  await p.waitForURL('**/signing/nda/**',{timeout:60000});
  await p.locator('#contents').waitFor({state:'visible',timeout:60000});
  const elapsed=(Date.now()-completed)/1000;
  if(elapsed>60)throw Error('NDA fileback exceeded 60 seconds: '+elapsed);
  await p.screenshot({path:shots+'/C-nda-room.png'});
  console.log('PASS NDA signing -> room:',elapsed.toFixed(2),'seconds');
  fs.writeFileSync(root+'/deploy/chief-glue-v1/.local/flow-a.json',JSON.stringify({pass:true,seconds:elapsed}));
  await browser.close();
 }catch(e){console.error('FAIL:',e.message);await p.screenshot({path:shots+'/C-failure.png'});console.log((await p.locator('body').innerText()).slice(0,1400));await browser.close();process.exitCode=1;}
})();
