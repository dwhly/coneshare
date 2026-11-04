const {chromium} = require('/Users/dano/code/amforge-forks/shots/node_modules/playwright');
const fs = require('fs');
const base = 'http://send-v1.100-110-241-2.sslip.io';
const shots = '/Users/dano/code/chief-dealroom/docs/status/shots';
const delay = ms => new Promise(r=>setTimeout(r,ms));
async function codeFor(email) {
  for(let tries=0;tries<25;tries++) {
    const list=await (await fetch('http://localhost:8785/api/v1/messages')).json();
    const msg=list.messages.find(m=>m.To.some(t=>t.Address===email)&&m.Subject.includes('verification code'));
    if(msg){const detail=await (await fetch(`http://localhost:8785/api/v1/message/${msg.ID}`)).json();const match=detail.Text.match(/code is (\d{6})/);if(match)return match[1];}
    await delay(400);
  }
  throw Error('No OTP email');
}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Users/dano/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 page.on('pageerror',e=>console.log('BROWSER_ERROR',e.message));
 await page.goto(base+'/view/project-atlas');
 await page.getByLabel('Your name').fill('Jane'); await page.getByLabel('Email address').fill('jane@acme.test');
 await page.getByRole('button',{name:'Send verification code'}).click();
 await page.getByLabel('Verification code').waitFor(); await page.getByLabel('Verification code').fill(await codeFor('jane@acme.test'));
 await page.getByRole('button',{name:'Confirm access'}).click();
 await page.getByRole('heading',{name:'Project Atlas'}).waitFor();
 await page.locator('img[alt^="Personalized page"]').waitFor();
 await page.waitForFunction(()=>{const img=document.querySelector('img[alt^="Personalized page"]');return img && img.complete && img.naturalWidth>0;});
 await page.screenshot({path:shots+'/B-recipient-jane.png',fullPage:true}); console.log('PASS jane OTP and watermarked page'); await page.context().storageState({path:'/tmp/chief-send-v1-jane-session.json'});
 const response=await page.request.get(base+'/api/v1/dealroom/recipient/project-atlas/room/');const room=await response.json();
 const image=await page.request.get(base+room.files[0].page_url);
 if(image.headers()['cache-control']!=='private, no-store'||!image.headers()['x-dealroom-copy-id']) throw Error('personalized headers missing');
 console.log('PASS private/no-store + Copy ID',image.headers()['x-dealroom-copy-id']);
 const bob=await browser.newPage();await bob.goto(base+'/view/project-atlas');await bob.getByLabel('Your name').fill('Bob');await bob.getByLabel('Email address').fill('bob@other.test');await bob.getByRole('button',{name:'Send verification code'}).click();await bob.getByLabel('Verification code').waitFor();await bob.getByLabel('Verification code').fill(await codeFor('bob@other.test'));await bob.getByRole('button',{name:'Confirm access'}).click();await bob.getByRole('alert').waitFor();await bob.screenshot({path:shots+'/B-bob-refused.png'});console.log('PASS bob refused');
 const staff=await browser.newPage({viewport:{width:1440,height:1000}});await staff.goto(base+'/login');
 console.log('LOGIN_FIELDS',await staff.locator('input').evaluateAll(xs=>xs.map(x=>({type:x.type,name:x.name,placeholder:x.placeholder}))));
 await staff.locator('input[type=email]').fill('admin@amforge.test');await staff.locator('input[type=password]').fill(process.env.SEND_PASSWORD);
 await staff.getByRole('button',{name:/log in|sign in/i}).click();await staff.getByRole('heading',{name:'Your deal rooms'}).waitFor();
 await staff.screenshot({path:shots+'/B-staff-topbar.png',fullPage:true});
 const token=await staff.evaluate(()=>localStorage.getItem('access_token'));
 const headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'};
 const rejected=await fetch(base+'/api/v1/dealroom/orgs/',{method:'POST',headers,body:JSON.stringify({name:'Bad Gmail',email_domains:['gmail.com'],confirm_domains:true})});if(rejected.status!==400)throw Error('gmail org not rejected');console.log('PASS gmail org refused');
 const key=await (await fetch(base+'/api/v1/dealroom/agent-keys/',{method:'POST',headers,body:JSON.stringify({name:'e2e agent',tier:'full_access'})})).json();
 const approvedEmail=`reviewed+${Date.now()}@other.test`;
 const pending=await (await fetch(base+'/api/v1/dealroom/grants/',{method:'POST',headers:{...headers,Authorization:'Bearer '+key.key},body:JSON.stringify({room:room.id,email:approvedEmail})})).json();if(pending.status!=='pending_approval')throw Error(JSON.stringify(pending));
 await staff.reload();await staff.getByRole('button',{name:'Approve access'}).last().click();await delay(500);
 const approvals=await (await fetch(base+'/api/v1/dealroom/approvals/'+pending.approval_id+'/',{headers})).json();if(approvals.status!=='approved')throw Error(JSON.stringify(approvals));console.log('PASS agent pending -> staff approves');
 const admitted=await browser.newPage(); await admitted.goto(base+'/view/project-atlas'); await admitted.getByLabel('Your name').fill('Approved recipient'); await admitted.getByLabel('Email address').fill(approvedEmail); await admitted.getByRole('button',{name:'Send verification code'}).click(); await admitted.getByLabel('Verification code').waitFor(); await admitted.getByLabel('Verification code').fill(await codeFor(approvedEmail)); await admitted.getByRole('button',{name:'Confirm access'}).click(); await admitted.getByRole('heading',{name:'Project Atlas'}).waitFor(); await admitted.screenshot({path:shots+'/B-approved-recipient.png'}); console.log('PASS approved grant takes effect for new recipient');
 await staff.screenshot({path:shots+'/B-approved.png',fullPage:true});
 const readkey=await (await fetch(base+'/api/v1/dealroom/agent-keys/',{method:'POST',headers,body:JSON.stringify({name:'e2e read only',tier:'read_only'})})).json();
 fs.writeFileSync('/tmp/chief-send-v1-read-key',readkey.key,{mode:0o600});
 await staff.goto(base+'/?layout=sidebar');await staff.getByRole('heading',{name:'Your deal rooms'}).waitFor();await staff.screenshot({path:shots+'/B-staff-sidebar.png',fullPage:true});
 await browser.close(); console.log('E2E 6 checks passed; MCP separately');
})().catch(e=>{console.error(e);process.exit(1)});
