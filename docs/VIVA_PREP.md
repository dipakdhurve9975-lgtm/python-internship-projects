# Viva preparation

These answers describe the delivered demo, not undocumented internship activities. The certificate and diary were not supplied. Verify their wording before discussing organization details or weekly training topics.

1. **Why Python?** It is readable and has useful libraries for a desktop app, a web server and testing.
2. **What are the two projects?** SunDrop downloads authorized media; MathDuel runs mental math practice and local two-player matches.
3. **What is a variable?** A name that refers to a value, such as a score.
4. **What is an integer?** A whole number. The math game's answers are integers.
5. **What is a float?** A number with a fractional part. Response times use floats.
6. **What is a function?** Reusable code with inputs and often a return value.
7. **What is a class?** A description for objects holding data and behavior.
8. **What is a dictionary?** A collection of key-value pairs. Room codes map to rooms.
9. **What is an exception?** A signal that an operation failed; `try/except` can handle it.
10. **Why use a virtual environment?** It isolates a project's installed packages.
11. **What is Flask?** A Python framework for HTTP routes and web responses.
12. **What is a route?** A URL path connected to a server function.
13. **What does `/health` do?** It returns a small JSON response showing the running service is reachable.
14. **Why Flask-SocketIO?** It sends live events between Python and browsers for synchronized play.
15. **Is Socket.IO the same as WebSocket?** No. It adds an event protocol and may fall back to polling.
16. **What is the frontend?** HTML, CSS and JavaScript that the browser displays and runs.
17. **What is the backend?** Python handling rules, clocks, scores and storage.
18. **Why does the server check answers?** A browser can be modified. Client-supplied scores cannot be trusted.
19. **How are questions shared?** The server emits the same room state to both players.
20. **How many questions and seconds?** Ten questions with up to 15 seconds each and two seconds of feedback.
21. **How is scoring calculated?** Correct gives 10 plus floor(remaining seconds / 3), clamped to five bonus points. Wrong gives zero.
22. **How are duplicates prevented?** Each round stores one submission per player. Match ID and round must match.
23. **What happens on timeout?** Missing answers receive zero, count as incorrect, and the match moves on.
24. **Can matches tie?** Yes. Every player with the highest final score is listed as a winner.
25. **What is a room code?** A random six-digit identifier for a room on the reachable server.
26. **Does a room code find the host?** No. The phone must open the host's IP-and-port URL first.
27. **How are collisions handled?** A newly generated code is checked against existing rooms and retried.
28. **When do rooms expire?** Thirty minutes after creation, or immediately on server restart because state is in memory.
29. **What is LAN?** A local network connecting nearby reachable devices.
30. **How is LAN different from the Internet?** Internet access involves external routing; this demo is designed for a trusted local network.
31. **Can a phone provide a hotspot?** Yes, with the laptop hosting Python, if the hotspot permits routing between devices.
32. **Can every phone host Python automatically?** No. Phone-server mode is experimental and untested, not a supported automatic feature.
33. **What is client isolation?** A router or hotspot setting that blocks traffic between connected devices.
34. **Why bind `0.0.0.0`?** It allows the laptop server to listen on its network interfaces, including Wi-Fi.
35. **Why is debug off?** LAN users must not access a development debugger. This demo also disables automatic reload.
36. **Why is SQLite used?** It provides a local relational database without a separate database service.
37. **What are parameterized queries?** SQL and values are passed separately using `?`, reducing injection risk.
38. **What data is kept?** Completed match scores, round accuracy and times for 30 days; nicknames and IPs are not persisted.
39. **What happens after disconnect?** The slot remains, timers continue, and the same tab can resume using its secret token.
40. **What is adaptive solo mode?** Simple recent accuracy and time rules choose the next difficulty; it is not machine learning.
41. **What is CustomTkinter?** A Tk-based Python library for themed desktop widgets.
42. **Why use a worker thread?** Metadata and downloads can be slow; a worker keeps the UI responsive.
43. **Why use a queue for UI updates?** Tk widgets should be updated by the main UI thread.
44. **What is yt-dlp?** A media extraction and download library whose site support may change.
45. **What does FFmpeg do?** It merges separate audio/video streams and performs the explicitly selected MP3 conversion. Original MP4 downloads are preserved without re-encoding.
46. **Can SunDrop download every Instagram or YouTube link?** No. Restrictions, extractor changes and terms can prevent downloads; it does not bypass access controls.
47. **How are filenames made safe?** Invalid Windows characters, reserved names, trailing dots and template percent signs are sanitized.
48. **What was tested?** See the current JUnit evidence for the exact total. Tests cover rules, storage, original downloads, artwork, MP3 tags, player controls and hidden GUI responsiveness. Browser checks before the last visual refinement covered two tabs, results, rematch, reload reconnect and a phone-sized layout. A physical phone LAN test was not done.
49. **What is Git and what is future scope?** Git records code versions. Future work includes a physical phone test, optional QR links, more accessibility checks and stronger deployment hardening.
50. **Were these built during the internship?** That is not documented. Describe them as independent demonstrations connected to Python study, and verify the actual diary separately.
