"""Open the repaired downloader for the user's scroll check, without a network request."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'sundrop'))
from app import SunDrop
app=SunDrop();app.geometry('1080x640+20+20');app.set_theme('Dark')
app.url.insert(0,'https://youtu.be/yDtCh2D8gog')
app.notice('Scroll up and down to check the text. Fetch Media remains available when you are ready.')
app.after(300,app.focus_force)
app.mainloop()
