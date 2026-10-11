"""Optional real server smoke test; creates and leaves its own solo room only."""
import argparse
import json
import time
import requests
import socketio

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--transport', choices=['polling', 'websocket'], default='websocket')
    args = parser.parse_args()
    http = requests.Session()
    http.get(args.url, timeout=90).raise_for_status()
    client = socketio.Client(http_session=http, reconnection=False)
    phases = []
    client.on('state', lambda state: phases.append((state['phase'], state['round'])))
    try:
        client.connect(args.url, transports=[args.transport], wait_timeout=60)
        created = client.call('create', {'name': 'Clock QA', 'solo': True}, timeout=15)
        assert created['ok'], created
        assert client.call('start', {}, timeout=15)['ok']
        deadline = time.monotonic() + 23
        while time.monotonic() < deadline and not any(n >= 2 for _, n in phases):
            time.sleep(.2)
        print(json.dumps({'url': args.url, 'transport': client.transport(), 'phases': phases,
                          'clock_advanced': any(n >= 2 for _, n in phases)}))
        assert any(n >= 2 for _, n in phases), 'Server clock did not advance'
    finally:
        if client.connected:
            client.call('leave', {}, timeout=15)
            client.disconnect()
