import functools
import hashlib
import http.server
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import pytest
import yt_dlp
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Downloader,History
from media import probe_media,MediaValidationError
from player import VideoPlayer
from effects import video_effect

def run_ffmpeg(*args):
    subprocess.run([shutil.which('ffmpeg'),'-v','error',*map(str,args)],check=True,capture_output=True)

@pytest.fixture
def source(tmp_path):
    if not shutil.which('ffmpeg'):pytest.skip('FFmpeg generates the test media.')
    video=tmp_path/'video.mp4';audio=tmp_path/'audio.m4a'
    run_ffmpeg('-f','lavfi','-i','testsrc2=s=320x180:r=15','-t','4','-c:v','libx264','-pix_fmt','yuv420p',video)
    run_ffmpeg('-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','4','-c:a','aac',audio)
    return video,audio

def test_separate_streams_merge_with_picture_and_sound(source,tmp_path):
    video,audio=source
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(video.parent))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    class LocalFixture(yt_dlp.YoutubeDL):
        def extract_info(self,url,download=True,**kwargs):
            return self.process_ie_result({'id':'own','title':'Own merged video','extractor':'fixture','extractor_key':'Fixture','webpage_url':base,'formats':[
                {'format_id':'a','url':base+'/audio.m4a','ext':'m4a','vcodec':'none','acodec':'aac','abr':128},
                {'format_id':'v','url':base+'/video.mp4','ext':'mp4','vcodec':'avc1','acodec':'none','height':180,'width':320},
                {'format_id':'drm','url':base+'/video.mp4','ext':'mp4','vcodec':'avc1','acodec':'aac','has_drm':True}]},download=download)
    try:
        service=Downloader(History(tmp_path/'data/history.json'),LocalFixture)
        info,choices=service.inspect(base+'/media')
        label,choice=next(iter(choices.items()))
        assert choice['kind']=='video' and choice['format']=='v+a'
        assert choice['group']=='Video · MP4' and '180p' in label
        path=service.download(base+'/media',info,choice,tmp_path/'out',threading.Event(),lambda _:None)
        assert Path(path).suffix=='.mp4'
        streams=probe_media(path)
        assert streams['has_video'] and streams['has_audio'] and streams['width']==320
        entry=service.history.read()[0]
        assert entry['media_kind']=='video' and entry['streams_verified']
        service.ffmpeg=lambda:None
        info,choices=service.inspect(base+'/media')
        assert info['video_needs_ffmpeg'] and all(c['kind']=='audio' for c in choices.values())
    finally:server.shutdown();server.server_close()

def test_audio_disguised_as_video_is_not_marked_complete(source,tmp_path):
    _,audio=source
    class Wrong:
        def __init__(self,options):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def extract_info(self,*args,**kwargs):return {'filepath':str(audio)}
    service=Downloader(History(tmp_path/'history.json'),Wrong)
    with pytest.raises(MediaValidationError,match='audio without video'):
        service.download('http://example.com/media',{'title':'Video'},{'format':'v','kind':'video'},tmp_path,threading.Event(),lambda _:None)
    assert service.history.read()==[] and audio.is_file()

def test_video_play_pause_seek_and_unchanged_bytes(source,tmp_path,monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER','dummy')
    video,audio=source;combined=tmp_path/'combined.mp4'
    run_ffmpeg('-i',video,'-i',audio,'-c','copy',combined)
    before=hashlib.sha256(combined.read_bytes()).hexdigest()
    player=VideoPlayer()
    try:
        player.play(combined)
        frames=[];deadline=time.monotonic()+3
        while time.monotonic()<deadline and len(frames)<3:
            frame=player.frame()
            if frame is not None:frames.append(frame)
            time.sleep(.02)
        assert len(frames)>=3 and player.has_video and player.duration>=3.9
        player.toggle();position=player.position();time.sleep(.1)
        assert player.paused and player.position()==pytest.approx(position,abs=.05)
        player.seek(2);player.toggle();deadline=time.monotonic()+2
        while time.monotonic()<deadline and player.last_pts<1.8:player.frame();time.sleep(.02)
        assert player.last_pts>=1.8
        player.set_volume(.2);assert player.media.get_volume()==pytest.approx(.2,abs=.02)
        for mode in ('Normal','Pixel','ASCII'):
            assert video_effect(frames[0],mode).size==(640,360)
    finally:player.stop()
    assert hashlib.sha256(combined.read_bytes()).hexdigest()==before

def test_effects_are_optional_and_read_only():
    frame=Image.new('RGB',(160,90),'#BCE8E5');before=frame.tobytes()
    for mode in ('Normal','Pixel','ASCII'):assert video_effect(frame,mode).size==(640,360)
    assert frame.tobytes()==before

def test_cd_reference_is_the_exact_user_supplied_clip():
    clip=Path(__file__).resolve().parents[1]/'assets/music-cd-reference.mp4'
    assert hashlib.sha256(clip.read_bytes()).hexdigest()=='20b07c7fed35905b8c9221f62e19769d4f69eca2d20a4f568b9a0b91b070b96d'
    player=VideoPlayer()
    try:
        player.play(clip,muted=True,loop=True)
        deadline=time.monotonic()+3;frames=0
        while time.monotonic()<deadline and frames<2:
            if player.frame() is not None:frames+=1
            time.sleep(.02)
        assert frames>=2 and player.media.get_volume()==0
    finally:player.stop()
