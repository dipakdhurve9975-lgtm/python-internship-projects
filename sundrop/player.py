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
