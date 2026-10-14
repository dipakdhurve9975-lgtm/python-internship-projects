"""SunDrop desktop. All network work is in workers; Tk updates use a queue."""
import os
from pathlib import Path
import queue
import threading
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps
from core import Downloader, History, friendly_error
from player import AudioPlayer, VideoPlayer, open_local
from effects import video_effect, cd_landscape

ctk.set_appearance_mode('Light')
BG=('#BCE8E5','#203534');CARD=('#F5EFE2','#293a37');INK=('#282923','#f5efe2');MUTED=('#58635c','#b8cec5');AMBER='#f4bd35';OUTLINE=('#282923','#b8cec5')

def sun_art():
    image=Image.new('RGB',(340,180),'#fff1be');draw=ImageDraw.Draw(image)
    draw.ellipse((125,45,215,135),fill='#f4bd35')
    for x,y,x2,y2 in [(170,16,170,32),(170,148,170,164),(98,90,112,90),(229,90,245,90),(116,37,127,48),(218,133,230,145),(117,144,128,133),(218,48,230,36)]:draw.line((x,y,x2,y2),fill='#b97805',width=5)
    draw.arc((150,77,190,111),0,180,fill='#6b4e13',width=4)
    draw.ellipse((148,73,155,80),fill='#6b4e13');draw.ellipse((185,73,192,80),fill='#6b4e13')
    return image

