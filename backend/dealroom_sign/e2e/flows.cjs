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
 await p.locator('[data-testid="signature-pad-dialog-button"]').first().waitFor({timeout:30000});
 await p.locator('[data-testid="signature-pad-dialog-button"]').first().click();
 const d=p.getByRole('dialog');await d.getByText('Type',{exact:true}).click();await d.locator('input').first().fill(name);
 await d.getByRole('button',{name:'Next',exact:true}).click();await p.waitForTimeout(800);
 if(await p.getByRole('button',{name:'Next Field',exact:true}).count())await p.getByRole('button',{name:'Next Field',exact:true}).first().click();
 await p.waitForTimeout(500);
 const c=await p.locator('canvas').evaluateAll(cs=>{const c=cs.filter(c=>c.getBoundingClientRect().width>300).sort((a,b)=>b.width*b.height-a.width*a.height)[0];if(!c)return null;const r=c.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height}});
 if(c)await p.mouse.click(c.x+c.w*.275,c.y+c.h*.74);
 await p.waitForTimeout(1000);
 await p.screenshot({path:shots+'/C-signing-fields.png'});
 await p.getByRole('button',{name:'Complete',exact:true}).first().click();
 await p.getByRole('dialog').getByRole('button',{name:'Sign',exact:true}).last().click();
 return Date.now();
}
(async()=>{
 const browser=await chromium.launch();
 const context=await browser.newContext({viewport:{width:1360,height:950}}),p=await context.newPage();
 p.on('pageerror',e=>console.log('PAGE ERROR:',e.message));
 try {
  await p.goto(base+'/view/'+fixture.slug,{waitUntil:'networkidle'});
  await p.locator('#name').fill('Jane Acme');await p.locator('#email').fill('member@acme.test');
  await p.getByRole('button',{name:'Send verification code'}).click();
  await p.locator('#code-form').waitFor({state:'visible'});
  const code=await mail('member@acme.test',m=>m.Text.match(/verification code is (\d{6})/)?.[1]);
  await p.locator('#code').fill(code);await p.getByRole('button',{name:'Continue',exact:true}).click();
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
