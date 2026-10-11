/* The browser displays state; answers, scores and deadlines belong to Python. */
'use strict';
const $ = id => document.getElementById(id);
const socket = io({reconnection:true});
let identity = null, state = null, receivedAt = 0, lastRound = '';
try { identity = JSON.parse(sessionStorage.getItem('mathduelIdentity')); } catch (_) {}
function problem(message) { $('message').textContent = message; }
function send(event, payload={}) { problem(''); socket.emit(event,payload); }
socket.on('connect',()=>{ $('connection').textContent='● Connected to host'; if(identity) send('resume',identity); });
socket.on('disconnect',()=>{ $('connection').textContent='○ Reconnecting…'; $('submit').disabled=true; $('start').disabled=true; problem('Connection lost. Server timers continue. Keep this tab open to reconnect.'); });
socket.on('identity',data=>{identity=data;sessionStorage.setItem('mathduelIdentity',JSON.stringify(data));});
socket.on('problem',data=>problem(data.message));
socket.on('expired',()=>{reset();problem('Room expired after 30 minutes. Create a new one.');});
function reset(){identity=null;state=null;sessionStorage.removeItem('mathduelIdentity');$('home').hidden=false;$('play').hidden=true;}
for(const id of ['create','solo']) $(id).onclick=()=>send('create',{name:$('name').value,level:$('level').value,solo:id==='solo'});
$('join').onclick=()=>send('join',{name:$('name').value,code:$('code').value});
$('start').onclick=()=>send('start');
$('copy-code').onclick=async()=>{if(!state)return;try{await navigator.clipboard.writeText(state.code);problem('Room code copied. Share the host URL too.');}catch(_){problem('Room code: '+state.code+'. Open the host URL first.');}};
$('leave').onclick=()=>socket.emit('leave',{},reply=>{if(reply?.ok) reset();});
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
});
setInterval(()=>{if(!state||state.phase!=='question')return;const left=Math.max(0,state.remaining-(performance.now()-receivedAt)/1000);$('timer').firstElementChild.style.width=(100*left/state.duration)+'%';$('timer').setAttribute('aria-valuenow',left.toFixed(1));$('seconds').textContent=left.toFixed(1)+' seconds left';},100);
fetch('/network').then(r=>r.json()).then(data=>{
 $('network-note').textContent=data.note;const candidates=data.candidates.length?data.candidates:[location.origin];
 candidates.forEach(url=>{const button=document.createElement('button');button.textContent=url+' · copy';button.onclick=async()=>{try{await navigator.clipboard.writeText(url);problem('Host URL copied.');}catch(_){problem('Copy this URL manually: '+url);}};$('urls').append(button);});
}).catch(()=>{$('network-note').textContent='Use ipconfig on the host to find its Wi-Fi IPv4 address.';});
