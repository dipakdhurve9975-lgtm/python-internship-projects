import functools
import http.server
import importlib.util
import sys
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Downloader,History

def test_real_ytdlp_download_of_own_tone(tmp_path):
    sample_script=Path(__file__).resolve().parents[2]/'docs'/'make_sample.py'
    spec=importlib.util.spec_from_file_location('sample',sample_script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=module.create_sample(tmp_path/'source')
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(original.parent))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        url=f'http://127.0.0.1:{server.server_port}/{original.name}'
        service=Downloader(History(tmp_path/'history.json'));progress=[]
        info,choices=service.inspect(url)
        path=service.download(url,info,list(choices.values())[0],tmp_path/'output',threading.Event(),progress.append)
        assert Path(path).read_bytes()==original.read_bytes()
        assert progress and service.history.read()[0]['status']=='complete'
    finally:server.shutdown();server.server_close()
