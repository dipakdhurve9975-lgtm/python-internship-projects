"""Bounded thumbnail cache and transactional MP3 tags."""
import hashlib
import io
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request
from urllib.parse import urlsplit
from PIL import Image, ImageDraw, ImageFont, ImageOps
from mutagen.id3 import ID3, ID3NoHeaderError, APIC, TIT2, TPE1, TALB
from mutagen.mp3 import MP3

def placeholder(title, extension):
    """An original cover when a source has no usable artwork."""
    image=Image.new('RGB',(640,640),'#BCE8E5');draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((35,35,605,605),radius=25,fill='#F5EFE2',outline='#282923',width=5)
    draw.rectangle((35,100,605,104),fill='#282923')
    try:
        font=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',28)
        large=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',86)
    except OSError:font=ImageFont.load_default(size=28);large=ImageFont.load_default(size=86)
    draw.text((65,52),'SUNDROP / LOCAL MEDIA',font=font,fill='#282923')
    draw.ellipse((225,165,415,355),fill='#F4BD35',outline='#282923',width=5)
    draw.text((279,214),'♪',font=large,fill='#282923')
    words=str(title).replace('\n',' ').split();lines=[];line=''
    for word in words:
        candidate=(line+' '+word).strip()
        if draw.textlength(candidate,font=font)>480 and line:lines.append(line);line=word[:25]
        else:line=candidate
    if line:lines.append(line)
    for i,text in enumerate(lines[:3]):draw.text((65,395+i*38),text[:29],font=font,fill='#282923')
    draw.text((65,550),str(extension or 'MEDIA').upper()[:12]+' / ORIGINAL COVER',font=font,fill='#5a655d')
    return image

class ArtworkCache:
    def __init__(self,folder,fetch=None):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
        self.fetch=fetch or self._fetch
    @staticmethod
    def _fetch(url):
        parsed=urlsplit(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Unsupported artwork URL.')
        request=urllib.request.Request(url,headers={'User-Agent':'SunDrop/1.0'})
        with urllib.request.urlopen(request,timeout=10) as response:data=response.read(4_000_001)
        if len(data)>4_000_000:raise ValueError('Artwork exceeds the size limit.')
        return data
    def get(self,url,title,extension):
        key=hashlib.sha256((url or f'fallback:{title}:{extension}').encode()).hexdigest()
        target=self.folder/(key+'.jpg')
        if target.exists():
            try:
                with Image.open(target) as existing:existing.verify()
                return str(target), bool(url), None
            except (OSError,ValueError):pass
        real=False;warning=None
        if url:
            try:
                data=self.fetch(url)
                if len(data)>4_000_000:raise ValueError('Oversized thumbnail')
                with Image.open(io.BytesIO(data)) as source:
                    if source.width*source.height>20_000_000:raise ValueError('Oversized image')
                    image=ImageOps.exif_transpose(source).convert('RGB');image.thumbnail((640,640))
                real=True
            except Exception:warning='Artwork unavailable; an original placeholder is used.'
        if not real:
            # Cache failed fetches separately. A future preview can retry the URL.
            key=hashlib.sha256(f'fallback:{title}:{extension}'.encode()).hexdigest()
            target=self.folder/(key+'.jpg')
            if target.exists():return str(target),False,warning
            image=placeholder(title,extension)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=self.folder,suffix='.tmp',delete=False) as file:temporary=Path(file.name)
            image.save(temporary,format='JPEG',quality=90)
            temporary.replace(target)
        finally:
            if temporary and temporary.exists():temporary.unlink()
        return str(target),real,warning

def embed_mp3(path,thumbnail,title,artist='',album=''):
    """Edit a copy, verify tags and audio frames, then replace the original."""
    path=Path(path);before=MP3(path)
    expected_length=before.info.length
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.mp3',delete=False) as stream:temporary=Path(stream.name)
        shutil.copy2(path,temporary)
        try:tags=ID3(temporary)
        except ID3NoHeaderError:tags=ID3()
        tags.add(TIT2(encoding=3,text=[title]))
        if artist:tags.add(TPE1(encoding=3,text=[artist]))
        if album:tags.add(TALB(encoding=3,text=[album]))
        # Placeholder covers are useful in the app, but only source art is embedded.
        if thumbnail:
            with Image.open(thumbnail) as source:
                cover=source.convert('RGB');cover.thumbnail((640,640));buf=io.BytesIO();cover.save(buf,'JPEG',quality=90)
            tags.delall('APIC');tags.add(APIC(encoding=3,mime='image/jpeg',type=3,desc='Cover',data=buf.getvalue()))
        tags.save(temporary,v2_version=3)
        result=MP3(temporary);verified=ID3(temporary)
        if abs(result.info.length-expected_length)>.05 or str(verified.get('TIT2'))!=title:
            raise ValueError('MP3 metadata verification failed.')
        if artist and str(verified.get('TPE1'))!=artist:raise ValueError('Artist verification failed.')
        if album and str(verified.get('TALB'))!=album:raise ValueError('Album verification failed.')
        if thumbnail and not verified.getall('APIC'):raise ValueError('Cover verification failed.')
        os.replace(temporary,path)
        return bool(thumbnail)
    finally:
        if temporary and temporary.exists():temporary.unlink()
