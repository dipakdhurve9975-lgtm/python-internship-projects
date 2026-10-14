"""Local audio playback. Unsupported files are opened using the OS instead."""
from pathlib import Path
import os
import subprocess
import sys
import time

def open_local(path,folder=False,opener=None):
    target=Path(path)
    if folder:target=target.parent
    if not target.exists():raise FileNotFoundError('This file or folder was moved or removed.')
    if opener:opener(str(target));return
    if sys.platform=='win32':os.startfile(str(target))
    elif sys.platform=='darwin':subprocess.Popen(['open',str(target)])
    else:subprocess.Popen(['xdg-open',str(target)])

class AudioPlayer:
    supported={'.wav','.mp3','.ogg'}
    def __init__(self,clock=time.monotonic):
        self.clock=clock;self.music=None;self.path=None;self.duration=0;self.offset=0;self.started=0;self.paused=False;self.active=False;self.volume=.6
    def initialize(self):
        if self.music is None:
            import pygame
            pygame.mixer.init();self.music=pygame.mixer.music;self.music.set_volume(self.volume)
    def play(self,path,duration=None):
        path=Path(path)
        if not path.is_file():raise FileNotFoundError('This audio file was moved or removed.')
        if path.suffix.lower() not in self.supported:raise ValueError('Internal playback supports WAV, MP3 and OGG. Use Open File for other formats.')
        self.initialize();self.music.load(str(path));self.music.play()
        self.path=str(path);self.duration=float(duration or 0)
        if not self.duration:
            try:
                from mutagen import File
                self.duration=float(File(path).info.length)
            except Exception:self.duration=0
        self.offset=0;self.started=self.clock();self.paused=False;self.active=True
    def position(self):
        if not self.active:return self.offset
        position=self.offset if self.paused else self.offset+max(0,self.clock()-self.started)
        if self.duration and position>=self.duration:
            self.offset=self.duration;self.active=False
            return self.duration
        return position
    def toggle(self):
        if not self.music or not self.path:raise ValueError('Choose a local audio track first.')
        if not self.active:self.play(self.path,self.duration);return
        if self.paused:self.music.unpause();self.started=self.clock();self.paused=False
        else:self.offset=self.position();self.music.pause();self.paused=True
    def set_volume(self,value):
        self.volume=max(0,min(1,float(value)))
        if self.music:self.music.set_volume(self.volume)
    def stop(self):
        if self.music:self.music.stop()
        self.offset=0;self.active=False;self.paused=False

class VideoPlayer:
    """SDL audio plus synchronized FFmpeg frames; all public calls stay on Tk's thread."""
    supported={'.mp4','.webm','.mov','.mkv','.avi','.m4a','.flac','.aac','.opus'}
    def __init__(self):
        self.media=None;self.path=None;self.duration=0;self.active=False;self.paused=False;self.volume=.6;self.offset=0
        self.pending=None;self.due=0;self.has_video=False;self.started=0;self.ready=False;self.last_pts=0
        import queue
        self.errors=queue.SimpleQueue()
    def play(self,path,duration=None,muted=False,loop=False):
        path=Path(path)
        if not path.is_file():raise FileNotFoundError('This media file was moved or removed.')
        from media import probe_media
        streams=probe_media(path)
        from ffpyplayer.player import MediaPlayer
        self.stop();self.path=str(path);self.duration=float(duration or (streams or {}).get('duration') or 0)
        while not self.errors.empty():self.errors.get()
        self.has_video=bool((streams or {}).get('has_video',path.suffix.lower() in {'.mp4','.webm','.mov','.mkv','.avi'}))
        def callback(selector,value):
            if selector.endswith(':error'):self.errors.put(str(value))
        self.media=MediaPlayer(str(path),callback=callback,ff_opts={'out_fmt':'rgb24','x':-1,'y':360,'volume':0 if muted else self.volume,'an':muted,'loop':0 if loop else 1,
            'af':'aresample=44100,aformat=channel_layouts=stereo'},lib_opts={'threads':'2'},loglevel='error')
        self.active=True;self.paused=False;self.offset=0;self.started=time.monotonic();self.ready=False;self.last_pts=0
    def frame(self):
        if not self.media or not self.active:return None
        if not self.errors.empty():raise RuntimeError(self.errors.get())
        metadata=self.media.get_metadata()
        self.duration=float(metadata.get('duration') or self.duration)
        if metadata.get('duration') is not None and not self.ready:
            self.ready=True;self.started=time.monotonic()
        if self.pending:
            if time.monotonic()<self.due:return None
            result=self.pending;self.pending=None;return result
        frame,wait=self.media.get_frame()
        if wait=='eof' and self.has_video:self.active=False;self.paused=False;self.offset=self.duration;return None
        # Audio-only files have no video frames, so get_frame() may report eof
        # while SDL is still playing the audio. Use the audio duration instead.
        if not self.has_video and self.ready and self.duration and self.position()>=self.duration:
            self.active=False;self.paused=False;self.offset=self.duration
            self.media.set_pause(True)
            return None
        if frame:
            from PIL import Image
            image,self.last_pts=frame
            pixels=Image.frombytes('RGB',image.get_size(),bytes(image.to_bytearray()[0]))
            if isinstance(wait,(int,float)) and wait>0:
                self.pending=pixels;self.due=time.monotonic()+wait;return None
            return pixels
        return None
    def position(self):
        if not self.media or not self.active:return self.offset
        # get_pts() in the Windows decoder can dereference an uninitialized
        # audio clock immediately after opening a file. Keep the UI clock here;
        # FFpyplayer still owns synchronized frame scheduling and audio output.
        value=self.offset if self.paused or not self.ready else self.offset+time.monotonic()-self.started
        return min(value,self.duration) if self.duration else value
    def toggle(self):
        if not self.path:raise ValueError('Open a local media file first.')
        if not self.active:self.play(self.path,self.duration);return
        if not self.paused:self.offset=self.position()
        else:self.started=time.monotonic()
        self.paused=not self.paused;self.media.set_pause(self.paused)
        if self.paused:self.pending=None
    def seek(self,seconds):
        if not self.media:return
        seconds=max(0,min(float(seconds),self.duration or float(seconds)))
        self.media.seek(seconds,relative=False);self.pending=None;self.offset=seconds;self.started=time.monotonic();self.last_pts=0
        self.media.set_pause(self.paused)
        self.active=True
    def set_volume(self,value):
        self.volume=max(0,min(1,float(value)))
        if self.media:self.media.set_volume(self.volume)
    def stop(self):
        media=self.media;self.media=None
        if media:media.close_player()
        self.active=False;self.paused=False;self.pending=None;self.offset=0
