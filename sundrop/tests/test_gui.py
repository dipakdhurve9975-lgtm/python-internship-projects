"""Hidden Tk integration checks; these are not screenshots or visual QA."""
import importlib.util
from pathlib import Path
import sys
import time
import threading
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

@pytest.fixture(scope='module')
def gui(tmp_path_factory):
    tmp_path=tmp_path_factory.mktemp('gui_session');monkeypatch=pytest.MonkeyPatch()
    monkeypatch.setenv('SUNDROP_DATA_DIR',str(tmp_path/'data'))
    monkeypatch.setenv('SDL_AUDIODRIVER','dummy')
    spec=importlib.util.spec_from_file_location('sundrop_gui',Path(__file__).resolve().parents[1]/'app.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    root=module.SunDrop();root.withdraw()
    yield root
    root.close()
    monkeypatch.undo()

def test_gui_worker_responsiveness(gui):
    gui.update();ticks=[];release=threading.Event()
    def ticker():ticks.append(gui.busy);gui.after(15,ticker)
    gui.after(15,ticker);gui.work(lambda:release.wait(timeout=2));gui.after(200,release.set)
    deadline=time.monotonic()+1
    while time.monotonic()<deadline:gui.update();time.sleep(.01)
    assert len(ticks)>=3 and any(ticks) and not gui.busy and release.is_set()
    assert str(gui.preview_button.cget('state'))=='normal'

def test_library_missing_files_and_player_navigation(gui,tmp_path):
    sample=Path(__file__).resolve().parents[2]/'docs'/'make_sample.py'
    spec=importlib.util.spec_from_file_location('gui_sample',sample);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    first=module.create_sample(tmp_path/'first');second=module.create_sample(tmp_path/'second')
    gui.service.history.add('One',first,'complete',duration=2,format='wav')
    gui.service.history.add('Two',second,'complete',duration=2,format='wav')
    gui.service.history.add('Missing',tmp_path/'gone.wav','complete',format='wav')
    gui.show('History');gui.update();gui.next_track(1);gui.player_window.withdraw();gui.update()
    assert gui.current_track['title']=='Two'
    gui.toggle_playback();assert gui.player.paused
    gui.next_track(1);assert gui.current_track['title']=='One'
    gui.next_track(-1);assert gui.current_track['title']=='Two'
    gui.player.stop()

def test_format_selectors_and_theme(gui):
    gui.choices={'Audio only · wav · 0':{'format':'0'},'720p video · mp4 · 22':{'format':'22'},'MP3 audio · convert with FFmpeg':{'format':'bestaudio','convert':'mp3'}}
    gui.filter_formats('MP4');assert gui.formats.get()=='720p video · mp4 · 22'
    gui.filter_formats('MP3 conversion');assert 'MP3' in gui.formats.get()
    gui.toggle_theme();gui.update();gui.toggle_theme()
