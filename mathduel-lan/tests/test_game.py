import random
import re
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Engine, Stats, question, parse_answer, nickname, points
from app import create_app

@pytest.fixture
def match(tmp_path):
    now = [100.0]
    engine = Engine(Stats(tmp_path / 'test.sqlite3'), clock=lambda: now[0])
    room, p = engine.create('Ada', 'easy')
    p.sid = 'one'
    _, p2 = engine.join(room.code, 'Alan')
    p2.sid = 'two'
    return engine, room, now

@pytest.mark.parametrize('level', ['easy','medium','hard'])
@pytest.mark.parametrize('op', ['+','-','*','/','square','root'])
def test_generator(level, op):
    rng = random.Random(40)
    for _ in range(100):
        text, answer = question(level, rng, op)
        values = [int(n) for n in re.findall(r'\d+', text)]
        if op == '+': expected = values[0] + values[1]
        elif op == '-': expected = values[0] - values[1]
        elif op == '*': expected = values[0] * values[1]
        elif op == '/':
            assert values[1] and values[0] % values[1] == 0
            expected = values[0] // values[1]
        elif op == 'square': expected = values[0] ** 2
        else: expected = int(values[0] ** .5); assert expected ** 2 == values[0]
        assert isinstance(answer,int) and answer == expected

@pytest.mark.parametrize('bad',[None,True,1.5,'1.5','1e2','12345678','<script>'])
def test_invalid_answer(bad):
    with pytest.raises(ValueError): parse_answer(bad)

def test_names():
    assert nickname('  Ada  ') == 'Ada'
    for value in ('', '<script>', 'x'*21, None):
        with pytest.raises(ValueError): nickname(value)

def test_scoring():
    assert points(True,0)==15
    assert points(True,3)==14
    assert points(True,14.9)==10
    assert points(False,0)==0

def test_duplicate_and_stale(match):
    e,r,now = match; e.start_match(r,0)
    with pytest.raises(ValueError): e.submit(r,0,r.answer,r.round,'forged')
    e.submit(r,0,r.answer,r.round,r.match_id)
    initial = r.players[0].score
    with pytest.raises(ValueError): e.submit(r,0,r.answer,r.round,r.match_id)
    assert r.players[0].score == initial
    assert 'answer' not in e.public(r)

def test_lifecycle_and_limits(match):
    e,r,_=match
    assert re.fullmatch(r'\d{6}',r.code)
    with pytest.raises(ValueError): e.join(r.code,'Third')
    with pytest.raises(ValueError): e.start_match(r,1)
    e.start_match(r,0)
    with pytest.raises(ValueError): e.start_match(r,0)
    assert e.public(r)['players'][0]['score']==0

def test_timeout_and_statistics(match):
    e,r,now=match; e.start_match(r,0)
    for _ in range(10):
        e.submit(r,0,r.answer,r.round,r.match_id)
        now[0] += 15
        e.tick()
        assert r.phase=='feedback' and not r.players[1].records[-1]['answered']
        now[0] += 2; e.tick()
    assert r.phase=='results'
    s=e.stats.summary()
    assert s['matches']==1 and s['rounds']==20 and s['accuracy']==50
    assert s['average_response']==0
    e.stats.save(r)
    assert e.stats.summary()['rounds']==20
    previous=r.match_id; e.start_match(r,0)
    assert r.match_id!=previous and r.players[0].score==0

def test_deadline_rejects(match):
    e,r,now=match;e.start_match(r,0);now[0]+=15
    with pytest.raises(ValueError):e.submit(r,0,r.answer,r.round,r.match_id)
    e.tick();assert r.phase=='feedback'

def test_resume_expiry_and_collision(match,monkeypatch):
    e,r,now=match
    assert e.resume(r.code,r.players[0].token)[1] is r.players[0]
    with pytest.raises(ValueError):e.resume(r.code,'bad')
    monkeypatch.setattr('engine.secrets.randbelow',lambda _:int(r.code)-100000)
    with pytest.raises(ValueError,match='allocate'):e.create('New','easy')
    now[0]+=1801;e.tick()
    with pytest.raises(ValueError):e.get(r.code)

def test_adaptive_solo(match):
    e,_,now=match;r,p=e.create('Solo','easy',True);p.sid='solo';e.start_match(r,0)
    for _ in range(5):
        e.submit(r,0,r.answer,r.round,r.match_id);now[0]+=2;e.tick()
    assert r.round==6 and r.level=='medium'

def test_socket_integration(tmp_path):
    app,sio=create_app(tmp_path/'test.sqlite3',background=False)
    one=sio.test_client(app);two=sio.test_client(app);three=sio.test_client(app)
    assert app.test_client().get('/health').json['status']=='ok'
    one.emit('create',{'name':'Ada','level':'easy'},callback=True)
    events=one.get_received();ident=next(x['args'][0] for x in events if x['name']=='identity')
    assert two.emit('join',{'code':ident['code'],'name':'Alan'},callback=True)['ok']
    assert not three.emit('join',{'code':ident['code'],'name':'Third'},callback=True)['ok']
    assert not two.emit('start',{},callback=True)['ok']
    assert one.emit('start',{},callback=True)['ok']
    s1=[x['args'][0] for x in one.get_received() if x['name']=='state'][-1]
    s2=[x['args'][0] for x in two.get_received() if x['name']=='state'][-1]
    assert s1['question']==s2['question'] and 'answer' not in s1
    e=app.extensions['match_engine'];room=e.get(ident['code'])
    payload={'answer':room.answer,'round':room.round,'match_id':room.match_id,'score':999999}
    assert one.emit('answer',payload,callback=True)['ok']
    assert room.players[0].score<=15
    assert not one.emit('answer',payload,callback=True)['ok']
    one.disconnect();new=sio.test_client(app)
    assert new.emit('resume',ident,callback=True)['ok']
    assert room.players[0].sid is not None
    for client in (two,three,new):client.disconnect()

def test_rate_limit(tmp_path):
    app,sio=create_app(tmp_path/'test.sqlite3',False);client=sio.test_client(app)
    for _ in range(15):client.emit('join',{'code':'000000','name':'A'},callback=True)
    result=client.emit('join',{'code':'000000','name':'A'},callback=True)
    assert 'Too many' in result['error']

def test_tie(match):
    e,r,now=match;e.start_match(r,0)
    for _ in range(10):
        e.submit(r,0,r.answer,r.round,r.match_id);e.submit(r,1,r.answer,r.round,r.match_id)
        now[0]+=2;e.tick()
    assert e.public(r)['winners']==['Ada','Alan']
