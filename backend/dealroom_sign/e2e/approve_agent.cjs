const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/Users/dano/code/amforge-forks/shots/node_modules/playwright');
const fs=require('fs'),path=require('path'),root=path.resolve(__dirname,'../../..');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1380,height:1000}});try{
 await p.goto('http://glue-v1.100-110-241-2.sslip.io/signing/',{waitUntil:'networkidle'});
 await p.locator('#email').fill('admin@amforge.test');await p.locator('#password').fill('z8QjMn4nWYK3qoXPLX2Q');await p.getByRole('button',{name:'Sign in',exact:true}).click();
 await p.getByRole('button',{name:'Approve request',exact:true}).first().waitFor();
 await p.screenshot({path:'/Users/dano/code/chief-dealroom/docs/status/shots/C-agent-approval.png',fullPage:true});
 const approved=p.waitForResponse(r=>r.url().includes('/approvals/')&&r.url().endsWith('/approve/'));
 await p.getByRole('button',{name:'Approve request',exact:true}).first().click();
 const response=await approved,result=await response.json();if(!response.ok()||result.status!=='approved')throw Error('Approval execution failed');
 let status;for(let i=0;i<30;i++){
  status=await p.evaluate(async id=>fetch('/api/v1/dealroom-sign/envelopes/'+id+'/',{headers:{Authorization:'Bearer '+sessionStorage.getItem('glue-staff-token')}}).then(r=>r.json()),result.result.id);
  if(status.source_status==='PENDING')break;await new Promise(r=>setTimeout(r,1000));
 }
 if(status.source_status!=='PENDING')throw Error('Approved command was not distributed');
 fs.writeFileSync(root+'/deploy/chief-glue-v1/.local/approval-result.json',JSON.stringify({pass:true,workflow_id:result.result.id,envelope_id:status.envelope_id}));
 console.log('PASS staff-JWT browser approval executed exact agent request; remote envelope is PENDING');
}catch(e){console.error(e.message);process.exitCode=1}finally{await b.close()}})();
