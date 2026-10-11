# Interface design and verification

## SunDrop retro desktop

The supplied reference establishes the style: pastel cyan `#BCE8E5`, warm cream `#F5EFE2`, charcoal outlines, monospace headings and hard offset shadows. SunDrop reinterprets it as an original desktop with a menu bar, a left launcher rail, a scrollable download studio, library cards and a floating audio player. It does not copy the reference's window arrangement or third-party assets.

File selects the destination; Downloads opens the library; View toggles light/dark; Settings opens the preferences page. Custom minimize/close work alongside native window controls. Paste reads text only when clicked. Fetch Media requires the permission checkbox before contacting a source. Format chooses a media container/conversion group; Quality / Source lists the formats actually reported by yt-dlp. Unknown direct media appears as Original media without a fabricated resolution.

Cards use nested frames for a five-pixel hard shadow. Cream buttons have two-pixel outlines, cyan hover feedback and normal toolkit click handling. No ornamental controls are added. The library shows thumbnail, title, creator, size, type, UTC date and file availability. Open File and Open Folder call the OS file handler. Internal Play/Pause appears only for WAV/MP3/OGG. The mini player contains functional previous/next, progress and volume.

Pillow loads artwork and letterboxes it to avoid distortion. Missing covers use an original title/type card. Mutagen embeds source artwork only into MP3; placeholder art stays in the library sidecar. Videos are not re-encoded to manufacture a thumbnail.

Hidden Tk integration tests verify worker responsiveness, library rendering with missing files, track navigation, pause, format filtering and theme switching. Playback uses SDL's dummy audio driver in tests, so speaker output is not proven. Visual automation was stopped with Escape after initial screens were captured. The current retro layout still needs a fresh user-visible screenshot check. Earlier screenshots must not be presented as the new retro interface.

## MathDuel practice and duel

The refined game uses charcoal `#141715`, lime `#B2FF66`, an original CSS mascot, practice/duel navigation, a concise mode selector, generous question space, round-progress dots and clear score cards. Mobile layouts use the numeric keypad. The room-code copy button includes a manual fallback because clipboard access may be restricted on plain LAN HTTP.

The UI is inspired by mental-math products in its friendly tone and large problem area; it retains the original MathDuel name, CSS mascot and arrangement. No Mathiks branding or assets are copied. There are no fake account profiles, achievements, ranks or online matchmaking claims. The actual local-game engine remains authoritative.

Real browser checks before the final refinement verified a full two-tab match, unequal speed bonuses, timeout rounds, result statistics, host rematch and reload reconnection. A 390 × 844 viewport showed a keypad and no horizontal overflow. The final styling and copy-code addition passed syntax/route checks, but a fresh visual walkthrough is pending after computer-use interruption.
