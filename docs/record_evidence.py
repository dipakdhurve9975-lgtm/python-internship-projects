"""Record actual test output and screenshot provenance, never invented results."""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];evidence=ROOT/'docs'/'evidence'
suite=ET.parse(evidence/'tests.xml').getroot().find('testsuite')
data={'date':'2026-10-11','timezone':'Asia/Calcutta','python':platform.python_version(),'platform':platform.platform(),
      **{key:int(suite.get(key,0)) for key in ('tests','failures','errors','skipped')},
      'packages':{name:importlib.metadata.version(name) for name in ('Flask','Flask-SocketIO','yt-dlp','customtkinter','Pillow','pytest','mutagen','pygame-ce')},'ffmpeg_detected':bool(shutil.which('ffmpeg'))}
(evidence/'environment.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
captions={
'sundrop-home.png':'Real initial SunDrop desktop window, before the retro redesign. No downloaded media is shown. Current retro visual capture pending after user stopped computer use.',
'mathduel-home.jpg':'Real initial welcome page. Before final practice/duel styling refinement.',
'mathduel-lobby.jpg':'Two connected browser tabs on one laptop: Ada and Alan, waiting for host start. Local simulation, not physical LAN evidence.',
'mathduel-match.jpg':'Real shared first-round question and server-derived countdown in the local two-tab match. Before final styling refinement.',
'mathduel-results.jpg':'Real completed two-tab match: Ada 54, Alan 53, both 40 percent accuracy. Missing rounds timed out. No physical phone test.',
'mathduel-mobile-solo.jpg':'Real solo game in a 390 by 844 browser viewport, visible numeric keypad, content width 375. Browser viewport simulation, not a real phone. Before final refinement.'}
manifest=[]
for name,caption in captions.items():
    path=evidence/'screenshots'/name
    if not path.is_file():raise FileNotFoundError(path)
    manifest.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'caption':caption,'capture_date':'2026-10-11','current_design':False})
(evidence/'screenshot-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(evidence/'SCREENSHOT_MANIFEST.md').write_text('# Real screenshot manifest\n\nAll images were captured from running apps on 11 October 2026. They show the initial working designs; the latest visual refinements have not been recaptured. No fabricated screenshots are included.\n\n'+'\n\n'.join(f"- `{r['file']}` — {r['caption']}\n  SHA256: `{r['sha256']}`" for r in manifest),encoding='utf-8')
groups={}
for case in suite.findall('testcase'):groups[case.get('classname')]=groups.get(case.get('classname'),0)+1
(evidence/'test-groups.json').write_text(json.dumps(groups,indent=2),encoding='utf-8')
print(json.dumps(data,indent=2));print(groups)