class SunDrop(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(os.environ.get('SUNDROP_WINDOW_TITLE','SunDrop · your little media shelf'))
        self.geometry('1080x640');self.minsize(860,560);self.configure(fg_color=BG)
        self.events=queue.Queue();self.cancel=threading.Event();self.busy=False;self.info=None;self.choices={};self.inspected_url=None
        # Use one decoder family for the GUI: pygame and FFpyplayer ship different
        # SDL DLL versions on Windows and cannot safely be initialized together.
        self.player=VideoPlayer();self.video_player=VideoPlayer();self.using_video=False;self.player_window=None;self.library_images=[];self.current_track=None
        self.last_frame=None;self.effect_mode='Normal';self.disc_enabled=True;self._frame_after=None
        self.cd_visual=VideoPlayer();self.cd_reference=Path(__file__).resolve().parent/'assets/music-cd-reference.mp4';self.last_cd_frame=None
        data=Path(os.environ.get('SUNDROP_DATA_DIR',Path.home()/'.sundrop'))
        self.service=Downloader(History(data/'history.json'))
        self.folder=ctk.StringVar(value=str(Path.home()/'Downloads'/'SunDrop'))
        self.authorized=ctk.BooleanVar(value=False)
        self.grid_columnconfigure(1,weight=1);self.grid_rowconfigure(1,weight=1)
        top=ctk.CTkFrame(self,fg_color=CARD,corner_radius=10,border_width=2,border_color=OUTLINE,height=42);top.grid(row=0,column=0,columnspan=2,sticky='ew',padx=12,pady=(12,0))
        self.label(top,'▣ SunDrop',18,True).pack(side='left',padx=15,pady=8)
        for name,callback in [('File',self.pick_media),('Downloads',lambda:self.show('History')),('View',self.toggle_theme),('Settings',lambda:self.show('Settings'))]:
            self.button(top,name,callback,width=92,height=30).pack(side='left',padx=3)
        self.button(top,'×',self.close,width=35,height=30).pack(side='right',padx=8)
        self.button(top,'–',self.iconify,width=35,height=30).pack(side='right',padx=3)
        side=ctk.CTkFrame(self,width=176,corner_radius=0,fg_color=BG);side.grid(row=1,column=0,sticky='nsew');side.grid_propagate(False)
        self.label(side,'LOCAL DESKTOP',11,True).pack(pady=(28,16),padx=18,anchor='w')
        for text in ('Download','History','Settings'):
            self.button(side,{'Download':'↓  Download','History':'▤  Library','Settings':'⚙  Settings'}[text],lambda t=text:self.show(t),height=55).pack(fill='x',padx=16,pady=8)
        self.button(side,'♫  Mini player',self.show_player,height=48).pack(fill='x',padx=16,pady=(25,8))
        self.label(side,'Made for media\nyou may download.',12,color=MUTED).pack(side='bottom',pady=30,padx=20,anchor='w')
        self.content=ctk.CTkScrollableFrame(self,fg_color=BG,corner_radius=0);self.content.grid(row=1,column=1,sticky='nsew',padx=(10,22),pady=15)
        self.pages={}
        for name in ('Download','History','Settings'):self.pages[name]=ctk.CTkFrame(self.content,fg_color='transparent')
        self.build_download();self.build_settings();self.show('Download');self.style_inputs(self)
        self.after(100,self.poll)
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.icon_image=ctk.CTkImage(sun_art(),size=(32,32))
        # The icon is drawn from original shapes, independent of any brand assets.
        from PIL import ImageTk
        self._window_icon=ImageTk.PhotoImage(sun_art().resize((64,64)))
        self.iconphoto(True,self._window_icon)

    def label(self,parent,text,size=14,bold=False,color=INK,**kwargs):
        return ctk.CTkLabel(parent,text=text,font=ctk.CTkFont(family='Consolas' if bold or size<=12 else 'Segoe UI',size=size,weight='bold' if bold else 'normal'),text_color=color,justify='left',**kwargs)

    def button(self,parent,text,command,**kwargs):
        return ctk.CTkButton(parent,text=text,command=command,font=ctk.CTkFont(family='Consolas',size=13,weight='bold'),border_width=2,border_color=OUTLINE,corner_radius=7,fg_color=CARD,hover_color=('#a9d9d5','#3d5852'),text_color=INK,**kwargs)

    def style_inputs(self,widget):
        # Apply the retro skin to existing controls without changing their actions.
        for child in widget.winfo_children():
            if isinstance(child,ctk.CTkEntry):child.configure(border_width=2,border_color=OUTLINE,fg_color=CARD,corner_radius=7)
            elif isinstance(child,ctk.CTkButton):child.configure(border_width=2,border_color=OUTLINE,corner_radius=7,font=ctk.CTkFont(family='Consolas',size=13,weight='bold'),fg_color=CARD,hover_color=('#a9d9d5','#3d5852'),text_color=INK)
            self.style_inputs(child)

    def set_theme(self,mode):
        ctk.set_appearance_mode(mode)
        if hasattr(self,'settings_theme'):self.settings_theme.set(mode)
        if hasattr(self,'player_theme') and self.player_theme.winfo_exists():self.player_theme.set(ctk.get_appearance_mode())

    def toggle_theme(self):self.set_theme('Dark' if ctk.get_appearance_mode()=='Light' else 'Light')

    def card(self,parent):
        shadow=ctk.CTkFrame(parent,fg_color=('#282923','#0f201d'),corner_radius=12);shadow.pack(fill='x',pady=10,padx=(0,5));shadow.grid_columnconfigure(0,weight=1)
        frame=ctk.CTkFrame(shadow,fg_color=CARD,corner_radius=10,border_width=2,border_color=OUTLINE);frame.grid(row=0,column=0,sticky='ew',padx=(0,5),pady=(0,5));return frame

    def build_download(self):
        page=self.pages['Download'];self.label(page,'Your download studio.',30,True).pack(anchor='w',pady=(8,2))
        self.label(page,'A quiet corner for media you may keep.',14,color=MUTED).pack(anchor='w',pady=(0,10))
        card=self.card(page);self.label(card,'01  /  FIND YOUR MEDIA',11,True,color=MUTED).pack(anchor='w',padx=22,pady=(20,10))
        row=ctk.CTkFrame(card,fg_color='transparent');row.pack(fill='x',padx=22,pady=(0,14));row.grid_columnconfigure(0,weight=1)
        self.url=ctk.CTkEntry(row,placeholder_text='Paste an authorized media URL…',height=46,fg_color=BG,text_color=INK,border_color=('#dbd1b7','#444b40'));self.url.grid(row=0,column=0,sticky='ew',padx=(0,12))
        self.button(row,'Paste',self.paste_url,width=65,height=46).grid(row=0,column=1,padx=(0,8))
        self.preview_button=self.button(row,'Fetch Media',self.preview,width=125,height=46);self.preview_button.grid(row=0,column=2)
        ctk.CTkCheckBox(card,text='I own this media or have permission to download it.',variable=self.authorized,text_color=INK,fg_color='#b97805',hover_color='#ce9e29').pack(anchor='w',padx=22,pady=(0,20))
        card=self.card(page);body=ctk.CTkFrame(card,fg_color='transparent');body.pack(fill='x',padx=22,pady=20);body.grid_columnconfigure(1,weight=1)
        self.art=ctk.CTkImage(sun_art(),size=(170,90));self.thumbnail=ctk.CTkLabel(body,text='',image=self.art);self.thumbnail.grid(row=0,column=0,rowspan=2,padx=(0,22))
        self.title_label=self.label(body,'Your next favorite file.',20,True,wraplength=450);self.title_label.grid(row=0,column=1,sticky='w')
        self.detail_label=self.label(body,'Title, creator and duration will appear here.',13,color=MUTED,wraplength=450);self.detail_label.grid(row=1,column=1,sticky='w')
        card=self.card(page);self.label(card,'02  /  MAKE IT YOURS',11,True,color=MUTED).pack(anchor='w',padx=22,pady=(18,8))
        selectors=ctk.CTkFrame(card,fg_color='transparent');selectors.pack(fill='x',padx=22,pady=6);selectors.grid_columnconfigure(1,weight=1)
        self.label(selectors,'FORMAT',11,True).grid(row=0,column=0,sticky='w',pady=(0,5))
        self.label(selectors,'QUALITY / SOURCE',11,True).grid(row=0,column=1,sticky='w',padx=14,pady=(0,5))
        self.format_type=ctk.CTkOptionMenu(selectors,values=['Original'],command=self.filter_formats,height=42,fg_color=('#BCE8E5','#364e48'),button_color='#526e62',button_hover_color='#3b554a',text_color=INK,width=150);self.format_type.grid(row=1,column=0)
        self.formats=ctk.CTkOptionMenu(selectors,values=['Fetch a URL first'],command=self.selection_note,height=42,fg_color=('#BCE8E5','#364e48'),button_color='#526e62',button_hover_color='#3b554a',text_color=INK);self.formats.grid(row=1,column=1,sticky='ew',padx=(14,0))
        self.selection_hint=self.label(card,'Video keeps the picture. Audio only saves sound.',12,color=MUTED,wraplength=700);self.selection_hint.pack(anchor='w',padx=22,pady=5)
        row=ctk.CTkFrame(card,fg_color='transparent');row.pack(fill='x',padx=22,pady=(8,18));row.grid_columnconfigure(0,weight=1)
        ctk.CTkEntry(row,textvariable=self.folder,height=40,fg_color=BG,text_color=INK).grid(row=0,column=0,sticky='ew',padx=(0,12))
        ctk.CTkButton(row,text='Choose folder',width=125,height=40,fg_color=('#eee3c4','#363c30'),text_color=INK,hover_color=('#e0cea3','#454c3f'),command=self.pick_folder).grid(row=0,column=1)
        self.progress=ctk.CTkProgressBar(page,progress_color='#526e62',fg_color=CARD,border_width=2,border_color=OUTLINE,height=15);self.progress.pack(fill='x',pady=(14,8));self.progress.set(0)
        self.status=self.label(page,'Ready when you are.',13,color=MUTED,wraplength=750);self.status.pack(anchor='w')
        row=ctk.CTkFrame(page,fg_color='transparent');row.pack(fill='x',pady=16)
        self.download_button=ctk.CTkButton(row,text='Download to my shelf ↓',height=47,width=250,fg_color=AMBER,hover_color='#dfab27',text_color='#302a1d',command=self.download);self.download_button.pack(side='left')
        self.cancel_button=ctk.CTkButton(row,text='Cancel',height=47,width=95,fg_color=('#eee3c4','#363c30'),hover_color=('#e0cea3','#454c3f'),text_color=INK,command=lambda:self.cancel.set(),state='disabled');self.cancel_button.pack(side='left',padx=12)
        self.label(page,'Site support and terms can change. Restricted or DRM media is not supported.',11,color=MUTED).pack(anchor='w',pady=5)

    def build_settings(self):
        page=self.pages['Settings'];self.label(page,'Keep things comfortable.',28,True).pack(anchor='w',pady=12)
        card=self.card(page);self.label(card,'Appearance',18,True).pack(anchor='w',padx=24,pady=(24,10))
        self.settings_theme=ctk.CTkSegmentedButton(card,values=['Light','Dark','System'],command=self.set_theme,selected_color='#b97805',selected_hover_color='#a16a09')
        self.settings_theme.set(ctk.get_appearance_mode());self.settings_theme.pack(anchor='w',padx=24,pady=(0,24))
        card=self.card(page);self.label(card,'FFmpeg',18,True).pack(anchor='w',padx=24,pady=(24,10))
        self.label(card,('Detected: '+self.service.ffmpeg()) if self.service.ffmpeg() else 'Not installed. Single-file downloads are still available.',13,color=MUTED,wraplength=650).pack(anchor='w',padx=24,pady=(0,24))
        card=self.card(page)
        self.label(card,'Your privacy and permissions',18,True).pack(anchor='w',padx=24,pady=(24,10))
        self.label(card,'The last 100 files keep their title, creator, format, artwork and UTC date.\nSource URLs, credentials and cookies are not saved in the library.\nOnly save media you own or have permission to download.\nMP3 source artwork is tagged on a verified copy; MP4 uses a sidecar.\nCancel is cooperative. An active merge may not stop immediately.\nThe player supports video and audio. Normal, Pixel and ASCII are display effects; saved files stay unchanged.\nFile opens an existing local video or audio file.',14,color=MUTED,wraplength=660).pack(anchor='w',padx=24,pady=(0,24))

    def show(self,name):
        for page in self.pages.values():page.pack_forget()
        if name=='History':
            page=self.pages[name]
            for widget in page.winfo_children():widget.destroy()
            self.library_images=[]
            self.label(page,'Your local library.',28,True).pack(anchor='w',pady=12)
            self.library_status=self.label(page,'Artwork stays with each download. Missing files are marked below.',13,color=MUTED,wraplength=700);self.library_status.pack(anchor='w')
            try:rows=self.service.history.read()
            except ValueError as exc:self.label(page,str(exc),14,color=MUTED).pack();rows=[]
            if not rows:self.label(page,'No completed downloads yet. Your first one will appear here.',14,color=MUTED).pack(anchor='w',pady=25)
            for item in rows:
                card=self.card(page);top=ctk.CTkFrame(card,fg_color='transparent');top.pack(fill='x',padx=18,pady=18);top.grid_columnconfigure(1,weight=1)
                image=self.cover_image(item.get('thumbnail'),item.get('title','Media'),item.get('format','media'),(90,90));self.library_images.append(image)
                ctk.CTkLabel(top,text='',image=image).grid(row=0,column=0,rowspan=3,padx=(0,18))
                self.label(top,item.get('title','Media'),18,True,wraplength=510).grid(row=0,column=1,sticky='w')
                path=Path(item.get('path',''));exists=path.is_file();size=path.stat().st_size if exists else item.get('size',0)
                kind=item.get('media_kind') or ('audio' if path.suffix.lower() in {'.m4a','.mp3','.wav','.ogg','.aac','.flac','.opus'} else 'media')
                self.label(top,(item.get('creator') or 'Unknown creator')+' · '+kind.upper()+' · '+(item.get('format') or path.suffix.lstrip('.')).upper()+f' · {size/1024/1024:.2f} MB',12,color=MUTED).grid(row=1,column=1,sticky='w')
                self.label(top,item.get('time','')[:19].replace('T',' ')+' UTC · '+('complete' if exists else 'File moved or missing'),12,color=MUTED).grid(row=2,column=1,sticky='w')
                actions=ctk.CTkFrame(card,fg_color='transparent');actions.pack(fill='x',padx=18,pady=(0,18))
                file_button=self.button(actions,'Open File',lambda p=str(path):self.open_item(p),width=110);file_button.pack(side='left',padx=(0,8));file_button.configure(state='normal' if exists else 'disabled')
                self.button(actions,'Open Folder',lambda p=str(path):self.open_item(p,True),width=120).pack(side='left',padx=(0,8))
                if path.suffix.lower() in AudioPlayer.supported|VideoPlayer.supported:
                    play_button=self.button(actions,'Play / Pause',lambda record=item:self.play_item(record),width=130);play_button.pack(side='left');play_button.configure(state='normal' if exists else 'disabled')
                if item.get('warning'):self.label(card,item['warning'],12,color=MUTED,wraplength=660).pack(anchor='w',padx=18,pady=(0,12))
        self.pages[name].pack(fill='both',expand=True)

    def pick_folder(self):
        folder=filedialog.askdirectory(initialdir=str(Path.home()/'Downloads'))
        if folder:self.folder.set(folder)

    def paste_url(self):
        try:value=self.clipboard_get();self.url.delete(0,'end');self.url.insert(0,value.strip())
        except Exception:self.status.configure(text='Clipboard has no text URL. Paste one manually.')

    def filter_formats(self,group):
        values=[label for label in self.choices if self.format_group(label)==group]
        if values:self.formats.configure(values=values);self.formats.set(values[0])
        self.selection_note()

    def selection_note(self,_=None):
        choice=self.choices.get(self.formats.get(),{})
        text='Video download: picture + sound.' if choice.get('kind')=='video' else 'Audio-only download: sound, no video picture.'
        if choice.get('needs_ffmpeg') and choice.get('kind')=='video':text+=' Separate source streams will be merged.'
        self.selection_hint.configure(text=text)

    def format_group(self,label):
        if self.choices.get(label,{}).get('group'):return self.choices[label]['group']
        if 'MP3 audio' in label:return 'MP3 conversion'
        if 'merge with' in label:return 'Merged video'
        parts=label.split(' · ')
        return parts[1].upper() if len(parts)>1 else 'Original'

    def cover_image(self,path,title,extension,size):
        from artwork import placeholder
        try:
            if not path:raise ValueError('No artwork path')
            with Image.open(path) as source:image=source.convert('RGB').copy()
        except (OSError,TypeError,ValueError):image=placeholder(title,extension)
        image=ImageOps.pad(image,size,color='#F5EFE2');return ctk.CTkImage(image,size=size)

    def notice(self,text):
        self.status.configure(text=text)
        if hasattr(self,'library_status') and self.library_status.winfo_exists():self.library_status.configure(text=text)

    def open_item(self,path,folder=False):
        try:open_local(path,folder)
        except Exception as error:self.notice(str(error))

    def play_item(self,item):
        try:
            if self.current_track and self.current_track.get('path')==item.get('path'):self.active_player().toggle()
            else:
                self.player.stop();self.video_player.stop();self.cd_visual.stop();self.last_cd_frame=None;self.last_frame=None
                self.using_video=Path(item['path']).suffix.lower() not in AudioPlayer.supported
                self.active_player().play(item['path'],item.get('duration'));self.current_track=item
            self.show_player();self.update_player()
        except Exception as error:self.notice('Playback unavailable: '+str(error))

    def active_player(self):return self.video_player if self.using_video else self.player

    def pick_media(self):
        path=filedialog.askopenfilename(title='Open a video or audio file',filetypes=[('Media','*.mp4 *.webm *.mkv *.mov *.avi *.mp3 *.wav *.ogg *.m4a *.flac *.aac *.opus'),('All files','*.*')])
        if path:self.play_item({'path':path,'title':Path(path).stem,'thumbnail':str(Path(path).with_name(Path(path).name+'.cover.jpg'))})

    def next_track(self,direction):
        try:
            tracks=[r for r in self.service.history.read() if Path(r.get('path','')).is_file() and Path(r.get('path','')).suffix.lower() in AudioPlayer.supported|VideoPlayer.supported]
            if not tracks:raise ValueError('Open a local media file with File, or download one first.')
            current=next((i for i,r in enumerate(tracks) if self.current_track and r['path']==self.current_track['path']),-1)
            self.current_track=None;self.play_item(tracks[(current+direction)%len(tracks)])
        except Exception as error:self.notice(str(error))

    def show_player(self):
        if self.player_window and self.player_window.winfo_exists():self.player_window.lift();return
        self.player_window=ctk.CTkToplevel(self);self.player_window.title('SunDrop · video & audio player');self.player_window.geometry('740x720');self.player_window.minsize(700,500);self.player_window.configure(fg_color=BG)
        self.player_window.protocol('WM_DELETE_WINDOW',self.close_player)
        window=self.player_window
        body=ctk.CTkScrollableFrame(window,fg_color=BG);body.pack(fill='both',expand=True,padx=10,pady=8)
        card=self.card(body)
        theme_row=ctk.CTkFrame(card,fg_color='transparent');theme_row.pack(fill='x',padx=20,pady=(10,0))
        self.label(theme_row,'APPEARANCE',11,True,color=MUTED).pack(side='left')
        self.player_theme=ctk.CTkSegmentedButton(theme_row,values=['Light','Dark'],command=self.set_theme,selected_color='#526e62')
        self.player_theme.set(ctk.get_appearance_mode());self.player_theme.pack(side='right')
        self.track_title=self.label(card,'Open a video or audio file.',14,True,wraplength=620);self.track_title.pack(padx=15,pady=(12,5))
        self.player_cover=ctk.CTkLabel(card,text='Open a local file below, or choose one from your library.',width=640,height=360,fg_color='#172522',corner_radius=8);self.player_cover.pack(padx=20,pady=5)
        effects=ctk.CTkFrame(card,fg_color='transparent');effects.pack(pady=5)
        self.effect_control=ctk.CTkSegmentedButton(effects,values=['Normal','Pixel','ASCII'],command=self.set_effect,selected_color='#526e62');self.effect_control.set(self.effect_mode);self.effect_control.pack(side='left',padx=8)
        self.disc_toggle=ctk.CTkCheckBox(effects,text='Your CD video (audio)',command=self.toggle_disc,text_color=INK)
        if self.disc_enabled:self.disc_toggle.select()
        self.disc_toggle.pack(side='left',padx=8)
        row=ctk.CTkFrame(card,fg_color='transparent');row.pack(pady=8)
        self.previous_button=self.button(row,'←',lambda:self.next_track(-1),width=55);self.previous_button.pack(side='left',padx=5)
        self.play_button=self.button(row,'Play',self.toggle_playback,width=130);self.play_button.pack(side='left',padx=5)
        self.next_button=self.button(row,'→',lambda:self.next_track(1),width=55);self.next_button.pack(side='left',padx=5)
        self.playback_progress=ctk.CTkProgressBar(card,width=330,progress_color='#526e62',fg_color=BG);self.playback_progress.pack(padx=18,pady=6);self.playback_progress.set(0)
        self.track_time=self.label(card,'00:00 / --:--',11,color=MUTED);self.track_time.pack()
        self.seek_slider=ctk.CTkSlider(card,from_=0,to=1,command=self.seek_media,width=330);self.seek_slider.pack(pady=5);self.seek_slider.set(0)
        row=ctk.CTkFrame(card,fg_color='transparent');row.pack(fill='x',padx=18,pady=(8,18));self.label(row,'VOL',11,True).pack(side='left')
        self.volume_slider=ctk.CTkSlider(row,from_=0,to=1,command=self.set_player_volume,progress_color='#526e62',button_color='#282923');self.volume_slider.set(self.active_player().volume);self.volume_slider.pack(side='left',fill='x',expand=True,padx=10)
        self.button(card,'Open local video / audio',self.pick_media,width=240).pack(pady=(0,10))
        self.label(card,'Display effects only · your saved file stays unchanged.',11,color=MUTED).pack(pady=(0,10))
        if self._frame_after is None:self._frame_after=self.after(20,self.render_player)
        self.update_player()

    def set_player_volume(self,value):
        self.player.set_volume(value);self.video_player.set_volume(value)
        if hasattr(self,'volume_slider') and self.volume_slider.winfo_exists():self.volume_slider.set(float(value))
    def set_effect(self,mode):self.effect_mode=mode;self.draw_frame()
    def toggle_disc(self):
        self.disc_enabled=bool(self.disc_toggle.get())
        if not self.disc_enabled:self.cd_visual.stop();self.last_cd_frame=None
        self.draw_frame()
    def seek_media(self,fraction):
        player=self.active_player();player.seek(float(fraction)*player.duration)
    def close_player(self):
        self.player.stop();self.video_player.stop();self.cd_visual.stop()
        if self._frame_after is not None:self.after_cancel(self._frame_after);self._frame_after=None
        self.player_window.destroy();self.player_window=None
    def draw_frame(self):
        if not self.player_window or not self.player_window.winfo_exists() or not self.current_track:return
        if self.using_video and self.video_player.has_video:
            if self.last_frame is None:return
            image=video_effect(self.last_frame,self.effect_mode)
        elif self.disc_enabled:
            if self.last_cd_frame is None:return
            image=cd_landscape(self.last_cd_frame)
        else:
            try:
                with Image.open(self.current_track.get('thumbnail','')) as cover:image=ImageOps.contain(cover.convert('RGB'),(300,300))
            except (OSError,TypeError):
                self.player_cover.configure(image=None,text='Audio playback · CD video off');return
        self._player_art=ctk.CTkImage(image,size=image.size);self.player_cover.configure(image=self._player_art,text='')
    def render_player(self):
        self._frame_after=None
        if not self.player_window or not self.player_window.winfo_exists():return
        try:
            player=self.active_player();frame=player.frame()
            if self.using_video and self.video_player.has_video:
                if frame is not None:self.last_frame=frame;self.draw_frame()
            elif self.current_track:
                if self.disc_enabled:
                    try:
                        if self.cd_visual.media is None:self.cd_visual.play(self.cd_reference,muted=True,loop=True)
                        should_pause=player.paused or not player.active
                        if self.cd_visual.paused!=should_pause:self.cd_visual.toggle()
                        visual=self.cd_visual.frame()
                        if visual is not None:self.last_cd_frame=visual
                    except Exception:
                        self.cd_visual.stop();self.disc_enabled=False;self.disc_toggle.deselect()
                        self.notice('The CD reference video could not play. Your music can still play normally.')
                self.draw_frame()
        except Exception as error:
            self.active_player().stop();self.notice('Playback error: '+str(error))
        self._frame_after=self.after(40,self.render_player)

    def toggle_playback(self):
        if not self.current_track:self.next_track(1);return
        try:self.active_player().toggle();self.update_player()
        except Exception as error:self.notice(str(error))

    def update_player(self):
        if not self.player_window or not self.player_window.winfo_exists():return
        item=self.current_track or {};player=self.active_player();position=player.position();duration=player.duration
        self.track_title.configure(text=item.get('title','Choose a track from your library.'))
        self.play_button.configure(text='Pause' if player.active and not player.paused else 'Play')
        is_video=self.using_video and self.video_player.has_video
        self.effect_control.configure(state='normal' if is_video else 'disabled')
        self.disc_toggle.configure(state='disabled' if is_video else 'normal')
        self.seek_slider.configure(state='normal' if duration else 'disabled')
        self.seek_slider.set(min(1,position/duration) if duration else 0)
        self.playback_progress.set(min(1,position/duration) if duration else 0)
        self.track_time.configure(text=f'{int(position)//60:02}:{int(position)%60:02} / '+(f'{int(duration)//60:02}:{int(duration)%60:02}' if duration else '--:--'))

    def work(self,task):
        self.busy=True;self.cancel.clear();self.preview_button.configure(state='disabled');self.download_button.configure(state='disabled')
        def worker():
            try:task()
            except Exception as exc:self.events.put(('error',friendly_error(exc)))
            finally:self.events.put(('idle',None))
        threading.Thread(target=worker,daemon=True).start()

    def preview(self):
        if self.busy:return
        if not self.authorized.get():self.status.configure(text='Confirm permission before contacting the media source.');return
        url=self.url.get();self.info=None;self.inspected_url=None;self.status.configure(text='Looking up metadata…');self.progress.set(0)
        def task():
            info,choices=self.service.inspect(url)
            self.events.put(('metadata',(url,info,choices)))
        self.work(task)

    def download(self):
        if self.busy:return
        if not self.authorized.get():self.status.configure(text='Please confirm that you may download this media.');return
        if not self.info or self.url.get()!=self.inspected_url:self.status.configure(text='Preview this URL before downloading.');return
        choice=self.choices.get(self.formats.get())
        if not choice:return
        url,info,folder=self.url.get(),self.info,self.folder.get()
        self.status.configure(text='Starting download…');self.progress.set(0);self.cancel_button.configure(state='normal')
        def task():
            path=self.service.download(url,info,choice,folder,self.cancel,lambda data:self.events.put(('progress',data)))
            self.events.put(('complete',path))
        self.work(task)

    def poll(self):
        for _ in range(100):
            try:kind,data=self.events.get_nowait()
            except queue.Empty:break
            if kind=='metadata':
                self.inspected_url,self.info,self.choices=data
                self.title_label.configure(text=self.info.get('title','Untitled media'))
                seconds=self.info.get('duration');creator=self.info.get('artist') or self.info.get('uploader') or 'Unknown creator';self.detail_label.configure(text=f"{creator}\n{seconds or 'Unknown'} seconds · {len(self.choices)} source choices")
                groups=list(dict.fromkeys(self.format_group(label) for label in self.choices));self.format_type.configure(values=groups);self.format_type.set(groups[0]);self.filter_formats(groups[0]);self.status.configure(text='Video needs FFmpeg to combine picture and sound. Only audio is available until it is installed.' if self.info.get('video_needs_ffmpeg') else 'Media ready. Video includes visuals; Audio only saves sound.')
                self.art=self.cover_image(self.info.get('local_thumbnail'),self.info.get('title','Media'),self.info.get('ext','media'),(170,110));self.thumbnail.configure(image=self.art)
            elif kind=='thumbnail':self.art=ctk.CTkImage(data,size=(170,90));self.thumbnail.configure(image=self.art)
            elif kind=='progress':
                total=data.get('total_bytes') or data.get('total_bytes_estimate') or 0
                done=data.get('downloaded_bytes',0);ratio=min(1,done/total) if total else 0
                self.progress.set(ratio);speed=data.get('speed') or 0
                self.status.configure(text=(f'{ratio:.0%}' if total else f'{done/1024:.0f} KB')+f' · {speed/1024:.0f} KB/s · '+('Finishing / processing…' if data.get('status')=='finished' else 'Downloading…'))
            elif kind=='complete':self.progress.set(1);self.status.configure(text='Saved to your shelf: '+data)
            elif kind=='error':self.status.configure(text=data)
            elif kind=='idle':self.busy=False;self.preview_button.configure(state='normal');self.download_button.configure(state='normal');self.cancel_button.configure(state='disabled')
        if self.player_window and self.player_window.winfo_exists():self.update_player()
        self.after(100,self.poll)

    def close(self):
        self.cancel.set();self.player.stop();self.video_player.stop();self.cd_visual.stop()
        if self._frame_after is not None:self.after_cancel(self._frame_after);self._frame_after=None
        self.destroy()

if __name__=='__main__':SunDrop().mainloop()
