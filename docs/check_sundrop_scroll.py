"""Exercise real Tk scrolling and compare a settled view before/after wheel bursts."""
import os
from pathlib import Path
import sys
import tempfile
import time
from PIL import ImageGrab,ImageChops
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'sundrop'))
os.environ['SUNDROP_DATA_DIR']=tempfile.mkdtemp(prefix='sundrop-scroll-')
from app import SunDrop
app=SunDrop();app.geometry('1080x640+30+30');app.attributes('-topmost',True)
errors=[];app.report_callback_exception=lambda *exc:errors.append(str(exc[1]))
out=root/'docs/evidence/sundrop-scroll';out.mkdir(parents=True,exist_ok=True)
def pump(seconds):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:app.update();time.sleep(.005)
def shot():
    return ImageGrab.grab(bbox=(app.winfo_rootx(),app.winfo_rooty(),app.winfo_rootx()+app.winfo_width(),app.winfo_rooty()+app.winfo_height()))
try:
    app.url.insert(0,'https://youtu.be/yDtCh2D8gog');app.authorized.set(True)
    choices={'1080p video + audio · mp4 · 137':{'kind':'video','group':'Video · MP4','format':'137+140','needs_ffmpeg':True},'Audio only · m4a · 140':{'kind':'audio','group':'Audio only · M4A','format':'140'}}
    app.events.put(('metadata',(app.url.get(),{'title':'RADHA · scrolling verification','duration':239,'uploader':'Ananta Roy'},choices)))
    pump(.5)
    for theme in ('Light','Dark'):
        app.set_theme(theme);app.content.yview('moveto',0);pump(.25)
        before=shot();before.save(out/(theme.lower()+'-before.png'))
        for i in range(80):
            app.title_label.event_generate('<MouseWheel>',delta=-120 if i%20<10 else 120)
            pump(.018)
            if i in (8,28,48):shot().save(out/(theme.lower()+f'-scroll-{i}.png'))
        app.content.yview('moveto',0);pump(.25)
        after=shot();after.save(out/(theme.lower()+'-after.png'))
        difference=ImageChops.difference(before,after).convert('L')
        changed=sum(1 for v in difference.getdata() if v>15)/(difference.width*difference.height)
        assert changed<.01,(theme,changed)
        assert app.url.get()=='https://youtu.be/yDtCh2D8gog' and app.authorized.get()
    assert not errors,errors
    print('PASS: 160 wheel events in Light/Dark, intact input/selection, no Tk errors, settled image change <1%.')
finally:app.close()
