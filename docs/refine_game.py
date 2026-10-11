"""One-time refinement of our existing template, preserving event control IDs."""
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'mathduel-lan'/'templates'/'index.html'
text=path.read_text(encoding='utf-8')
if '/static/refinement.css' in text:
    print('The refinement is already applied.')
    raise SystemExit(0)
text=text.replace('<link rel="stylesheet" href="/static/style.css">','<link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/refinement.css">')
text=text.replace('</a><span id="connection"','</a><nav aria-label="Play modes"><a href="#practice-card">Practice</a><a href="#duel-card">Play together</a></nav><span id="connection"')
text=text.replace('A LITTLE MATH. A FRIENDLY CHALLENGE.','YOUR DAILY DOSE OF QUICK THINKING')
text=text.replace('<h1>Quick minds.<br><span>Good company.</span></h1>','<span class="pill">6 operations · 3 levels · all you</span><h1>Train your mind.<br><span>Challenge a friend.</span></h1>')
text=text.replace('Ten questions. Fifteen seconds each.<br>Sharpen your mental math, solo or with a friend nearby.','Small questions. A sharper you.<br>Find your rhythm in practice, or bring a friend to a local duel.')
text=text.replace('</p></div><div class="mascot"','</p><div class="feature-strip"><span><strong>10</strong> questions</span><span><strong>15s</strong> per round</span><span><strong>2</strong> minds, one room</span></div></div><div class="mascot"')
text=text.replace('<b>+</b><em>×</em></div>','<b>+</b><em>×</em><span class="mascot-caption">LET\'S THINK.</span></div>')
text=text.replace('<div class="home-grid"><section class="card">','<div class="home-grid"><section class="card mode-card" id="practice-card"><div class="mode-icon" aria-hidden="true">√</div>')
text=text.replace('01 / MAKE IT YOURS','FIND YOUR FLOW').replace('Ready to play?','A little better every round.')
text=text.replace('<section class="card"><div class="eyebrow">02 / PLAY TOGETHER','<section class="card mode-card" id="duel-card"><div class="mode-icon duel-icon" aria-hidden="true">×</div><div class="eyebrow">A FRIENDLY FACE-OFF')
text=text.replace('Meet in a room.','Same question. Your moment.')
text=text.replace('<button id="leave" class="small-button">Leave room</button>','<div class="room-actions"><button id="copy-code" class="small-button">Copy code</button><button id="leave" class="small-button">Leave room</button></div>')
text=text.replace('<div id="round-label" class="eyebrow"></div>','<div id="round-label" class="eyebrow"></div><div id="round-track" aria-label="Round progress"></div>')
path.write_text(text,encoding='utf-8')
