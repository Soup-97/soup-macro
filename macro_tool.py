import tkinter as tk
from tkinter import messagebox, filedialog
import threading, time, sys, os, json, subprocess, tempfile, urllib.request, webbrowser
from PIL import Image, ImageTk
from pynput.keyboard import Key, Controller as KbCtrl, Listener as KbListener
from pynput.mouse import Button, Controller as MsCtrl, Listener as MsListener

VERSION     = "1.3"
GITHUB_USER = "FunkelVult"
GITHUB_REPO = "soup-macro"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.txt"
RELEASE_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
GITHUB_URL  = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}"

SPECIAL_KEYS = {
    "enter":Key.enter,"space":Key.space,"tab":Key.tab,"esc":Key.esc,"escape":Key.esc,
    "backspace":Key.backspace,"delete":Key.delete,"up":Key.up,"down":Key.down,
    "left":Key.left,"right":Key.right,
    **{f"f{i}":getattr(Key,f"f{i}") for i in range(1,13)},
}

# ── Paths ─────────────────────────────────────────────────────
def res(p):
    try:    base = sys._MEIPASS
    except: base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, p)

def _cfg_path():
    base = os.path.dirname(sys.executable) if getattr(sys,"frozen",False) \
           else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.json")

def load_cfg():
    try:
        with open(_cfg_path()) as f: return json.load(f)
    except: return {}

def save_cfg(d):
    try:
        with open(_cfg_path(),"w") as f: json.dump(d,f)
    except: pass

# ── Colors ────────────────────────────────────────────────────
BG      = "#0c0c18"
CARD    = "#11112a"
CARD2   = "#17173a"
BORDER  = "#1c1c3c"
BORDER2 = "#272755"
GREEN   = "#34d399"
BLUE    = "#818cf8"
PURPLE  = "#c084fc"
RED     = "#f87171"
ORANGE  = "#fb923c"
AMBER   = "#fbbf24"
TEXT    = "#eef2ff"
MUTED   = "#4a5280"
MUTED2  = "#6b7aaa"
INPUT   = "#0d0d22"
INP_FG  = "#c7d2fe"

