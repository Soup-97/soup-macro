import tkinter as tk
from tkinter import messagebox, filedialog
import threading, time, sys, os, json, subprocess, tempfile, urllib.request
from PIL import Image, ImageTk
from pynput.keyboard import Key, Controller as KbCtrl, Listener as KbListener
from pynput.mouse import Button, Controller as MsCtrl, Listener as MsListener

VERSION     = "1.2"
GITHUB_USER = "FunkelVult"
GITHUB_REPO = "soup-macro"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.txt"
RELEASE_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

SPECIAL_KEYS = {
    "enter":Key.enter,"space":Key.space,"tab":Key.tab,"esc":Key.esc,"escape":Key.esc,
    "backspace":Key.backspace,"delete":Key.delete,"up":Key.up,"down":Key.down,
    "left":Key.left,"right":Key.right,
    **{f"f{i}": getattr(Key,f"f{i}") for i in range(1,13)},
}

# ── Paths ────────────────────────────────────────────────────
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
    except: return {"lang":"de"}

def save_cfg(d):
    try:
        with open(_cfg_path(),"w") as f: json.dump(d,f)
    except: pass

# ── Color palette ─────────────────────────────────────────────
BG      = "#0c0c18"
CARD    = "#11112a"
CARD2   = "#17173a"
BORDER  = "#1c1c3c"
BORDER2 = "#262650"
GREEN   = "#34d399"
BLUE    = "#818cf8"
PURPLE  = "#c084fc"
RED     = "#f87171"
ORANGE  = "#fb923c"
AMBER   = "#fbbf24"
TEXT    = "#eef2ff"
MUTED   = "#4a5280"
INPUT   = "#0d0d22"
INP_FG  = "#c7d2fe"

# ── Drawing helpers ───────────────────────────────────────────
def rrect(cv, x1, y1, x2, y2, r=10, **kw):
    pts = (x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
           x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1)
    return cv.create_polygon(pts, smooth=True, **kw)

def _ltn(c, a=22):
    return "#{:02x}{:02x}{:02x}".format(
        min(int(c[1:3],16)+a,255), min(int(c[3:5],16)+a,255), min(int(c[5:7],16)+a,255))

# ── Widgets ───────────────────────────────────────────────────

class RoundBtn(tk.Canvas):
    """Full-width rounded button."""
    def __init__(self, parent, text, color, cmd, h=44, r=10, light_fg=False, **kw):
        super().__init__(parent, height=h, highlightthickness=0, bd=0,
                         bg=parent.cget("bg"), cursor="hand2", **kw)
        self._t=text; self._c=color; self._cmd=cmd; self._r=r
        self._fg = TEXT if light_fg else BG
        self._hover=False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>",  lambda e: cmd())
        self.bind("<Enter>",     lambda e: self._sh(True))
        self.bind("<Leave>",     lambda e: self._sh(False))

    def set(self, text=None, color=None):
        if text  is not None: self._t = text
        if color is not None: self._c = color
        self._draw()

    def _sh(self, h): self._hover=h; self._draw()

    def _draw(self):
        self.delete("all")
        w,h = self.winfo_width(), self.winfo_height()
        if w<2: return
        c = _ltn(self._c) if self._hover else self._c
        rrect(self, 0,0, w,h, self._r, fill=c, outline="")
        self.create_text(w//2, h//2, text=self._t, fill=self._fg,
                         font=("Segoe UI",10,"bold"))


class SBtn(tk.Canvas):
    """Small rounded button."""
    def __init__(self, parent, text, color, cmd, h=28, r=6, **kw):
        super().__init__(parent, height=h, highlightthickness=0, bd=0,
                         bg=parent.cget("bg"), cursor="hand2", **kw)
        self._t=text; self._c=color; self._cmd=cmd; self._r=r; self._hover=False
        self._fg = BG if color!=MUTED else TEXT
        self.configure(width=max(44, len(text)*7+16))
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>",  lambda e: cmd())
        self.bind("<Enter>",     lambda e: self._sh(True))
        self.bind("<Leave>",     lambda e: self._sh(False))

    def _sh(self, h): self._hover=h; self._draw()

    def _draw(self):
        self.delete("all")
        w,h = self.winfo_width(), self.winfo_height()
        if w<2: return
        c = _ltn(self._c,15) if self._hover else self._c
        rrect(self, 0,0, w,h, self._r, fill=c, outline="")
        self.create_text(w//2, h//2, text=self._t, fill=self._fg,
                         font=("Segoe UI",8,"bold"))


