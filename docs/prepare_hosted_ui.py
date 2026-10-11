"""Keep hosted connection instructions distinct from the LAN instructions."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'mathduel-lan/templates/index.html'
text = path.read_text(encoding='utf-8')
text = text.replace('<span class="muted">LAN</span>', '<span class="muted">{{ "LIVE" if hosted else "LAN" }}</span>')
text = text.replace('Same reachable Wi-Fi or hotspot required.<br>A room code does not find the host for you.', '{{ "Share this page URL first. Rooms reset when the server restarts." if hosted else "Same reachable Wi-Fi or hotspot required. A room code does not find the host for you." }}')
text = text.replace("Choose the host's Wi-Fi adapter address. VPN and virtual adapters may also appear. No phone or physical LAN test is implied.", '{{ "Free demo: saved statistics may be cleared by restarts." if hosted else "Choose the host Wi-Fi adapter address. VPN and virtual adapters may also appear. No phone or physical LAN test is implied." }}')
text = text.replace('Your local connection', '{{ "Invite a friend" if hosted else "Your local connection" }}')
path.write_text(text, encoding='utf-8')
