# MathDuel multiplayer repair — 11 October 2026

## Confirmed cause

The exact message `Too many requests. Wait one minute.` came from MathDuel's Socket.IO event guard, not a Render HTTP rate-limit response. The guard allowed only 15 `create` or `join` events per source address per minute, including unsuccessful attempts. `ProxyFix` was inside the Socket.IO middleware, so Socket.IO intercepted its route before forwarded addresses were corrected. Requests from unrelated players could therefore share the reverse proxy's address and consume the same small allowance.

The Render application logs inspected in Chrome showed `/socket.io/` requests with address `127.0.0.1`, and the deployed command was `gunicorn --workers 1 --threads 40 --timeout 120 --bind 0.0.0.0:$PORT wsgi:app`, using one `gthread` worker. A full WSGI handshake regression verifies the forwarded address and HTTPS scheme reach Socket.IO. The old guard did not log its event decisions, so the exact historical attempt count for the user's failed join cannot be recovered from those access logs.

The frontend fetched `/network` once. Its 100 ms interval only updated the local countdown; it did not poll the backend. Socket.IO's transport polling is normal connection traffic and is not counted by the game-event limiter. Buttons previously allowed duplicate clicks and socket emits while disconnected, which could queue extra create/join requests.

## Changes

- Move `ProxyFix` outside Socket.IO in hosted mode, trusting one hosting proxy only.
- Give each browser a signed anonymous HTTP session. Keep 15 create/join attempts per action per minute for that session, plus a 300-per-minute network ceiling per action to reduce cookie-rotation/code-guessing abuse. Other events allow 120 per player and 1,200 per network per action. Reconnecting keeps the player's allowance. These are basic demo protections, not a distributed denial-of-service solution.
- Log rate-limit action, scope and retry delay without nicknames, room tokens or raw addresses. Return a structured retry delay and disable controls during cooldown.
- Send each action once while connected and wait for acknowledgement. Block duplicate clicks and disconnected actions. Do not automatically replay create/join requests after an acknowledgement timeout.
- Restore the same player using its existing high-entropy token. Atomically replace a stale socket, preserving the slot and score. The replaced tab is told to reload. Missing/expired rooms clear stale identity and show how to start again.
- Show connecting, connected, restoring, reconnecting and failed-connection status in the existing status area. Timers remain server-owned during disconnection.
- Keep all existing CSS, game modes, operations, scoring, solo adaptation and statistics.
- Start the background clock on the serving worker's first HTTP request or Socket.IO connection, rather than at WSGI import time. Prevent duplicate clock tasks, log exceptions and include a clock heartbeat in `/health`.

An additional live smoke test on the old deployed version successfully communicated over WebSocket but did not receive feedback or round 2 after 23 seconds. The inspected exception-filtered logs did not reveal its cause. The clock lifecycle and diagnostics changes address worker-start hazards and make future failures visible; the exact old clock failure is not claimed as proven.

## Online mode — Render

Share `https://mathduel-python.onrender.com` with your friend. Create a room and send them your six-digit room code. Both players may use different reachable networks; their browsers connect to the same online server. They do not need the laptop's local address.

Use root directory `mathduel-lan`, build `pip install -r requirements-hosted.txt`, and the single-worker command above. Enable `MATHDUEL_HOSTED=1` and set `MATHDUEL_DATA_DIR=/tmp/mathduel`. The included `.python-version` and blueprint pin Python 3.12.14. An optional stable `SECRET_KEY` environment value signs anonymous sessions; the fallback is a fresh random secret per server process. Do not publish that value.

Keep exactly one worker and one instance with this in-memory room design. Multiple workers/instances require shared game state and Socket.IO messaging plus appropriate routing; merely adding Redis as a message queue does not persist the Engine's room dictionary. Do not enable Gunicorn preloading. Threading mode plus `simple-websocket` supports WebSocket upgrade and long-polling fallback with same-origin protection.

### Free-plan limitations

Render can spin down a free service after 15 minutes without inbound HTTP/WebSocket traffic; waking takes about one minute. It can also restart free instances. Every process restart loses active rooms. SQLite files on the ephemeral filesystem are lost on redeploy, restart or spin-down, and free web services cannot attach persistent disks. Free instance hours are shared across a workspace (750 per calendar month), with separate bandwidth/build allowances. Reconnect can recover a temporary network loss while the same room still exists; it cannot recover a room erased by restart. A paid instance reduces free-plan sleep limitations, but lasting rooms/statistics still need shared persistent storage.

References: [Render free hosting](https://render.com/docs/free), [Render WebSockets](https://render.com/docs/websocket), [Flask-SocketIO deployment](https://flask-socketio.readthedocs.io/en/stable/deployment.html), [Render Python versions](https://render.com/docs/python-version).

## Local LAN mode — laptop

Unset `MATHDUEL_HOSTED`, then run `python mathduel-lan/app.py --host 0.0.0.0 --port 5000` from the project root. Connect both devices to reachable Wi-Fi or a hotspot. Open `http://LAPTOP_LOCAL_IP:5000` on both devices, then create/join using the code. `127.0.0.1` only works on the laptop itself. The room code does not discover the laptop. See [LAN_GUIDE.md](LAN_GUIDE.md) for adapter, guest-network and firewall troubleshooting. Local mode does not trust forwarded headers and stores statistics locally.

## Verification and deployment

Backend regressions cover forwarded source/scheme handling, two independent simulated source networks, player limits across reconnect, shared-network fairness, network abuse ceiling, stale-connection replacement, missing rooms, separate UI instructions and the worker clock. Chrome verification uses two independent browser contexts with distinct signed sessions; it checks create/join, duplicate-click prevention, reload recovery, simulated temporary offline recovery, WebSocket frames, ten synchronized rounds and missing-room recovery. Results and screenshots are under `docs/evidence/multiplayer/`.

Local validation: 80 Python tests passed (43 MathDuel and 37 SunDrop). The Chrome check passed with no JavaScript page errors and received 116 WebSocket frames. These counts describe local verification before the Render redeployment.

No physical-device or different-real-network test was performed. The forwarded-address test simulates two networks, and browser offline mode simulates connection loss. A real phone/laptop test over mobile data versus Wi-Fi remains a manual check.

A new Render deployment is required: local changes and a GitHub push do not update the manually created public-repository service by themselves. Deploy the corrected commit, then check `/health` for `version: multiplayer-2`, `mode: online`, `ticker_active: true`, and repeat the browser test against the public URL. Until that succeeds, do not describe the live service as fixed.

### Completed Render deployment

The user confirmed deployment. Commit `db3efe5af377de384dd1d8c8a785374568c5c5d4` was manually deployed as `dep-db5s8c942hec73a1phug`. Render reported a successful live deployment and logged the clock starting inside the serving worker. Public `/health` returned HTTP 200 with `mode: online`, `version: multiplayer-2` and `ticker_active: true`.

The same two-context Chrome verification then passed against `https://mathduel-python.onrender.com`, including create/join, a full synchronized ten-round duel, reload resume, simulated temporary offline recovery and stale-room cleanup, with zero page errors and 104 received WebSocket frames. Evidence is in `docs/evidence/multiplayer/render/`. Separate real-server WebSocket and polling-fallback smoke tests both observed lobby → question 1 → feedback 1 → question 2. The older clock stall was no longer reproduced after this deployment. The exact old clock failure remains unproven because the inspected historical logs had no matching exception.

No further application deployment is needed for this repair. Documentation/test-evidence commits after `db3efe5` do not change the serving application.
