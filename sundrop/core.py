"""Small testable downloader service, independent of Tk widgets."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import threading
from urllib.parse import urlsplit
import yt_dlp
from artwork import ArtworkCache, embed_mp3
from media import probe_media, MediaValidationError

class Cancelled(Exception): pass

def validate_url(value):
    if not isinstance(value,str) or len(value)>4096 or any(c.isspace() for c in value.strip()):
        raise ValueError('Paste one complete HTTP or HTTPS media URL.')
    value=value.strip()
    try:
        parsed=urlsplit(value)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError()
        _=parsed.port
        if re.search(r'[^\w.:-]',parsed.hostname):raise ValueError()
    except ValueError:
        raise ValueError('Use an HTTP or HTTPS URL without embedded credentials.') from None
    return value

def safe_filename(value):
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(value)).strip(' .')[:100].rstrip(' .')
    if not name:name='media'
    if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',name,re.I):name='_'+name
    # yt-dlp treats percent characters as output-template operators.
    return name.replace('%','_')

def friendly_error(error):
    if isinstance(error,MediaValidationError):return str(error)
    text=str(error).lower()
    if isinstance(error,Cancelled) or 'sundrop_cancel' in text:return 'Cancelled. Partial files may remain; retry to resume.'
    if 'ffmpeg' in text:return 'FFmpeg is required for this selection. Install it, restart SunDrop, or choose a single-file format.'
    if any(x in text for x in ('private','sign in','login','403','drm','unsupported url')):
        return 'This source is restricted or unsupported. SunDrop cannot bypass access controls. Try an authorized direct media URL.'
    if any(x in text for x in ('timed out','connection','resolve','network')):
        return 'The network request failed. Check your connection and URL, then retry.'
    if isinstance(error,PermissionError):return 'The output folder is not writable. Choose another folder.'
    return 'Could not process this media. The site or format may have changed. Check the URL, update yt-dlp, and retry.'

class History:
    def __init__(self,path):self.path=Path(path);self.lock=threading.Lock()
    def read(self):
        if not self.path.exists():return []
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data,list) or any(not isinstance(r,dict) for r in data):raise ValueError()
            return data
        except (ValueError,OSError) as exc:
            raise ValueError('History could not be read. Back up or rename history.json to recover.') from exc
    def add(self,title,path,status,**details):
        with self.lock:
            rows=self.read()
            rows=[r for r in rows if r.get('path')!=str(path)]
            rows.insert(0,{'title':title,'path':str(path),'status':status,'time':datetime.now(timezone.utc).isoformat(timespec='seconds'),**details})
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(rows[:100],indent=2),encoding='utf-8')
            temporary.replace(self.path)

class Downloader:
    def __init__(self,history,factory=yt_dlp.YoutubeDL):
        self.history=history;self.factory=factory;self.artwork=ArtworkCache(history.path.parent/'artwork')
    @staticmethod
    def ffmpeg():return shutil.which('ffmpeg')
    def options(self):
        return {'quiet':True,'no_warnings':True,'noplaylist':True,'socket_timeout':15,'retries':2,'fragment_retries':2,'extractor_retries':1,'cachedir':False}
    def inspect(self,url):
        url=validate_url(url)
        with self.factory(self.options()) as ydl:info=ydl.extract_info(url,download=False)
        if not isinstance(info,dict) or info.get('_type') in ('playlist','multi_video'):
            raise ValueError('Choose a single media item, not a playlist.')
        choices={}
        available=[f for f in (info.get('formats') or [info]) if not f.get('has_drm')]
        audio_sources=[f for f in available if f.get('format_id') and f.get('url') and f.get('acodec') not in (None,'none') and f.get('vcodec') in (None,'none')]
        for f in available:
            if f.get('has_drm'):continue
            if f.get('url') and f.get('ext') in ('mp4','webm','mov','mkv') and f.get('vcodec') is None and f.get('acodec') is None:
                choices[f"Original video · {f['ext']} · {f.get('format_id','direct')}"]={'format':str(f.get('format_id') or 'best'),'needs_ffmpeg':False,'kind':'video','group':'Video · '+f['ext'].upper()}
                continue
            video=f.get('vcodec') not in (None,'none')
            audio=f.get('acodec') not in (None,'none') or f.get('ext') in ('wav','mp3','m4a','ogg','flac','opus','aac')
            if not f.get('format_id') or not f.get('url') or not (video or audio):continue
            if video and not audio:
                if not self.ffmpeg() or not audio_sources:continue
                audio_source=max(audio_sources,key=lambda a:(a.get('ext')=='m4a' if f.get('ext')=='mp4' else a.get('ext')==f.get('ext'),a.get('abr') or 0))
                container='mp4' if f.get('ext')=='mp4' and audio_source.get('ext')=='m4a' else 'mkv'
                label=f"{f.get('height') or '?'}p video + audio · {container} · {f['format_id']}"
                choices[label]={'format':str(f['format_id'])+'+'+str(audio_source['format_id']),'needs_ffmpeg':True,'merge_output_format':container,'kind':'video','group':'Video · '+container.upper(),'has_audio':True}
                continue
            kind=f"{f.get('height') or '?'}p video" if video else 'Audio only'
            label=f"{kind} · {f.get('ext','file')} · {f.get('format_id')}"
            choices[label]={'format':str(f['format_id']),'needs_ffmpeg':False,'kind':'video' if video else 'audio','group':('Video · ' if video else 'Audio only · ')+f.get('ext','file').upper(),'has_audio':audio}
        if not choices:raise ValueError('No usable non-DRM single-file formats were found. Install FFmpeg for separate streams.')
        if self.ffmpeg() and any(f.get('acodec') not in (None,'none') or f.get('ext') in ('wav','mp3','m4a','ogg','flac','opus','aac') for f in available):
            choices['MP3 audio · convert with FFmpeg']={'format':'bestaudio/best','needs_ffmpeg':True,'convert':'mp3','kind':'audio','group':'Audio only · MP3'}
        # Prefer video over audio, then the highest listed source resolution.
        choices=dict(sorted(choices.items(),key=lambda item:(item[1].get('kind')!='video',-int(re.match(r'(\d+)p',item[0])[1]) if re.match(r'(\d+)p',item[0]) else 0)))
        info['video_needs_ffmpeg']=any(f.get('vcodec') not in (None,'none') for f in available) and not any(c.get('kind')=='video' for c in choices.values())
        info['local_thumbnail'],info['source_artwork'],info['artwork_warning']=self.artwork.get(info.get('thumbnail'),info.get('title','Media'),info.get('ext','media'))
        return info,choices
    def download(self,url,info,choice,folder,cancel,progress):
        validate_url(url)
        if choice.get('needs_ffmpeg') and not self.ffmpeg():raise RuntimeError('FFmpeg missing')
        if cancel.is_set():raise Cancelled()
        folder=Path(folder).expanduser().resolve();folder.mkdir(parents=True,exist_ok=True)
        title=safe_filename(info.get('title','media'))
        identifier=safe_filename(info.get('id','item'))[:24]
        def hook(data):
            if cancel.is_set():raise Cancelled('SUNDROP_CANCEL')
            progress(data)
        options=self.options()
        options.update({'format':choice['format'],'outtmpl':str(folder/f'{title} [{identifier}].%(ext)s'),'windowsfilenames':True,'overwrites':False,'progress_hooks':[hook], 'postprocessor_hooks':[hook]})
        if choice.get('merge_output_format'):options['merge_output_format']=choice['merge_output_format']
        if choice.get('convert')=='mp3':options['postprocessors']=[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]
        with self.factory(options) as ydl:
            result=ydl.extract_info(url,download=True)
            downloaded=result.get('requested_downloads') or []
            path=result.get('filepath') or result.get('_filename') or (downloaded[0].get('filepath') if downloaded else ydl.prepare_filename(result))
            if choice.get('merge_output_format'):
                merged=Path(path).with_suffix('.'+choice['merge_output_format'])
                if merged.is_file():path=str(merged)
            if choice.get('convert')=='mp3':path=str(Path(path).with_suffix('.mp3'))
        # Completion is recorded only after the extractor and processors return.
        path=Path(path)
        if not path.is_file():raise FileNotFoundError('The downloaded file could not be located.')
        streams=probe_media(path)
        if streams and choice.get('kind')=='video' and not streams['has_video']:
            raise MediaValidationError('This source saved audio without video. Choose a Video option and download again; the audio file was kept.')
        if streams and choice.get('has_audio') and not streams['has_audio']:
            raise MediaValidationError('The video has no audio stream. Choose another Video + audio source; the file was kept.')
        thumbnail=info.get('local_thumbnail')
        artist=info.get('artist') or info.get('creator') or info.get('uploader') or ''
        album=info.get('album') or ''
        warning=info.get('artwork_warning');embedded=False
        if not streams and choice.get('kind')=='video':warning='Video stream verification needs FFprobe. The source file was preserved.'
        if thumbnail and Path(thumbnail).is_file():
            # A sidecar keeps artwork together with the file when it is moved.
            sidecar=path.with_name(path.name+'.cover.jpg')
            shutil.copyfile(thumbnail,sidecar);thumbnail=str(sidecar)
        if path.suffix.lower()=='.mp3':
            try:embedded=embed_mp3(path,thumbnail if info.get('source_artwork') else None,info.get('title','media'),artist,album)
            except Exception:warning='Download saved, but optional MP3 tags could not be verified; the original audio was preserved.'
        self.history.add(info.get('title','media'),path,'complete',creator=artist,album=album,duration=(streams or {}).get('duration') or info.get('duration'),format=path.suffix.lstrip('.').lower(),size=path.stat().st_size,thumbnail=thumbnail,source_artwork=bool(info.get('source_artwork')),artwork_embedded=embedded,warning=warning,media_kind='video' if streams and streams['has_video'] else choice.get('kind','audio'),streams_verified=bool(streams))
        return str(path or folder)
