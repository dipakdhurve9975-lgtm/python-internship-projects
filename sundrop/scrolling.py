"""Native child-window scrolling avoids Windows canvas bitmap-copy artifacts."""
import sys
import tkinter as tk
import customtkinter as ctk

class StableScrollableFrame(ctk.CTkFrame):
    def __init__(self,master,fg_color,**kwargs):
        self._outer=ctk.CTkFrame(master,fg_color=fg_color,corner_radius=0)
        self._outer.grid_columnconfigure(0,weight=1);self._outer.grid_rowconfigure(0,weight=1)
        self._viewport=ctk.CTkFrame(self._outer,fg_color=fg_color,corner_radius=0)
        self._viewport.grid(row=0,column=0,sticky='nsew')
        self._bar=ctk.CTkScrollbar(self._outer,command=self.yview)
        self._bar.grid(row=0,column=1,sticky='ns')
        super().__init__(self._viewport,fg_color=fg_color,corner_radius=0)
        self._offset=0;self._pending=0;self._wheel_job=None;self._layout_job=None;self._layout_state=None
        self.bind('<Configure>',self._schedule_layout,add='+')
        self._viewport.bind('<Configure>',self._schedule_layout,add='+')
        self._wheel_root=self.winfo_toplevel();self._wheel_bindings=[]
        for sequence in ('<MouseWheel>','<Button-4>','<Button-5>'):
            self._wheel_bindings.append((sequence,self._wheel_root.bind(sequence,self._wheel,add='+')))
        tk.Place.place_configure(self,x=0,y=0,relwidth=1)
        self._schedule_layout()

    def grid(self,**kwargs):return self._outer.grid(**kwargs)
    def pack(self,**kwargs):return self._outer.pack(**kwargs)
    def pack_forget(self):return self._outer.pack_forget()

    def _schedule_layout(self,event=None):
        if self._layout_job is None:self._layout_job=self.after_idle(self._layout)

    def _layout(self):
        self._layout_job=None
        width=self._viewport.winfo_width();visible=self._viewport.winfo_height()
        height=max(visible,self.winfo_reqheight())
        self._offset=max(0,min(self._offset,height-visible))
        state=(width,height,round(self._offset))
        if state!=self._layout_state:
            # Move a real child window rather than scrolling a Canvas window item.
            # Tk/Windows repaints exposed child widgets instead of reusing stale pixels.
            tk.Place.place_configure(self,x=0,y=-state[2],width=width,height=height,relwidth=0)
            self._layout_state=state
        self._bar.set(self._offset/height,min(1,(self._offset+visible)/height))

    def yview(self,*args):
        if not args:
            height=max(self._viewport.winfo_height(),self.winfo_reqheight(),1)
            return self._offset/height,min(1,(self._offset+self._viewport.winfo_height())/height)
        height=max(self.winfo_reqheight(),1)
        if args[0]=='moveto':self._offset=float(args[1])*height
        elif args[0]=='scroll':
            step=self._viewport.winfo_height()*.9 if args[2]=='pages' else 48
            self._offset+=float(args[1])*step
        self._schedule_layout()

    def _wheel(self,event):
        widget=event.widget
        while widget is not None:
            if isinstance(widget,(ctk.CTkSlider,ctk.CTkScrollbar,ctk.CTkTextbox)):return
            if widget is self:break
            widget=getattr(widget,'master',None)
        if widget is not self:return
        if getattr(event,'num',None) in (4,5):delta=-48 if event.num==4 else 48
        elif sys.platform=='darwin':delta=-event.delta*8
        else:delta=-event.delta/120*48
        self._pending+=delta
        if self._wheel_job is None:self._wheel_job=self.after(16,self._flush_wheel)

    def _flush_wheel(self):
        self._wheel_job=None;self._offset+=self._pending;self._pending=0
        self._schedule_layout()

    def destroy(self):
        for job in (self._wheel_job,self._layout_job):
            if job is not None:self.after_cancel(job)
        for sequence,binding in self._wheel_bindings:
            try:self._wheel_root.unbind(sequence,binding)
            except tk.TclError:pass
        super().destroy()
        self._outer.destroy()
