# Verified results and remaining work

Verification date: 11 October 2026, Asia/Calcutta. Environment and test totals are read from actual JUnit XML by `record_evidence.py`.

## Automated verification

Final combined run: **73 passed, 0 failures, 0 errors, 0 skipped**. Python 3.12.14 on Windows 11. The JUnit file is `tests.xml`; `test-output.txt` contains the terminal outcome. `environment.json` and `requirements-tested.txt` record package versions. MathDuel has 36 cases; SunDrop has 37, including hidden Tk integration.

MathDuel: generator properties across all six operations and three levels, nickname/answer validation, deadline rejection, scoring, duplicate/stale answers, two-player limits, host authorization, timeout completion, tie results, rematch reset, room expiration, collision exhaustion, reconnect tokens, source-IP rate limiting, SQLite aggregation and idempotent saves. Socket.IO integration tests use test clients against the real Flask handlers.

SunDrop: URL and Windows filename validation, corrupt-history protection, history cap, retryable messages, cooperative pre-start cancellation, missing FFmpeg, format inspection, extraction failure and a real yt-dlp byte-for-byte download of original WAV audio. The updated suite adds real local HTTP artwork retrieval and one-fetch cache reuse, invalid/oversized thumbnail fallback, MP3 APIC/title/artist/album verification, identical decoded audio before/after tag editing, transactional tag-write failure, persisted artwork records, missing-file and OS-opener dispatch, pygame controls with dummy audio, real FFmpeg MP3 conversion, unchanged original MP4 plus sidecar, hidden GUI library/player/theme/format checks and an active worker responsiveness check.

## Browser observations

Two tabs on one laptop joined a room, saw the same question, submitted valid answers and completed a match. Actual final scores were Ada 54 and Alan 53; both had 40% accuracy. Several unattended rounds timed out during other verification tasks. Host rematch reset scores and started a fresh match. Reloading the second tab restored its identity and question. A 390 × 844 solo browser viewport showed 12 keypad buttons with content width 375, no horizontal overflow.

These observations occurred before the final styling refinements. The exact saved evidence is `browser-check.json` and the screenshot manifest. The final game JavaScript passed syntax checking and the backend suite remains green; a fresh visible walkthrough of the refined CSS and copy-code action remains pending.

## Honest limits

The final retro SunDrop desktop was captured on 11 October 2026 in a separate empty verification library. The report now uses sundrop-retro.png. Earlier MathDuel screenshots remain labelled by version. The library and floating player were covered by hidden Tk tests, not a new visible capture. Hidden Tk tests prove selected behavior, not visual polish. No speaker-output check, actual desktop OS-handler launch, physical phone-to-laptop LAN test, real hotspot test or Termux phone-hosting test was completed. Windows Firewall was not modified. Large active-download cancellation and external-site compatibility remain source-dependent manual checks.

The internship certificate, 12-week diary, reference report and student/college/supervisor details were not attached. Organization and dates are brief-supplied and unverified. The report describes independent demonstrations, uses editable placeholders and does not invent diary headings or signatures. No GitHub repository was pushed.
