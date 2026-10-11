"""Reproducible vendor fetch, only our chosen JS and license are extracted."""
import hashlib
import io
from pathlib import Path
import tarfile
import urllib.request
target=Path(__file__).resolve().parents[1]/'mathduel-lan'/'static'/'vendor'
target.mkdir(parents=True,exist_ok=True)
url='https://registry.npmjs.org/socket.io-client/-/socket.io-client-4.8.1.tgz'
with urllib.request.urlopen(url,timeout=25) as response:raw=response.read(4_000_000)
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
    for member,name in [('package/dist/socket.io.min.js','socket.io.min.js'),('package/LICENSE','SOCKET_IO_LICENSE.txt')]:
        data=archive.extractfile(member).read();(target/name).write_bytes(data)
(target/'SOURCE.txt').write_text(f'Socket.IO client 4.8.1\nSource: {url}\nTarball SHA256: {hashlib.sha256(raw).hexdigest()}\nMIT license in SOCKET_IO_LICENSE.txt\n',encoding='utf-8')
print('Vendored Socket.IO client and MIT license.')
