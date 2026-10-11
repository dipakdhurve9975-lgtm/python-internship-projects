"""Single-process game server, with separate LAN and hosted-demo settings."""
from collections import defaultdict, deque
import argparse
import os
from pathlib import Path
import secrets
import socket
import time
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from engine import Engine, Stats
from werkzeug.middleware.proxy_fix import ProxyFix

def lan_candidates():
    addresses = set()
    try:
        addresses.update(a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except OSError: pass
    return sorted(a for a in addresses if not a.startswith('127.'))

def create_app(db_path=None, background=True):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=secrets.token_hex(32), MAX_CONTENT_LENGTH=8192)
    hosted = os.environ.get('MATHDUEL_HOSTED') == '1'
    if hosted:
        # Enable only behind the hosting platform's single trusted reverse proxy.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    sio = SocketIO(app, async_mode='threading', max_http_buffer_size=8192, cors_allowed_origins=None, logger=False)
    data = Path(os.environ.get('MATHDUEL_DATA_DIR', Path.home() / '.mathduel'))
    engine = Engine(Stats(db_path or data / 'matches.sqlite3'))
    limits = defaultdict(deque)
    app.extensions['match_engine'] = engine
    app.extensions['socketio'] = sio

    @app.get('/')
    def index(): return render_template('index.html', hosted=hosted)

    @app.get('/health')
    def health(): return jsonify(status='ok', service='MathDuel LAN', debug=False)

    @app.get('/network')
    def network():
        if hosted:
            return jsonify(candidates=[], note='Share this page URL with a friend, then share your room code. Active rooms reset when the server restarts.')
        port = app.config.get('LAN_PORT', 5000)
        return jsonify(candidates=[f'http://{a}:{port}' for a in lan_candidates()], note='Open a reachable host URL before entering a room code. No automatic discovery.')

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        if hosted:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.get('/statistics')
    def statistics(): return jsonify(engine.stats.summary())

    def broadcast(room): sio.emit('state', engine.public(room), to=room.code)

    def guard(action):
        def handler(payload=None):
            try:
                with engine.lock:
                    now = time.monotonic()
                    # Limits are by source IP, so reconnecting does not reset them.
                    if len(limits) > 1000:
                        for key in list(limits):
                            if not limits[key] or now - limits[key][-1] > 60: del limits[key]
                    key = (request.remote_addr, action.__name__)
                    bucket = limits[key]
                    while bucket and now - bucket[0] > 60: bucket.popleft()
                    maximum = 15 if action.__name__ in ('create', 'join') else 120
                    if len(bucket) >= maximum: raise ValueError('Too many requests. Wait one minute.')
                    bucket.append(now)
                    if payload is None: payload = {}
                    if not isinstance(payload, dict): raise ValueError('Invalid request.')
                    # One active membership per socket avoids phantom players.
                    return action(payload)
            except ValueError as error:
                emit('problem', {'message': str(error)})
                return {'ok': False, 'error': str(error)}
        handler.__name__ = action.__name__
        return handler

    def attach(room, player):
        player.sid = request.sid
        join_room(room.code)
        emit('identity', {'code': room.code, 'token': player.token, 'index': room.players.index(player)})
        broadcast(room)
        return {'ok': True, 'code': room.code}

    def require_unjoined():
        try: engine.find(request.sid)
        except ValueError: return
        raise ValueError('Leave the current room first.')

    @sio.on('create')
    @guard
    def create(p):
        require_unjoined()
        if not isinstance(p.get('solo', False), bool): raise ValueError('Invalid solo mode.')
        room, player = engine.create(p.get('name'), p.get('level', 'easy'), p.get('solo', False))
        return attach(room, player)

    @sio.on('join')
    @guard
    def join(p):
        require_unjoined()
        room, player = engine.join(p.get('code'), p.get('name'))
        return attach(room, player)

    @sio.on('resume')
    @guard
    def resume(p):
        require_unjoined()
        room, player = engine.resume(p.get('code'), p.get('token'))
        if player.sid and player.sid != request.sid:
            raise ValueError('This player is still connected in another tab.')
        return attach(room, player)

    @sio.on('start')
    @guard
    def start(p):
        room, i = engine.find(request.sid)
        engine.start_match(room, i)
        broadcast(room)
        return {'ok': True}

    @sio.on('answer')
    @guard
    def answer(p):
        room, i = engine.find(request.sid)
        engine.submit(room, i, p.get('answer'), p.get('round'), p.get('match_id'))
        broadcast(room)
        return {'ok': True}

    @sio.on('leave')
    @guard
    def leave(p):
        room, i = engine.find(request.sid)
        leave_room(room.code)
        if room.phase == 'lobby':
            room.players.pop(i)
            if not room.players: engine.rooms.pop(room.code, None)
            else: broadcast(room)
        else:
            room.players[i].sid = None
            # Explicit leave invalidates resume; transient disconnect preserves it.
            room.players[i].token = secrets.token_urlsafe(32)
            broadcast(room)
        return {'ok': True}

    @sio.on('disconnect')
    def disconnected(reason=None):
        with engine.lock:
            try: room, i = engine.find(request.sid)
            except ValueError: return
            room.players[i].sid = None
            broadcast(room)

    def ticker():
        while True:
            sio.sleep(.2)
            with engine.lock:
                for code, room in engine.tick():
                    if room: broadcast(room)
                    else: sio.emit('expired', {}, to=code)
    if background: sio.start_background_task(ticker)
    return app, sio

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()
    app, sio = create_app()
    app.config['LAN_PORT'] = args.port
    print('MathDuel LAN: laptop browser http://127.0.0.1:' + str(args.port), flush=True)
    print('Candidate phone URLs:', [f'http://{a}:{args.port}' for a in lan_candidates()], flush=True)
    print('Trusted LAN only. Debug disabled. Firewall rules are not changed.', flush=True)
    sio.run(app, host=args.host, port=args.port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