# ── Canvas helpers ────────────────────────────────────────────
def rrect(cv, x1, y1, x2, y2, r=10, **kw):
    r = min(r, (x2-x1)//2, (y2-y1)//2)
    pts = (x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
           x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1)
    return cv.create_polygon(pts, smooth=True, **kw)

def ltn(c, a=22):
    return "#{:02x}{:02x}{:02x}".format(
        min(int(c[1:3],16)+a,255), min(int(c[3:5],16)+a,255), min(int(c[5:7],16)+a,255))

# ── Custom Widgets ────────────────────────────────────────────

class RoundBtn(tk.Canvas):
    def __init__(self, parent, text, color, cmd, h=44, r=10, light=False, **kw):
        super().__init__(parent, height=h, highlightthickness=0, bd=0,
                         bg=parent.cget("bg"), cursor="hand2", **kw)
        self._t=text; self._c=color; self._cmd=cmd; self._r=r
        self._fg=TEXT if light else BG; self._hov=False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>",  lambda e: cmd())
        self.bind("<Enter>",     lambda e: self._s(True))
        self.bind("<Leave>",     lambda e: self._s(False))

    def set(self, text=None, color=None):
        if text  is not None: self._t=text
        if color is not None: self._c=color
        self._draw()

    def _s(self,h): self._hov=h; self._draw()

    def _draw(self):
        self.delete("all")
        w,h=self.winfo_width(),self.winfo_height()
        if w<2: return
        c=ltn(self._c) if self._hov else self._c
        rrect(self,0,0,w,h,self._r,fill=c,outline="")
        self.create_text(w//2,h//2,text=self._t,fill=self._fg,font=("Segoe UI",10,"bold"))


class SBtn(tk.Canvas):
    def __init__(self, parent, text, color, cmd, h=28, r=6, light=False, **kw):
        super().__init__(parent, height=h, highlightthickness=0, bd=0,
                         bg=parent.cget("bg"), cursor="hand2", **kw)
        self._t=text; self._c=color; self._cmd=cmd; self._r=r; self._hov=False
        self._fg=TEXT if (light or color==MUTED or color==MUTED2) else BG
        self.configure(width=max(36, len(text)*7+16))
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>",  lambda e: cmd())
        self.bind("<Enter>",     lambda e: self._s(True))
        self.bind("<Leave>",     lambda e: self._s(False))

    def set(self,text=None,color=None):
        if text  is not None: self._t=text
        if color is not None: self._c=color
        self.configure(width=max(36, len(self._t)*7+16))
        self._draw()

    def _s(self,h): self._hov=h; self._draw()

    def _draw(self):
        self.delete("all")
        w,h=self.winfo_width(),self.winfo_height()
        if w<2: return
        c=ltn(self._c,12) if self._hov else self._c
        rrect(self,0,0,w,h,self._r,fill=c,outline="")
        self.create_text(w//2,h//2,text=self._t,fill=self._fg,font=("Segoe UI",8,"bold"))


class TabBar(tk.Frame):
    def __init__(self, parent, tabs, callback, bg=BG):
        super().__init__(parent, bg=bg)
        self._active=0; self._cb=callback; self._cvs=[]; self._data=tabs; self._hov=-1
        cont = tk.Frame(self, bg=CARD2, highlightbackground=BORDER2, highlightthickness=1)
        cont.pack(fill="x", padx=12)
        for i,(icon,label,color) in enumerate(tabs):
            cv = tk.Canvas(cont, height=46, highlightthickness=0, bg=CARD2, cursor="hand2")
            cv.pack(side="left", fill="both", expand=True)
            cv.bind("<Configure>", lambda e,i=i: self._draw(i))
            cv.bind("<Button-1>",  lambda e,i=i: self._click(i))
            cv.bind("<Enter>",     lambda e,i=i: self._hover(i,True))
            cv.bind("<Leave>",     lambda e,i=i: self._hover(i,False))
            self._cvs.append(cv)
        self._redraw()

    def select(self,idx): self._active=idx; self._redraw()
    def _click(self,idx): self.select(idx); self._cb(idx)
    def _hover(self,idx,h): self._hov=idx if h else -1; self._draw(idx)
    def _redraw(self):
        for i in range(len(self._cvs)): self._draw(i)

    def _draw(self,idx):
        cv=self._cvs[idx]; cv.delete("all")
        w,h=cv.winfo_width(),cv.winfo_height()
        if w<2: return
        icon,label,color=self._data[idx]
        active=idx==self._active; hover=self._hov==idx
        if hover and not active:
            cv.create_rectangle(0,0,w,h,fill=CARD,outline="")
        if active:
            # Colored pill indicator at bottom
            rrect(cv,6,h-5,w-6,h,3,fill=color,outline="")
            fg=TEXT; font=("Segoe UI",9,"bold")
        else:
            fg=MUTED2; font=("Segoe UI",9)
        cv.create_text(w//2,h//2-2,text=f"{icon}  {label}",fill=fg,font=font)


class StatusRow(tk.Frame):
    def __init__(self, parent, text, bg=CARD):
        super().__init__(parent, bg=bg)
        self._bg=bg
        self._dot=tk.Canvas(self,width=8,height=8,bg=bg,highlightthickness=0)
        self._dot.pack(side="left",padx=(0,6))
        self._lbl=tk.Label(self,font=("Segoe UI",9,"bold"),bg=bg,fg=RED)
        self._lbl.pack(side="left")
        self.set(text,False)

    def set(self,text,active,rec_mode=False):
        c = RED if not active else (RED if rec_mode else GREEN)
        self._dot.delete("all")
        self._dot.create_oval(0,0,8,8,fill=c,outline="")
        self._lbl.config(text=text,fg=c)


class Divider(tk.Frame):
    def __init__(self,parent,bg=BORDER,**kw):
        super().__init__(parent,bg=bg,height=1,**kw)


# ── Strings ───────────────────────────────────────────────────
S = {
"de": dict(
    tab_spam="SPAM", tab_tame="TAME", tab_macro="MAKROS",
    tab_rec="AUFNAHME", tab_set="EINSTELLUNGEN",
    card_spam="SPAM MODUS", card_tame="TAME MODUS",
    card_macro="EIGENER MAKRO", card_rec="AUFNAHME",
    card_lang="SPRACHE", card_hotkeys="TASTENKÜRZEL",
    card_reset="STANDARDWERTE", card_about="INFO",
    f_key="Taste", f_interval="Intervall (ms)",
    f_tame_key="Tame-Taste", f_wait="Warten (s)", f_press_key="Drück-Taste",
    btn_spam0="▶   Start Spam   (F1)", btn_spam1="⏸   Stop Spam   (F1)",
    btn_tame0="▶   Start Tame   (F2)", btn_tame1="⏸   Stop Tame   (F2)",
    btn_macro0="▶   Start Makro   (F3)", btn_macro1="⏸   Stop Makro   (F3)",
    btn_rec0="⏺   Aufnahme starten   (F4)", btn_rec1="⏹   Aufnahme stoppen   (F4)",
    btn_play0="▶   Abspielen   (F5)", btn_play1="⏸   Abspielen stoppen   (F5)",
    btn_add_key="+ Taste", btn_add_wait="+ Warten",
    btn_up="↑", btn_down="↓", btn_remove="✕ Löschen",
    btn_clear="Alle löschen", btn_save="💾 Speichern", btn_load="📂 Laden",
    btn_del_rec="🗑 Löschen", btn_stop_all="⏹   ALLE STOPPEN   (F12)",
    btn_reset="Auf Standard zurücksetzen",
    btn_github="Auf GitHub öffnen",
    st_stopped="Gestoppt", st_running="Läuft...", st_rec="Aufnahme läuft...",
    st_ok="Aktuell  ✓", st_no_net="Kein Internet", st_fail="Update fehlgeschlagen",
    upd_click="verfügbar  —  klicken zum Update",
    upd_title="Update verfügbar",
    upd_msg="Version {v} ist verfügbar!\n\nJetzt herunterladen und installieren?",
    downloading="Lade herunter...", upd_done="Fertig! Wird neugestartet...",
    tame_after="Warte nach Tame", tame_press="Warte nach Drücken",
    step_key="▶  Taste:", step_wait="⏱  Warten:",
    no_steps="Füge zuerst Schritte hinzu!", confirm_clear="Alle Schritte löschen?",
    save_macro="Makro speichern", load_macro="Makro laden",
    no_rec="Keine Aufnahme vorhanden!", rec_n="{n} Ereignisse aufgezeichnet",
    repeat="Wiederholen:", repeat_hint="(0 = endlos)",
    incl_mouse="Mausbewegungen aufzeichnen",
    save_rec="Aufnahme speichern", load_rec="Aufnahme laden",
    confirm_del="Löschen", hint="Hinweis", error="Fehler",
    key_lbl="Taste:", wait_lbl="Warten (s):",
    evt_key="⌨", evt_click="🖱 Klick", evt_scroll="🖱 Scroll",
    lang_label="Sprache / Language",
    hk_spam="F1", hk_spam_l="Spam umschalten",
    hk_tame="F2", hk_tame_l="Tame umschalten",
    hk_macro="F3", hk_macro_l="Makro umschalten",
    hk_rec="F4", hk_rec_l="Aufnahme umschalten",
    hk_play="F5", hk_play_l="Abspielen umschalten",
    hk_stop="F12", hk_stop_l="Alles stoppen",
    reset_hint="Setzt alle Felder auf ihre Standardwerte zurück.",
    reset_done="Standardwerte wiederhergestellt.",
    about_made="Erstellt von",
    about_ver="Version",
),
"en": dict(
    tab_spam="SPAM", tab_tame="TAME", tab_macro="MACROS",
    tab_rec="RECORD", tab_set="SETTINGS",
    card_spam="SPAM MODE", card_tame="TAME MODE",
    card_macro="CUSTOM MACRO", card_rec="RECORDING",
    card_lang="LANGUAGE", card_hotkeys="HOTKEYS",
    card_reset="RESET DEFAULTS", card_about="ABOUT",
    f_key="Key", f_interval="Interval (ms)",
    f_tame_key="Tame Key", f_wait="Wait (s)", f_press_key="Press Key",
    btn_spam0="▶   Start Spam   (F1)", btn_spam1="⏸   Stop Spam   (F1)",
    btn_tame0="▶   Start Tame   (F2)", btn_tame1="⏸   Stop Tame   (F2)",
    btn_macro0="▶   Start Macro   (F3)", btn_macro1="⏸   Stop Macro   (F3)",
    btn_rec0="⏺   Start Recording   (F4)", btn_rec1="⏹   Stop Recording   (F4)",
    btn_play0="▶   Play   (F5)", btn_play1="⏸   Stop Playing   (F5)",
    btn_add_key="+ Key", btn_add_wait="+ Wait",
    btn_up="↑", btn_down="↓", btn_remove="✕ Delete",
    btn_clear="Clear all", btn_save="💾 Save", btn_load="📂 Load",
    btn_del_rec="🗑 Delete", btn_stop_all="⏹   STOP ALL   (F12)",
    btn_reset="Reset to defaults",
    btn_github="Open on GitHub",
    st_stopped="Stopped", st_running="Running...", st_rec="Recording...",
    st_ok="Up to date  ✓", st_no_net="No Internet", st_fail="Update failed",
    upd_click="available  —  click to update",
    upd_title="Update available",
    upd_msg="Version {v} is available!\n\nDownload and install now?",
    downloading="Downloading...", upd_done="Done! Restarting...",
    tame_after="Waiting after Tame", tame_press="Waiting after Press",
    step_key="▶  Key:", step_wait="⏱  Wait:",
    no_steps="Add steps first!", confirm_clear="Delete all steps?",
    save_macro="Save Macro", load_macro="Load Macro",
    no_rec="No recording available!", rec_n="{n} events recorded",
    repeat="Repeat:", repeat_hint="(0 = endless)",
    incl_mouse="Record mouse movements",
    save_rec="Save Recording", load_rec="Load Recording",
    confirm_del="Delete", hint="Info", error="Error",
    key_lbl="Key:", wait_lbl="Wait (s):",
    evt_key="⌨", evt_click="🖱 Click", evt_scroll="🖱 Scroll",
    lang_label="Sprache / Language",
    hk_spam="F1", hk_spam_l="Toggle Spam",
    hk_tame="F2", hk_tame_l="Toggle Tame",
    hk_macro="F3", hk_macro_l="Toggle Macro",
    hk_rec="F4", hk_rec_l="Toggle Recording",
    hk_play="F5", hk_play_l="Toggle Playback",
    hk_stop="F12", hk_stop_l="Stop everything",
    reset_hint="Resets all fields to their default values.",
    reset_done="Default values restored.",
    about_made="Created by",
    about_ver="Version",
),
}


class MacroApp:
    def __init__(self, root, lang="de"):
        self.root=root; self.lang=lang
        self.root.title("Soup Macro")
        self.root.geometry("520x720")
        self.root.resizable(False,False)
        self.root.configure(bg=BG)

        self.spam_running=False; self.tame_running=False
        self.macro_running=False; self.rec_running=False; self.play_running=False
        self.tame_phase=""; self.tame_cd=0.0
        self.macro_steps=[]; self.recording=[]
        self._rec_start=0.0; self._last_move=0.0
        self.kb=KbCtrl(); self.ms=MsCtrl()
        self._kb_rec=None; self._ms_rec=None

        self._load_icons()
        self._build()
        self._hotkeys()
        self._tick()
        threading.Thread(target=self._check_update,daemon=True).start()

    def t(self,k): return S[self.lang].get(k,k)

    # ── Icons ──────────────────────────────────────────────
    def _load_icons(self):
        self.logo_tk=self.icon_tk=None
        try:
            raw=Image.open(res("logo.png")).convert("RGBA")
            self.logo_tk=ImageTk.PhotoImage(raw.resize((48,48),Image.NEAREST))
            self.icon_tk=ImageTk.PhotoImage(raw.resize((32,32),Image.NEAREST))
            self.root.iconphoto(True,self.icon_tk)
        except: pass

    # ── Build ──────────────────────────────────────────────
    def _build(self):
        # ── Header ──────────────────────────────────────
        hdr=tk.Frame(self.root,bg=BG)
        hdr.pack(fill="x",padx=18,pady=(18,6))

        if self.logo_tk:
            tk.Label(hdr,image=self.logo_tk,bg=BG).pack(side="left",padx=(0,14))

        info=tk.Frame(hdr,bg=BG)
        info.pack(side="left",anchor="center")
        tk.Label(info,text="Soup Macro",font=("Segoe UI",22,"bold"),
                 bg=BG,fg=TEXT).pack(anchor="w")
        tk.Label(info,text="github.com/FunkelVult/soup-macro",
                 font=("Segoe UI",8),bg=BG,fg=MUTED).pack(anchor="w")

        tr=tk.Frame(hdr,bg=BG)
        tr.pack(side="right",anchor="ne")
        self.upd_lbl=tk.Label(tr,text=f"v{VERSION}  ·  ...",
                               font=("Segoe UI",8),bg=BG,fg=MUTED,cursor="arrow")
        self.upd_lbl.pack(anchor="e")

        Divider(self.root).pack(fill="x",padx=18,pady=(8,0))

        # ── Tab bar ─────────────────────────────────────
        tabs=[
            ("⚡",self.t("tab_spam"),  GREEN),
            ("🎯",self.t("tab_tame"),  BLUE),
            ("🛠",self.t("tab_macro"), PURPLE),
            ("⏺",self.t("tab_rec"),   RED),
            ("⚙",self.t("tab_set"),   AMBER),
        ]
        self._tabbar=TabBar(self.root,tabs,self._show_tab)
        self._tabbar.pack(fill="x",pady=(10,0))

        # ── Content area (all frames stacked via grid) ───
        self._cont=tk.Frame(self.root,bg=BG)
        self._cont.pack(fill="both",expand=True)
        self._cont.grid_rowconfigure(0,weight=1)
        self._cont.grid_columnconfigure(0,weight=1)

        keys=["spam","tame","macro","rec","settings"]
        self._frames={k:tk.Frame(self._cont,bg=BG) for k in keys}
        for f in self._frames.values():
            f.grid(row=0,column=0,sticky="nsew")

        self._build_spam(self._frames["spam"])
        self._build_tame(self._frames["tame"])
        self._build_macro(self._frames["macro"])
        self._build_record(self._frames["rec"])
        self._build_settings(self._frames["settings"])

        # ── Always-visible Stop button ───────────────────
        bot=tk.Frame(self.root,bg=BG)
        bot.pack(fill="x",padx=12,pady=(4,12))
        RoundBtn(bot,self.t("btn_stop_all"),RED,self.stop_all,h=42,light=True).pack(fill="x")

        self._show_tab(0)

    def _show_tab(self,idx):
        keys=["spam","tame","macro","rec","settings"]
        self._frames[keys[idx]].tkraise()

    # ── Card ───────────────────────────────────────────────
    def _card(self,parent,title,accent=BLUE):
        outer=tk.Frame(parent,bg=BORDER2,padx=1,pady=1)
        outer.pack(fill="x",padx=12,pady=(10,4))
        inner=tk.Frame(outer,bg=CARD)
        inner.pack(fill="both",expand=True)
        hrow=tk.Frame(inner,bg=CARD)
        hrow.pack(fill="x",padx=16,pady=(12,8))
        dot=tk.Canvas(hrow,width=8,height=8,bg=CARD,highlightthickness=0)
        dot.create_oval(0,0,8,8,fill=accent,outline="")
        dot.pack(side="left",padx=(0,8))
        tk.Label(hrow,text=title,font=("Segoe UI",8,"bold"),bg=CARD,fg=MUTED2).pack(side="left")
        Divider(inner,bg=BORDER).pack(fill="x",padx=16,pady=(0,10))
        return inner

    def _field(self,parent,label,attr,default,spin=None,w=10):
        f=tk.Frame(parent,bg=CARD)
        tk.Label(f,text=label,font=("Segoe UI",8),bg=CARD,fg=MUTED2).pack(anchor="w",pady=(0,3))
        wrap=tk.Frame(f,bg=INPUT,highlightbackground=BORDER2,highlightthickness=1)
        wrap.pack(fill="x")
        kw=dict(font=("Segoe UI",10),bg=INPUT,fg=INP_FG,relief="flat",
                insertbackground=TEXT,bd=0,width=w)
        if spin:
            lo,hi,inc=spin
            var=tk.DoubleVar(value=default) if isinstance(default,float) else tk.IntVar(value=default)
            wgt=tk.Spinbox(wrap,from_=lo,to=hi,increment=inc,textvariable=var,
                           buttonbackground=BORDER2,**kw)
        else:
            var=tk.StringVar(value=str(default))
            wgt=tk.Entry(wrap,textvariable=var,**kw)
        wgt.pack(fill="x",ipady=6,padx=8)
        setattr(self,attr,var)
        return f

    def _inrow(self,parent,*fields):
        row=tk.Frame(parent,bg=CARD)
        row.pack(fill="x",padx=16,pady=(0,12))
        for i,(lbl,attr,default,spin) in enumerate(fields):
            self._field(row,lbl,attr,default,spin).pack(side="left",padx=(0,20) if i<len(fields)-1 else 0)
        return row

    # ── SPAM tab ───────────────────────────────────────────
    def _build_spam(self,p):
        c=self._card(p,self.t("card_spam"),GREEN)
        self._inrow(c,
            (self.t("f_key"),"spam_key","1",None),
            (self.t("f_interval"),"spam_interval",10,(1,5000,1)),
        )
        self.spam_btn=RoundBtn(c,self.t("btn_spam0"),GREEN,self.toggle_spam)
        self.spam_btn.pack(fill="x",padx=16,pady=(0,10))
        self.spam_st=StatusRow(c,self.t("st_stopped"))
        self.spam_st.pack(padx=16,pady=(0,14),anchor="w")

    # ── TAME tab ───────────────────────────────────────────
    def _build_tame(self,p):
        c=self._card(p,self.t("card_tame"),BLUE)
        self._inrow(c,
            (self.t("f_tame_key"),"tame_key","2",None),
            (self.t("f_wait"),"tame_wait1",7.0,(0.5,120,0.5)),
        )
        self._inrow(c,
            (self.t("f_press_key"),"press_key","1",None),
            (self.t("f_wait"),"tame_wait2",3.0,(0.5,120,0.5)),
        )
        self.tame_btn=RoundBtn(c,self.t("btn_tame0"),BLUE,self.toggle_tame)
        self.tame_btn.pack(fill="x",padx=16,pady=(0,10))
        self.tame_st=StatusRow(c,self.t("st_stopped"))
        self.tame_st.pack(padx=16,anchor="w")
        self.cd_lbl=tk.Label(c,text="",font=("Segoe UI",9),bg=CARD,fg=ORANGE)
        self.cd_lbl.pack(padx=16,pady=(4,14),anchor="w")

    # ── MACRO tab ──────────────────────────────────────────
    def _build_macro(self,p):
        c=self._card(p,self.t("card_macro"),PURPLE)

        # Step list
        lw=tk.Frame(c,bg=INPUT,highlightbackground=BORDER2,highlightthickness=1)
        lw.pack(fill="x",padx=16,pady=(0,8))
        self.step_list=tk.Listbox(lw,bg=INPUT,fg=TEXT,
            selectbackground=PURPLE,selectforeground=BG,
            font=("Segoe UI",9),relief="flat",height=5,borderwidth=0,activestyle="none")
        sbl=tk.Scrollbar(lw,orient="vertical",command=self.step_list.yview,bg=BORDER)
        self.step_list.config(yscrollcommand=sbl.set)
        self.step_list.pack(side="left",fill="both",expand=True)
        sbl.pack(side="right",fill="y")

        # Controls
        ctrl=tk.Frame(c,bg=CARD); ctrl.pack(fill="x",padx=16,pady=(0,10))
        for txt,col,cmd in [(self.t("btn_up"),BORDER2,self._step_up),
                             (self.t("btn_down"),BORDER2,self._step_down),
                             (self.t("btn_remove"),RED,self._step_remove),
                             (self.t("btn_clear"),BORDER2,self._step_clear)]:
            SBtn(ctrl,txt,col,cmd,light=True).pack(side="left",padx=(0,4))

        # Add step rows
        add=tk.Frame(c,bg=CARD); add.pack(fill="x",padx=16,pady=(0,8))
        rk=tk.Frame(add,bg=CARD); rk.pack(fill="x",pady=3)
        tk.Label(rk,text=self.t("key_lbl"),font=("Segoe UI",8),
                 bg=CARD,fg=MUTED2,width=9,anchor="w").pack(side="left")
        self.new_key=tk.StringVar(value="1")
        wk=tk.Frame(rk,bg=INPUT,highlightbackground=BORDER2,highlightthickness=1)
        wk.pack(side="left",padx=(0,8))
        tk.Entry(wk,textvariable=self.new_key,width=7,font=("Segoe UI",10),
                 bg=INPUT,fg=INP_FG,relief="flat",insertbackground=TEXT,bd=0).pack(ipady=5,padx=6)
        SBtn(rk,self.t("btn_add_key"),GREEN,self._step_add_key).pack(side="left")

        rw=tk.Frame(add,bg=CARD); rw.pack(fill="x",pady=3)
        tk.Label(rw,text=self.t("wait_lbl"),font=("Segoe UI",8),
                 bg=CARD,fg=MUTED2,width=9,anchor="w").pack(side="left")
        self.new_wait=tk.DoubleVar(value=1.0)
        ww=tk.Frame(rw,bg=INPUT,highlightbackground=BORDER2,highlightthickness=1)
        ww.pack(side="left",padx=(0,8))
        tk.Spinbox(ww,from_=0.1,to=60,increment=0.5,textvariable=self.new_wait,
                   width=7,font=("Segoe UI",10),bg=INPUT,fg=INP_FG,
                   relief="flat",buttonbackground=BORDER2,insertbackground=TEXT,
                   bd=0).pack(ipady=5,padx=6)
        SBtn(rw,self.t("btn_add_wait"),BLUE,self._step_add_wait).pack(side="left")

        Divider(c,bg=BORDER).pack(fill="x",padx=16,pady=(6,10))

        # Repeat + Save/Load
        bot=tk.Frame(c,bg=CARD); bot.pack(fill="x",padx=16,pady=(0,10))
        tk.Label(bot,text=self.t("repeat"),font=("Segoe UI",8),bg=CARD,fg=MUTED2).pack(side="left")
        self.macro_repeat=tk.IntVar(value=0)
        wr=tk.Frame(bot,bg=INPUT,highlightbackground=BORDER2,highlightthickness=1)
        wr.pack(side="left",padx=(6,4))
        tk.Spinbox(wr,from_=0,to=9999,textvariable=self.macro_repeat,
                   width=5,font=("Segoe UI",10),bg=INPUT,fg=INP_FG,
                   relief="flat",buttonbackground=BORDER2,insertbackground=TEXT,
                   bd=0).pack(ipady=4,padx=4)
        tk.Label(bot,text=self.t("repeat_hint"),font=("Segoe UI",8),
                 bg=CARD,fg=MUTED).pack(side="left",padx=(2,12))
        SBtn(bot,self.t("btn_save"),BORDER2,self._macro_save,light=True).pack(side="left",padx=(0,4))
        SBtn(bot,self.t("btn_load"),BORDER2,self._macro_load,light=True).pack(side="left")

        self.macro_btn=RoundBtn(c,self.t("btn_macro0"),PURPLE,self.toggle_macro)
        self.macro_btn.pack(fill="x",padx=16,pady=(0,10))
        self.macro_st=StatusRow(c,self.t("st_stopped"))
        self.macro_st.pack(padx=16,pady=(0,14),anchor="w")

    # ── RECORD tab ─────────────────────────────────────────
    def _build_record(self,p):
        c=self._card(p,self.t("card_rec"),RED)

        self.rec_btn=RoundBtn(c,self.t("btn_rec0"),RED,self.toggle_record,light=True)
        self.rec_btn.pack(fill="x",padx=16,pady=(0,8))

        ir=tk.Frame(c,bg=CARD); ir.pack(fill="x",padx=16,pady=(0,8))
        self.rec_st=StatusRow(ir,self.t("st_stopped")); self.rec_st.pack(side="left")
        self.rec_count=tk.Label(ir,text=self.t("rec_n").format(n=0),
                                 font=("Segoe UI",8),bg=CARD,fg=MUTED2)
        self.rec_count.pack(side="right")

        # Event list
        lw=tk.Frame(c,bg=INPUT,highlightbackground=BORDER2,highlightthickness=1)
        lw.pack(fill="x",padx=16,pady=(0,8))
        self.rec_list=tk.Listbox(lw,bg=INPUT,fg=TEXT,
            selectbackground=BLUE,selectforeground=BG,
            font=("Segoe UI",8),relief="flat",height=5,borderwidth=0,activestyle="none")
        rsb=tk.Scrollbar(lw,orient="vertical",command=self.rec_list.yview,bg=BORDER)
        self.rec_list.config(yscrollcommand=rsb.set)
        self.rec_list.pack(side="left",fill="both",expand=True)
        rsb.pack(side="right",fill="y")

        # Mouse option
        opt=tk.Frame(c,bg=CARD); opt.pack(fill="x",padx=16,pady=(0,6))
        self.incl_mouse=tk.BooleanVar(value=False)
        tk.Checkbutton(opt,text=self.t("incl_mouse"),variable=self.incl_mouse,
                       bg=CARD,fg=TEXT,selectcolor=INPUT,activebackground=CARD,
                       activeforeground=TEXT,font=("Segoe UI",9),relief="flat",
                       cursor="hand2").pack(side="left")

        Divider(c,bg=BORDER).pack(fill="x",padx=16,pady=(4,10))

        bot=tk.Frame(c,bg=CARD); bot.pack(fill="x",padx=16,pady=(0,10))
        tk.Label(bot,text=self.t("repeat"),font=("Segoe UI",8),bg=CARD,fg=MUTED2).pack(side="left")
        self.rec_repeat=tk.IntVar(value=1)
        wr=tk.Frame(bot,bg=INPUT,highlightbackground=BORDER2,highlightthickness=1)
        wr.pack(side="left",padx=(6,4))
        tk.Spinbox(wr,from_=0,to=9999,textvariable=self.rec_repeat,
                   width=5,font=("Segoe UI",10),bg=INPUT,fg=INP_FG,
                   relief="flat",buttonbackground=BORDER2,insertbackground=TEXT,
                   bd=0).pack(ipady=4,padx=4)
        tk.Label(bot,text=self.t("repeat_hint"),font=("Segoe UI",8),
                 bg=CARD,fg=MUTED).pack(side="left",padx=(2,12))
        SBtn(bot,self.t("btn_save"),BORDER2,self._rec_save,light=True).pack(side="left",padx=(0,4))
        SBtn(bot,self.t("btn_load"),BORDER2,self._rec_load,light=True).pack(side="left",padx=(0,4))
        SBtn(bot,self.t("btn_del_rec"),BORDER2,self._rec_clear,light=True).pack(side="left")

        self.play_btn=RoundBtn(c,self.t("btn_play0"),GREEN,self.toggle_play)
        self.play_btn.pack(fill="x",padx=16,pady=(0,10))
        self.play_st=StatusRow(c,self.t("st_stopped"))
        self.play_st.pack(padx=16,pady=(0,14),anchor="w")

    # ── SETTINGS tab ───────────────────────────────────────
    def _build_settings(self,p):
        # Language card
        cl=self._card(p,self.t("card_lang"),AMBER)
        tk.Label(cl,text=self.t("lang_label"),font=("Segoe UI",9),
                 bg=CARD,fg=MUTED2).pack(padx=16,pady=(0,10),anchor="w")
        lr=tk.Frame(cl,bg=CARD); lr.pack(padx=16,pady=(0,14),anchor="w")
        for code,label in [("de","🇩🇪  Deutsch"),("en","🇬🇧  English")]:
            active=code==self.lang
            col=AMBER if active else BORDER2
            RoundBtn(lr,label,col,lambda c=code:self._switch_lang(c),
                     h=36,r=8,light=not active).pack(side="left",padx=(0,8))

        # Hotkeys card
        ch=self._card(p,self.t("card_hotkeys"),BLUE)
        hkeys=[
            (self.t("hk_spam"),GREEN, self.t("hk_spam_l")),
            (self.t("hk_tame"),BLUE,  self.t("hk_tame_l")),
            (self.t("hk_macro"),PURPLE,self.t("hk_macro_l")),
            (self.t("hk_rec"),RED,    self.t("hk_rec_l")),
            (self.t("hk_play"),GREEN, self.t("hk_play_l")),
            (self.t("hk_stop"),ORANGE,self.t("hk_stop_l")),
        ]
        grid=tk.Frame(ch,bg=CARD); grid.pack(fill="x",padx=16,pady=(0,14))
        for i,(key,col,desc) in enumerate(hkeys):
            r,c=divmod(i,2)
            cell=tk.Frame(grid,bg=CARD); cell.grid(row=r,column=c,sticky="w",padx=(0,24),pady=3)
            kb_lbl=tk.Label(cell,text=f" {key} ",font=("Segoe UI",9,"bold"),
                            bg=col,fg=BG,padx=4,pady=2)
            kb_lbl.pack(side="left",padx=(0,8))
            tk.Label(cell,text=desc,font=("Segoe UI",9),bg=CARD,fg=TEXT).pack(side="left")

        # Reset card
        cr=self._card(p,self.t("card_reset"),ORANGE)
        tk.Label(cr,text=self.t("reset_hint"),font=("Segoe UI",9),
                 bg=CARD,fg=MUTED2).pack(padx=16,anchor="w")
        RoundBtn(cr,self.t("btn_reset"),ORANGE,self._reset_defaults,h=36,r=8).pack(
            fill="x",padx=16,pady=(8,14))

        # About card
        ca=self._card(p,self.t("card_about"),PURPLE)
        ab=tk.Frame(ca,bg=CARD); ab.pack(fill="x",padx=16,pady=(0,14))
        if self.logo_tk:
            tk.Label(ab,image=self.logo_tk,bg=CARD).pack(side="left",padx=(0,14))
        ai=tk.Frame(ab,bg=CARD); ai.pack(side="left",anchor="center")
        tk.Label(ai,text="Soup Macro",font=("Segoe UI",14,"bold"),bg=CARD,fg=TEXT).pack(anchor="w")
        tk.Label(ai,text=f"{self.t('about_ver')} {VERSION}",font=("Segoe UI",9),
                 bg=CARD,fg=MUTED2).pack(anchor="w")
        tk.Label(ai,text=f"{self.t('about_made')} FunkelVult",font=("Segoe UI",9),
                 bg=CARD,fg=MUTED2).pack(anchor="w",pady=(2,6))
        RoundBtn(ai,self.t("btn_github"),PURPLE,
                 lambda:webbrowser.open(GITHUB_URL),h=30,r=8).pack(anchor="w")

    # ── Reset defaults ─────────────────────────────────────
    def _reset_defaults(self):
        self.spam_key.set("1"); self.spam_interval.set(10)
        self.tame_key.set("2"); self.tame_wait1.set(7.0)
        self.press_key.set("1"); self.tame_wait2.set(3.0)
        messagebox.showinfo(self.t("hint"),self.t("reset_done"),parent=self.root)

    # ── Recording ──────────────────────────────────────────
    def toggle_record(self):
        if self.rec_running: self._stop_rec()
        else:                self._start_rec()

    def _start_rec(self):
        self.recording.clear(); self._rec_start=time.time(); self._last_move=0.0
        self.rec_running=True
        self.rec_btn.set(self.t("btn_rec1"),ORANGE)
        self.rec_st.set(self.t("st_rec"),True,rec_mode=True)
        self._rec_refresh()

        def on_kp(key):
            if not self.rec_running: return False
            if key==Key.f4: return
            self.recording.append({"type":"key_down","key":_k2s(key),"t":round(time.time()-self._rec_start,4)})
            self.root.after(0,self._rec_refresh)
        def on_kr(key):
            if not self.rec_running: return
            if key==Key.f4: return
            self.recording.append({"type":"key_up","key":_k2s(key),"t":round(time.time()-self._rec_start,4)})
        def on_click(x,y,btn,pressed):
            if not self.rec_running: return
            self.recording.append({"type":"mouse_click","x":x,"y":y,"btn":_b2s(btn),"pressed":pressed,"t":round(time.time()-self._rec_start,4)})
            self.root.after(0,self._rec_refresh)
        def on_move(x,y):
            if not self.rec_running or not self.incl_mouse.get(): return
            now=time.time()
            if now-self._last_move<0.016: return
            self._last_move=now
            self.recording.append({"type":"mouse_move","x":x,"y":y,"t":round(now-self._rec_start,4)})
        def on_scroll(x,y,dx,dy):
            if not self.rec_running: return
            self.recording.append({"type":"mouse_scroll","x":x,"y":y,"dx":dx,"dy":dy,"t":round(time.time()-self._rec_start,4)})
            self.root.after(0,self._rec_refresh)

        self._kb_rec=KbListener(on_press=on_kp,on_release=on_kr)
        self._ms_rec=MsListener(on_click=on_click,on_move=on_move,on_scroll=on_scroll)
        self._kb_rec.daemon=True; self._ms_rec.daemon=True
        self._kb_rec.start(); self._ms_rec.start()

    def _stop_rec(self):
        self.rec_running=False
        for l in (self._kb_rec,self._ms_rec):
            try: l.stop()
            except: pass
        self.rec_btn.set(self.t("btn_rec0"),RED)
        self.rec_st.set(self.t("st_stopped"),False)
        self._rec_refresh()

    def _rec_refresh(self):
        n=len(self.recording)
        self.rec_count.config(text=self.t("rec_n").format(n=n))
        vis=[e for e in self.recording if e["type"]!="mouse_move"]
        self.rec_list.delete(0,tk.END)
        for e in vis[-100:]:
            t_=e["t"]
            if   e["type"]=="key_down":                     self.rec_list.insert(tk.END,f"  {t_:.2f}s   {self.t('evt_key')} {e['key']}")
            elif e["type"]=="mouse_click" and e["pressed"]:  self.rec_list.insert(tk.END,f"  {t_:.2f}s   {self.t('evt_click')} {e['btn']} ({e['x']},{e['y']})")
            elif e["type"]=="mouse_scroll":                  self.rec_list.insert(tk.END,f"  {t_:.2f}s   {self.t('evt_scroll')} dy={e['dy']}")
        self.rec_list.yview_moveto(1.0)

    def _rec_save(self):
        if not self.recording:
            messagebox.showinfo(self.t("hint"),self.t("no_rec"),parent=self.root); return
        p=filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("Recording","*.json")],title=self.t("save_rec"),parent=self.root)
        if p:
            with open(p,"w") as f: json.dump({"repeat":self.rec_repeat.get(),"events":self.recording},f)

    def _rec_load(self):
        p=filedialog.askopenfilename(filetypes=[("Recording","*.json")],
            title=self.t("load_rec"),parent=self.root)
        if p:
            with open(p) as f: data=json.load(f)
            self.recording=data.get("events",[]); self.rec_repeat.set(data.get("repeat",1))
            self._rec_refresh()

    def _rec_clear(self):
        self.recording.clear(); self._rec_refresh()

    # ── Playback ───────────────────────────────────────────
    def toggle_play(self):
        if self.play_running:
            self.play_running=False
            self.play_btn.set(self.t("btn_play0"),GREEN)
            self.play_st.set(self.t("st_stopped"),False)
        else:
            if not self.recording:
                messagebox.showinfo(self.t("hint"),self.t("no_rec"),parent=self.root); return
            self.play_running=True
            self.play_btn.set(self.t("btn_play1"),ORANGE)
            self.play_st.set(self.t("st_running"),True)
            threading.Thread(target=self._play_loop,daemon=True).start()

    def _play_loop(self):
        repeat=self.rec_repeat.get(); count=0
        while self.play_running:
            evts=list(self.recording)
            if not evts: break
            start=time.time()
            for evt in evts:
                if not self.play_running: break
                while self.play_running and time.time()<start+evt["t"]: time.sleep(0.004)
                if self.play_running: self._play_evt(evt)
            count+=1
            if repeat>0 and count>=repeat: break
        self.play_running=False
        self.root.after(0,lambda: self.play_btn.set(self.t("btn_play0"),GREEN))
        self.root.after(0,lambda: self.play_st.set(self.t("st_stopped"),False))

    def _play_evt(self,e):
        try:
            tp=e["type"]
            if   tp=="key_down":    k=_s2k(e["key"]); self.kb.press(k) if k else None
            elif tp=="key_up":      k=_s2k(e["key"]); self.kb.release(k) if k else None
            elif tp=="mouse_click":
                b=_s2b(e["btn"]); self.ms.position=(e["x"],e["y"])
                self.ms.press(b) if e["pressed"] else self.ms.release(b)
            elif tp=="mouse_move":   self.ms.position=(e["x"],e["y"])
            elif tp=="mouse_scroll": self.ms.scroll(e["dx"],e["dy"])
        except: pass

    # ── Macro steps ────────────────────────────────────────
    def _step_add_key(self):
        k=self.new_key.get().strip()
        if k: self.macro_steps.append({"type":"press","key":k}); self._refresh_steps()

    def _step_add_wait(self):
        self.macro_steps.append({"type":"wait","seconds":self.new_wait.get()}); self._refresh_steps()

    def _step_up(self):
        s=self.step_list.curselection()
        if not s or s[0]==0: return
        i=s[0]; self.macro_steps[i-1],self.macro_steps[i]=self.macro_steps[i],self.macro_steps[i-1]
        self._refresh_steps(); self.step_list.select_set(i-1)

    def _step_down(self):
        s=self.step_list.curselection()
        if not s or s[0]>=len(self.macro_steps)-1: return
        i=s[0]; self.macro_steps[i],self.macro_steps[i+1]=self.macro_steps[i+1],self.macro_steps[i]
        self._refresh_steps(); self.step_list.select_set(i+1)

    def _step_remove(self):
        s=self.step_list.curselection()
        if s: del self.macro_steps[s[0]]; self._refresh_steps()

    def _step_clear(self):
        if messagebox.askyesno(self.t("confirm_del"),self.t("confirm_clear"),parent=self.root):
            self.macro_steps.clear(); self._refresh_steps()

    def _refresh_steps(self):
        self.step_list.delete(0,tk.END)
        for i,s in enumerate(self.macro_steps,1):
            if s["type"]=="press": self.step_list.insert(tk.END,f"  {i}.   {self.t('step_key')}  {s['key']}")
            else:                  self.step_list.insert(tk.END,f"  {i}.   {self.t('step_wait')}  {s['seconds']}s")

    def _macro_save(self):
        p=filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("Macro","*.json")],title=self.t("save_macro"),parent=self.root)
        if p:
            with open(p,"w") as f: json.dump({"repeat":self.macro_repeat.get(),"steps":self.macro_steps},f,indent=2)

    def _macro_load(self):
        p=filedialog.askopenfilename(filetypes=[("Macro","*.json")],
            title=self.t("load_macro"),parent=self.root)
        if p:
            with open(p) as f: data=json.load(f)
            self.macro_steps=data.get("steps",[]); self.macro_repeat.set(data.get("repeat",0))
            self._refresh_steps()

    # ── Toggle Spam / Tame / Macro ─────────────────────────
    def toggle_spam(self):
        if self.spam_running:
            self.spam_running=False
            self.spam_btn.set(self.t("btn_spam0"),GREEN)
            self.spam_st.set(self.t("st_stopped"),False)
        else:
            self.spam_running=True
            self.spam_btn.set(self.t("btn_spam1"),ORANGE)
            self.spam_st.set(self.t("st_running"),True)
            threading.Thread(target=self._spam_loop,daemon=True).start()

    def toggle_tame(self):
        if self.tame_running:
            self.tame_running=False
            self.tame_btn.set(self.t("btn_tame0"),BLUE)
            self.tame_st.set(self.t("st_stopped"),False)
        else:
            self.tame_running=True
            self.tame_btn.set(self.t("btn_tame1"),ORANGE)
            self.tame_st.set(self.t("st_running"),True)
            threading.Thread(target=self._tame_loop,daemon=True).start()

    def toggle_macro(self):
        if self.macro_running:
            self.macro_running=False
            self.macro_btn.set(self.t("btn_macro0"),PURPLE)
            self.macro_st.set(self.t("st_stopped"),False)
        else:
            if not self.macro_steps:
                messagebox.showinfo(self.t("hint"),self.t("no_steps"),parent=self.root); return
            self.macro_running=True
            self.macro_btn.set(self.t("btn_macro1"),ORANGE)
            self.macro_st.set(self.t("st_running"),True)
            threading.Thread(target=self._macro_loop,daemon=True).start()

    def stop_all(self):
        self.spam_running=self.tame_running=self.macro_running=False
        self.rec_running=self.play_running=False
        for l in (self._kb_rec,self._ms_rec):
            try: l.stop()
            except: pass
        self.root.after(0,self._ui_reset)

    def _ui_reset(self):
        self.spam_btn.set(self.t("btn_spam0"),GREEN);  self.spam_st.set(self.t("st_stopped"),False)
        self.tame_btn.set(self.t("btn_tame0"),BLUE);   self.tame_st.set(self.t("st_stopped"),False)
        self.cd_lbl.config(text="")
        self.macro_btn.set(self.t("btn_macro0"),PURPLE); self.macro_st.set(self.t("st_stopped"),False)
        self.rec_btn.set(self.t("btn_rec0"),RED);       self.rec_st.set(self.t("st_stopped"),False)
        self.play_btn.set(self.t("btn_play0"),GREEN);   self.play_st.set(self.t("st_stopped"),False)

    # ── Loops ──────────────────────────────────────────────
    def _spam_loop(self):
        while self.spam_running:
            try: self.kb.tap(self.spam_key.get())
            except: pass
            time.sleep(self.spam_interval.get()/1000.0)

    def _tame_loop(self):
        while self.tame_running:
            try: self.kb.tap(self.tame_key.get())
            except: pass
            self.tame_phase="tame"; self._tw(self.tame_wait1.get())
            if not self.tame_running: break
            try: self.kb.tap(self.press_key.get())
            except: pass
            self.tame_phase="press"; self._tw(self.tame_wait2.get())
        self.tame_phase=""; self.tame_cd=0.0

    def _tw(self,s):
        end=time.time()+s
        while self.tame_running and time.time()<end:
            self.tame_cd=end-time.time(); time.sleep(0.05)

    def _macro_loop(self):
        repeat=self.macro_repeat.get(); count=0
        while self.macro_running:
            for step in self.macro_steps:
                if not self.macro_running: break
                if step["type"]=="press":
                    try:
                        k=SPECIAL_KEYS.get(step["key"].lower())
                        self.kb.tap(k if k else step["key"][0])
                    except: pass
                else:
                    end=time.time()+step["seconds"]
                    while self.macro_running and time.time()<end: time.sleep(0.05)
            count+=1
            if repeat>0 and count>=repeat: break
        self.macro_running=False
        self.root.after(0,lambda: self.macro_btn.set(self.t("btn_macro0"),PURPLE))
        self.root.after(0,lambda: self.macro_st.set(self.t("st_stopped"),False))

    # ── Tick ───────────────────────────────────────────────
    def _tick(self):
        if self.tame_running and self.tame_phase:
            lbl=self.t("tame_after") if self.tame_phase=="tame" else self.t("tame_press")
            f=max(0,min(10,round(self.tame_cd/10*10)))
            self.cd_lbl.config(text=f"{lbl}  ·  {self.tame_cd:.1f}s   {'█'*f}{'░'*(10-f)}")
        else:
            self.cd_lbl.config(text="")
        self.root.after(100,self._tick)

    # ── Hotkeys ────────────────────────────────────────────
    def _hotkeys(self):
        def on_press(key):
            try:
                if   key==Key.f1:  self.root.after(0,self.toggle_spam)
                elif key==Key.f2:  self.root.after(0,self.toggle_tame)
                elif key==Key.f3:  self.root.after(0,self.toggle_macro)
                elif key==Key.f4:  self.root.after(0,self.toggle_record)
                elif key==Key.f5:  self.root.after(0,self.toggle_play)
                elif key==Key.f12: self.root.after(0,self.stop_all)
            except: pass
        lst=KbListener(on_press=on_press); lst.daemon=True; lst.start()

    # ── Language switch ────────────────────────────────────
    def _switch_lang(self,nl):
        if nl==self.lang: return
        cfg=load_cfg(); cfg["lang"]=nl; save_cfg(cfg)
        self.spam_running=self.tame_running=self.macro_running=False
        self.rec_running=self.play_running=False
        self.root.after(120,self._restart)

    def _restart(self):
        self.root.destroy()
        root=tk.Tk()
        MacroApp(root,lang=load_cfg().get("lang","de"))
        root.mainloop()

    # ── Auto-Update ────────────────────────────────────────
    def _check_update(self):
        try:
            with urllib.request.urlopen(VERSION_URL,timeout=6) as r:
                latest=r.read().decode().strip()
            if latest!=VERSION: self.root.after(0,lambda: self._upd_avail(latest))
            else: self.root.after(0,lambda: self.upd_lbl.config(
                text=f"v{VERSION}  ·  {self.t('st_ok')}",fg=GREEN))
        except: self.root.after(0,lambda: self.upd_lbl.config(
                text=f"v{VERSION}  ·  {self.t('st_no_net')}",fg=MUTED))

    def _upd_avail(self,latest):
        self.upd_lbl.config(text=f"v{VERSION}  →  v{latest}  {self.t('upd_click')}",
                             fg=AMBER,cursor="hand2")
        self.upd_lbl.bind("<Button-1>",lambda e:self._ask_upd(latest))

    def _ask_upd(self,latest):
        if messagebox.askyesno(self.t("upd_title"),self.t("upd_msg").format(v=latest),parent=self.root):
            self.upd_lbl.config(text=self.t("downloading"),fg=ORANGE,cursor="arrow")
            self.upd_lbl.unbind("<Button-1>")
            threading.Thread(target=lambda:self._download(latest),daemon=True).start()

    def _download(self,latest):
        try:
            req=urllib.request.Request(RELEASE_URL,headers={"Accept":"application/vnd.github+json"})
            with urllib.request.urlopen(req,timeout=15) as r: data=json.loads(r.read())
            url=next((a["browser_download_url"] for a in data.get("assets",[])
                      if a["name"]=="SoupMacro.exe"),None)
            if not url: raise RuntimeError("SoupMacro.exe not found in release.")
            exe=sys.executable; new=exe+".new"
            def _p(c,b,tot):
                if tot>0:
                    pct=min(100,int(c*b*100/tot))
                    self.root.after(0,lambda p=pct:self.upd_lbl.config(
                        text=f"{self.t('downloading')} {p}%",fg=ORANGE))
            urllib.request.urlretrieve(url,new,reporthook=_p)
            bat=tempfile.mktemp(suffix=".bat")
            with open(bat,"w") as f:
                f.write(f'@echo off\ntimeout /t 2 /nobreak>nul\nmove /y "{new}" "{exe}"\nstart "" "{exe}"\ndel "%~f0"\n')
            self.root.after(0,lambda:self.upd_lbl.config(text=self.t("upd_done"),fg=GREEN))
            subprocess.Popen(["cmd","/c",bat],creationflags=subprocess.CREATE_NO_WINDOW)
            self.root.after(1500,self.root.destroy)
        except Exception as ex:
            self.root.after(0,lambda:messagebox.showerror(self.t("error"),str(ex),parent=self.root))


# ── Key / Button helpers ──────────────────────────────────────
def _k2s(k):
    try:    return k.char or str(k)
    except: return str(k)

def _s2k(s):
    if not s: return None
    if s.startswith("Key."): return getattr(Key,s[4:],None)
    if len(s)==1: return s
    return SPECIAL_KEYS.get(s.lower())

def _b2s(b): return str(b)
def _s2b(s): return getattr(Button,s.replace("Button.",""),Button.left)


if __name__=="__main__":
    cfg=load_cfg()
    root=tk.Tk()
    MacroApp(root,lang=cfg.get("lang","de"))
    root.mainloop()
