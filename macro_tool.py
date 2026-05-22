import tkinter as tk
from tkinter import messagebox, filedialog
import threading, time, sys, os, json, subprocess, tempfile
import urllib.request, webbrowser, random, ctypes
from PIL import Image, ImageTk, ImageDraw
from pynput.keyboard import Key, Controller as KbCtrl, Listener as KbListener
from pynput.mouse import Button, Controller as MsCtrl, Listener as MsListener

try:
    import pystray
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

VERSION     = "1.4"
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
KEY_NAMES = {v:k for k,v in SPECIAL_KEYS.items()}

# ── Paths & Config ────────────────────────────────────────────
def res(p):
    try:    base = sys._MEIPASS
    except: base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, p)

def _cfg_path():
    # Store config in %APPDATA%\SoupMacro\ so it survives updates and is writable
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    base    = os.path.join(appdata, "SoupMacro")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "config.json")

def load_cfg():
    try:
        with open(_cfg_path()) as f: return json.load(f)
    except: return {}

def save_cfg(d):
    try:
        with open(_cfg_path(),"w") as f: json.dump(d,f,indent=2)
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

def ltn(c, a=22):
    return "#{:02x}{:02x}{:02x}".format(
        min(int(c[1:3],16)+a,255), min(int(c[3:5],16)+a,255), min(int(c[5:7],16)+a,255))

def rrect(cv, x1, y1, x2, y2, r=10, **kw):
    r = min(r, (x2-x1)//2, (y2-y1)//2)
    pts = (x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
           x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1)
    return cv.create_polygon(pts, smooth=True, **kw)

# ── Widgets ───────────────────────────────────────────────────
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

    def set(self, text=None, color=None, light=None):
        if text  is not None: self._t=text
        if color is not None: self._c=color
        if light is not None: self._fg=TEXT if light else BG
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
        self._fg=TEXT if (light or color in (MUTED,MUTED2,BORDER2)) else BG
        self.configure(width=max(36,len(text)*7+16))
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>",  lambda e: cmd())
        self.bind("<Enter>",     lambda e: self._s(True))
        self.bind("<Leave>",     lambda e: self._s(False))

    def set(self, text=None, color=None, fg=None):
        if text  is not None: self._t=text
        if color is not None: self._c=color
        if fg    is not None: self._fg=fg
        self.configure(width=max(36,len(self._t)*7+16))
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
    """Tab bar using plain Frame+Label — no Canvas, fully compatible."""
    def __init__(self, parent, tabs, callback, bg=BG):
        super().__init__(parent, bg=bg)
        self._active = 0
        self._cb     = callback
        self._data   = tabs
        self._items  = []   # (outer_frame, label, indicator)

        cont = tk.Frame(self, bg=CARD2,
                        highlightbackground=BORDER2, highlightthickness=1)
        cont.pack(fill="x", padx=12)

        for i, (icon, label, color) in enumerate(tabs):
            col = CARD if i == 0 else CARD2
            outer = tk.Frame(cont, bg=col, cursor="hand2")
            outer.pack(side="left", fill="both", expand=True)

            lbl = tk.Label(outer,
                           text=f"{icon}  {label}",
                           font=("Segoe UI", 9, "bold") if i == 0 else ("Segoe UI", 9),
                           fg=TEXT if i == 0 else MUTED2,
                           bg=col, pady=10, cursor="hand2")
            lbl.pack(fill="both", expand=True)

            ind = tk.Frame(outer, height=3, bg=color if i == 0 else CARD2)
            ind.pack(fill="x", padx=6)

            for w in (outer, lbl):
                w.bind("<Button-1>", lambda e, idx=i: self._click(idx))
                w.bind("<Enter>",    lambda e, idx=i: self._hover(idx, True))
                w.bind("<Leave>",    lambda e, idx=i: self._hover(idx, False))

            self._items.append((outer, lbl, ind))

    def select(self, idx):
        self._active = idx
        self._refresh()

    def _click(self, idx):
        self.select(idx)
        self._cb(idx)

    def _hover(self, idx, on):
        if idx == self._active: return
        outer, lbl, _ = self._items[idx]
        c = CARD if on else CARD2
        outer.config(bg=c); lbl.config(bg=c)

    def _refresh(self):
        for i, (outer, lbl, ind) in enumerate(self._items):
            _, _, color = self._data[i]
            if i == self._active:
                outer.config(bg=CARD); lbl.config(bg=CARD, fg=TEXT,
                    font=("Segoe UI", 9, "bold"))
                ind.config(bg=color)
            else:
                outer.config(bg=CARD2); lbl.config(bg=CARD2, fg=MUTED2,
                    font=("Segoe UI", 9))
                ind.config(bg=CARD2)


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
    tab_rec="AUFNAHME", tab_set="CONFIG",
    card_spam="SPAM MODUS", card_tame="TAME MODUS",
    card_macro="EIGENER MAKRO", card_rec="AUFNAHME",
    card_lang="SPRACHE", card_hotkeys="TASTENKÜRZEL",
    card_reset="STANDARDWERTE", card_about="INFO",
    card_sound="SOUND", card_panic="PANIC KEY",
    card_autopause="AUTO-PAUSE", card_overlay="OVERLAY",
    card_profile="PROFILE",
    f_key="Taste", f_interval="Intervall (ms)",
    f_keys="Tasten (kommagetrennt, z.B. 1,e,2)",
    f_fixed="Fest", f_random="Zufall",
    f_min="Min (ms)", f_max="Max (ms)",
    f_hold="Nur beim Halten", f_hold_key="Halte-Taste",
    f_delay="Startverzögerung (s)",
    f_tame_key="Tame-Taste", f_wait="Warten (s)", f_press_key="Drück-Taste",
    btn_spam0="▶   Start Spam   (F1)", btn_spam1="⏸   Stop Spam   (F1)",
    btn_tame0="▶   Start Tame   (F2)", btn_tame1="⏸   Stop Tame   (F2)",
    btn_macro0="▶   Start Makro   (F3)", btn_macro1="⏸   Stop Makro   (F3)",
    btn_rec0="⏺   Aufnahme starten   (F4)", btn_rec1="⏹   Aufnahme stoppen   (F4)",
    btn_play0="▶   Abspielen   (F5)", btn_play1="⏸   Abspielen stoppen   (F5)",
    btn_add_key="+ Taste", btn_add_wait="+ Warten",
    btn_add_click="+ Klick", btn_add_label="+ Label",
    btn_pick="📍 Pos",
    btn_up="↑", btn_down="↓", btn_remove="✕ Löschen",
    btn_clear="Alle löschen", btn_save="💾 Speichern", btn_load="📂 Laden",
    btn_del_rec="🗑 Löschen", btn_stop_all="⏹   ALLE STOPPEN   (F12)",
    btn_reset="Auf Standard zurücksetzen",
    btn_github="Auf GitHub öffnen",
    btn_overlay="Overlay anzeigen",
    btn_save_profile="💾 Profil speichern",
    btn_load_profile="📂 Profil laden",
    btn_capture="Aufzeichnen",
    btn_capture_active="Drücke eine Taste...",
    st_stopped="Gestoppt", st_running="Läuft...", st_rec="Aufnahme läuft...",
    st_ok="Aktuell  ✓", st_no_net="Kein Internet",
    st_starting="Startet in {n}s...",
    upd_click="verfügbar  —  klicken zum Update",
    upd_title="Update verfügbar",
    upd_msg="Version {v} ist verfügbar!\n\nJetzt herunterladen und installieren?",
    downloading="Lade herunter...", upd_done="Fertig! Wird neugestartet...",
    tame_after="Warte nach Tame", tame_press="Warte nach Drücken",
    step_key="▶  Taste:", step_wait="⏱  Warten:",
    step_click="🖱  Klick:", step_label="💬",
    no_steps="Füge zuerst Schritte hinzu!", confirm_clear="Alle Schritte löschen?",
    save_macro="Makro speichern", load_macro="Makro laden",
    no_rec="Keine Aufnahme vorhanden!", rec_n="{n} Ereignisse",
    repeat="Wiederholen:", repeat_hint="(0 = endlos)",
    incl_mouse="Mausbewegungen aufzeichnen",
    save_rec="Aufnahme speichern", load_rec="Aufnahme laden",
    confirm_del="Löschen", hint="Hinweis", error="Fehler",
    key_lbl="Taste:", wait_lbl="Warten (s):",
    click_l="Links", click_r="Rechts",
    click_x="X", click_y="Y", label_lbl="Text:",
    evt_key="⌨", evt_click="🖱 Klick", evt_scroll="🖱 Scroll",
    lang_label="Sprache / Language",
    play_speed="Geschwindigkeit:",
    hk_spam="F1", hk_spam_l="Spam umschalten",
    hk_tame="F2", hk_tame_l="Tame umschalten",
    hk_macro="F3", hk_macro_l="Makro umschalten",
    hk_rec="F4", hk_rec_l="Aufnahme umschalten",
    hk_play="F5", hk_play_l="Abspielen umschalten",
    hk_stop="Panic*", hk_stop_l="Alles stoppen",
    panic_lbl="Aktuelle Panic-Taste:",
    sound_lbl="Sound-Feedback bei Start/Stop",
    autopause_lbl="Fenster-Titel (enthält):",
    autopause_chk="Auto-Pause wenn Fenster aktiv",
    overlay_hint="Kleines Statusfenster immer im Vordergrund.",
    reset_hint="Setzt alle Felder auf ihre Standardwerte zurück.",
    reset_done="Standardwerte wiederhergestellt.",
    about_made="Erstellt von", about_ver="Version",
    pick_hint="Fenster minimiert sich — in 3s wird Mausposition übernommen.",
    tray_show="Öffnen", tray_stop="Alles stoppen", tray_quit="Beenden",
),
"en": dict(
    tab_spam="SPAM", tab_tame="TAME", tab_macro="MACROS",
    tab_rec="RECORD", tab_set="SETTINGS",
    card_spam="SPAM MODE", card_tame="TAME MODE",
    card_macro="CUSTOM MACRO", card_rec="RECORDING",
    card_lang="LANGUAGE", card_hotkeys="HOTKEYS",
    card_reset="RESET DEFAULTS", card_about="ABOUT",
    card_sound="SOUND", card_panic="PANIC KEY",
    card_autopause="AUTO-PAUSE", card_overlay="OVERLAY",
    card_profile="PROFILES",
    f_key="Key", f_interval="Interval (ms)",
    f_keys="Keys (comma-separated, e.g. 1,e,2)",
    f_fixed="Fixed", f_random="Random",
    f_min="Min (ms)", f_max="Max (ms)",
    f_hold="Hold Mode", f_hold_key="Hold Key",
    f_delay="Startup Delay (s)",
    f_tame_key="Tame Key", f_wait="Wait (s)", f_press_key="Press Key",
    btn_spam0="▶   Start Spam   (F1)", btn_spam1="⏸   Stop Spam   (F1)",
    btn_tame0="▶   Start Tame   (F2)", btn_tame1="⏸   Stop Tame   (F2)",
    btn_macro0="▶   Start Macro   (F3)", btn_macro1="⏸   Stop Macro   (F3)",
    btn_rec0="⏺   Start Recording   (F4)", btn_rec1="⏹   Stop Recording   (F4)",
    btn_play0="▶   Play   (F5)", btn_play1="⏸   Stop Playing   (F5)",
    btn_add_key="+ Key", btn_add_wait="+ Wait",
    btn_add_click="+ Click", btn_add_label="+ Label",
    btn_pick="📍 Pos",
    btn_up="↑", btn_down="↓", btn_remove="✕ Delete",
    btn_clear="Clear all", btn_save="💾 Save", btn_load="📂 Load",
    btn_del_rec="🗑 Delete", btn_stop_all="⏹   STOP ALL   (F12)",
    btn_reset="Reset to defaults",
    btn_github="Open on GitHub",
    btn_overlay="Show Overlay",
    btn_save_profile="💾 Save Profile",
    btn_load_profile="📂 Load Profile",
    btn_capture="Capture",
    btn_capture_active="Press a key...",
    st_stopped="Stopped", st_running="Running...", st_rec="Recording...",
    st_ok="Up to date  ✓", st_no_net="No Internet",
    st_starting="Starting in {n}s...",
    upd_click="available  —  click to update",
    upd_title="Update available",
    upd_msg="Version {v} is available!\n\nDownload and install now?",
    downloading="Downloading...", upd_done="Done! Restarting...",
    tame_after="Waiting after Tame", tame_press="Waiting after Press",
    step_key="▶  Key:", step_wait="⏱  Wait:",
    step_click="🖱  Click:", step_label="💬",
    no_steps="Add steps first!", confirm_clear="Delete all steps?",
    save_macro="Save Macro", load_macro="Load Macro",
    no_rec="No recording available!", rec_n="{n} events",
    repeat="Repeat:", repeat_hint="(0 = endless)",
    incl_mouse="Record mouse movements",
    save_rec="Save Recording", load_rec="Load Recording",
    confirm_del="Delete", hint="Info", error="Error",
    key_lbl="Key:", wait_lbl="Wait (s):",
    click_l="Left", click_r="Right",
    click_x="X", click_y="Y", label_lbl="Text:",
    evt_key="⌨", evt_click="🖱 Click", evt_scroll="🖱 Scroll",
    lang_label="Sprache / Language",
    play_speed="Speed:",
    hk_spam="F1", hk_spam_l="Toggle Spam",
    hk_tame="F2", hk_tame_l="Toggle Tame",
    hk_macro="F3", hk_macro_l="Toggle Macro",
    hk_rec="F4", hk_rec_l="Toggle Recording",
    hk_play="F5", hk_play_l="Toggle Playback",
    hk_stop="Panic*", hk_stop_l="Stop everything",
    panic_lbl="Current Panic Key:",
    sound_lbl="Sound feedback on start/stop",
    autopause_lbl="Window title (contains):",
    autopause_chk="Auto-pause when window is active",
    overlay_hint="Small status window always on top.",
    reset_hint="Resets all fields to their default values.",
    reset_done="Default values restored.",
    about_made="Created by", about_ver="Version",
    pick_hint="Window minimizes — mouse position captured after 3s.",
    tray_show="Show", tray_stop="Stop All", tray_quit="Quit",
),
}


