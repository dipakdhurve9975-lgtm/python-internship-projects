"""Single-process game server, with separate LAN and hosted-demo settings."""
from collections import defaultdict, deque
import argparse
import math
import logging
import os
from pathlib import Path
import secrets
import socket
import threading
import time
from flask import Flask, jsonify, render_template, request, session
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
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32), MAX_CONTENT_LENGTH=8192,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
    hosted = os.environ.get('MATHDUEL_HOSTED') == '1'
    if hosted: app.logger.setLevel(logging.INFO)
    app.config['SESSION_COOKIE_SECURE'] = hosted
    sio = SocketIO(app, async_mode='threading', max_http_buffer_size=8192, cors_allowed_origins=None, logger=False)
    if hosted:
        # OUTSIDE Socket.IO: otherwise /socket.io bypasses forwarded IP/protocol handling.
        # Hosted mode must only be used behind a single trusted reverse proxy.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    data = Path(os.environ.get('MATHDUEL_DATA_DIR', Path.home() / '.mathduel'))
    engine = Engine(Stats(db_path or data / 'matches.sqlite3'))
    limits = defaultdict(deque)
    app.extensions['match_engine'] = engine
    app.extensions['socketio'] = sio

    @app.get('/')
    def index():
        session.setdefault('visitor', secrets.token_urlsafe(24))
        return render_template('index.html', hosted=hosted)

    @app.get('/health')
    def health():
        age = time.monotonic() - app.extensions.get('ticker_heartbeat', time.monotonic())
        healthy = not background or age < 5
        return jsonify(status='ok' if healthy else 'unhealthy', service='MathDuel',
                       mode='online' if hosted else 'lan', version='multiplayer-2',
                       ticker_active=background and healthy, debug=False), 200 if healthy else 503

    @app.get('/network')
    def network():
        if hosted:
            return jsonify(candidates=[], mode='online', note='Share the MathDuel website with your friend. Create a room and send them your six-digit room code.')
        port = app.config.get('LAN_PORT', 5000)
        return jsonify(candidates=[f'http://{a}:{port}' for a in lan_candidates()], mode='lan', note='Connect both devices to the same Wi-Fi or hotspot. Open the laptop host\u2019s local IP URL on both devices, then share the six-digit room code.')

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
                    # A signed HTTP session survives socket reconnects. The larger IP
                    # ceiling still protects against cookie clearing and code guessing.
                    if len(limits) > 1000:
                        for key in list(limits):
                            if not limits[key] or now - limits[key][-1] > 60: del limits[key]
                    action_name = action.__name__
                    visitor = session.get('visitor') or request.sid
                    maximum = 15 if action_name in ('create', 'join') else 120
                    buckets = [('player', visitor, maximum), ('network', request.remote_addr, 300 if maximum == 15 else 1200)]
                    for scope, principal, ceiling in buckets:
                        bucket = limits[(scope, principal, action_name)]
                        while bucket and now - bucket[0] >= 60: bucket.popleft()
                        if len(bucket) >= ceiling:
                            retry = max(1, math.ceil(60 - (now - bucket[0])))
                            app.logger.warning('rate_limit action=%s scope=%s retry_after=%s', action_name, scope, retry)
                            result = {'ok': False, 'code': 'rate_limited', 'retry_after': retry,
                                      'error': f'Too many requests. Try again in {retry} seconds.'}
                            emit('problem', {**result, 'message': result['error']})
                            return result
                    for scope, principal, _ in buckets: limits[(scope, principal, action_name)].append(now)
                    if payload is None: payload = {}
                    if not isinstance(payload, dict): raise ValueError('Invalid request.')
                    # One active membership per socket avoids phantom players.
                    return action(payload)
            except ValueError as error:
                code = 'room_unavailable' if 'not found or expired' in str(error) else 'invalid_request'
                if action.__name__ == 'resume': code = 'resume_failed'
                emit('problem', {'message': str(error), 'code': code, 'action': action.__name__})
                return {'ok': False, 'error': str(error), 'code': code}
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
        # Repeating an authenticated resume is safe; a stale connection is replaced.
        room, player = engine.resume(p.get('code'), p.get('token'))
        try:
            existing, index = engine.find(request.sid)
        except ValueError:
            existing = None
        if existing is not None and (existing is not room or existing.players[index] is not player):
            raise ValueError('Leave the current room first.')
        if player.sid and player.sid != request.sid:
            old_sid = player.sid
            player.sid = request.sid  # Old disconnect must not mark the new connection offline.
            sio.emit('replaced', {}, to=old_sid)
            sio.server.disconnect(old_sid)
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
            try:
                with engine.lock:
                    for code, room in engine.tick():
                        if room: broadcast(room)
                        else: sio.emit('expired', {}, to=code)
                app.extensions['ticker_heartbeat'] = time.monotonic()
            except Exception:
                # Keep the clock alive and make failures visible in platform logs.
                app.logger.exception('MathDuel ticker failed')
    task_lock = threading.Lock()

    def ensure_ticker():
        if not background: return
        # Start inside the serving worker, never during WSGI import/preloading.
        # A task inherited from a pre-fork parent has no live worker thread.
        with task_lock:
            task = app.extensions.get('ticker_task')
            if (app.extensions.get('ticker_pid') != os.getpid()
                    or task is None or not task.is_alive()):
                app.extensions['ticker_pid'] = os.getpid()
                app.extensions['ticker_heartbeat'] = time.monotonic()
                app.extensions['ticker_task'] = sio.start_background_task(ticker)
                app.logger.info('MathDuel ticker started in serving worker')

    @app.before_request
    def start_worker_tasks(): ensure_ticker()

    @sio.on('connect')
    def connected(auth=None): ensure_ticker()

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
