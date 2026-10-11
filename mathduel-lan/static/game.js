/* The browser displays state; answers, scores and deadlines belong to Python. */
'use strict';
const $ = id => document.getElementById(id);
const socket = io({reconnection:true, reconnectionDelay:1000, reconnectionDelayMax:10000, randomizationFactor:0.5});
let identity = null, state = null, receivedAt = 0, lastRound = '';
let pending = null, restoring = false, cooldownUntil = 0;
try { identity = JSON.parse(sessionStorage.getItem('mathduelIdentity')); } catch (_) {}
function problem(message) { $('message').textContent = message; }
function controls(){
 const busy=!socket.connected||restoring||pending!==null||Date.now()<cooldownUntil;
 for(const id of ['create','solo','join','leave']) $(id).disabled=busy;
 $('submit').disabled=busy||state?.phase!=='question'||state?.players[identity?.index]?.submitted;
 $('start').disabled=busy||!state||state.players.length!==(state.solo?1:2)||state.players.some(p=>!p.connected);
}
function send(event, payload={}, done=()=>{}) {
 if(!socket.connected){problem('Connecting to the server. Please wait, then try again.');return;}
 if(pending!==null||Date.now()<cooldownUntil)return;
 problem(''); const marker={event}; pending=marker; controls();
 socket.timeout(10000).emit(event,payload,(error,reply)=>{
  if(pending!==marker)return;pending=null;
  if(event==='resume')restoring=false;
  if(error){problem('The server did not confirm the request. Reconnecting to check your room…'); socket.disconnect();socket.connect();}
  else if(!reply?.ok){if(event==='resume'){reset();problem((reply?.error||'Your room is no longer available.')+' Create a new room or join with a current code.');}else problem(reply?.error||'Request failed. Please try again.');}
  else {done(reply);$('connection').textContent='● Connected';}
  controls();
 });
}
socket.on('connect',()=>{ pending=null;restoring=Boolean(identity);$('connection').textContent=restoring?'◌ Restoring your room…':'● Connected'; if(identity){const wait=Math.max(0,cooldownUntil-Date.now());if(wait)setTimeout(()=>{if(socket.connected&&identity&&restoring)send('resume',identity);},wait+50);else send('resume',identity);}controls(); });
socket.on('connect_error',()=>{$('connection').textContent='○ Unable to connect · retrying…';problem('The server may be waking up. Keep this page open; connecting can take a minute.');controls();});
socket.on('disconnect',()=>{pending=null;restoring=false;$('connection').textContent='○ Reconnecting…';controls();problem('Connection lost. Server timers continue. Keep this tab open to reconnect.');});
socket.on('identity',data=>{identity=data;sessionStorage.setItem('mathduelIdentity',JSON.stringify(data));});
socket.on('problem',data=>{if(data.retry_after){cooldownUntil=Date.now()+data.retry_after*1000;setTimeout(controls,data.retry_after*1000+50);}problem(data.message);controls();});
socket.on('expired',()=>{reset();problem('Room expired after 30 minutes. Create a new one.');});
socket.on('replaced',()=>{reset();socket.disconnect();$('connection').textContent='○ Room opened in another tab';problem('Your player reconnected in another tab. Reload this page to play again.');});
function reset(){identity=null;state=null;restoring=false;lastRound='';sessionStorage.removeItem('mathduelIdentity');$('home').hidden=false;$('play').hidden=true;controls();}
for(const id of ['create','solo']) $(id).onclick=()=>send('create',{name:$('name').value,level:$('level').value,solo:id==='solo'});
$('join').onclick=()=>send('join',{name:$('name').value,code:$('code').value});
$('start').onclick=()=>send('start');
$('copy-code').onclick=async()=>{if(!state)return;try{await navigator.clipboard.writeText(state.code);problem('Room code copied. Share the MathDuel website with your friend too.');}catch(_){problem('Room code: '+state.code+'. Share this website URL too.');}};
$('leave').onclick=()=>send('leave',{},reset);
$('answer-form').onsubmit=event=>{event.preventDefault();if(!state||state.phase!=='question')return;send('answer',{answer:$('answer').value,round:state.round,match_id:state.match_id});};
for(const button of document.querySelectorAll('[data-key]')) button.onclick=()=>{
 if($('answer').disabled)return;let value=$('answer').value,key=button.dataset.key;
 $('answer').value=key==='back'?value.slice(0,-1):key==='-'?(value.startsWith('-')?value.slice(1):'-'+value):(value+key).slice(0,8);
};
socket.on('state',data=>{
 if(!identity)return;state=data;receivedAt=performance.now();$('home').hidden=true;$('play').hidden=false;
 $('room-label').textContent=(data.solo?'Solo practice':'Room '+data.code)+' · '+data.level;
 $('copy-code').hidden=data.solo;
 $('round-track').hidden=data.phase==='lobby';$('round-track').replaceChildren();for(let i=1;i<=data.total;i++){const dot=document.createElement('span');dot.className=i<data.round?'done':i===data.round?'current':'';dot.setAttribute('aria-label','Round '+i);$('round-track').append(dot);}
 $('players').replaceChildren(); data.players.forEach((player,index)=>{
  const card=document.createElement('div');card.className='player';const name=document.createElement('div');name.textContent=player.name+(index===identity.index?' (you)':'');
  const status=document.createElement('small');status.textContent=player.connected?(player.submitted?'Answer locked':'Connected'):'Disconnected · waiting to reconnect';name.append(status);
  const score=document.createElement('strong');score.textContent=player.score;card.append(name,score);$('players').append(card);
 });
 const active=data.phase==='question',mine=data.players[identity.index];
 $('round-label').textContent=data.phase==='lobby'?'YOUR NEXT CHALLENGE':`ROUND ${data.round} OF ${data.total}`;
 $('question').textContent=data.phase==='lobby'?(data.solo?'Your daily brain boost':data.players.length===2?'Both minds are here.':'Waiting for a friend'):data.phase==='results'?(data.solo?'Practice complete!':data.winners.length>1?'A well-earned tie!':data.winners[0]+' wins!'):data.question;
 const roundKey=data.match_id+':'+data.round;
 if(roundKey!==lastRound){$('answer').value='';lastRound=roundKey;if(active&&innerWidth>650)$('answer').focus();}
 $('answer-form').hidden=!active;$('keypad').hidden=!active;$('timer').hidden=!active;$('seconds').hidden=!active;
 $('answer').disabled=!active||mine?.submitted;$('submit').disabled=!active||mine?.submitted||!socket.connected;
 $('start').hidden=!['lobby','results'].includes(data.phase)||identity.index!==0;
 $('start').textContent=data.phase==='results'?'Play again →':'Start '+(data.solo?'practice':'match')+' →';
 $('start').disabled=data.players.length!==(data.solo?1:2)||data.players.some(p=>!p.connected)||!socket.connected;
 $('feedback').textContent=data.phase==='feedback'?`Answer: ${data.answer} · ${data.feedback[identity.index].correct?'Correct! +'+data.feedback[identity.index].points:'No points this round. Keep going.'}`:mine?.submitted&&active?'Answer locked. Waiting for the round to finish.':'';
 $('match-note').textContent=data.solo?'Solo adapts by recent accuracy and speed every five rounds. Rule-based, no ML.':'Correct = 10 points + up to 5 speed points. One answer per round. Host starts the match.';
 $('results').replaceChildren();if(data.phase==='results')data.statistics.forEach((s,i)=>{const p=document.createElement('p');p.textContent=`${data.players[i].name}: ${s.accuracy}% accuracy · ${s.average_response}s average submitted response`; $('results').append(p);});
 controls();
});
controls();
setInterval(()=>{if(!state||state.phase!=='question')return;const left=Math.max(0,state.remaining-(performance.now()-receivedAt)/1000);$('timer').firstElementChild.style.width=(100*left/state.duration)+'%';$('timer').setAttribute('aria-valuenow',left.toFixed(1));$('seconds').textContent=left.toFixed(1)+' seconds left';},100);
fetch('/network').then(r=>r.json()).then(data=>{
 $('network-note').textContent=data.note;const candidates=data.candidates.length?data.candidates:[location.origin];
 candidates.forEach(url=>{const button=document.createElement('button');button.textContent=url+' · copy';button.onclick=async()=>{try{await navigator.clipboard.writeText(url);problem('Host URL copied.');}catch(_){problem('Copy this URL manually: '+url);}};$('urls').append(button);});
}).catch(()=>{$('network-note').textContent='Could not load connection instructions. Reload when connected.';});
