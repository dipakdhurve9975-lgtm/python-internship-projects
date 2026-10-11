# Troubleshooting

| Symptom | What to check |
|---|---|
| Python cannot import a module | Use the environment's Python; install the matching requirements. Check `python --version` is at least 3.11. |
| PowerShell blocks activation | Use `.\.venv\Scripts\python.exe` directly. No execution-policy change is necessary. |
| Port already in use | Stop the previous server with Ctrl+C, or run `python mathduel-lan\app.py --port 5001`. Change the browser URL too. |
| Phone cannot reach laptop | Test `/health`; check active Wi-Fi IPv4, port, firewall Private-profile allowance and hotspot client isolation. |
| Room not found | Reach the correct host first. Codes expire after 30 minutes or a server restart. |
| Resume refused | The same player may still be connected elsewhere, the token may be missing, the room may have expired, or explicit Leave invalidated it. |
| Lobby cannot start | Two-player mode requires both slots connected. Only the first player starts. Solo requires its one player. |
| Game says answer already received | One valid whole-number answer is allowed per round. Invalid syntax can be corrected before the deadline. |
| Downloader reports source restriction | Use an authorized unrestricted source; SunDrop cannot bypass DRM, login or access controls. |
| Formats are unavailable | Preview again, update yt-dlp inside the venv, check source availability; separate video/audio streams need FFmpeg. |
| FFmpeg missing | Run `ffmpeg -version`; ensure its bin folder is on PATH and restart SunDrop. Original audio and combined formats remain available. |
| Cancellation seems delayed | yt-dlp progress hooks cooperate with cancellation. A network request can wait up to its timeout; an active merge may not stop immediately. |
| History cannot be read | Preserve the damaged history file, then rename it manually so a fresh file can be created. Do not lose the backup. |
| Desktop controls below screen | Scroll the main pane. The sidebar stays visible; minimum window width is 860 pixels. |

## Manual test checklist

Use the original local tone in `make_sample.py`; it is safe to download. Test a writable destination and a non-writable destination. Attempt an invalid URL. Uncheck permission and confirm no request starts. During a larger authorized download, click Cancel and verify the message and no completion entry. Check history on restart and both appearance modes. Actual large-file cancellation, external-site thumbnail fetching and FFmpeg merging remain manual checks if not recorded in the evidence file.
