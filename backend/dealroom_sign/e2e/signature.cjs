async function sign(p,name,shots){
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

module.exports={sign};