class TabBar(tk.Frame):
    """Custom tab bar with colored underline indicator."""
    def __init__(self, parent, tabs, callback, bg=BG):
        super().__init__(parent, bg=bg)
        self._active=0; self._cb=callback; self._cvs=[]; self._data=tabs; self._hov=-1
        cont = tk.Frame(self, bg=CARD, highlightbackground=BORDER2, highlightthickness=1)
        cont.pack(fill="x", padx=12)
        for i,(icon,label,color) in enumerate(tabs):
            cv = tk.Canvas(cont, height=46, highlightthickness=0, bg=CARD, cursor="hand2")
            cv.pack(side="left", fill="both", expand=True)
            cv.bind("<Configure>", lambda e,i=i: self._draw(i))
            cv.bind("<Button-1>",  lambda e,i=i: self._click(i))
            cv.bind("<Enter>",     lambda e,i=i: self._hover(i,True))
            cv.bind("<Leave>",     lambda e,i=i: self._hover(i,False))
            self._cvs.append(cv)
        self._redraw_all()

    def select(self, idx):
        self._active=idx; self._redraw_all()

    def _click(self, idx): self.select(idx); self._cb(idx)
    def _hover(self, idx, h): self._hov = idx if h else -1; self._draw(idx)
    def _redraw_all(self):
        for i in range(len(self._cvs)): self._draw(i)

    def _draw(self, idx):
        cv=self._cvs[idx]; cv.delete("all")
        w,h = cv.winfo_width(), cv.winfo_height()
        if w<2: return
        icon,label,color = self._data[idx]
        active = idx==self._active
        if self._hov==idx and not active:
            cv.create_rectangle(0,0,w,h, fill=CARD2, outline="")
        if active:
            cv.create_rectangle(6,h-3,w-6,h, fill=color, outline="")
            fg=TEXT; font=("Segoe UI",9,"bold")
        else:
            fg=MUTED; font=("Segoe UI",9)
        cv.create_text(w//2, h//2-1, text=f"{icon}  {label}", fill=fg, font=font)

# ── Strings ───────────────────────────────────────────────────
S = {
"de": dict(
    tab_spam="SPAM", tab_tame="TAME", tab_macro="MAKROS", tab_rec="AUFNAHME",
    card_spam="SPAM MODUS", card_tame="TAME MODUS",
    card_macro="EIGENER MAKRO", card_rec="AUFNAHME",
    f_key="Taste", f_interval="Intervall (ms)",
    f_tame_key="Tame-Taste", f_wait="Warten (s)", f_press_key="Drück-Taste",
    btn_spam0="▶   Start Spam   (F1)", btn_spam1="⏸   Stop Spam   (F1)",
    btn_tame0="▶   Start Tame   (F2)", btn_tame1="⏸   Stop Tame   (F2)",
    btn_macro0="▶   Start Makro   (F3)", btn_macro1="⏸   Stop Makro   (F3)",
    btn_rec0="⏺   Aufnahme starten   (F4)", btn_rec1="⏹   Aufnahme stoppen   (F4)",
    btn_play0="▶   Abspielen   (F5)", btn_play1="⏸   Stop   (F5)",
    btn_add_key="+ Taste", btn_add_wait="+ Warten",
    btn_up="↑", btn_down="↓", btn_remove="✕ Entfernen",
    btn_clear="Leeren", btn_save="💾 Speichern", btn_load="📂 Laden",
    btn_del_rec="🗑 Löschen", btn_stop_all="⏹   ALLE STOPPEN   (F12)",
    st_stopped="Gestoppt", st_running="Läuft...", st_recording="Aufnahme läuft...",
    st_ok="Aktuell", st_no_net="Kein Internet", st_fail="Update fehlgeschlagen",
    upd_click="verfügbar — klicken",
    upd_title="Update verfügbar", upd_msg="Version {v} verfügbar!\n\nJetzt laden?",
    downloading="Lade herunter...", upd_done="Fertig! Neustart...",
    tame_after="Warte nach Tame", tame_press="Warte nach Drücken",
    step_key="▶  Taste:", step_wait="⏱  Warten:",
    no_steps="Erst Schritte hinzufügen!", confirm_clear="Alle Schritte löschen?",
    save_macro="Makro speichern", load_macro="Makro laden",
    no_rec="Keine Aufnahme!", rec_n="Ereignisse: {n}",
    repeat="Wiederholen:", repeat_hint="0 = endlos",
    incl_mouse="Mausbewegungen aufzeichnen",
    save_rec="Aufnahme speichern", load_rec="Aufnahme laden",
    confirm_del="Löschen", hint="Hinweis", error="Fehler",
    sub="F1 · Spam   F2 · Tame   F3 · Makro   F4 · Aufnahme   F12 · Stop",
    key_lbl="Taste:", wait_lbl="Warten (s):",
    evt_key="⌨", evt_click="🖱 Klick", evt_scroll="🖱 Scroll",
),
"en": dict(
    tab_spam="SPAM", tab_tame="TAME", tab_macro="MACROS", tab_rec="RECORD",
    card_spam="SPAM MODE", card_tame="TAME MODE",
    card_macro="CUSTOM MACRO", card_rec="RECORDING",
    f_key="Key", f_interval="Interval (ms)",
    f_tame_key="Tame Key", f_wait="Wait (s)", f_press_key="Press Key",
    btn_spam0="▶   Start Spam   (F1)", btn_spam1="⏸   Stop Spam   (F1)",
    btn_tame0="▶   Start Tame   (F2)", btn_tame1="⏸   Stop Tame   (F2)",
    btn_macro0="▶   Start Macro   (F3)", btn_macro1="⏸   Stop Macro   (F3)",
    btn_rec0="⏺   Start Recording   (F4)", btn_rec1="⏹   Stop Recording   (F4)",
    btn_play0="▶   Play   (F5)", btn_play1="⏸   Stop   (F5)",
    btn_add_key="+ Key", btn_add_wait="+ Wait",
    btn_up="↑", btn_down="↓", btn_remove="✕ Remove",
    btn_clear="Clear", btn_save="💾 Save", btn_load="📂 Load",
    btn_del_rec="🗑 Delete", btn_stop_all="⏹   STOP ALL   (F12)",
    st_stopped="Stopped", st_running="Running...", st_recording="Recording...",
    st_ok="Up to date", st_no_net="No Internet", st_fail="Update failed",
    upd_click="available — click",
    upd_title="Update available", upd_msg="Version {v} available!\n\nDownload?",
    downloading="Downloading...", upd_done="Done! Restarting...",
    tame_after="Waiting after Tame", tame_press="Waiting after Press",
    step_key="▶  Key:", step_wait="⏱  Wait:",
    no_steps="Add steps first!", confirm_clear="Delete all steps?",
    save_macro="Save Macro", load_macro="Load Macro",
    no_rec="No recording!", rec_n="Events: {n}",
    repeat="Repeat:", repeat_hint="0 = endless",
    incl_mouse="Record mouse movements",
    save_rec="Save Recording", load_rec="Load Recording",
    confirm_del="Delete", hint="Info", error="Error",
    sub="F1 · Spam   F2 · Tame   F3 · Macro   F4 · Record   F12 · Stop",
    key_lbl="Key:", wait_lbl="Wait (s):",
    evt_key="⌨", evt_click="🖱 Click", evt_scroll="🖱 Scroll",
),
}


class MacroApp:
    def __init__(self, root, lang="de"):
        self.root=root; self.lang=lang
        self.root.title("Soup Macro")
        self.root.geometry("500x720")
        self.root.resizable(False,False)
        self.root.configure(bg=BG)

        self.spam_running=False; self.tame_running=False
        self.macro_running=False; self.rec_running=False; self.play_running=False
        self.tame_phase=""; self.tame_cd=0.0
        self.macro_steps=[]; self.recording=[]
        self._rec_start=0.0; self._last_move=0.0
        self.kb=KbCtrl(); self.ms=MsCtrl()

        self._load_icons()
        self._build()
        self._hotkeys()
        self._tick()
        threading.Thread(target=self._check_update, daemon=True).start()

    def t(self, k): return S[self.lang].get(k, k)

    # ── Icons ─────────────────────────────────────────────
    def _load_icons(self):
        self.logo_tk=self.icon_tk=None
        try:
            raw=Image.open(res("logo.png")).convert("RGBA")
            self.logo_tk=ImageTk.PhotoImage(raw.resize((48,48),Image.NEAREST))
            self.icon_tk=ImageTk.PhotoImage(raw.resize((32,32),Image.NEAREST))
            self.root.iconphoto(True,self.icon_tk)
        except: pass

    # ── Build ─────────────────────────────────────────────
    def _build(self):
        # ── Header ──────────────────────────────────────
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=18, pady=(18,6))

        if self.logo_tk:
            tk.Label(hdr, image=self.logo_tk, bg=BG).pack(side="left", padx=(0,14))

        info = tk.Frame(hdr, bg=BG)
        info.pack(side="left", anchor="center")
        tk.Label(info, text="Soup Macro", font=("Segoe UI",22,"bold"),
                 bg=BG, fg=TEXT).pack(anchor="w")
        self._sub = tk.Label(info, text=self.t("sub"),
                              font=("Segoe UI",8), bg=BG, fg=MUTED)
        self._sub.pack(anchor="w")

        # Lang + update (top-right)
        tr = tk.Frame(hdr, bg=BG)
        tr.pack(side="right", anchor="ne")
        other = "en" if self.lang=="de" else "de"
        SBtn(tr, f"🌐 {other.upper()}", BORDER2, lambda: self._switch_lang(other),
             h=26, r=6).pack(anchor="e")
        self.upd_lbl = tk.Label(tr, text=f"v{VERSION}", font=("Segoe UI",8),
                                 bg=BG, fg=MUTED)
        self.upd_lbl.pack(anchor="e", pady=(4,0))

        # Divider
        tk.Frame(self.root, bg=BORDER2, height=1).pack(fill="x", padx=18, pady=(4,0))

        # ── Tab bar ─────────────────────────────────────
        tabs = [
            ("⚡", self.t("tab_spam"),  GREEN),
            ("🎯", self.t("tab_tame"),  BLUE),
            ("🛠", self.t("tab_macro"), PURPLE),
            ("⏺", self.t("tab_rec"),   RED),
        ]
        tb = TabBar(self.root, tabs, self._show_tab)
        tb.pack(fill="x", pady=(10,0))

        # ── Tab content ──────────────────────────────────
        self._cont = tk.Frame(self.root, bg=BG)
        self._cont.pack(fill="both", expand=True)

        self._frames = {}
        for key in ("spam","tame","macro","rec"):
            f = tk.Frame(self._cont, bg=BG)
            self._frames[key] = f

        self._build_spam(self._frames["spam"])
        self._build_tame(self._frames["tame"])
        self._build_macro(self._frames["macro"])
        self._build_record(self._frames["rec"])

        # ── Always-visible Stop button ───────────────────
        bot = tk.Frame(self.root, bg=BG)
        bot.pack(fill="x", padx=12, pady=(0,14))
        RoundBtn(bot, self.t("btn_stop_all"), RED, self.stop_all,
                 h=42, light_fg=True).pack(fill="x")

        self._show_tab(0)

    def _show_tab(self, idx):
        keys = ["spam","tame","macro","rec"]
        for i,(k,f) in enumerate(self._frames.items()):
            if i==idx: f.pack(fill="both", expand=True)
            else:       f.pack_forget()

    # ── Card helper ───────────────────────────────────────
    def _card(self, parent, title, accent=BLUE):
        outer = tk.Frame(parent, bg=BORDER2, padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=12, pady=(10,4))
        inner = tk.Frame(outer, bg=CARD)
        inner.pack(fill="both", expand=True)
        # Header row
        hrow = tk.Frame(inner, bg=CARD)
        hrow.pack(fill="x", padx=16, pady=(14,8))
        dot = tk.Canvas(hrow, width=8, height=8, bg=CARD, highlightthickness=0)
        dot.create_oval(0,0,8,8, fill=accent, outline="")
        dot.pack(side="left", padx=(0,8))
        tk.Label(hrow, text=title, font=("Segoe UI",8,"bold"),
                 bg=CARD, fg=MUTED).pack(side="left")
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(0,12))
        return inner

    def _field(self, parent, label, attr, default, spin=None):
        f = tk.Frame(parent, bg=CARD)
        tk.Label(f, text=label, font=("Segoe UI",8),
                 bg=CARD, fg=MUTED).pack(anchor="w", pady=(0,3))
        wrap = tk.Frame(f, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        wrap.pack(fill="x")
        kw = dict(font=("Segoe UI",10), bg=INPUT, fg=INP_FG,
                  relief="flat", insertbackground=TEXT, bd=0)
        if spin:
            lo,hi,inc=spin
            var = tk.DoubleVar(value=default) if isinstance(default,float) else tk.IntVar(value=default)
            w = tk.Spinbox(wrap, from_=lo, to=hi, increment=inc,
                           textvariable=var, width=10,
                           buttonbackground=BORDER2, **kw)
        else:
            var = tk.StringVar(value=str(default))
            w = tk.Entry(wrap, textvariable=var, width=10, **kw)
        w.pack(fill="x", ipady=6, padx=8)
        setattr(self, attr, var)
        return f

    def _status(self, parent, key="st_stopped", color=RED):
        row = tk.Frame(parent, bg=CARD)
        dot = tk.Canvas(row, width=8, height=8, bg=CARD, highlightthickness=0)
        dot.create_oval(0,0,8,8, fill=color, outline="")
        dot.pack(side="left", padx=(0,6))
        lbl = tk.Label(row, text=self.t(key), font=("Segoe UI",9,"bold"),
                       bg=CARD, fg=color)
        lbl.pack(side="left")
        row._dot = dot; row._lbl = lbl
        return row

    def _set_status(self, widget, text, active=False, is_rec=False):
        c = RED if not active else (RED if is_rec else GREEN)
        widget._dot.delete("all")
        widget._dot.create_oval(0,0,8,8, fill=c, outline="")
        widget._lbl.config(text=text, fg=c)

    # ── SPAM tab ─────────────────────────────────────────
    def _build_spam(self, p):
        c = self._card(p, self.t("card_spam"), GREEN)
        row = tk.Frame(c, bg=CARD)
        row.pack(fill="x", padx=16, pady=(0,14))
        self._field(row, self.t("f_key"), "spam_key", "1").pack(side="left", padx=(0,20))
        self._field(row, self.t("f_interval"), "spam_interval", 10,
                    spin=(1,5000,1)).pack(side="left")
        self.spam_btn = RoundBtn(c, self.t("btn_spam0"), GREEN, self.toggle_spam)
        self.spam_btn.pack(fill="x", padx=16, pady=(0,10))
        self.spam_st = self._status(c); self.spam_st.pack(pady=(0,16))

    # ── TAME tab ─────────────────────────────────────────
    def _build_tame(self, p):
        c = self._card(p, self.t("card_tame"), BLUE)
        r1 = tk.Frame(c, bg=CARD); r1.pack(fill="x", padx=16, pady=(0,10))
        self._field(r1, self.t("f_tame_key"), "tame_key", "2").pack(side="left", padx=(0,20))
        self._field(r1, self.t("f_wait"), "tame_wait1", 7.0, spin=(0.5,120,0.5)).pack(side="left")
        r2 = tk.Frame(c, bg=CARD); r2.pack(fill="x", padx=16, pady=(0,14))
        self._field(r2, self.t("f_press_key"), "press_key", "1").pack(side="left", padx=(0,20))
        self._field(r2, self.t("f_wait"), "tame_wait2", 3.0, spin=(0.5,120,0.5)).pack(side="left")
        self.tame_btn = RoundBtn(c, self.t("btn_tame0"), BLUE, self.toggle_tame)
        self.tame_btn.pack(fill="x", padx=16, pady=(0,10))
        self.tame_st = self._status(c); self.tame_st.pack()
        self.cd_lbl = tk.Label(c, text="", font=("Segoe UI",9), bg=CARD, fg=ORANGE)
        self.cd_lbl.pack(pady=(2,16))

    # ── MACRO tab ────────────────────────────────────────
    def _build_macro(self, p):
        c = self._card(p, self.t("card_macro"), PURPLE)

        # Listbox
        lw = tk.Frame(c, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        lw.pack(fill="x", padx=16, pady=(0,8))
        self.step_list = tk.Listbox(lw, bg=INPUT, fg=TEXT,
            selectbackground=PURPLE, selectforeground=BG,
            font=("Segoe UI",9), relief="flat", height=5,
            borderwidth=0, activestyle="none")
        sb = tk.Scrollbar(lw, orient="vertical", command=self.step_list.yview, bg=BORDER)
        self.step_list.config(yscrollcommand=sb.set)
        self.step_list.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Controls row
        ctrl = tk.Frame(c, bg=CARD); ctrl.pack(fill="x", padx=16, pady=(0,8))
        for txt,col,cmd in [(self.t("btn_up"),BORDER2,self._step_up),
                             (self.t("btn_down"),BORDER2,self._step_down),
                             (self.t("btn_remove"),RED,self._step_remove),
                             (self.t("btn_clear"),BORDER2,self._step_clear)]:
            SBtn(ctrl,txt,col,cmd).pack(side="left",padx=(0,4))

        # Add step rows
        add = tk.Frame(c, bg=CARD); add.pack(fill="x", padx=16, pady=(0,8))
        rk = tk.Frame(add, bg=CARD); rk.pack(fill="x", pady=3)
        tk.Label(rk, text=self.t("key_lbl"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED, width=10, anchor="w").pack(side="left")
        self.new_key = tk.StringVar(value="1")
        wrap_k = tk.Frame(rk, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        wrap_k.pack(side="left", padx=(0,8))
        tk.Entry(wrap_k, textvariable=self.new_key, width=8,
                 font=("Segoe UI",10), bg=INPUT, fg=INP_FG,
                 relief="flat", insertbackground=TEXT, bd=0).pack(ipady=5, padx=6)
        SBtn(rk, self.t("btn_add_key"), GREEN, self._step_add_key).pack(side="left")

        rw = tk.Frame(add, bg=CARD); rw.pack(fill="x", pady=3)
        tk.Label(rw, text=self.t("wait_lbl"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED, width=10, anchor="w").pack(side="left")
        self.new_wait = tk.DoubleVar(value=1.0)
        wrap_w = tk.Frame(rw, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        wrap_w.pack(side="left", padx=(0,8))
        tk.Spinbox(wrap_w, from_=0.1, to=60, increment=0.5, textvariable=self.new_wait,
                   width=8, font=("Segoe UI",10), bg=INPUT, fg=INP_FG,
                   relief="flat", buttonbackground=BORDER2, insertbackground=TEXT,
                   bd=0).pack(ipady=5, padx=6)
        SBtn(rw, self.t("btn_add_wait"), BLUE, self._step_add_wait).pack(side="left")

        tk.Frame(c, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(4,8))

        # Bottom: repeat + save/load
        bot = tk.Frame(c, bg=CARD); bot.pack(fill="x", padx=16, pady=(0,8))
        tk.Label(bot, text=self.t("repeat"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED).pack(side="left")
        self.macro_repeat = tk.IntVar(value=0)
        wr = tk.Frame(bot, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        wr.pack(side="left", padx=(4,4))
        tk.Spinbox(wr, from_=0, to=9999, textvariable=self.macro_repeat,
                   width=5, font=("Segoe UI",10), bg=INPUT, fg=INP_FG,
                   relief="flat", buttonbackground=BORDER2, insertbackground=TEXT,
                   bd=0).pack(ipady=4, padx=4)
        tk.Label(bot, text=self.t("repeat_hint"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED).pack(side="left", padx=(0,10))
        SBtn(bot, self.t("btn_save"), BORDER2, self._macro_save).pack(side="left", padx=(0,4))
        SBtn(bot, self.t("btn_load"), BORDER2, self._macro_load).pack(side="left")

        self.macro_btn = RoundBtn(c, self.t("btn_macro0"), PURPLE, self.toggle_macro)
        self.macro_btn.pack(fill="x", padx=16, pady=(0,10))
        self.macro_st = self._status(c); self.macro_st.pack(pady=(0,14))

    # ── RECORD tab ───────────────────────────────────────
    def _build_record(self, p):
        c = self._card(p, self.t("card_rec"), RED)

        self.rec_btn = RoundBtn(c, self.t("btn_rec0"), RED, self.toggle_record, light_fg=True)
        self.rec_btn.pack(fill="x", padx=16, pady=(0,8))

        info_row = tk.Frame(c, bg=CARD); info_row.pack(fill="x", padx=16, pady=(0,8))
        self.rec_st = self._status(info_row); self.rec_st.pack(side="left")
        self.rec_count = tk.Label(info_row, text=self.t("rec_n").format(n=0),
                                   font=("Segoe UI",8), bg=CARD, fg=MUTED)
        self.rec_count.pack(side="right")

        # Event list
        lw = tk.Frame(c, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        lw.pack(fill="x", padx=16, pady=(0,8))
        self.rec_list = tk.Listbox(lw, bg=INPUT, fg=TEXT,
            selectbackground=BLUE, selectforeground=BG,
            font=("Segoe UI",8), relief="flat", height=5,
            borderwidth=0, activestyle="none")
        rsb = tk.Scrollbar(lw, orient="vertical", command=self.rec_list.yview, bg=BORDER)
        self.rec_list.config(yscrollcommand=rsb.set)
        self.rec_list.pack(side="left", fill="both", expand=True)
        rsb.pack(side="right", fill="y")

        # Options
        opt = tk.Frame(c, bg=CARD); opt.pack(fill="x", padx=16, pady=(0,6))
        self.incl_mouse = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(opt, text=self.t("incl_mouse"),
                            variable=self.incl_mouse,
                            bg=CARD, fg=TEXT, selectcolor=INPUT,
                            activebackground=CARD, activeforeground=TEXT,
                            font=("Segoe UI",9), relief="flat", cursor="hand2")
        cb.pack(side="left")

        tk.Frame(c, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(4,8))

        bot = tk.Frame(c, bg=CARD); bot.pack(fill="x", padx=16, pady=(0,8))
        tk.Label(bot, text=self.t("repeat"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED).pack(side="left")
        self.rec_repeat = tk.IntVar(value=1)
        wr = tk.Frame(bot, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        wr.pack(side="left", padx=(4,4))
        tk.Spinbox(wr, from_=0, to=9999, textvariable=self.rec_repeat,
                   width=5, font=("Segoe UI",10), bg=INPUT, fg=INP_FG,
                   relief="flat", buttonbackground=BORDER2, insertbackground=TEXT,
                   bd=0).pack(ipady=4, padx=4)
        tk.Label(bot, text=self.t("repeat_hint"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED).pack(side="left", padx=(0,10))
        SBtn(bot, self.t("btn_save"), BORDER2, self._rec_save).pack(side="left", padx=(0,4))
        SBtn(bot, self.t("btn_load"), BORDER2, self._rec_load).pack(side="left", padx=(0,4))
        SBtn(bot, self.t("btn_del_rec"), BORDER2, self._rec_clear).pack(side="left")

        self.play_btn = RoundBtn(c, self.t("btn_play0"), GREEN, self.toggle_play)
        self.play_btn.pack(fill="x", padx=16, pady=(0,10))
        self.play_st = self._status(c); self.play_st.pack(pady=(0,14))

    # ── Recording ─────────────────────────────────────────
    def toggle_record(self):
        if self.rec_running: self._stop_rec()
        else:                self._start_rec()

    def _start_rec(self):
        self.recording.clear(); self._rec_start=time.time(); self._last_move=0.0
        self.rec_running=True
        self.rec_btn.set(self.t("btn_rec1"), ORANGE)
        self._set_status(self.rec_st, self.t("st_recording"), True, is_rec=True)
        self._rec_refresh()

        def on_kp(key):
            if not self.rec_running: return False
            if key==Key.f4: return
            self.recording.append({"type":"key_down","key":_k2s(key),"t":round(time.time()-self._rec_start,4)})
            self.root.after(0, self._rec_refresh)
        def on_kr(key):
            if not self.rec_running: return
            if key==Key.f4: return
            self.recording.append({"type":"key_up","key":_k2s(key),"t":round(time.time()-self._rec_start,4)})
        def on_click(x,y,btn,pressed):
            if not self.rec_running: return
            self.recording.append({"type":"mouse_click","x":x,"y":y,"btn":_b2s(btn),"pressed":pressed,"t":round(time.time()-self._rec_start,4)})
            self.root.after(0, self._rec_refresh)
        def on_move(x,y):
            if not self.rec_running or not self.incl_mouse.get(): return
            now=time.time()
            if now-self._last_move<0.016: return
            self._last_move=now
            self.recording.append({"type":"mouse_move","x":x,"y":y,"t":round(now-self._rec_start,4)})
        def on_scroll(x,y,dx,dy):
            if not self.rec_running: return
            self.recording.append({"type":"mouse_scroll","x":x,"y":y,"dx":dx,"dy":dy,"t":round(time.time()-self._rec_start,4)})
            self.root.after(0, self._rec_refresh)

        self._kb_rec=KbListener(on_press=on_kp, on_release=on_kr)
        self._ms_rec=MsListener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)
        self._kb_rec.daemon=True; self._ms_rec.daemon=True
        self._kb_rec.start(); self._ms_rec.start()

    def _stop_rec(self):
        self.rec_running=False
        try: self._kb_rec.stop()
        except: pass
        try: self._ms_rec.stop()
        except: pass
        self.rec_btn.set(self.t("btn_rec0"), RED)
        self._set_status(self.rec_st, self.t("st_stopped"), False)
        self._rec_refresh()

    def _rec_refresh(self):
        n=len(self.recording)
        self.rec_count.config(text=self.t("rec_n").format(n=n))
        vis=[e for e in self.recording if e["type"]!="mouse_move"]
        self.rec_list.delete(0,tk.END)
        for e in vis[-100:]:
            t=e["t"]
            if   e["type"]=="key_down":                    self.rec_list.insert(tk.END, f"  {t:.2f}s   {self.t('evt_key')} {e['key']}")
            elif e["type"]=="mouse_click" and e["pressed"]: self.rec_list.insert(tk.END, f"  {t:.2f}s   {self.t('evt_click')} {e['btn']} ({e['x']},{e['y']})")
            elif e["type"]=="mouse_scroll":                 self.rec_list.insert(tk.END, f"  {t:.2f}s   {self.t('evt_scroll')} dy={e['dy']}")
        self.rec_list.yview_moveto(1.0)

    def _rec_save(self):
        if not self.recording:
            messagebox.showinfo(self.t("hint"), self.t("no_rec"), parent=self.root); return
        p=filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("Recording","*.json")], title=self.t("save_rec"), parent=self.root)
        if p:
            with open(p,"w") as f: json.dump({"repeat":self.rec_repeat.get(),"events":self.recording},f)

    def _rec_load(self):
        p=filedialog.askopenfilename(filetypes=[("Recording","*.json")],
            title=self.t("load_rec"), parent=self.root)
        if p:
            with open(p) as f: data=json.load(f)
            self.recording=data.get("events",[]); self.rec_repeat.set(data.get("repeat",1))
            self._rec_refresh()

    def _rec_clear(self):
        self.recording.clear(); self._rec_refresh()

    # ── Playback ──────────────────────────────────────────
    def toggle_play(self):
        if self.play_running:
            self.play_running=False
            self.play_btn.set(self.t("btn_play0"), GREEN)
            self._set_status(self.play_st, self.t("st_stopped"), False)
        else:
            if not self.recording:
                messagebox.showinfo(self.t("hint"), self.t("no_rec"), parent=self.root); return
            self.play_running=True
            self.play_btn.set(self.t("btn_play1"), ORANGE)
            self._set_status(self.play_st, self.t("st_running"), True)
            threading.Thread(target=self._play_loop, daemon=True).start()

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
        self.root.after(0, lambda: self.play_btn.set(self.t("btn_play0"), GREEN))
        self.root.after(0, lambda: self._set_status(self.play_st, self.t("st_stopped"), False))

    def _play_evt(self, e):
        try:
            tp=e["type"]
            if   tp=="key_down":    k=_s2k(e["key"]);  self.kb.press(k) if k else None
            elif tp=="key_up":      k=_s2k(e["key"]);  self.kb.release(k) if k else None
            elif tp=="mouse_click":
                b=_s2b(e["btn"]); self.ms.position=(e["x"],e["y"])
                self.ms.press(b) if e["pressed"] else self.ms.release(b)
            elif tp=="mouse_move":   self.ms.position=(e["x"],e["y"])
            elif tp=="mouse_scroll": self.ms.scroll(e["dx"],e["dy"])
        except: pass

    # ── Macro steps ───────────────────────────────────────
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
            if s["type"]=="press": self.step_list.insert(tk.END, f"  {i}.   {self.t('step_key')}  {s['key']}")
            else:                  self.step_list.insert(tk.END, f"  {i}.   {self.t('step_wait')}  {s['seconds']}s")

    def _macro_save(self):
        p=filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("Macro","*.json")], title=self.t("save_macro"), parent=self.root)
        if p:
            with open(p,"w") as f: json.dump({"repeat":self.macro_repeat.get(),"steps":self.macro_steps},f,indent=2)

    def _macro_load(self):
        p=filedialog.askopenfilename(filetypes=[("Macro","*.json")],
            title=self.t("load_macro"), parent=self.root)
        if p:
            with open(p) as f: data=json.load(f)
            self.macro_steps=data.get("steps",[]); self.macro_repeat.set(data.get("repeat",0))
            self._refresh_steps()

    # ── Toggle Spam / Tame / Macro ────────────────────────
    def toggle_spam(self):
        if self.spam_running:
            self.spam_running=False
            self.spam_btn.set(self.t("btn_spam0"), GREEN)
            self._set_status(self.spam_st, self.t("st_stopped"), False)
        else:
            self.spam_running=True
            self.spam_btn.set(self.t("btn_spam1"), ORANGE)
            self._set_status(self.spam_st, self.t("st_running"), True)
            threading.Thread(target=self._spam_loop, daemon=True).start()

    def toggle_tame(self):
        if self.tame_running:
            self.tame_running=False
            self.tame_btn.set(self.t("btn_tame0"), BLUE)
            self._set_status(self.tame_st, self.t("st_stopped"), False)
        else:
            self.tame_running=True
            self.tame_btn.set(self.t("btn_tame1"), ORANGE)
            self._set_status(self.tame_st, self.t("st_running"), True)
            threading.Thread(target=self._tame_loop, daemon=True).start()

    def toggle_macro(self):
        if self.macro_running:
            self.macro_running=False
            self.macro_btn.set(self.t("btn_macro0"), PURPLE)
            self._set_status(self.macro_st, self.t("st_stopped"), False)
        else:
            if not self.macro_steps:
                messagebox.showinfo(self.t("hint"),self.t("no_steps"),parent=self.root); return
            self.macro_running=True
            self.macro_btn.set(self.t("btn_macro1"), ORANGE)
            self._set_status(self.macro_st, self.t("st_running"), True)
            threading.Thread(target=self._macro_loop, daemon=True).start()

    def stop_all(self):
        self.spam_running=self.tame_running=self.macro_running=False
        self.rec_running=self.play_running=False
        try: self._kb_rec.stop()
        except: pass
        try: self._ms_rec.stop()
        except: pass
        self.root.after(0, self._ui_reset)

    def _ui_reset(self):
        self.spam_btn.set(self.t("btn_spam0"), GREEN)
        self._set_status(self.spam_st, self.t("st_stopped"), False)
        self.tame_btn.set(self.t("btn_tame0"), BLUE)
        self._set_status(self.tame_st, self.t("st_stopped"), False)
        self.cd_lbl.config(text="")
        self.macro_btn.set(self.t("btn_macro0"), PURPLE)
        self._set_status(self.macro_st, self.t("st_stopped"), False)
        self.rec_btn.set(self.t("btn_rec0"), RED)
        self._set_status(self.rec_st, self.t("st_stopped"), False)
        self.play_btn.set(self.t("btn_play0"), GREEN)
        self._set_status(self.play_st, self.t("st_stopped"), False)

    # ── Loops ─────────────────────────────────────────────
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

    def _tw(self, s):
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
        self.root.after(0, lambda: self.macro_btn.set(self.t("btn_macro0"), PURPLE))
        self.root.after(0, lambda: self._set_status(self.macro_st, self.t("st_stopped"), False))

    # ── Tick ──────────────────────────────────────────────
    def _tick(self):
        if self.tame_running and self.tame_phase:
            lbl=self.t("tame_after") if self.tame_phase=="tame" else self.t("tame_press")
            f=max(0,min(10,round(self.tame_cd/10*10)))
            self.cd_lbl.config(text=f"{lbl}  ·  {self.tame_cd:.1f}s   {'█'*f}{'░'*(10-f)}")
        else:
            self.cd_lbl.config(text="")
        self.root.after(100, self._tick)

    # ── Hotkeys ───────────────────────────────────────────
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

    # ── Language switch ───────────────────────────────────
    def _switch_lang(self, nl):
        cfg=load_cfg(); cfg["lang"]=nl; save_cfg(cfg)
        self.spam_running=self.tame_running=self.macro_running=False
        self.rec_running=self.play_running=False
        self.root.after(120, self._restart)

    def _restart(self):
        self.root.destroy()
        root=tk.Tk()
        MacroApp(root, lang=load_cfg().get("lang","de"))
        root.mainloop()

    # ── Auto-Update ───────────────────────────────────────
    def _check_update(self):
        try:
            with urllib.request.urlopen(VERSION_URL,timeout=6) as r:
                latest=r.read().decode().strip()
            if latest!=VERSION: self.root.after(0,lambda: self._upd_avail(latest))
            else: self.root.after(0,lambda: self.upd_lbl.config(text=f"v{VERSION}  ·  {self.t('st_ok')}",fg=MUTED))
        except: self.root.after(0,lambda: self.upd_lbl.config(text=f"v{VERSION}  ·  {self.t('st_no_net')}",fg=MUTED))

    def _upd_avail(self, latest):
        self.upd_lbl.config(text=f"v{VERSION} → v{latest} {self.t('upd_click')}",fg=AMBER,cursor="hand2")
        self.upd_lbl.bind("<Button-1>",lambda e: self._ask_upd(latest))

    def _ask_upd(self, latest):
        if messagebox.askyesno(self.t("upd_title"),self.t("upd_msg").format(v=latest),parent=self.root):
            self.upd_lbl.config(text=self.t("downloading"),fg=ORANGE,cursor="arrow")
            self.upd_lbl.unbind("<Button-1>")
            threading.Thread(target=lambda: self._download(latest),daemon=True).start()

    def _download(self, latest):
        try:
            req=urllib.request.Request(RELEASE_URL,headers={"Accept":"application/vnd.github+json"})
            with urllib.request.urlopen(req,timeout=15) as r: data=json.loads(r.read())
            url=next((a["browser_download_url"] for a in data.get("assets",[]) if a["name"]=="SoupMacro.exe"),None)
            if not url: raise RuntimeError("SoupMacro.exe not found.")
            exe=sys.executable; new=exe+".new"
            def _p(c,b,tot):
                if tot>0:
                    pct=min(100,int(c*b*100/tot))
                    self.root.after(0,lambda p=pct: self.upd_lbl.config(text=f"{self.t('downloading')} {p}%",fg=ORANGE))
            urllib.request.urlretrieve(url,new,reporthook=_p)
            bat=tempfile.mktemp(suffix=".bat")
            with open(bat,"w") as f:
                f.write(f'@echo off\ntimeout /t 2 /nobreak>nul\nmove /y "{new}" "{exe}"\nstart "" "{exe}"\ndel "%~f0"\n')
            self.root.after(0,lambda: self.upd_lbl.config(text=self.t("upd_done"),fg=GREEN))
            subprocess.Popen(["cmd","/c",bat],creationflags=subprocess.CREATE_NO_WINDOW)
            self.root.after(1500,self.root.destroy)
        except Exception as ex:
            self.root.after(0,lambda: messagebox.showerror(self.t("error"),str(ex),parent=self.root))


# ── Serialization ─────────────────────────────────────────────
def _k2s(k):
    try:    return k.char or str(k)
    except: return str(k)

def _s2k(s):
    if s.startswith("Key."): return getattr(Key,s[4:],None)
    if s and len(s)==1: return s
    return SPECIAL_KEYS.get(s.lower())

def _b2s(b): return str(b)
def _s2b(s):
    return getattr(Button, s.replace("Button.",""), Button.left)


if __name__=="__main__":
    cfg=load_cfg()
    root=tk.Tk()
    MacroApp(root, lang=cfg.get("lang","de"))
    root.mainloop()
