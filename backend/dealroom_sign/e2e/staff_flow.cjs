const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/Users/dano/code/amforge-forks/shots/node_modules/playwright');
const fs=require('fs'),path=require('path');const root=path.resolve(__dirname,'../../..');
const f=JSON.parse(fs.readFileSync(root+'/deploy/chief-glue-v1/.local/fixture.json'));
const base='http://glue-v1.100-110-241-2.sslip.io';
(async()=>{const browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1380,height:1000}});
try{
 await page.goto(base+'/signing/',{waitUntil:'networkidle'});
 await page.locator('#email').fill('admin@amforge.test');await page.locator('#password').fill('z8QjMn4nWYK3qoXPLX2Q');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.locator('#workspace').waitFor({state:'visible'});
 await page.locator('#version').selectOption(f.versions['Investment agreement']);
 await page.locator('#recipient-name').fill('Raj Acme');await page.locator('#recipient-email').fill('raj@acme.test');
 for(const [id,value]of Object.entries({page:1,x:10,y:70,w:35,h:8}))await page.locator('#'+id).fill(String(value));
 await page.screenshot({path:'/Users/dano/code/chief-dealroom/docs/status/shots/C-staff-send.png'});
 await page.getByRole('button',{name:'Send for signature',exact:true}).click();
 await page.getByText('Signature request queued.',{exact:false}).waitFor();
 console.log('PASS staff browser created a signature request with sender-specified field placement');
 await page.screenshot({path:'/Users/dano/code/chief-dealroom/docs/status/shots/C-staff-envelopes.png'});
 await page.context().storageState({path:root+'/deploy/chief-glue-v1/.local/staff-state.json'});
}catch(e){console.error('FAIL staff:',e.message);console.log((await page.locator('body').innerText()).slice(0,1000));process.exitCode=1}finally{await browser.close()}})();
