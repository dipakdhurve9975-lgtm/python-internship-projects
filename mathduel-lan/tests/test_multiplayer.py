"""Regression tests for proxy routing, shared networks, recovery and server clock."""
import json
import time
from flask import request
from app import create_app


def player(app, sio):
    http = app.test_client()
    http.get('/')
    return http, sio.test_client(app, flask_test_client=http)


def test_forwarded_address_reaches_socket_middleware(tmp_path, monkeypatch):
    monkeypatch.setenv('MATHDUEL_HOSTED', '1')
    app, sio = create_app(tmp_path / 'proxy.db', False)
    seen = []
    @sio.on('connect')
    def connected(auth=None):
        seen.append((request.remote_addr, request.scheme))
    http = app.test_client()
    headers = {'X-Forwarded-For': '198.51.100.23', 'X-Forwarded-Proto': 'https'}
    response = http.get('/socket.io/?EIO=4&transport=polling', headers=headers)
    sid = json.loads(response.text[1:])['sid']
    response = http.post('/socket.io/?EIO=4&transport=polling&sid=' + sid, data='40', headers=headers)
    assert response.status_code == 200
    assert seen == [('198.51.100.23', 'https')]
    http.post('/socket.io/?EIO=4&transport=polling&sid=' + sid, data='1', headers=headers)


def test_room_between_independent_forwarded_network_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv('MATHDUEL_HOSTED', '1')
    app, sio = create_app(tmp_path / 'networks.db', False)
    sio.server.async_handlers = False
    peers = []
    for address in ('198.51.100.23', '203.0.113.45'):
        http = app.test_client()
        headers = {'X-Forwarded-For': address, 'X-Forwarded-Proto': 'https'}
        http.get('/', headers=headers)
        response = http.get('/socket.io/?EIO=4&transport=polling', headers=headers)
        sid = json.loads(response.text[1:])['sid']
        endpoint = '/socket.io/?EIO=4&transport=polling&sid=' + sid
        http.post(endpoint, data='40', headers=headers)
        http.get(endpoint, headers=headers)  # consume connect acknowledgement
        peers.append((http, headers, endpoint))
    host, headers, endpoint = peers[0]
    host.post(endpoint, data='421' + json.dumps(['create', {'name': 'Host'}]), headers=headers)
    packets = host.get(endpoint, headers=headers).text.split('\x1e')
    identity = next(json.loads(p[2:])[1] for p in packets if p.startswith('42["identity"'))
    friend, friend_headers, friend_endpoint = peers[1]
    friend.post(friend_endpoint, data='421' + json.dumps(['join', {'name': 'Friend', 'code': identity['code']}]), headers=friend_headers)
    packets = friend.get(friend_endpoint, headers=friend_headers).text.split('\x1e')
    assert any(p.startswith('431') and json.loads(p[3:])[0]['ok'] for p in packets)
    state = next(json.loads(p[2:])[1] for p in packets if p.startswith('42["state"'))
    assert len(state['players']) == 2 and all(p['connected'] for p in state['players'])
    for http, headers, endpoint in peers: http.post(endpoint, data='1', headers=headers)


def test_player_limit_survives_reconnect_without_blocking_friend(tmp_path):
    app, sio = create_app(tmp_path / 'limits.db', False)
    http, abusive = player(app, sio)
    for _ in range(15):
        abusive.emit('join', {'code': '000000', 'name': 'Test'}, callback=True)
    abusive.disconnect()
    reconnected = sio.test_client(app, flask_test_client=http)
    result = reconnected.emit('join', {'code': '000000', 'name': 'Test'}, callback=True)
    assert result['code'] == 'rate_limited' and 1 <= result['retry_after'] <= 60
    # Flask test clients all share the same remote_addr, just like a NAT/proxy.
    _, host = player(app, sio)
    _, friend = player(app, sio)
    code = host.emit('create', {'name': 'Host'}, callback=True)['code']
    assert friend.emit('join', {'code': code, 'name': 'Friend'}, callback=True)['ok']
    for client in (reconnected, host, friend): client.disconnect()


def test_network_ceiling_still_blocks_cookie_rotation(tmp_path):
    app, sio = create_app(tmp_path / 'ceiling.db', False)
    for _ in range(20):
        _, client = player(app, sio)
        for _ in range(15):
            client.emit('join', {'code': '000000', 'name': 'Test'}, callback=True)
        client.disconnect()
    _, client = player(app, sio)
    result = client.emit('join', {'code': '000000', 'name': 'Test'}, callback=True)
    assert result['code'] == 'rate_limited'
    client.disconnect()


def test_resume_replaces_stale_connection_and_preserves_player(tmp_path):
    app, sio = create_app(tmp_path / 'resume.db', False)
    _, old = player(app, sio)
    old.emit('create', {'name': 'Host'}, callback=True)
    identity = next(e['args'][0] for e in old.get_received() if e['name'] == 'identity')
    room = app.extensions['match_engine'].get(identity['code'])
    _, new = player(app, sio)
    assert new.emit('resume', identity, callback=True)['ok']
    assert not old.is_connected()
    new_sid = room.players[0].sid
    assert new.emit('resume', identity, callback=True)['ok']
    assert room.players[0].sid == new_sid and len(room.players) == 1
    new.emit('leave', {}, callback=True)
    assert not new.emit('resume', identity, callback=True)['ok']
    new.disconnect()


def test_missing_room_and_modes(tmp_path, monkeypatch):
    for hosted in ('0', '1'):
        monkeypatch.setenv('MATHDUEL_HOSTED', hosted)
        app, sio = create_app(tmp_path / (hosted + '.db'), False)
        page = app.test_client().get('/').text
        if hosted == '1':
            assert 'Share the MathDuel website with your friend.' in page
            assert "Open this host's URL on both devices first" not in page
        else:
            assert 'local IP' in page
        client = sio.test_client(app)
        result = client.emit('resume', {'code': '000000', 'token': 'gone'}, callback=True)
        assert result['code'] == 'resume_failed' and 'expired' in result['error']
        client.disconnect()


def test_background_clock_starts_in_worker_and_advances(tmp_path):
    app, sio = create_app(tmp_path / 'clock.db', True)
    assert 'ticker_task' not in app.extensions  # Import/preload cannot start worker threads.
    engine = app.extensions['match_engine']
    _, client = player(app, sio)
    code = client.emit('create', {'name': 'Clock', 'solo': True}, callback=True)['code']
    engine.duration = .05
    engine.feedback = .05
    client.emit('start', {}, callback=True)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and engine.get(code).round < 2:
        time.sleep(.05)
    assert engine.get(code).round >= 2
    task = app.extensions['ticker_task']
    assert app.test_client().get('/health').json['ticker_active']
    assert app.extensions['ticker_task'] is task  # No duplicate clocks per request.
    client.disconnect()
