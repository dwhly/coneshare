const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/Users/dano/code/amforge-forks/shots/node_modules/playwright');
const fs=require('fs'),path=require('path');const root=path.resolve(__dirname,'../../..');
const f=JSON.parse(fs.readFileSync(root+'/deploy/chief-glue-v1/.local/fixture.json'));
const {sign}=require('./signature.cjs');
const shots='/Users/dano/code/chief-dealroom/docs/status/shots';
const base='http://glue-v1.100-110-241-2.sslip.io';
(async()=>{const browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1380,height:1000}});
try{
 await page.goto(base+'/signing/',{waitUntil:'networkidle'});
 await page.locator('#email').fill('admin@amforge.test');await page.locator('#password').fill('z8QjMn4nWYK3qoXPLX2Q');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.locator('#workspace').waitFor({state:'visible'});
 await page.locator('#version').selectOption(f.versions['Investment agreement']);
 const recipient='raj+'+Date.now()+'@acme.test';
 await page.locator('#recipient-name').fill('Raj Acme');await page.locator('#recipient-email').fill(recipient);
 for(const [id,value]of Object.entries({page:1,x:10,y:70,w:35,h:8}))await page.locator('#'+id).fill(String(value));
 await page.screenshot({path:'/Users/dano/code/chief-dealroom/docs/status/shots/C-staff-send.png'});
 const created=page.waitForResponse(r=>r.url().endsWith('/api/v1/dealroom-sign/envelopes/')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Send for signature',exact:true}).click();
 const workflow=await (await created).json();
 await page.getByText('Signature request queued.',{exact:false}).waitFor();
 console.log('PASS staff browser created a signature request with sender-specified field placement');
 await page.screenshot({path:'/Users/dano/code/chief-dealroom/docs/status/shots/C-staff-envelopes.png'});
 await page.context().storageState({path:root+'/deploy/chief-glue-v1/.local/staff-state.json'});
 let url;for(let n=0;n<45&&!url;n++){
  const list=await fetch('http://100.110.241.2:8785/api/v1/search?query='+encodeURIComponent('to:'+recipient)).then(r=>r.json());
  for(const m of list.messages||[]){const full=await fetch('http://100.110.241.2:8785/api/v1/message/'+m.ID).then(r=>r.json());url=(full.Text+' '+full.HTML).match(/http:\/\/sign-v1[^\s"<>]+\/sign\/[A-Za-z0-9_-]+/)?.[0];if(url)break;}
  if(!url)await new Promise(r=>setTimeout(r,1000));
 }
 if(!url)throw Error('Signing email was not delivered');
 const recipientContext=await browser.newContext({viewport:{width:1360,height:950}});const signer=await recipientContext.newPage();
 await signer.goto(url,{waitUntil:'networkidle'});const completed=await sign(signer,'Raj Acme',shots);
 let status;for(let n=0;n<40;n++){
  status=await page.evaluate(async id=>fetch('/api/v1/dealroom-sign/envelopes/'+id+'/',{headers:{Authorization:'Bearer '+sessionStorage.getItem('glue-staff-token')}}).then(r=>r.json()),workflow.id);
  if(status.state==='done')break;await new Promise(r=>setTimeout(r,1500));
 }
 const seconds=(Date.now()-completed)/1000;
 if(status.state!=='done'||seconds>60||status.artifacts.length!==3)throw Error('Agreement fileback failed: '+status.state+' after '+seconds+'s');
 await page.reload({waitUntil:'networkidle'});await page.getByText('3 files in Executed/',{exact:true}).first().waitFor();
 await page.screenshot({path:shots+'/C-agreement-fileback.png',fullPage:true});
 const activity=await page.evaluate(()=>fetch('/api/v1/dealroom/activity/',{headers:{Authorization:'Bearer '+sessionStorage.getItem('glue-staff-token')}}).then(r=>r.json()));
 const kinds=new Set((activity.results||activity).map(a=>a.event_type));
 for(const kind of ['member.joined','envelope.signed','fileback.completed'])if(!kinds.has(kind))throw Error('Missing activity '+kind);
 fs.writeFileSync(root+'/deploy/chief-glue-v1/.local/flow-b.json',JSON.stringify({pass:true,seconds,workflow_id:workflow.id,artifacts:status.artifacts}));
 console.log('PASS signature email -> real signature -> Executed/:',seconds.toFixed(2),'seconds; unified activity verified');
}catch(e){console.error('FAIL staff:',e.message);console.log((await page.locator('body').innerText()).slice(0,1000));process.exitCode=1}finally{await browser.close()}})();
