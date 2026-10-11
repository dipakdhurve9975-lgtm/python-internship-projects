import hashlib
import io
import functools
import http.server
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from artwork import ArtworkCache,embed_mp3
from core import Downloader,History
from player import AudioPlayer,open_local
from mutagen.id3 import ID3
from mutagen.mp3 import MP3

def own_tone(folder):
    script=Path(__file__).resolve().parents[2]/'docs'/'make_sample.py'
    spec=importlib.util.spec_from_file_location('sample2',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.create_sample(folder)

@pytest.fixture
def mp3(tmp_path):
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:pytest.skip('FFmpeg is not installed; MP3 conversion integration requires it.')
    wav=own_tone(tmp_path/'source');mp3=tmp_path/'original.mp3'
    subprocess.run([ffmpeg,'-v','error','-i',str(wav),'-codec:a','libmp3lame',str(mp3)],check=True,capture_output=True)
    return mp3

def test_real_thumbnail_retrieval_and_cache(tmp_path):
    source=tmp_path/'source';source.mkdir();Image.new('RGB',(100,80),'#BCE8E5').save(source/'own.png')
    hits=[]
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):hits.append(self.path);super().do_GET()
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(source)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        cache=ArtworkCache(tmp_path/'cache');url=f'http://127.0.0.1:{server.server_port}/own.png'
        path,real,warning=cache.get(url,'Original recording','wav')
        assert real and warning is None
        assert Image.open(path).format=='JPEG'
        assert cache.get(url,'Original recording','wav')[0]==path and hits==['/own.png']
    finally:server.shutdown();server.server_close()

@pytest.mark.parametrize('data',[b'not an image',b'x'*4_000_001],ids=['invalid-image','oversized-image'])
def test_thumbnail_failure_fallback(tmp_path,data):
    cache=ArtworkCache(tmp_path/'cache',fetch=lambda _:data)
    path,real,warning=cache.get('https://example.com/bad','Our song','mp3')
    assert not real and warning and Image.open(path).size==(640,640)
    assert cache.get(None,'Our song','mp3')[0]==path
    assert not list(cache.folder.glob('*.tmp'))

def test_mp3_artwork_tags_and_unchanged_audio(mp3,tmp_path):
    picture=tmp_path/'cover.png';Image.new('RGB',(200,180),'#F5EFE2').save(picture)
    ffmpeg=shutil.which('ffmpeg')
    def pcm():return subprocess.check_output([ffmpeg,'-v','error','-i',str(mp3),'-f','s16le','-'])
    before=hashlib.sha256(pcm()).hexdigest()
    assert embed_mp3(mp3,picture,'Our recording','Student demo','Original tones')
    tags=ID3(mp3)
    assert str(tags['TIT2'])=='Our recording' and str(tags['TPE1'])=='Student demo' and str(tags['TALB'])=='Original tones'
    cover=tags.getall('APIC')[0];assert cover.mime=='image/jpeg' and cover.type==3
    assert Image.open(io.BytesIO(cover.data)).format=='JPEG'
    assert hashlib.sha256(pcm()).hexdigest()==before and MP3(mp3).info.length>0

def test_mp3_transaction_failure_preserves_original(mp3,tmp_path,monkeypatch):
    original=mp3.read_bytes()
    def failed(*args,**kwargs):raise OSError('Simulated tag write failure')
    monkeypatch.setattr(ID3,'save',failed)
    with pytest.raises(OSError):embed_mp3(mp3,None,'Title')
    assert mp3.read_bytes()==original and list(tmp_path.glob('*.mp3'))==[mp3]

def test_library_persistence_with_artwork(tmp_path):
    path=tmp_path/'track.wav';path.write_bytes(b'example')
    art=tmp_path/'track.wav.cover.jpg';Image.new('RGB',(20,20),'#BCE8E5').save(art)
    history=History(tmp_path/'history.json')
    history.add('Own track',path,'complete',creator='Student',duration=2,format='wav',thumbnail=str(art),size=7)
    restarted=History(history.path).read()[0]
    assert restarted['thumbnail']==str(art) and Path(restarted['thumbnail']).exists()
    assert restarted['creator']=='Student' and restarted['format']=='wav'
    history.add('Own track',path,'complete',thumbnail=str(art));assert len(history.read())==1

def test_open_file_and_missing_folder(tmp_path):
    path=tmp_path/'track.wav';path.write_bytes(b'own');opened=[]
    open_local(path,opener=opened.append);open_local(path,folder=True,opener=opened.append)
    assert opened==[str(path),str(tmp_path)]
    with pytest.raises(FileNotFoundError):open_local(tmp_path/'missing.wav',opener=opened.append)

def test_real_player_controls_with_dummy_audio(tmp_path,monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER','dummy')
    path=own_tone(tmp_path/'source');clock=[0.0];player=AudioPlayer(clock=lambda:clock[0])
    try:
        player.play(path,2);clock[0]=.5;assert player.position()==.5
        player.toggle();clock[0]=1.0;assert player.paused and player.position()==.5
        player.toggle();clock[0]=1.3;assert not player.paused and player.position()==pytest.approx(.8)
        player.set_volume(.25);assert player.music.get_volume()==pytest.approx(.25,abs=.01)
        player.stop();assert not player.active and player.position()==0
        with pytest.raises(FileNotFoundError):player.play(tmp_path/'missing.mp3')
        bad=tmp_path/'video.mp4';bad.write_bytes(b'not media')
        with pytest.raises(ValueError):player.play(bad)
    finally:
        player.stop()
        import pygame
        pygame.mixer.quit()

def test_real_ffmpeg_conversion_and_sidecar(tmp_path):
    if not shutil.which('ffmpeg'):pytest.skip('FFmpeg is needed for conversion.')
    original=own_tone(tmp_path/'source')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(original.parent)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        service=Downloader(History(tmp_path/'data'/'history.json'));url=f'http://127.0.0.1:{server.server_port}/{original.name}'
        info,choices=service.inspect(url)
        choice=choices['MP3 audio · convert with FFmpeg']
        path=service.download(url,info,choice,tmp_path/'out',threading.Event(),lambda _:None)
        assert Path(path).suffix=='.mp3' and MP3(path).info.length>0
        saved=service.history.read()[0]
        assert saved['format']=='mp3' and Path(saved['thumbnail']).is_file() and str(ID3(path)['TIT2'])==info['title']
    finally:server.shutdown();server.server_close()

def test_direct_mp4_preserved_with_associated_cover(tmp_path):
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:pytest.skip('FFmpeg generates the original test video; downloading it does not need FFmpeg.')
    original=tmp_path/'own-test.mp4'
    subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','color=c=cyan:s=160x90:r=10','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(original)],check=True,capture_output=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        service=Downloader(History(tmp_path/'data'/'history.json'));service.ffmpeg=lambda:None
        url=f'http://127.0.0.1:{server.server_port}/{original.name}';info,choices=service.inspect(url)
        path=service.download(url,info,next(iter(choices.values())),tmp_path/'out',threading.Event(),lambda _:None)
        assert Path(path).read_bytes()==original.read_bytes()
        entry=service.history.read()[0]
        assert entry['format']=='mp4' and Path(entry['thumbnail']).is_file() and not entry['artwork_embedded']
    finally:server.shutdown();server.server_close()
