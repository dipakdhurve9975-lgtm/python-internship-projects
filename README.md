# Python internship demonstration projects

Two working independent student demos: **SunDrop**, a desktop downloader for authorized media, and **MathDuel LAN**, a server-controlled mental math game. These were built as demonstrations on 11 October 2026. No claim is made that they were completed during an internship.

## Windows quick start

Python **3.11 or newer** is required. The machine's default `python` is 3.10; development and tests here used the bundled Python **3.12.14**. Install a suitable Python from python.org if needed. Open PowerShell:

```powershell
cd "C:\Users\ADMIN\Downloads\python project intership\python-internship-projects"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r mathduel-lan\requirements.txt -r sundrop\requirements.txt
python mathduel-lan\app.py
```

If activation is blocked by the local execution policy, call `.\.venv\Scripts\python.exe` directly instead of changing system policy. If `py -3.12` is unavailable, replace it with your Python 3.11+ executable. On this machine this pre-existing executable also works:

```powershell
& "C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m venv .venv
```

Open **http://127.0.0.1:5000** on the host laptop. In a second PowerShell window:

```powershell
cd "C:\Users\ADMIN\Downloads\python project intership\python-internship-projects"
.\.venv\Scripts\python.exe sundrop\app.py
```

For the development environment already created in the parent folder, both apps can run immediately without reinstalling:

```powershell
cd "C:\Users\ADMIN\Downloads\python project intership"
.\.venv\Scripts\python.exe python-internship-projects\mathduel-lan\app.py
# In a separate PowerShell window:
.\.venv\Scripts\python.exe python-internship-projects\sundrop\app.py
```

Stop the server with **Ctrl+C**. If the currently running server already owns port 5000, use `--port 5001` and open the matching URL.

## Play on a local network

The Windows laptop hosts Python on `0.0.0.0`, with debug off. Both devices must first reach the host URL. On the laptop, run `ipconfig` and select the Wi-Fi adapter's IPv4 address. Open `http://HOST_LAN_IP:5000` on the phone, create a room on the laptop, and join its six-digit code on the phone. The home page and console show IP **candidates**, which may include unusable virtual adapters.

A phone can provide a hotspot while the laptop hosts Python. Hotspot client isolation can block device-to-device traffic. A room code selects a room on an already reachable server; it is not discovery. A QR code is optional and not implemented. No router port forwarding, public hosting or firewall changes are made. See [LAN guide](docs/LAN_GUIDE.md).

## Safe SunDrop demonstration

Create and serve an original two-second sine-wave recording:

```powershell
python docs\make_sample.py
python -m http.server 8765 --bind 127.0.0.1 --directory docs\evidence\runtime\sample
```

In SunDrop use `http://127.0.0.1:8765/sundrop-original-tone.wav`, confirm permission, click Fetch Media, select WAV and its source quality, choose a folder and download. The generated sample is ours; no third-party copyrighted media is needed. When source artwork is unavailable, an original retro cover uses the title and type. Site thumbnails appear only when metadata supplies one and the fetch succeeds.

SunDrop uses yt-dlp's supported extraction. It does not install cookies, log in, bypass DRM or overcome source restrictions. Site behavior and terms change. YouTube and Instagram are not guaranteed. Original audio and combined video can download without FFmpeg; merging and explicit MP3 conversion require it. Optional install, performed by you: `winget install --id Gyan.FFmpeg -e`, then reopen PowerShell and run `ffmpeg -version`. See [troubleshooting](docs/TROUBLESHOOTING.md).

The retro update adds pastel cyan and cream windows, hard shadows, Paste, separate format/source quality selectors, artwork caching, thumbnail sidecars and a local library. MP3 source art and title/artist/album tags use Mutagen on a temporary copy, verified before replacing the file. Video and Audio only are now labeled separately; separate video/audio streams can merge with FFmpeg. The integrated FFpyplayer player supports video and audio, pause/resume, seeking, volume and library navigation. Optional Normal/Pixel/ASCII video views leave the saved file unchanged. Music uses the exact user-supplied muted CD video as a looping visual. File opens local media in SunDrop; Library's Open File retains the OS handler. See [video repair and test instructions](docs/SUNDROP_VIDEO_FIX.md).

## Verification and evidence

```powershell
python -m pytest mathduel-lan\tests sundrop\tests -q
```

The evidence folder contains JUnit XML, test outputs, environment versions, a screenshot manifest and actual screenshots of running apps. Unit tests use controlled server time to test deadlines without waiting 170 seconds per match. Browser evidence uses the real default round duration. Two browser tabs on one laptop and a 390-pixel viewport were tested; **physical phone-to-laptop LAN connectivity and phone-as-server mode were not tested**.

- [Beginner guide](docs/BEGINNER_GUIDE.md) — tiny runnable Python examples and file explanations.
- [Viva preparation](docs/VIVA_PREP.md) — 50 short answers.
- [Architecture](docs/ARCHITECTURE.md) — event flow, data and limitations.
- [Evidence](docs/evidence/VERIFICATION.md) — actual outcomes and remaining checks.
- `report/` — editable DOCX and printable PDF. Replace student placeholders and verify internship details against the missing certificate and diary before academic submission.

## Local data

MathDuel stores scores and anonymous per-player round records in `%USERPROFILE%\.mathduel\matches.sqlite3`. It does not persist nicknames, resume tokens or IPs in the database. Completed matches are retained for 30 days; pruning runs at startup and each save. Active rooms live only in process memory and expire 30 minutes after creation. Restarting the server loses them. `MATHDUEL_DATA_DIR` can change storage location.

SunDrop stores the latest 100 completed titles, creator, album, duration, type, size, paths, artwork paths, status and UTC times in `%USERPROFILE%\.sundrop\history.json`. Cached normalized covers are in its `artwork` folder; each download has a `.cover.jpg` sidecar. Successful thumbnail fetches reuse a URL-hash cache; source URLs are not written to JSON. `SUNDROP_DATA_DIR` can change storage. Cached artwork is not automatically pruned in this MVP. Downloads remain wherever you chose. Missing/moved library files are marked and cannot be played internally. Corrupt history is reported, not overwritten. Histories, databases and environments are ignored by Git.

## GitHub instructions

Nothing has been pushed. Review the files and report placeholders first. Create an empty repository in your own GitHub account, then run:

```powershell
git init
git add .
git status
git commit -m "Add SunDrop and MathDuel LAN demonstration projects"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
# Run only when you choose to publish:
git push -u origin main
```

Screenshots contain local demonstration room codes and IP candidates; review them before publication. `requirements-tested.txt` records the versions used here; project requirements permit compatible updates. The vendored Socket.IO client includes its MIT license and source hash.
