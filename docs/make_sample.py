"""Create our own tiny test recording. No copyrighted media needed."""
import math
from pathlib import Path
import struct
import wave

def create_sample(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    path=folder/'sundrop-original-tone.wav'
    rate=16000
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate)
        stream.writeframes(b''.join(struct.pack('<h',int(3000*math.sin(2*math.pi*440*i/rate))) for i in range(rate*2)))
    return path

if __name__=='__main__':
    print(create_sample(Path(__file__).parent/'evidence'/'runtime'/'sample'))
    print('Then run: python -m http.server 8765 --bind 127.0.0.1 --directory docs/evidence/runtime/sample')
    print('Authorized URL: http://127.0.0.1:8765/sundrop-original-tone.wav')
