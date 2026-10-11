/* Run with Node and Playwright; uses installed Google Chrome and isolated cookies. */
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const url = process.env.MATHDUEL_TEST_URL || 'http://127.0.0.1:5057';
const output = path.resolve(__dirname, '../../docs/evidence/multiplayer');
fs.mkdirSync(output, {recursive:true});
function solve(text){
 const n=text.match(/-?\d+/g).map(Number);
 if(text.includes('√'))return Math.sqrt(n[0]);
 if(text.includes('²'))return n[0]**2;
 if(text.includes(' + '))return n[0]+n[1];
 if(text.includes(' - '))return n[0]-n[1];
 if(text.includes(' × '))return n[0]*n[1];
 if(text.includes(' ÷ '))return n[0]/n[1];
 throw Error('Unexpected question '+text);
}
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
 const contexts=await Promise.all([browser.newContext(),browser.newContext()]);
 const [host,friend]=await Promise.all(contexts.map(c=>c.newPage()));
 const errors=[],sockets=[];
 let websocketFrames=0;
 for(const page of [host,friend]){page.on('pageerror',e=>errors.push(String(e)));page.on('websocket',ws=>{sockets.push(ws.url());ws.on('framereceived',()=>websocketFrames++);});}
 await Promise.all([host.goto(url),friend.goto(url)]);
 await Promise.all([host.locator('#connection').filter({hasText:'● Connected'}).waitFor(),friend.locator('#connection').filter({hasText:'● Connected'}).waitFor()]);
 assert.notEqual((await contexts[0].cookies()).find(c=>c.name==='session').value,(await contexts[1].cookies()).find(c=>c.name==='session').value);
 await host.locator('#name').fill('QA Host');await friend.locator('#name').fill('QA Friend');
 await host.locator('#create').dblclick();
 await host.locator('#play').waitFor({state:'visible'});
 const identity=await host.evaluate(()=>JSON.parse(sessionStorage.getItem('mathduelIdentity')));
 assert.match(identity.code,/^\d{6}$/);
 await friend.locator('#code').fill(identity.code);await friend.locator('#join').click();
 await host.locator('#players').filter({hasText:'QA Friend'}).waitFor();
 await friend.locator('#players').filter({hasText:'QA Friend'}).waitFor();
 assert.equal(await host.locator('.player').count(),2);
 assert.equal(await friend.locator('.player').count(),2);
 await host.screenshot({path:path.join(output,'two-player-lobby.png'),fullPage:true});
 // Simulate losing internet for this browser context, without changing the OS network.
 await contexts[1].setOffline(true);
 await friend.locator('#connection').filter({hasText:'Reconnecting'}).waitFor({timeout:60000});
 assert(await friend.locator('#join').isDisabled());
 await contexts[1].setOffline(false);
 await friend.locator('#connection').filter({hasText:'● Connected'}).waitFor({timeout:60000});
 assert.equal((await friend.evaluate(()=>JSON.parse(sessionStorage.getItem('mathduelIdentity')))).code,identity.code);
 await host.reload();await host.locator('#play').waitFor({state:'visible'});
 await host.locator('#connection').filter({hasText:'● Connected'}).waitFor();
 assert.equal(await host.locator('.player').count(),2);
 await host.locator('#start').click();
 for(let round=1;round<=10;round++){
  await host.locator('#round-label').filter({hasText:`ROUND ${round} OF 10`}).waitFor();
  await friend.locator('#round-label').filter({hasText:`ROUND ${round} OF 10`}).waitFor();
  await host.locator('#answer-form').waitFor({state:'visible'});
  await friend.locator('#answer-form').waitFor({state:'visible'});
  const question=await host.locator('#question').textContent();
  assert.equal(await friend.locator('#question').textContent(),question);
  const answer=String(solve(question));
  await Promise.all([host.locator('#answer').fill(answer),friend.locator('#answer').fill(answer)]);
  await Promise.all([host.locator('#submit').click(),friend.locator('#submit').click()]);
  await host.locator('#answer-form').waitFor({state:'hidden'});
 }
 await host.locator('#results').filter({hasText:'100% accuracy'}).waitFor();
 await friend.locator('#results').filter({hasText:'100% accuracy'}).waitFor();
 await host.screenshot({path:path.join(output,'two-player-results.png'),fullPage:true});
 await host.locator('#leave').click();await friend.locator('#leave').click();
 await host.locator('#home').waitFor({state:'visible'});
 await host.evaluate(()=>sessionStorage.setItem('mathduelIdentity',JSON.stringify({code:'000000',token:'missing'})));
 await host.reload();await host.locator('#message').filter({hasText:'Create a new room'}).waitFor();
 assert.equal(await host.evaluate(()=>sessionStorage.getItem('mathduelIdentity')),null);
 assert(await host.locator('#create').isEnabled());
 assert.equal(errors.length,0,errors.join('\n'));
 assert(sockets.length>=2&&websocketFrames>0,'WebSocket communication was not observed');
 const result={date:new Date().toISOString(),url,browser:'Installed Google Chrome',independentContexts:2,
  distinctSignedSessions:true,createJoin:true,duplicateCreatePrevented:true,reloadResume:true,
  temporaryOfflineResume:true,synchronizedTenRoundMatch:true,missingRoomRecovery:true,pageErrors:errors,webSocketConnections:sockets.length,webSocketFramesReceived:websocketFrames,
  physicalDevicesTested:false,differentPhysicalNetworksTested:false};
 fs.writeFileSync(path.join(output,'browser-result.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