# ── Main App ──────────────────────────────────────────────────
class MacroApp:
    def __init__(self, root, lang="de"):
        self.root = root
        self.lang = lang
        self.root.title("Soup Macro")
        self.root.geometry("540x780")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # Runtime state
        self.spam_running  = False
        self.tame_running  = False
        self.macro_running = False
        self.rec_running   = False
        self.play_running  = False
        self.tame_phase    = ""
        self.tame_cd       = 0.0
        self.macro_steps   = []
        self.recording     = []
        self._rec_start    = 0.0
        self._last_move    = 0.0
        self._hold_pressed = False
        self._hold_lst     = None
        self._capturing_panic = False
        self._overlay      = None
        self._ov_rows      = {}
        self._active_tab   = 0
        self._scroll_cvs   = {}

        # Load persisted config
        cfg = load_cfg()
        self._panic_key    = cfg.get("panic_key", "f12")
        self._sound_on     = cfg.get("sound", True)
        self._ap_on_init   = cfg.get("autopause", False)
        self._ap_win_init  = cfg.get("autopause_window", "")

        self.kb = KbCtrl()
        self.ms = MsCtrl()
        self._kb_rec = self._ms_rec = None

        self._load_icons()
        self._build()
        self._hotkeys()
        self._tick()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        threading.Thread(target=self._check_update, daemon=True).start()

    def t(self, k): return S[self.lang].get(k, k)

    # ── Icons ──────────────────────────────────────────────────
    def _load_icons(self):
        self.logo_tk = self.icon_tk = None
        self._logo_pil = None
        try:
            raw = Image.open(res("logo.png")).convert("RGBA")
            self.logo_tk  = ImageTk.PhotoImage(raw.resize((48,48), Image.NEAREST))
            self.icon_tk  = ImageTk.PhotoImage(raw.resize((32,32), Image.NEAREST))
            self._logo_pil = raw.resize((64,64), Image.NEAREST)
            self.root.iconphoto(True, self.icon_tk)
        except: pass

    # ── Build ──────────────────────────────────────────────────
    def _build(self):
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=18, pady=(18,6))
        if self.logo_tk:
            tk.Label(hdr, image=self.logo_tk, bg=BG).pack(side="left", padx=(0,14))
        info = tk.Frame(hdr, bg=BG)
        info.pack(side="left", anchor="center")
        tk.Label(info, text="Soup Macro", font=("Segoe UI",22,"bold"),
                 bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(info, text="github.com/FunkelVult/soup-macro",
                 font=("Segoe UI",8), bg=BG, fg=MUTED).pack(anchor="w")
        tr = tk.Frame(hdr, bg=BG)
        tr.pack(side="right", anchor="ne")
        self.upd_lbl = tk.Label(tr, text=f"v{VERSION}  ·  ...",
                                 font=("Segoe UI",8), bg=BG, fg=MUTED, cursor="arrow")
        self.upd_lbl.pack(anchor="e")

        Divider(self.root).pack(fill="x", padx=18, pady=(8,0))

        tabs = [
            ("⚡", self.t("tab_spam"),  GREEN),
            ("🎯", self.t("tab_tame"),  BLUE),
            ("🛠", self.t("tab_macro"), PURPLE),
            ("⏺", self.t("tab_rec"),   RED),
            ("⚙",  self.t("tab_set"),   AMBER),
        ]
        self._tabbar = TabBar(self.root, tabs, self._show_tab)
        self._tabbar.pack(fill="x", pady=(10,0))

        self._cont = tk.Frame(self.root, bg=BG)
        self._cont.pack(fill="both", expand=True)
        self._cont.grid_rowconfigure(0, weight=1)
        self._cont.grid_columnconfigure(0, weight=1)

        self._frames = {k: tk.Frame(self._cont, bg=BG)
                        for k in ["spam","tame","macro","rec","settings"]}
        for f in self._frames.values():
            f.grid(row=0, column=0, sticky="nsew")

        self._build_spam(self._frames["spam"])
        self._build_tame(self._frames["tame"])
        self._build_macro(self._frames["macro"])
        self._build_record(self._frames["rec"])
        self._build_settings(self._frames["settings"])

        self.root.bind("<MouseWheel>", self._on_wheel)

        bot = tk.Frame(self.root, bg=BG)
        bot.pack(fill="x", padx=12, pady=(4,12))
        RoundBtn(bot, self.t("btn_stop_all"), RED, self.stop_all,
                 h=42, light=True).pack(fill="x")
        self._show_tab(0)

    # ── Helpers ────────────────────────────────────────────────
    def _scrollable(self, parent, key):
        cv = tk.Canvas(parent, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(parent, orient="vertical", command=cv.yview,
                          bg=BORDER, troughcolor=BG, width=10)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=BG)
        wid = cv.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(wid, width=e.width))
        self._scroll_cvs[key] = cv
        return inner

    def _on_wheel(self, e):
        key = ["spam","tame","macro","rec","settings"][self._active_tab]
        cv  = self._scroll_cvs.get(key)
        if cv: cv.yview_scroll(int(-1*(e.delta/120)), "units")

    def _show_tab(self, idx):
        self._frames[["spam","tame","macro","rec","settings"][idx]].tkraise()
        self._active_tab = idx

    def _card(self, parent, title, accent=BLUE):
        outer = tk.Frame(parent, bg=BORDER2, padx=1, pady=1)
        outer.pack(fill="x", padx=12, pady=(10,4))
        inner = tk.Frame(outer, bg=CARD)
        inner.pack(fill="both", expand=True)
        hrow = tk.Frame(inner, bg=CARD)
        hrow.pack(fill="x", padx=16, pady=(12,8))
        dot = tk.Canvas(hrow, width=8, height=8, bg=CARD, highlightthickness=0)
        dot.create_oval(0,0,8,8, fill=accent, outline="")
        dot.pack(side="left", padx=(0,8))
        tk.Label(hrow, text=title, font=("Segoe UI",8,"bold"),
                 bg=CARD, fg=MUTED2).pack(side="left")
        Divider(inner, bg=BORDER).pack(fill="x", padx=16, pady=(0,10))
        return inner

    def _field(self, parent, label, attr, default, spin=None, w=10):
        f = tk.Frame(parent, bg=CARD)
        tk.Label(f, text=label, font=("Segoe UI",8), bg=CARD,
                 fg=MUTED2).pack(anchor="w", pady=(0,3))
        wrap = tk.Frame(f, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        wrap.pack(fill="x")
        kw = dict(font=("Segoe UI",10), bg=INPUT, fg=INP_FG, relief="flat",
                  insertbackground=TEXT, bd=0, width=w)
        if spin:
            lo,hi,inc = spin
            var = tk.DoubleVar(value=default) if isinstance(default,float) \
                  else tk.IntVar(value=default)
            wgt = tk.Spinbox(wrap, from_=lo, to=hi, increment=inc,
                             textvariable=var, buttonbackground=BORDER2, **kw)
        else:
            var = tk.StringVar(value=str(default))
            wgt = tk.Entry(wrap, textvariable=var, **kw)
        wgt.pack(fill="x", ipady=6, padx=8)
        setattr(self, attr, var)
        return f

    def _inrow(self, parent, *fields):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=16, pady=(0,12))
        for i,(lbl,attr,default,spin) in enumerate(fields):
            self._field(row, lbl, attr, default, spin).pack(
                side="left", padx=(0,20) if i<len(fields)-1 else 0)
        return row

    def _entry_wrap(self, parent, var, w=8):
        wrap = tk.Frame(parent, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        wrap.pack(side="left", padx=(0,6))
        tk.Entry(wrap, textvariable=var, width=w, font=("Segoe UI",10),
                 bg=INPUT, fg=INP_FG, relief="flat",
                 insertbackground=TEXT, bd=0).pack(ipady=5, padx=6)
        return wrap

    def _spin_wrap(self, parent, var, lo, hi, inc, w=6):
        wrap = tk.Frame(parent, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        wrap.pack(side="left", padx=(0,6))
        tk.Spinbox(wrap, from_=lo, to=hi, increment=inc, textvariable=var,
                   width=w, font=("Segoe UI",10), bg=INPUT, fg=INP_FG,
                   relief="flat", buttonbackground=BORDER2,
                   insertbackground=TEXT, bd=0).pack(ipady=5, padx=6)
        return wrap

    # ── SPAM tab ───────────────────────────────────────────────
    def _build_spam(self, p):
        sc = self._scrollable(p, "spam")
        c  = self._card(sc, self.t("card_spam"), GREEN)

        # Multi-key
        self._inrow(c, (self.t("f_keys"), "spam_key", "1", None))

        # Interval mode row
        mr = tk.Frame(c, bg=CARD)
        mr.pack(fill="x", padx=16, pady=(0,8))
        tk.Label(mr, text="Interval:", font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2).pack(side="left", padx=(0,8))
        self.spam_random = tk.BooleanVar(value=False)
        self._sb_fixed = SBtn(mr, self.t("f_fixed"), GREEN,
                               lambda: self._set_ivmode(False))
        self._sb_fixed.pack(side="left", padx=(0,4))
        self._sb_rand  = SBtn(mr, self.t("f_random"), BORDER2,
                               lambda: self._set_ivmode(True), light=True)
        self._sb_rand.pack(side="left")

        # Fixed frame
        self._fix_frame = tk.Frame(c, bg=CARD)
        self._fix_frame.pack(fill="x", padx=16, pady=(0,10))
        self._field(self._fix_frame, self.t("f_interval"),
                    "spam_interval", 10, (1,5000,1), w=8)

        # Random frame (hidden)
        self._rnd_frame = tk.Frame(c, bg=CARD)
        rfr = tk.Frame(self._rnd_frame, bg=CARD)
        rfr.pack(fill="x")
        self._field(rfr, self.t("f_min"), "spam_min", 8,  (1,5000,1), w=6).pack(side="left", padx=(0,16))
        self._field(rfr, self.t("f_max"), "spam_max", 12, (1,5000,1), w=6).pack(side="left")

        Divider(c, bg=BORDER).pack(fill="x", padx=16, pady=(4,10))

        # Hold mode
        hr = tk.Frame(c, bg=CARD)
        hr.pack(fill="x", padx=16, pady=(0,4))
        self.spam_hold = tk.BooleanVar(value=False)
        tk.Checkbutton(hr, text=self.t("f_hold"), variable=self.spam_hold,
                       command=self._update_hold_frame,
                       bg=CARD, fg=TEXT, selectcolor=INPUT, activebackground=CARD,
                       activeforeground=TEXT, font=("Segoe UI",9),
                       relief="flat", cursor="hand2").pack(side="left")
        self._hold_frame = tk.Frame(c, bg=CARD)
        hkr = tk.Frame(self._hold_frame, bg=CARD)
        hkr.pack(fill="x", padx=16, pady=(0,8))
        tk.Label(hkr, text=self.t("f_hold_key"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2).pack(side="left", padx=(0,6))
        self.spam_hold_key = tk.StringVar(value="")
        self._entry_wrap(hkr, self.spam_hold_key, w=8)

        Divider(c, bg=BORDER).pack(fill="x", padx=16, pady=(4,10))

        # Startup delay
        self._inrow(c, (self.t("f_delay"), "spam_delay", 0, (0,30,1)))

        self.spam_btn = RoundBtn(c, self.t("btn_spam0"), GREEN, self.toggle_spam)
        self.spam_btn.pack(fill="x", padx=16, pady=(0,10))
        self.spam_st = StatusRow(c, self.t("st_stopped"))
        self.spam_st.pack(padx=16, pady=(0,14), anchor="w")

    def _set_ivmode(self, rnd):
        self.spam_random.set(rnd)
        if rnd:
            self._fix_frame.pack_forget()
            self._rnd_frame.pack(fill="x", padx=16, pady=(0,10))
            self._sb_fixed.set(color=BORDER2, fg=TEXT)
            self._sb_rand.set(color=GREEN, fg=BG)
        else:
            self._rnd_frame.pack_forget()
            self._fix_frame.pack(fill="x", padx=16, pady=(0,10))
            self._sb_fixed.set(color=GREEN, fg=BG)
            self._sb_rand.set(color=BORDER2, fg=TEXT)

    def _update_hold_frame(self):
        if self.spam_hold.get():
            self._hold_frame.pack(fill="x", after=self._hold_frame.master.winfo_children()[0]
                                  if self._hold_frame.master.winfo_children() else None)
        else:
            self._hold_frame.pack_forget()

    # ── TAME tab ───────────────────────────────────────────────
    def _build_tame(self, p):
        sc = self._scrollable(p, "tame")
        c  = self._card(sc, self.t("card_tame"), BLUE)
        self._inrow(c,
            (self.t("f_tame_key"), "tame_key",   "2",  None),
            (self.t("f_wait"),     "tame_wait1",  7.0, (0.5,120,0.5)),
        )
        self._inrow(c,
            (self.t("f_press_key"), "press_key",  "1",  None),
            (self.t("f_wait"),      "tame_wait2",  3.0, (0.5,120,0.5)),
        )
        self._inrow(c, (self.t("f_delay"), "tame_delay", 0, (0,30,1)))
        self.tame_btn = RoundBtn(c, self.t("btn_tame0"), BLUE, self.toggle_tame)
        self.tame_btn.pack(fill="x", padx=16, pady=(0,10))
        self.tame_st = StatusRow(c, self.t("st_stopped"))
        self.tame_st.pack(padx=16, anchor="w")
        self.cd_lbl = tk.Label(c, text="", font=("Segoe UI",9), bg=CARD, fg=ORANGE)
        self.cd_lbl.pack(padx=16, pady=(4,14), anchor="w")

    # ── MACRO tab ──────────────────────────────────────────────
    def _build_macro(self, p):
        sc = self._scrollable(p, "macro")
        c  = self._card(sc, self.t("card_macro"), PURPLE)

        # Step list
        lw = tk.Frame(c, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        lw.pack(fill="x", padx=16, pady=(0,8))
        self.step_list = tk.Listbox(lw, bg=INPUT, fg=TEXT,
            selectbackground=PURPLE, selectforeground=BG,
            font=("Segoe UI",9), relief="flat", height=6,
            borderwidth=0, activestyle="none")
        sbl = tk.Scrollbar(lw, orient="vertical", command=self.step_list.yview, bg=BORDER)
        self.step_list.config(yscrollcommand=sbl.set)
        self.step_list.pack(side="left", fill="both", expand=True)
        sbl.pack(side="right", fill="y")

        # Step controls
        ctrl = tk.Frame(c, bg=CARD)
        ctrl.pack(fill="x", padx=16, pady=(0,10))
        for txt,col,cmd in [
            (self.t("btn_up"),     BORDER2, self._step_up),
            (self.t("btn_down"),   BORDER2, self._step_down),
            (self.t("btn_remove"), RED,     self._step_remove),
            (self.t("btn_clear"),  BORDER2, self._step_clear),
        ]:
            SBtn(ctrl, txt, col, cmd, light=True).pack(side="left", padx=(0,4))

        Divider(c, bg=BORDER).pack(fill="x", padx=16, pady=(2,10))

        # Add: Key
        rk = tk.Frame(c, bg=CARD)
        rk.pack(fill="x", padx=16, pady=(0,6))
        tk.Label(rk, text=self.t("key_lbl"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2, width=9, anchor="w").pack(side="left")
        self.new_key = tk.StringVar(value="1")
        self._entry_wrap(rk, self.new_key, w=7)
        SBtn(rk, self.t("btn_add_key"), GREEN, self._step_add_key).pack(side="left")

        # Add: Wait
        rw = tk.Frame(c, bg=CARD)
        rw.pack(fill="x", padx=16, pady=(0,6))
        tk.Label(rw, text=self.t("wait_lbl"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2, width=9, anchor="w").pack(side="left")
        self.new_wait = tk.DoubleVar(value=1.0)
        self._spin_wrap(rw, self.new_wait, 0.05, 600, 0.5, w=7)
        SBtn(rw, self.t("btn_add_wait"), BLUE, self._step_add_wait).pack(side="left")

        # Add: Mouse click
        rc = tk.Frame(c, bg=CARD)
        rc.pack(fill="x", padx=16, pady=(0,6))
        tk.Label(rc, text="🖱 Click:", font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2, width=9, anchor="w").pack(side="left")
        self.click_btn_var = tk.StringVar(value="left")
        self._cb_l = SBtn(rc, self.t("click_l"), GREEN,
                           lambda: self._set_click_btn("left"))
        self._cb_l.pack(side="left", padx=(0,4))
        self._cb_r = SBtn(rc, self.t("click_r"), BORDER2,
                           lambda: self._set_click_btn("right"), light=True)
        self._cb_r.pack(side="left", padx=(0,8))
        tk.Label(rc, text=self.t("click_x"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2).pack(side="left", padx=(0,4))
        self.click_x = tk.IntVar(value=0)
        self._spin_wrap(rc, self.click_x, 0, 9999, 1, w=5)
        tk.Label(rc, text=self.t("click_y"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2).pack(side="left", padx=(0,4))
        self.click_y = tk.IntVar(value=0)
        self._spin_wrap(rc, self.click_y, 0, 9999, 1, w=5)
        SBtn(rc, self.t("btn_add_click"), PURPLE, self._step_add_click).pack(side="left", padx=(0,4))
        SBtn(rc, self.t("btn_pick"), MUTED2, self._step_pick_pos, light=True).pack(side="left")

        # Add: Label
        rl = tk.Frame(c, bg=CARD)
        rl.pack(fill="x", padx=16, pady=(0,6))
        tk.Label(rl, text=self.t("label_lbl"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2, width=9, anchor="w").pack(side="left")
        self.new_label = tk.StringVar(value="")
        self._entry_wrap(rl, self.new_label, w=14)
        SBtn(rl, self.t("btn_add_label"), AMBER, self._step_add_label).pack(side="left")

        Divider(c, bg=BORDER).pack(fill="x", padx=16, pady=(4,10))

        bot = tk.Frame(c, bg=CARD)
        bot.pack(fill="x", padx=16, pady=(0,10))
        tk.Label(bot, text=self.t("repeat"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2).pack(side="left")
        self.macro_repeat = tk.IntVar(value=0)
        self._spin_wrap(bot, self.macro_repeat, 0, 9999, 1, w=5)
        tk.Label(bot, text=self.t("repeat_hint"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED).pack(side="left", padx=(2,12))
        SBtn(bot, self.t("btn_save"), BORDER2, self._macro_save, light=True).pack(side="left", padx=(0,4))
        SBtn(bot, self.t("btn_load"), BORDER2, self._macro_load, light=True).pack(side="left")

        self.macro_btn = RoundBtn(c, self.t("btn_macro0"), PURPLE, self.toggle_macro)
        self.macro_btn.pack(fill="x", padx=16, pady=(0,10))
        self.macro_st = StatusRow(c, self.t("st_stopped"))
        self.macro_st.pack(padx=16, pady=(0,14), anchor="w")

    def _set_click_btn(self, which):
        self.click_btn_var.set(which)
        if which == "left":
            self._cb_l.set(color=GREEN,   fg=BG)
            self._cb_r.set(color=BORDER2, fg=TEXT)
        else:
            self._cb_l.set(color=BORDER2, fg=TEXT)
            self._cb_r.set(color=GREEN,   fg=BG)

    # ── RECORD tab ─────────────────────────────────────────────
    def _build_record(self, p):
        sc = self._scrollable(p, "rec")
        c  = self._card(sc, self.t("card_rec"), RED)

        self.rec_btn = RoundBtn(c, self.t("btn_rec0"), RED,
                                self.toggle_record, light=True)
        self.rec_btn.pack(fill="x", padx=16, pady=(0,8))

        ir = tk.Frame(c, bg=CARD)
        ir.pack(fill="x", padx=16, pady=(0,8))
        self.rec_st = StatusRow(ir, self.t("st_stopped"))
        self.rec_st.pack(side="left")
        self.rec_count = tk.Label(ir, text=self.t("rec_n").format(n=0),
                                   font=("Segoe UI",8), bg=CARD, fg=MUTED2)
        self.rec_count.pack(side="right")

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

        opt = tk.Frame(c, bg=CARD)
        opt.pack(fill="x", padx=16, pady=(0,6))
        self.incl_mouse = tk.BooleanVar(value=False)
        tk.Checkbutton(opt, text=self.t("incl_mouse"), variable=self.incl_mouse,
                       bg=CARD, fg=TEXT, selectcolor=INPUT, activebackground=CARD,
                       activeforeground=TEXT, font=("Segoe UI",9),
                       relief="flat", cursor="hand2").pack(side="left")

        Divider(c, bg=BORDER).pack(fill="x", padx=16, pady=(4,10))

        # Playback speed
        sr = tk.Frame(c, bg=CARD)
        sr.pack(fill="x", padx=16, pady=(0,8))
        tk.Label(sr, text=self.t("play_speed"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2).pack(side="left", padx=(0,8))
        self.play_speed = tk.DoubleVar(value=1.0)
        self._speed_btns = {}
        for spd, label in [(0.5,"0.5x"), (1.0,"1x"), (2.0,"2x"), (4.0,"4x")]:
            active = spd == 1.0
            col = GREEN if active else BORDER2
            fg  = BG    if active else TEXT
            btn = SBtn(sr, label, col, lambda s=spd: self._set_speed(s), light=not active)
            btn.pack(side="left", padx=(0,4))
            self._speed_btns[spd] = btn

        bot = tk.Frame(c, bg=CARD)
        bot.pack(fill="x", padx=16, pady=(0,10))
        tk.Label(bot, text=self.t("repeat"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2).pack(side="left")
        self.rec_repeat = tk.IntVar(value=1)
        self._spin_wrap(bot, self.rec_repeat, 0, 9999, 1, w=5)
        tk.Label(bot, text=self.t("repeat_hint"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED).pack(side="left", padx=(2,12))
        SBtn(bot, self.t("btn_save"), BORDER2, self._rec_save, light=True).pack(side="left", padx=(0,4))
        SBtn(bot, self.t("btn_load"), BORDER2, self._rec_load, light=True).pack(side="left", padx=(0,4))
        SBtn(bot, self.t("btn_del_rec"), BORDER2, self._rec_clear, light=True).pack(side="left")

        self.play_btn = RoundBtn(c, self.t("btn_play0"), GREEN, self.toggle_play)
        self.play_btn.pack(fill="x", padx=16, pady=(0,10))
        self.play_st = StatusRow(c, self.t("st_stopped"))
        self.play_st.pack(padx=16, pady=(0,14), anchor="w")

    def _set_speed(self, spd):
        self.play_speed.set(spd)
        for s, btn in self._speed_btns.items():
            if s == spd:
                btn.set(color=GREEN, fg=BG)
            else:
                btn.set(color=BORDER2, fg=TEXT)

    # ── SETTINGS tab ───────────────────────────────────────────
    def _build_settings(self, p):
        sc = self._scrollable(p, "settings")

        # Language
        cl = self._card(sc, self.t("card_lang"), AMBER)
        tk.Label(cl, text=self.t("lang_label"), font=("Segoe UI",9),
                 bg=CARD, fg=MUTED2).pack(padx=16, pady=(0,10), anchor="w")
        lr = tk.Frame(cl, bg=CARD)
        lr.pack(padx=16, pady=(0,14), anchor="w")
        for code, label in [("de","🇩🇪  Deutsch"), ("en","🇬🇧  English")]:
            active = code == self.lang
            RoundBtn(lr, label, AMBER if active else BORDER2,
                     lambda c=code: self._switch_lang(c),
                     h=36, r=8, light=not active).pack(side="left", padx=(0,8))

        # Sound
        cs = self._card(sc, self.t("card_sound"), GREEN)
        sr = tk.Frame(cs, bg=CARD)
        sr.pack(fill="x", padx=16, pady=(0,14))
        self.sound_var = tk.BooleanVar(value=self._sound_on)
        tk.Checkbutton(sr, text=self.t("sound_lbl"), variable=self.sound_var,
                       command=self._save_sound_pref,
                       bg=CARD, fg=TEXT, selectcolor=INPUT, activebackground=CARD,
                       activeforeground=TEXT, font=("Segoe UI",9),
                       relief="flat", cursor="hand2").pack(side="left")

        # Panic key
        cp = self._card(sc, self.t("card_panic"), RED)
        pr = tk.Frame(cp, bg=CARD)
        pr.pack(fill="x", padx=16, pady=(0,10))
        tk.Label(pr, text=self.t("panic_lbl"), font=("Segoe UI",9),
                 bg=CARD, fg=MUTED2).pack(side="left", padx=(0,8))
        self._panic_lbl = tk.Label(pr, text=self._panic_key.upper(),
                                    font=("Segoe UI",10,"bold"),
                                    bg=BORDER2, fg=TEXT, padx=8, pady=4)
        self._panic_lbl.pack(side="left", padx=(0,10))
        self._capture_btn = SBtn(pr, self.t("btn_capture"), BLUE, self._begin_panic_capture)
        self._capture_btn.pack(side="left")

        # Auto-pause
        ca = self._card(sc, self.t("card_autopause"), ORANGE)
        self.autopause_var = tk.BooleanVar(value=self._ap_on_init)
        tk.Checkbutton(ca, text=self.t("autopause_chk"), variable=self.autopause_var,
                       command=self._save_ap_pref,
                       bg=CARD, fg=TEXT, selectcolor=INPUT, activebackground=CARD,
                       activeforeground=TEXT, font=("Segoe UI",9),
                       relief="flat", cursor="hand2").pack(padx=16, anchor="w")
        tk.Label(ca, text=self.t("autopause_lbl"), font=("Segoe UI",8),
                 bg=CARD, fg=MUTED2).pack(padx=16, pady=(8,4), anchor="w")
        apw = tk.Frame(ca, bg=INPUT, highlightbackground=BORDER2, highlightthickness=1)
        apw.pack(fill="x", padx=16, pady=(0,14))
        self.autopause_win = tk.StringVar(value=self._ap_win_init)
        tk.Entry(apw, textvariable=self.autopause_win, font=("Segoe UI",10),
                 bg=INPUT, fg=INP_FG, relief="flat", insertbackground=TEXT,
                 bd=0).pack(fill="x", ipady=6, padx=8)
        self.autopause_win.trace_add("write", lambda *_: self._save_ap_pref())

        # Overlay
        co = self._card(sc, self.t("card_overlay"), PURPLE)
        tk.Label(co, text=self.t("overlay_hint"), font=("Segoe UI",9),
                 bg=CARD, fg=MUTED2).pack(padx=16, anchor="w")
        RoundBtn(co, self.t("btn_overlay"), PURPLE, self._show_overlay,
                 h=36, r=8).pack(fill="x", padx=16, pady=(8,14))

        # Profile
        cpr = self._card(sc, self.t("card_profile"), BLUE)
        prr = tk.Frame(cpr, bg=CARD)
        prr.pack(fill="x", padx=16, pady=(0,14))
        SBtn(prr, self.t("btn_save_profile"), GREEN, self._save_profile).pack(side="left", padx=(0,8))
        SBtn(prr, self.t("btn_load_profile"), BLUE,  self._load_profile, light=False).pack(side="left")

        # Hotkeys
        ch = self._card(sc, self.t("card_hotkeys"), BLUE)
        hkeys = [
            (self.t("hk_spam"),  GREEN,  self.t("hk_spam_l")),
            (self.t("hk_tame"),  BLUE,   self.t("hk_tame_l")),
            (self.t("hk_macro"), PURPLE, self.t("hk_macro_l")),
            (self.t("hk_rec"),   RED,    self.t("hk_rec_l")),
            (self.t("hk_play"),  GREEN,  self.t("hk_play_l")),
            (self.t("hk_stop"),  ORANGE, self.t("hk_stop_l")),
        ]
        grid = tk.Frame(ch, bg=CARD)
        grid.pack(fill="x", padx=16, pady=(0,14))
        for i,(key,col,desc) in enumerate(hkeys):
            r,cc = divmod(i,2)
            cell = tk.Frame(grid, bg=CARD)
            cell.grid(row=r, column=cc, sticky="w", padx=(0,20), pady=3)
            tk.Label(cell, text=f" {key} ", font=("Segoe UI",9,"bold"),
                     bg=col, fg=BG, padx=4, pady=2).pack(side="left", padx=(0,8))
            tk.Label(cell, text=desc, font=("Segoe UI",9),
                     bg=CARD, fg=TEXT).pack(side="left")

        # Reset
        cr = self._card(sc, self.t("card_reset"), ORANGE)
        tk.Label(cr, text=self.t("reset_hint"), font=("Segoe UI",9),
                 bg=CARD, fg=MUTED2).pack(padx=16, anchor="w")
        RoundBtn(cr, self.t("btn_reset"), ORANGE, self._reset_defaults,
                 h=36, r=8).pack(fill="x", padx=16, pady=(8,14))

        # About
        cab = self._card(sc, self.t("card_about"), PURPLE)
        ab = tk.Frame(cab, bg=CARD)
        ab.pack(fill="x", padx=16, pady=(0,14))
        if self.logo_tk:
            tk.Label(ab, image=self.logo_tk, bg=CARD).pack(side="left", padx=(0,14))
        ai = tk.Frame(ab, bg=CARD)
        ai.pack(side="left", anchor="center")
        tk.Label(ai, text="Soup Macro", font=("Segoe UI",14,"bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(ai, text=f"{self.t('about_ver')} {VERSION}",
                 font=("Segoe UI",9), bg=CARD, fg=MUTED2).pack(anchor="w")
        tk.Label(ai, text=f"{self.t('about_made')} FunkelVult",
                 font=("Segoe UI",9), bg=CARD, fg=MUTED2).pack(anchor="w", pady=(2,6))
        RoundBtn(ai, self.t("btn_github"), PURPLE,
                 lambda: webbrowser.open(GITHUB_URL),
                 h=30, r=8).pack(anchor="w")

    # ── Settings logic ─────────────────────────────────────────
    def _save_sound_pref(self):
        cfg = load_cfg(); cfg["sound"] = self.sound_var.get(); save_cfg(cfg)
        self._sound_on = self.sound_var.get()

    def _save_ap_pref(self):
        cfg = load_cfg()
        cfg["autopause"]        = self.autopause_var.get()
        cfg["autopause_window"] = self.autopause_win.get()
        save_cfg(cfg)

    def _begin_panic_capture(self):
        if self._capturing_panic: return
        self._capturing_panic = True
        self._capture_btn.set(self.t("btn_capture_active"), AMBER)

        def on_press(key):
            if not self._capturing_panic: return False
            self._capturing_panic = False
            kname = KEY_NAMES.get(key, None) or _k2s(key)
            self._panic_key = kname
            cfg = load_cfg(); cfg["panic_key"] = kname; save_cfg(cfg)
            self.root.after(0, lambda: self._panic_lbl.config(text=kname.upper()))
            self.root.after(0, lambda: self._capture_btn.set(self.t("btn_capture"), BLUE))
            return False

        lst = KbListener(on_press=on_press)
        lst.daemon = True
        lst.start()

    def _get_active_window(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            n = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n+1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, n+1)
            return buf.value
        except: return ""

    def _should_pause(self):
        if not self.autopause_var.get(): return False
        tgt = self.autopause_win.get().strip().lower()
        if not tgt: return False
        return tgt in self._get_active_window().lower()

    def _beep(self, on):
        if self._sound_on and HAS_SOUND:
            try: threading.Thread(target=lambda: winsound.Beep(880 if on else 440, 80),
                                  daemon=True).start()
            except: pass

    def _reset_defaults(self):
        self.spam_key.set("1");     self.spam_interval.set(10)
        self.spam_min.set(8);       self.spam_max.set(12)
        self.spam_delay.set(0);     self.spam_hold.set(False)
        self.spam_hold_key.set("")
        self.tame_key.set("2");     self.tame_wait1.set(7.0)
        self.press_key.set("1");    self.tame_wait2.set(3.0)
        self.tame_delay.set(0)
        messagebox.showinfo(self.t("hint"), self.t("reset_done"), parent=self.root)

    # ── Overlay ────────────────────────────────────────────────
    def _show_overlay(self):
        if self._overlay and self._overlay.winfo_exists():
            self._overlay.lift(); return
        ov = tk.Toplevel(self.root)
        ov.title("Soup Macro")
        ov.geometry("210x195+120+120")
        ov.attributes("-topmost", True)
        ov.configure(bg=CARD)
        ov.resizable(False, False)

        def _sd(e): ov._dx, ov._dy = e.x, e.y
        def _mv(e):
            ov.geometry(f"+{ov.winfo_x()+e.x-ov._dx}+{ov.winfo_y()+e.y-ov._dy}")

        hdr = tk.Frame(ov, bg=BORDER2, height=28)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="🍜  Soup Macro", font=("Segoe UI",8,"bold"),
                 bg=BORDER2, fg=TEXT).pack(side="left", padx=8)
        tk.Button(hdr, text="✕", font=("Segoe UI",8), bg=BORDER2, fg=MUTED2,
                  relief="flat", bd=0, cursor="hand2", command=ov.destroy).pack(side="right", padx=4)
        hdr.bind("<ButtonPress-1>", _sd)
        hdr.bind("<B1-Motion>", _mv)

        body = tk.Frame(ov, bg=CARD)
        body.pack(fill="both", expand=True, padx=10, pady=8)
        self._ov_rows = {}
        for key, label, color in [
            ("spam",  "Spam",     GREEN),
            ("tame",  "Tame",     BLUE),
            ("macro", "Makro",    PURPLE),
            ("rec",   "Aufnahme", RED),
            ("play",  "Play",     GREEN),
        ]:
            row = tk.Frame(body, bg=CARD); row.pack(fill="x", pady=2)
            dot = tk.Canvas(row, width=8, height=8, bg=CARD, highlightthickness=0)
            dot.pack(side="left", padx=(0,6))
            lbl = tk.Label(row, font=("Segoe UI",9), bg=CARD, fg=MUTED2)
            lbl.pack(side="left")
            self._ov_rows[key] = (dot, lbl, color, label)
        self._overlay = ov
        self._ov_update()

    def _ov_update(self):
        if not (self._overlay and self._overlay.winfo_exists()): return
        states = {"spam":self.spam_running,"tame":self.tame_running,
                  "macro":self.macro_running,"rec":self.rec_running,"play":self.play_running}
        for key,(dot,lbl,color,label) in self._ov_rows.items():
            a = states[key]
            c = color if a else MUTED
            dot.delete("all"); dot.create_oval(0,0,8,8,fill=c,outline="")
            lbl.config(text=f"{label}:  {'Läuft' if a else 'Gestoppt'}", fg=c)

    # ── System tray ────────────────────────────────────────────
    def _setup_tray(self):
        if not HAS_TRAY: return
        try:
            img = self._logo_pil if self._logo_pil else self._make_tray_img()
            menu = pystray.Menu(
                pystray.MenuItem(self.t("tray_show"), lambda: self.root.after(0, self.root.deiconify)),
                pystray.MenuItem(self.t("tray_stop"), lambda: self.root.after(0, self.stop_all)),
                pystray.MenuItem(self.t("tray_quit"), lambda: self.root.after(0, self._quit)),
            )
            self._tray_icon = pystray.Icon("SoupMacro", img, "Soup Macro", menu)
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
        except: pass

    def _make_tray_img(self):
        img = Image.new("RGBA", (64,64), (0,0,0,0))
        d = ImageDraw.Draw(img)
        d.ellipse([4,4,60,60], fill=(52,211,153,255))
        return img

    def _on_close(self):
        if HAS_TRAY:
            self.root.withdraw()
            if not self._tray_icon:
                self._setup_tray()
        else:
            self._quit()

    def _quit(self):
        self.stop_all()
        try:
            if self._tray_icon: self._tray_icon.stop()
        except: pass
        self.root.destroy()

    # ── Profile save/load ──────────────────────────────────────
    def _save_profile(self):
        p = filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("Profile","*.json")], parent=self.root)
        if not p: return
        data = {
            "spam_key": self.spam_key.get(), "spam_interval": self.spam_interval.get(),
            "spam_random": self.spam_random.get(), "spam_min": self.spam_min.get(),
            "spam_max": self.spam_max.get(), "spam_hold": self.spam_hold.get(),
            "spam_hold_key": self.spam_hold_key.get(), "spam_delay": self.spam_delay.get(),
            "tame_key": self.tame_key.get(), "tame_wait1": self.tame_wait1.get(),
            "press_key": self.press_key.get(), "tame_wait2": self.tame_wait2.get(),
            "tame_delay": self.tame_delay.get(),
            "macro_steps": self.macro_steps, "macro_repeat": self.macro_repeat.get(),
        }
        with open(p,"w") as f: json.dump(data,f,indent=2)
        messagebox.showinfo(self.t("hint"), "✓ Profile saved", parent=self.root)

    def _load_profile(self):
        p = filedialog.askopenfilename(filetypes=[("Profile","*.json")], parent=self.root)
        if not p: return
        with open(p) as f: d = json.load(f)
        self.spam_key.set(d.get("spam_key","1"))
        self.spam_interval.set(d.get("spam_interval",10))
        self.spam_min.set(d.get("spam_min",8))
        self.spam_max.set(d.get("spam_max",12))
        self.spam_hold.set(d.get("spam_hold",False))
        self.spam_hold_key.set(d.get("spam_hold_key",""))
        self.spam_delay.set(d.get("spam_delay",0))
        self.tame_key.set(d.get("tame_key","2"))
        self.tame_wait1.set(d.get("tame_wait1",7.0))
        self.press_key.set(d.get("press_key","1"))
        self.tame_wait2.set(d.get("tame_wait2",3.0))
        self.tame_delay.set(d.get("tame_delay",0))
        self.macro_steps = d.get("macro_steps",[])
        self.macro_repeat.set(d.get("macro_repeat",0))
        use_rnd = d.get("spam_random", False)
        self._set_ivmode(use_rnd)
        self._update_hold_frame()
        self._refresh_steps()
        messagebox.showinfo(self.t("hint"), "✓ Profile loaded", parent=self.root)

    # ── Recording ──────────────────────────────────────────────
    def toggle_record(self):
        if self.rec_running: self._stop_rec()
        else:                self._start_rec()

    def _start_rec(self):
        self.recording.clear(); self._rec_start = time.time(); self._last_move = 0.0
        self.rec_running = True
        self.rec_btn.set(self.t("btn_rec1"), ORANGE)
        self.rec_st.set(self.t("st_rec"), True, rec_mode=True)
        self._beep(True)
        self._rec_refresh()

        def on_kp(key):
            if not self.rec_running: return False
            if key in (Key.f4,): return
            self.recording.append({"type":"key_down","key":_k2s(key),
                                   "t":round(time.time()-self._rec_start,4)})
            self.root.after(0, self._rec_refresh)

        def on_kr(key):
            if not self.rec_running: return
            if key in (Key.f4,): return
            self.recording.append({"type":"key_up","key":_k2s(key),
                                   "t":round(time.time()-self._rec_start,4)})

        def on_click(x,y,btn,pressed):
            if not self.rec_running: return
            self.recording.append({"type":"mouse_click","x":x,"y":y,
                                   "btn":_b2s(btn),"pressed":pressed,
                                   "t":round(time.time()-self._rec_start,4)})
            self.root.after(0, self._rec_refresh)

        def on_move(x,y):
            if not self.rec_running or not self.incl_mouse.get(): return
            now = time.time()
            if now - self._last_move < 0.016: return
            self._last_move = now
            self.recording.append({"type":"mouse_move","x":x,"y":y,
                                   "t":round(now-self._rec_start,4)})

        def on_scroll(x,y,dx,dy):
            if not self.rec_running: return
            self.recording.append({"type":"mouse_scroll","x":x,"y":y,"dx":dx,"dy":dy,
                                   "t":round(time.time()-self._rec_start,4)})
            self.root.after(0, self._rec_refresh)

        self._kb_rec = KbListener(on_press=on_kp, on_release=on_kr)
        self._ms_rec = MsListener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)
        self._kb_rec.daemon = True; self._ms_rec.daemon = True
        self._kb_rec.start(); self._ms_rec.start()

    def _stop_rec(self):
        self.rec_running = False
        for l in (self._kb_rec, self._ms_rec):
            try: l.stop()
            except: pass
        self.rec_btn.set(self.t("btn_rec0"), RED)
        self.rec_st.set(self.t("st_stopped"), False)
        self._beep(False)
        self._rec_refresh()

    def _rec_refresh(self):
        n = len(self.recording)
        self.rec_count.config(text=self.t("rec_n").format(n=n))
        vis = [e for e in self.recording if e["type"] != "mouse_move"]
        self.rec_list.delete(0, tk.END)
        for e in vis[-100:]:
            t_ = e["t"]
            if   e["type"]=="key_down":
                self.rec_list.insert(tk.END, f"  {t_:.2f}s   {self.t('evt_key')} {e['key']}")
            elif e["type"]=="mouse_click" and e["pressed"]:
                self.rec_list.insert(tk.END, f"  {t_:.2f}s   {self.t('evt_click')} {e['btn']} ({e['x']},{e['y']})")
            elif e["type"]=="mouse_scroll":
                self.rec_list.insert(tk.END, f"  {t_:.2f}s   {self.t('evt_scroll')} dy={e['dy']}")
        self.rec_list.yview_moveto(1.0)

    def _rec_save(self):
        if not self.recording:
            messagebox.showinfo(self.t("hint"), self.t("no_rec"), parent=self.root); return
        p = filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("Recording","*.json")], title=self.t("save_rec"), parent=self.root)
        if p:
            with open(p,"w") as f:
                json.dump({"repeat":self.rec_repeat.get(),"events":self.recording},f)

    def _rec_load(self):
        p = filedialog.askopenfilename(filetypes=[("Recording","*.json")],
            title=self.t("load_rec"), parent=self.root)
        if p:
            with open(p) as f: data = json.load(f)
            self.recording = data.get("events",[])
            self.rec_repeat.set(data.get("repeat",1))
            self._rec_refresh()

    def _rec_clear(self):
        self.recording.clear(); self._rec_refresh()

    # ── Playback ───────────────────────────────────────────────
    def toggle_play(self):
        if self.play_running:
            self.play_running = False
            self.play_btn.set(self.t("btn_play0"), GREEN)
            self.play_st.set(self.t("st_stopped"), False)
            self._beep(False)
        else:
            if not self.recording:
                messagebox.showinfo(self.t("hint"), self.t("no_rec"), parent=self.root); return
            self.play_running = True
            self.play_btn.set(self.t("btn_play1"), ORANGE)
            self.play_st.set(self.t("st_running"), True)
            self._beep(True)
            threading.Thread(target=self._play_loop, daemon=True).start()

    def _play_loop(self):
        repeat = self.rec_repeat.get(); count = 0
        speed  = self.play_speed.get()
        while self.play_running:
            if self._should_pause(): time.sleep(0.1); continue
            evts = list(self.recording)
            if not evts: break
            start = time.time()
            for evt in evts:
                if not self.play_running: break
                target = start + evt["t"] / speed
                while self.play_running and time.time() < target: time.sleep(0.004)
                if self.play_running: self._play_evt(evt)
            count += 1
            if repeat > 0 and count >= repeat: break
        self.play_running = False
        self.root.after(0, lambda: self.play_btn.set(self.t("btn_play0"), GREEN))
        self.root.after(0, lambda: self.play_st.set(self.t("st_stopped"), False))

    def _play_evt(self, e):
        try:
            tp = e["type"]
            if   tp=="key_down":    k=_s2k(e["key"]); self.kb.press(k) if k else None
            elif tp=="key_up":      k=_s2k(e["key"]); self.kb.release(k) if k else None
            elif tp=="mouse_click":
                b=_s2b(e["btn"]); self.ms.position=(e["x"],e["y"])
                self.ms.press(b) if e["pressed"] else self.ms.release(b)
            elif tp=="mouse_move":   self.ms.position=(e["x"],e["y"])
            elif tp=="mouse_scroll": self.ms.scroll(e["dx"],e["dy"])
        except: pass

    # ── Macro steps ────────────────────────────────────────────
    def _step_add_key(self):
        k = self.new_key.get().strip()
        if k: self.macro_steps.append({"type":"press","key":k}); self._refresh_steps()

    def _step_add_wait(self):
        self.macro_steps.append({"type":"wait","seconds":self.new_wait.get()})
        self._refresh_steps()

    def _step_add_click(self):
        self.macro_steps.append({"type":"click","x":self.click_x.get(),
                                  "y":self.click_y.get(),
                                  "button":self.click_btn_var.get()})
        self._refresh_steps()

    def _step_add_label(self):
        txt = self.new_label.get().strip()
        if txt: self.macro_steps.append({"type":"label","text":txt}); self._refresh_steps()

    def _step_pick_pos(self):
        messagebox.showinfo(self.t("hint"), self.t("pick_hint"), parent=self.root)
        def _pick():
            self.root.after(0, self.root.iconify)
            time.sleep(3.2)
            x, y = self.ms.position
            self.root.after(0, self.root.deiconify)
            self.root.after(0, lambda: self.click_x.set(x))
            self.root.after(0, lambda: self.click_y.set(y))
        threading.Thread(target=_pick, daemon=True).start()

    def _step_up(self):
        s = self.step_list.curselection()
        if not s or s[0]==0: return
        i = s[0]; self.macro_steps[i-1],self.macro_steps[i] = self.macro_steps[i],self.macro_steps[i-1]
        self._refresh_steps(); self.step_list.select_set(i-1)

    def _step_down(self):
        s = self.step_list.curselection()
        if not s or s[0]>=len(self.macro_steps)-1: return
        i = s[0]; self.macro_steps[i],self.macro_steps[i+1] = self.macro_steps[i+1],self.macro_steps[i]
        self._refresh_steps(); self.step_list.select_set(i+1)

    def _step_remove(self):
        s = self.step_list.curselection()
        if s: del self.macro_steps[s[0]]; self._refresh_steps()

    def _step_clear(self):
        if messagebox.askyesno(self.t("confirm_del"), self.t("confirm_clear"), parent=self.root):
            self.macro_steps.clear(); self._refresh_steps()

    def _refresh_steps(self):
        self.step_list.delete(0, tk.END)
        for i,s in enumerate(self.macro_steps, 1):
            if   s["type"]=="press":
                self.step_list.insert(tk.END, f"  {i}.  {self.t('step_key')}  {s['key']}")
            elif s["type"]=="wait":
                self.step_list.insert(tk.END, f"  {i}.  {self.t('step_wait')}  {s['seconds']}s")
            elif s["type"]=="click":
                self.step_list.insert(tk.END, f"  {i}.  {self.t('step_click')}  {s['button']} ({s['x']},{s['y']})")
            elif s["type"]=="label":
                self.step_list.insert(tk.END, f"  {i}.  {self.t('step_label')}  {s['text']}")

    def _macro_save(self):
        p = filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("Macro","*.json")], title=self.t("save_macro"), parent=self.root)
        if p:
            with open(p,"w") as f:
                json.dump({"repeat":self.macro_repeat.get(),"steps":self.macro_steps},f,indent=2)

    def _macro_load(self):
        p = filedialog.askopenfilename(filetypes=[("Macro","*.json")],
            title=self.t("load_macro"), parent=self.root)
        if p:
            with open(p) as f: data = json.load(f)
            self.macro_steps = data.get("steps",[])
            self.macro_repeat.set(data.get("repeat",0))
            self._refresh_steps()

    # ── Toggle / Start / Stop ──────────────────────────────────
    def toggle_spam(self):
        if self.spam_running:
            self.spam_running = False
            self.spam_btn.set(self.t("btn_spam0"), GREEN)
            self.spam_st.set(self.t("st_stopped"), False)
            self._beep(False)
            if self._hold_lst:
                try: self._hold_lst.stop()
                except: pass
        else:
            self.spam_running = True
            self.spam_btn.set(self.t("btn_spam1"), ORANGE)
            self.spam_st.set(self.t("st_running"), True)
            self._beep(True)
            threading.Thread(target=self._spam_loop, daemon=True).start()

    def toggle_tame(self):
        if self.tame_running:
            self.tame_running = False
            self.tame_btn.set(self.t("btn_tame0"), BLUE)
            self.tame_st.set(self.t("st_stopped"), False)
            self._beep(False)
        else:
            self.tame_running = True
            self.tame_btn.set(self.t("btn_tame1"), ORANGE)
            self.tame_st.set(self.t("st_running"), True)
            self._beep(True)
            threading.Thread(target=self._tame_loop, daemon=True).start()

    def toggle_macro(self):
        if self.macro_running:
            self.macro_running = False
            self.macro_btn.set(self.t("btn_macro0"), PURPLE)
            self.macro_st.set(self.t("st_stopped"), False)
            self._beep(False)
        else:
            if not self.macro_steps:
                messagebox.showinfo(self.t("hint"), self.t("no_steps"), parent=self.root); return
            self.macro_running = True
            self.macro_btn.set(self.t("btn_macro1"), ORANGE)
            self.macro_st.set(self.t("st_running"), True)
            self._beep(True)
            threading.Thread(target=self._macro_loop, daemon=True).start()

    def stop_all(self):
        self.spam_running = self.tame_running = self.macro_running = False
        self.rec_running  = self.play_running = False
        for l in (self._kb_rec, self._ms_rec, self._hold_lst):
            try: l.stop()
            except: pass
        self.root.after(0, self._ui_reset)

    def _ui_reset(self):
        self.spam_btn.set(self.t("btn_spam0"),  GREEN)
        self.spam_st.set(self.t("st_stopped"), False)
        self.tame_btn.set(self.t("btn_tame0"),  BLUE)
        self.tame_st.set(self.t("st_stopped"), False)
        self.cd_lbl.config(text="")
        self.macro_btn.set(self.t("btn_macro0"), PURPLE)
        self.macro_st.set(self.t("st_stopped"), False)
        self.rec_btn.set(self.t("btn_rec0"),   RED)
        self.rec_st.set(self.t("st_stopped"), False)
        self.play_btn.set(self.t("btn_play0"), GREEN)
        self.play_st.set(self.t("st_stopped"), False)

    # ── Loops ──────────────────────────────────────────────────
    def _countdown(self, seconds, mode):
        for i in range(int(seconds), 0, -1):
            alive = ((mode=="spam"  and self.spam_running)  or
                     (mode=="tame"  and self.tame_running)  or
                     (mode=="macro" and self.macro_running))
            if not alive: return
            n = i
            def _upd(n=n):
                txt = self.t("st_starting").format(n=n)
                if mode=="spam":  self.spam_st.set(txt,  True)
                elif mode=="tame": self.tame_st.set(txt,  True)
                elif mode=="macro":self.macro_st.set(txt, True)
            self.root.after(0, _upd)
            time.sleep(1)

    def _spam_loop(self):
        # Startup delay
        delay = self.spam_delay.get()
        if delay > 0: self._countdown(delay, "spam")
        if not self.spam_running: return

        # Hold mode setup
        hold_mode = self.spam_hold.get()
        self._hold_pressed = False
        if hold_mode:
            hk = self.spam_hold_key.get().strip()
            def _hp(key):
                if not self.spam_running: return False
                ks = _k2s(key).lower()
                if ks == hk.lower() or str(key).replace("Key.","").lower() == hk.lower():
                    self._hold_pressed = True
            def _hr(key):
                if not self.spam_running: return False
                ks = _k2s(key).lower()
                if ks == hk.lower() or str(key).replace("Key.","").lower() == hk.lower():
                    self._hold_pressed = False
            self._hold_lst = KbListener(on_press=_hp, on_release=_hr)
            self._hold_lst.daemon = True
            self._hold_lst.start()

        # Parse keys
        raw  = self.spam_key.get()
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not keys: keys = ["1"]

        self.root.after(0, lambda: self.spam_st.set(self.t("st_running"), True))
        while self.spam_running:
            if self._should_pause(): time.sleep(0.05); continue
            if hold_mode and not self._hold_pressed: time.sleep(0.01); continue
            for k in keys:
                if not self.spam_running: break
                if hold_mode and not self._hold_pressed: break
                try:
                    sk = SPECIAL_KEYS.get(k.lower())
                    self.kb.tap(sk if sk else k[0])
                except: pass
            if self.spam_random.get():
                ms = random.uniform(self.spam_min.get(), self.spam_max.get())
            else:
                ms = self.spam_interval.get()
            time.sleep(max(0.001, ms / 1000.0))

        self.spam_running = False
        self.root.after(0, lambda: self.spam_btn.set(self.t("btn_spam0"), GREEN))
        self.root.after(0, lambda: self.spam_st.set(self.t("st_stopped"), False))

    def _tame_loop(self):
        delay = self.tame_delay.get()
        if delay > 0: self._countdown(delay, "tame")
        if not self.tame_running: return
        self.root.after(0, lambda: self.tame_st.set(self.t("st_running"), True))
        while self.tame_running:
            if self._should_pause(): time.sleep(0.1); continue
            try: self.kb.tap(self.tame_key.get())
            except: pass
            self.tame_phase = "tame"; self._tw(self.tame_wait1.get())
            if not self.tame_running: break
            if self._should_pause(): time.sleep(0.1); continue
            try: self.kb.tap(self.press_key.get())
            except: pass
            self.tame_phase = "press"; self._tw(self.tame_wait2.get())
        self.tame_phase = ""; self.tame_cd = 0.0

    def _tw(self, s):
        end = time.time() + s
        while self.tame_running and time.time() < end:
            self.tame_cd = end - time.time(); time.sleep(0.05)

    def _macro_loop(self):
        delay = self.tame_delay.get() if hasattr(self,"tame_delay") else 0
        # macros use their own delay implicitly via steps; no extra countdown here
        repeat = self.macro_repeat.get(); count = 0
        self.root.after(0, lambda: self.macro_st.set(self.t("st_running"), True))
        while self.macro_running:
            for step in self.macro_steps:
                if not self.macro_running: break
                while self._should_pause() and self.macro_running: time.sleep(0.1)
                if step["type"] == "press":
                    try:
                        k = SPECIAL_KEYS.get(step["key"].lower())
                        self.kb.tap(k if k else step["key"][0])
                    except: pass
                elif step["type"] == "wait":
                    end = time.time() + step["seconds"]
                    while self.macro_running and time.time() < end: time.sleep(0.05)
                elif step["type"] == "click":
                    try:
                        b = Button.left if step["button"]=="left" else Button.right
                        self.ms.position = (step["x"], step["y"])
                        self.ms.click(b)
                    except: pass
                elif step["type"] == "label":
                    pass  # comment — skip
            count += 1
            if repeat > 0 and count >= repeat: break
        self.macro_running = False
        self.root.after(0, lambda: self.macro_btn.set(self.t("btn_macro0"), PURPLE))
        self.root.after(0, lambda: self.macro_st.set(self.t("st_stopped"), False))
        self._beep(False)

    # ── Tick ───────────────────────────────────────────────────
    def _tick(self):
        if self.tame_running and self.tame_phase:
            lbl = self.t("tame_after") if self.tame_phase=="tame" else self.t("tame_press")
            f   = max(0, min(10, round(self.tame_cd/10*10)))
            self.cd_lbl.config(text=f"{lbl}  ·  {self.tame_cd:.1f}s   {'█'*f}{'░'*(10-f)}")
        else:
            self.cd_lbl.config(text="")
        self._ov_update()
        self.root.after(100, self._tick)

    # ── Hotkeys ────────────────────────────────────────────────
    def _hotkeys(self):
        def on_press(key):
            try:
                if   key == Key.f1: self.root.after(0, self.toggle_spam)
                elif key == Key.f2: self.root.after(0, self.toggle_tame)
                elif key == Key.f3: self.root.after(0, self.toggle_macro)
                elif key == Key.f4: self.root.after(0, self.toggle_record)
                elif key == Key.f5: self.root.after(0, self.toggle_play)
                else:
                    kname = KEY_NAMES.get(key) or _k2s(key)
                    if kname.lower() == self._panic_key.lower():
                        self.root.after(0, self.stop_all)
            except: pass
        lst = KbListener(on_press=on_press)
        lst.daemon = True
        lst.start()

    # ── Language ───────────────────────────────────────────────
    def _switch_lang(self, nl):
        if nl == self.lang: return
        cfg = load_cfg(); cfg["lang"] = nl; save_cfg(cfg)
        self.spam_running = self.tame_running = self.macro_running = False
        self.rec_running  = self.play_running = False
        self.root.after(120, self._restart)

    def _restart(self):
        self.root.destroy()
        root = tk.Tk()
        MacroApp(root, lang=load_cfg().get("lang","de"))
        root.mainloop()

    # ── Auto-Update ────────────────────────────────────────────
    def _check_update(self):
        try:
            with urllib.request.urlopen(VERSION_URL, timeout=6) as r:
                latest = r.read().decode().strip()
            if latest != VERSION:
                self.root.after(0, lambda: self._upd_avail(latest))
            else:
                self.root.after(0, lambda: self.upd_lbl.config(
                    text=f"v{VERSION}  ·  {self.t('st_ok')}", fg=GREEN))
        except:
            self.root.after(0, lambda: self.upd_lbl.config(
                text=f"v{VERSION}  ·  {self.t('st_no_net')}", fg=MUTED))

    def _upd_avail(self, latest):
        self.upd_lbl.config(
            text=f"v{VERSION}  →  v{latest}  {self.t('upd_click')}",
            fg=AMBER, cursor="hand2")
        self.upd_lbl.bind("<Button-1>", lambda e: self._ask_upd(latest))

    def _ask_upd(self, latest):
        if messagebox.askyesno(self.t("upd_title"),
                               self.t("upd_msg").format(v=latest), parent=self.root):
            self.upd_lbl.config(text=self.t("downloading"), fg=ORANGE, cursor="arrow")
            self.upd_lbl.unbind("<Button-1>")
            threading.Thread(target=lambda: self._download(latest), daemon=True).start()

    def _download(self, latest):
        try:
            req = urllib.request.Request(RELEASE_URL,
                  headers={"Accept":"application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            assets = data.get("assets", [])

            # Prefer installer → silent install; fall back to raw exe swap (legacy)
            setup_url = next((a["browser_download_url"] for a in assets
                              if a["name"] == "SoupMacro_Setup.exe"), None)
            raw_url   = next((a["browser_download_url"] for a in assets
                              if a["name"] == "SoupMacro.exe"), None)
            url          = setup_url or raw_url
            is_installer = setup_url is not None
            if not url: raise RuntimeError("No download asset found in release.")

            new = tempfile.mktemp(suffix=".exe")
            def _p(c, b, tot):
                if tot > 0:
                    pct = min(100, int(c*b*100/tot))
                    self.root.after(0, lambda p=pct:
                        self.upd_lbl.config(text=f"{self.t('downloading')} {p}%", fg=ORANGE))
            urllib.request.urlretrieve(url, new, reporthook=_p)
            self.root.after(0, lambda: self.upd_lbl.config(text=self.t("upd_done"), fg=GREEN))

            if is_installer:
                # Run installer silently — replaces exe, keeps config in %APPDATA%
                subprocess.Popen([new, "/VERYSILENT", "/NORESTART"])
            else:
                # Legacy: batch-swap raw exe
                exe = sys.executable
                bat = tempfile.mktemp(suffix=".bat")
                with open(bat, "w") as f:
                    f.write(f'@echo off\ntimeout /t 2 /nobreak>nul\n'
                            f'move /y "{new}" "{exe}"\nstart "" "{exe}"\ndel "%~f0"\n')
                subprocess.Popen(["cmd","/c",bat], creationflags=subprocess.CREATE_NO_WINDOW)
            self.root.after(1500, self.root.destroy)
        except Exception as ex:
            self.root.after(0, lambda: messagebox.showerror(
                self.t("error"), str(ex), parent=self.root))


# ── Key/Button helpers ────────────────────────────────────────
def _k2s(k):
    try:    return k.char or str(k)
    except: return str(k)

def _s2k(s):
    if not s: return None
    if s.startswith("Key."): return getattr(Key, s[4:], None)
    if len(s)==1: return s
    return SPECIAL_KEYS.get(s.lower())

def _b2s(b): return str(b)
def _s2b(s): return getattr(Button, s.replace("Button.",""), Button.left)


if __name__ == "__main__":
    cfg  = load_cfg()
    root = tk.Tk()
    MacroApp(root, lang=cfg.get("lang","de"))
    root.mainloop()
