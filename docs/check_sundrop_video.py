"""Instrument our own Tk app for repeatable visual verification, not user-window input."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import time
import subprocess
import shutil
from PIL import ImageGrab

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'sundrop'))
os.environ['SUNDROP_DATA_DIR']=tempfile.mkdtemp(prefix='sundrop-visual-')
from app import SunDrop
sample=Path(sys.argv[1])
before=hashlib.sha256(sample.read_bytes()).hexdigest()
app=SunDrop();app.geometry('1100x750+15+15')
app.set_player_volume(0)
errors=[];app.report_callback_exception=lambda *exc:errors.append(str(exc[1]))
app.play_item({'path':str(sample),'title':'Your sample video · playback test'})
app.player_window.geometry('740x820+500+20')
def pump(seconds):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:app.update();time.sleep(.015)
out=root/'docs/evidence/sundrop-video';out.mkdir(parents=True,exist_ok=True)
def capture(name):
    app.player_window.attributes('-topmost',True);app.player_window.lift();pump(.3)
    w=app.player_window
    ImageGrab.grab(bbox=(w.winfo_rootx(),w.winfo_rooty(),w.winfo_rootx()+w.winfo_width(),w.winfo_rooty()+w.winfo_height())).save(out/(name+'.png'))
try:
    pump(2);assert app.last_frame is not None,'No video frame displayed'
    app.toggle_playback();pump(.2);assert app.video_player.paused
    for mode in ('Normal','Pixel','ASCII'):
        app.set_effect(mode);capture(mode.lower())
    app.seek_media(.5);app.toggle_playback();pump(.8);assert app.video_player.position()>4
    app.close_player();pump(.1)
    # Use the supplied clip's own audio for the music-mode visual check.
    audio=Path(os.environ['SUNDROP_DATA_DIR'])/'reference-audio.m4a'
    subprocess.run([shutil.which('ffmpeg'),'-v','error','-i',str(sample),'-vn','-c:a','copy',str(audio)],check=True,capture_output=True)
    app.play_item({'path':str(audio),'title':'Your supplied clip · music visual test'})
    assert app.player_window is not None,app.status.cget('text')
    app.player_window.geometry('740x820+500+20');pump(1)
    assert app.last_cd_frame is not None,'The user-provided CD video did not render'
    capture('reference-cd')
    app.toggle_playback();assert app.active_player().paused
    assert not errors,errors
    assert hashlib.sha256(sample.read_bytes()).hexdigest()==before
    print('PASS: actual sample frames, all effects, pause, seek, CD audio mode, zero Tk callback errors, unchanged source SHA-256')
finally:app.close()
