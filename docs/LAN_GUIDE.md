# Laptop hosting and phone joining

1. Connect the laptop and phone to the same reachable Wi-Fi network, or connect the laptop to the phone's hotspot.
2. Run `python mathduel-lan\app.py` on the laptop. The default port is 5000. Debug is off, reloading is off and one process owns the room state.
3. Test `http://127.0.0.1:5000/health` on the laptop; it should return `status: ok`.
4. Run `ipconfig`. Find the active Wi-Fi adapter's IPv4 address. Do not use 127.0.0.1 on the phone: that points to the phone itself. A 169.254 address often indicates a failed address assignment; confirm your active adapter.
5. Open `http://HOST_LAN_IP:5000/health` on the phone. Only after this works, open the main page and enter a room code.
6. Give both players different nicknames. Create a two-player room on the laptop; enter its code on the phone. The host starts when both are connected.

## Windows Firewall

No rule is created by this project. On a trusted private network, the user may allow the specific Python executable through Windows Defender Firewall for the Private profile using Windows settings. Do not turn the firewall off. Public-profile exposure is not recommended. If local loopback works but the phone cannot connect, check the allowed executable, network profile, address and port. Organization-managed laptops may need the network administrator's help.

## Hotspot and address limitations

Some hotspots isolate clients or deny access to the hotspot provider from a connected laptop. Some guest Wi-Fi networks isolate every device. A correct room code cannot solve a network block. Try a reachable trusted router network. IP addresses can change after reconnecting; recopy the new URL. VPNs and virtual adapters may create misleading candidates. Phone and laptop must be on networks that can route to each other.

## Privacy and threat model

This is a classroom demo on a trusted local network, not a public service. HTTP traffic is not encrypted. A high-entropy resume token in sessionStorage reconnects a player; a room code is not strong authentication. The server controls question generation, deadlines and scoring, but it cannot prevent someone solving questions with a calculator. Rate limiting and room limits reduce basic abuse; they are not Internet-grade denial-of-service defenses.

Disconnecting preserves a slot and its token until expiry; the timers continue. Reopen or reload the same tab to resume. Closing the tab can lose its sessionStorage token. The MVP has no lobby kick button; if a player disappears permanently, create a fresh room. Host rematch requires all players online. Explicit Leave during a running match invalidates that player's token.

## Evidence boundary and TODOs

Verified here: Flask health endpoint, server event integration tests, a two-tab match on one Windows laptop, host rematch, browser reload reconnect, solo mode and a 390 × 844 browser layout. No physical phone, router or hotspot was used for verification.

TODO: test an actual Android/iOS phone joining the Windows host and record browser, network, firewall decision and outcome. Optional phone-as-Python-server is experimental only: test an Android Termux installation separately before documenting support. No iOS/Android automatic server-hosting claim is made. Optional QR generation is future work.
