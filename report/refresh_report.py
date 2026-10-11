"""Update the ten-page report with the current desktop capture and plain wording."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
builder = root / 'report/build_report.py'
text = builder.read_text(encoding='utf-8')
replacements = {
    "SHOTS/'sundrop-home.png'": "SHOTS/'sundrop-retro.png'",
    'Figure 2. Real initial SunDrop desktop. This capture predates the cyan and cream retro redesign.': 'Figure 2. Current SunDrop desktop: cyan and cream panels, retro menus and media preview. Captured on 11 October 2026.',
    'Fresh visual capture was stopped with Escape; the earlier screenshot is not presented as the final retro interface.': 'The screenshot above was captured from the running final interface, using a separate empty library to protect personal download history.',
    'Physical phone networking and the final visual walkthrough remain pending. Screenshots show earlier running interfaces and are labelled accordingly.': 'The final SunDrop interface was captured from the running app. MathDuel screenshots record an earlier working version and are labelled. A physical phone networking test is still pending.',
    'A worker performs network tasks; a queue and Tk after() update the interface on the main thread.': 'A background task handles network requests. A queue passes its results to the main interface, where Tk after() safely updates the screen.',
    'monotonic deadlines': 'deadlines measured by a clock that cannot jump when the system time changes',
    'parameterized SQLite queries': 'SQLite queries that keep data values separate from SQL commands',
    'a sidecar image': 'a cover image saved next to the media file',
    'uses a sidecar': 'uses a separate cover image',
    'bounded thumbnails': 'thumbnails limited in file size and image dimensions',
    'MP3 tags/APIC': 'MP3 details and embedded cover art',
    'cover sidecar': 'separate cover image',
    'MP4 sidecar': 'MP4 cover image',
    'APIC were read': 'embedded cover art were read',
    'cached artwork, MP3 tags': 'saved cover images, MP3 track details',
    'cancellation is cooperative': 'the download stops when its next safe cancellation check is reached',
    'Fil enames': 'Filenames',
    'Final visuals and physical LAN operation need further checks.': 'The current SunDrop design has been captured. MathDuel’s final design and physical LAN operation need further checks.',
    'a final screenshot walkthrough': 'a final MathDuel screenshot walkthrough',
    'real earlier captures': 'the current SunDrop capture and labelled earlier MathDuel captures',
    'Old screenshots are labelled by version.': 'The current SunDrop screenshot and earlier MathDuel screenshots are labelled by version.',
    'No repository was pushed.': 'GitHub publication and live hosting are being prepared; this report does not claim a deployment that has not been verified.',
}
for old, new in replacements.items():
    text = text.replace(old, new)
builder.write_text(text, encoding='utf-8')
manifest = root / 'docs/evidence/screenshot-manifest.json'
records = json.loads(manifest.read_text(encoding='utf-8'))
for record in records:
    if record['file'] == 'sundrop-home.png':
        record['caption'] = 'Archived initial SunDrop interface. The report now uses sundrop-retro.png.'
records = [r for r in records if r['file'] != 'sundrop-retro.png']
shot = root / 'docs/evidence/screenshots/sundrop-retro.png'
records.append(dict(file=shot.name, sha256=hashlib.sha256(shot.read_bytes()).hexdigest(), caption='Actual current SunDrop retro desktop, separate empty verification library.', capture_date='2026-10-11', current_design=True))
manifest.write_text(json.dumps(records, indent=2), encoding='utf-8')
(root / 'docs/evidence/SCREENSHOT_MANIFEST.md').write_text('# Screenshot evidence\n\n' + '\n\n'.join(f"- **{r['file']}**: {r['caption']}\n  SHA256: `{r['sha256']}`" for r in records) + '\n', encoding='utf-8')
print('Updated report source and screenshot evidence.')
