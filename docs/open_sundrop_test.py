"""Open the updated app on the user's existing music, paused for a joint test."""
from pathlib import Path
import sys
import time
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'sundrop'))
from app import SunDrop
app=SunDrop();app.geometry('1080x640+20+20')
app.set_player_volume(0)
rows=app.service.history.read()
audio=next((r for r in rows if Path(r.get('path','')).is_file() and Path(r['path']).suffix.lower() in {'.mp3','.m4a','.wav','.ogg','.aac','.flac','.opus'}),None)
def ready():
    if audio:
        app.play_item(audio);app.player_window.geometry('740x720+550+40')
        deadline=time.monotonic()+5
        def pause_when_ready():
            if app.last_cd_frame is not None or time.monotonic()>deadline:
                player=app.active_player()
                if player.active and not player.paused:app.toggle_playback()
                app.set_player_volume(.6);app.notice('Ready for our test. Press Play in the player: your music + the exact CD video you supplied.')
                app.player_window.lift()
                print('READY: music paused; supplied CD reference displayed; press Play.',flush=True)
            else:app.after(100,pause_when_ready)
        app.after(100,pause_when_ready)
    else:app.show_player();app.notice('Choose a local song with Open local video / audio to test your CD visual.')
app.after(300,ready)
app.mainloop()
