import sys
import threading
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import validate_url,safe_filename,History,Downloader,Cancelled,friendly_error

@pytest.mark.parametrize('url',['https://example.com/file.mp4','http://127.0.0.1:8765/tone.wav',' https://example.org/a?b=1 '])
def test_url(url):assert validate_url(url)==url.strip()
@pytest.mark.parametrize('url',['',None,'file:///c:/a.mp4','ftp://example.com/a','https://u:secret@example.com','http://x:bad','https://example.com/a b','javascript:alert(1)'])
def test_bad_url(url):
    with pytest.raises(ValueError):validate_url(url)
@pytest.mark.parametrize('name',['CON','NUL.mp4','hello/../world?','<>:*','..','%title%','x'*300])
def test_filename(name):
    result=safe_filename(name)
    assert result and len(result)<=100 and not any(c in result for c in '<>:"/\\|?*%')
    assert result[-1] not in '. '
    assert result.split('.')[0].upper() not in ('CON','NUL')
def test_history(tmp_path):
    history=History(tmp_path/'history.json');assert history.read()==[]
    for i in range(105):history.add(f'Media {i}',f'{i}.wav','complete')
    assert len(history.read())==100 and history.read()[0]['title']=='Media 104'
    assert not history.path.with_suffix('.tmp').exists()
    history.path.write_text('bad',encoding='utf-8')
    with pytest.raises(ValueError):history.read()
    with pytest.raises(ValueError):history.add('x','x','complete')
    assert history.path.read_text()=='bad'
def test_errors():
    assert 'Cancelled' in friendly_error(Cancelled())
    assert 'FFmpeg' in friendly_error(RuntimeError('ffmpeg missing'))
    assert 'restricted' in friendly_error(RuntimeError('HTTP 403'))
    assert 'network' in friendly_error(RuntimeError('connection timed out'))
    assert 'writable' in friendly_error(PermissionError())
    assert 'retry' in friendly_error(RuntimeError('other'))
def test_cancellation_and_missing_ffmpeg(tmp_path,monkeypatch):
    d=Downloader(History(tmp_path/'history.json'));cancel=threading.Event();cancel.set()
    with pytest.raises(Cancelled):d.download('https://example.com/a',{}, {'format':'x'},tmp_path,cancel,lambda _:None)
    cancel.clear();monkeypatch.setattr(d,'ffmpeg',lambda:None)
    with pytest.raises(RuntimeError,match='FFmpeg'):d.download('https://example.com/a',{}, {'format':'x','needs_ffmpeg':True},tmp_path,cancel,lambda _:None)
    assert d.history.read()==[]
def test_format_and_error_handling(tmp_path):
    class Fake:
        def __init__(self,options):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def extract_info(self,url,download):return {'title':'Own media','formats':[{'format_id':'1','url':url,'vcodec':'h264','acodec':'aac','height':360,'ext':'mp4'},{'format_id':'2','url':url,'vcodec':'h264','acodec':'none','has_drm':True}]}
    d=Downloader(History(tmp_path/'history.json'),Fake);d.ffmpeg=lambda:None
    info,choices=d.inspect('https://example.com/a')
    assert len(choices)==1 and list(choices.values())[0]['format']=='1'
def test_extraction_failure(tmp_path):
    class Broken:
        def __init__(self,options):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def extract_info(self,*args,**kwargs):raise RuntimeError('unsupported URL')
    d=Downloader(History(tmp_path/'history.json'),Broken)
    with pytest.raises(RuntimeError):d.inspect('https://example.com/a')
    assert d.history.read()==[]
