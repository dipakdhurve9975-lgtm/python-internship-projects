"""Read-only stream inspection; effects never write to the original file."""
import json
from pathlib import Path
import shutil
import subprocess

class MediaValidationError(ValueError): pass

def probe_media(path):
    executable=shutil.which('ffprobe')
    if not executable:return None
    result=subprocess.run([executable,'-v','error','-show_streams','-show_format','-of','json',str(Path(path))],capture_output=True,text=True,timeout=30,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise MediaValidationError('The saved file could not be read as media. Try another source quality.')
    data=json.loads(result.stdout);streams=data.get('streams',[])
    video=next((s for s in streams if s.get('codec_type')=='video' and not s.get('disposition',{}).get('attached_pic')),None)
    return {'has_video':bool(video),'has_audio':any(s.get('codec_type')=='audio' for s in streams),
            'width':video.get('width',0) if video else 0,'height':video.get('height',0) if video else 0,
            'duration':float(data.get('format',{}).get('duration') or 0)}
