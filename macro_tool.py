import tkinter as tk
from tkinter import messagebox
import threading
import time
import sys
import os
import json
import subprocess
import tempfile
import urllib.request
from PIL import Image, ImageTk
from pynput.keyboard import Key, Controller, Listener

# ── Version & Update-Config ────────────────────────────────
VERSION      = "1.0"
GITHUB_USER  = "FunkelVult"
GITHUB_REPO  = "soup-macro"
VERSION_URL  = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.txt"
RELEASE_URL  = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

# ── Resource path (funktioniert auch als .exe) ─────────────
def res(path):
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, path)

# ── Farben ──────────────────────────────────────────────────
BG        = "#0b0b13"
CARD      = "#13131f"
BORDER    = "#252538"
GREEN     = "#27c96a"
BLUE      = "#5b9cf6"
RED       = "#e05252"
ORANGE    = "#f0a040"
YELLOW    = "#f5c542"
TEXT      = "#dde2ff"
SUBTEXT   = "#60607a"
INPUT_BG  = "#1e1e30"
INPUT_FG  = "#c8ceff"


class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soup Macro")
        self.root.geometry("460x680")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.spam_running = False
        self.tame_running = False
        self.keyboard = Controller()
        self.tame_phase = ""
        self.tame_countdown = 0.0

        self._load_icons()
        self._build()
        self._hotkeys()
        self._tick()

        # Update-Check im Hintergrund starten
        threading.Thread(target=self._check_update, daemon=True).start()

    # ── Icons ───────────────────────────────────────────────
    def _load_icons(self):
        self.logo_tk = self.icon_tk = None
        try:
            raw = Image.open(res("logo.png")).convert("RGBA")
            self.logo_tk = ImageTk.PhotoImage(raw.resize((52, 52), Image.NEAREST))
            self.icon_tk = ImageTk.PhotoImage(raw.resize((32, 32), Image.NEAREST))
            self.root.iconphoto(True, self.icon_tk)
        except Exception:
            pass

    # ── UI ──────────────────────────────────────────────────
    def _build(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=22, pady=(20, 6))

        if self.logo_tk:
            tk.Label(hdr, image=self.logo_tk, bg=BG).pack(side="left", padx=(0, 14))

        txt = tk.Frame(hdr, bg=BG)
        txt.pack(side="left", anchor="center")
        tk.Label(txt, text="Soup Macro",
                 font=("Segoe UI", 24, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(txt, text="F1  ·  Spam        F2  ·  Tame        F12  ·  Stop",
                 font=("Segoe UI", 8), bg=BG, fg=SUBTEXT).pack(anchor="w")

        # Update-Statuszeile
        self.update_lbl = tk.Label(
            self.root, text=f"v{VERSION}  ·  Suche nach Updates...",
            font=("Segoe UI", 8), bg=BG, fg=SUBTEXT, cursor="arrow"
        )
        self.update_lbl.pack(anchor="e", padx=22)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=22, pady=(6, 14))

        # SPAM Card
        s = self._card(self.root, "SPAM MODUS")
        row1 = tk.Frame(s, bg=CARD)
        row1.pack(fill="x", padx=16, pady=(0, 10))
        self._field(row1, "Taste", "spam_key", "1").pack(side="left", padx=(0, 24))
        self._field(row1, "Intervall (ms)", "spam_interval", 10, spin=(1, 5000, 1)).pack(side="left")
        self.spam_btn = self._mkbtn(s, "▶   Start Spam   (F1)", GREEN, self.toggle_spam)
        self.spam_btn.pack(fill="x", padx=16, pady=(0, 8))
        self.spam_lbl = tk.Label(s, text="⬤  Gestoppt",
                                  font=("Segoe UI", 9), bg=CARD, fg=RED)
        self.spam_lbl.pack(pady=(0, 14))

        # TAME Card
        t = self._card(self.root, "TAME MODUS")
        row2 = tk.Frame(t, bg=CARD)
        row2.pack(fill="x", padx=16, pady=(0, 8))
        self._field(row2, "Tame-Taste", "tame_key", "2").pack(side="left", padx=(0, 24))
        self._field(row2, "Warten (s)", "tame_wait1", 7.0, spin=(0.5, 120.0, 0.5)).pack(side="left")
        row3 = tk.Frame(t, bg=CARD)
        row3.pack(fill="x", padx=16, pady=(0, 10))
        self._field(row3, "Drück-Taste", "press_key", "1").pack(side="left", padx=(0, 24))
        self._field(row3, "Warten (s)", "tame_wait2", 3.0, spin=(0.5, 120.0, 0.5)).pack(side="left")
        self.tame_btn = self._mkbtn(t, "▶   Start Tame   (F2)", BLUE, self.toggle_tame)
        self.tame_btn.pack(fill="x", padx=16, pady=(0, 8))
        self.tame_lbl = tk.Label(t, text="⬤  Gestoppt",
                                  font=("Segoe UI", 9), bg=CARD, fg=RED)
        self.tame_lbl.pack()
        self.cd_lbl = tk.Label(t, text="", font=("Segoe UI", 9), bg=CARD, fg=ORANGE)
        self.cd_lbl.pack(pady=(2, 14))

        # Stop-Button
        stop = self._mkbtn(self.root, "⏹   ALLE STOPPEN   (F12)", RED, self.stop_all)
        stop.configure(fg=TEXT, activeforeground=TEXT)
        stop.pack(fill="x", padx=22, pady=14)

    # ── Widget-Helfer ───────────────────────────────────────

    def _card(self, parent, title):
        wrap = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        wrap.pack(fill="x", padx=22, pady=5)
        inner = tk.Frame(wrap, bg=CARD)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=title, font=("Segoe UI", 7, "bold"),
                 bg=CARD, fg=SUBTEXT, anchor="w").pack(fill="x", padx=16, pady=(12, 6))
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(0, 10))
        return inner

    def _field(self, parent, label, attr, default, spin=None):
        f = tk.Frame(parent, bg=CARD)
        tk.Label(f, text=label, font=("Segoe UI", 8),
                 bg=CARD, fg=SUBTEXT).pack(anchor="w")
        if spin:
            lo, hi, inc = spin
            var = tk.DoubleVar(value=default) if isinstance(default, float) else tk.IntVar(value=default)
            w = tk.Spinbox(f, from_=lo, to=hi, increment=inc, textvariable=var,
                           width=11, font=("Segoe UI", 10),
                           bg=INPUT_BG, fg=INPUT_FG, relief="flat",
                           buttonbackground=BORDER, insertbackground=TEXT,
                           highlightthickness=1, highlightbackground=BORDER,
                           highlightcolor=BLUE)
        else:
            var = tk.StringVar(value=str(default))
            w = tk.Entry(f, textvariable=var, width=11, font=("Segoe UI", 10),
                         bg=INPUT_BG, fg=INPUT_FG, relief="flat",
                         insertbackground=TEXT,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=BLUE)
        w.pack(ipady=5)
        setattr(self, attr, var)
        return f

    def _mkbtn(self, parent, text, color, cmd):
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=color, fg="#0b0b13",
                        font=("Segoe UI", 10, "bold"),
                        relief="flat", cursor="hand2", bd=0,
                        activebackground=color, activeforeground="#0b0b13")
        btn.configure(height=2)
        btn.bind("<Enter>", lambda e: btn.config(bg=self._lighten(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn

    @staticmethod
    def _lighten(hex_color, amount=30):
        r = min(int(hex_color[1:3], 16) + amount, 255)
        g = min(int(hex_color[3:5], 16) + amount, 255)
        b = min(int(hex_color[5:7], 16) + amount, 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ── Auto-Update ─────────────────────────────────────────

    def _check_update(self):
        try:
            with urllib.request.urlopen(VERSION_URL, timeout=6) as r:
                latest = r.read().decode().strip()
            if latest != VERSION:
                self.root.after(0, lambda: self._update_available(latest))
            else:
                self.root.after(0, lambda: self.update_lbl.config(
                    text=f"v{VERSION}  ·  Aktuell", fg=SUBTEXT))
        except Exception:
            self.root.after(0, lambda: self.update_lbl.config(
                text=f"v{VERSION}  ·  Kein Internet", fg=SUBTEXT))

    def _update_available(self, latest):
        self.update_lbl.config(
            text=f"v{VERSION}  →  v{latest} verfügbar!  Klicken zum Updaten",
            fg=YELLOW, cursor="hand2"
        )
        self.update_lbl.bind("<Button-1>", lambda e: self._ask_update(latest))

    def _ask_update(self, latest):
        if messagebox.askyesno(
            "Update verfügbar",
            f"Version {latest} ist verfügbar!\n\nJetzt herunterladen und installieren?",
            parent=self.root
        ):
            self.update_lbl.config(text="Lade Update herunter...", fg=ORANGE, cursor="arrow")
            self.update_lbl.unbind("<Button-1>")
            threading.Thread(target=lambda: self._download(latest), daemon=True).start()

    def _download(self, latest):
        try:
            # Download-URL aus GitHub API holen
            req = urllib.request.Request(RELEASE_URL,
                                         headers={"Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())

            url = next(
                (a["browser_download_url"] for a in data.get("assets", [])
                 if a["name"] == "SoupMacro.exe"),
                None
            )
            if not url:
                raise RuntimeError("SoupMacro.exe nicht im Release gefunden.")

            exe = sys.executable
            new_exe = exe + ".new"

            def _progress(count, block, total):
                if total > 0:
                    pct = min(100, int(count * block * 100 / total))
                    self.root.after(0, lambda p=pct: self.update_lbl.config(
                        text=f"Lade herunter...  {p}%", fg=ORANGE))

            urllib.request.urlretrieve(url, new_exe, reporthook=_progress)

            # Batch-Script erstellt sich selbst: wartet, tauscht .exe aus, startet neu
            bat = tempfile.mktemp(suffix=".bat")
            with open(bat, "w") as f:
                f.write(
                    f'@echo off\n'
                    f'timeout /t 2 /nobreak > nul\n'
                    f'move /y "{new_exe}" "{exe}"\n'
                    f'start "" "{exe}"\n'
                    f'del "%~f0"\n'
                )

            self.root.after(0, lambda: self.update_lbl.config(
                text="Update abgeschlossen! Neustart...", fg=GREEN))

            subprocess.Popen(
                ["cmd", "/c", bat],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.root.after(1500, self.root.destroy)

        except Exception as ex:
            self.root.after(0, lambda: messagebox.showerror(
                "Update fehlgeschlagen", str(ex), parent=self.root))
            self.root.after(0, lambda: self.update_lbl.config(
                text=f"v{VERSION}  ·  Update fehlgeschlagen", fg=RED))

    # ── Macro-Logik ─────────────────────────────────────────

    def toggle_spam(self):
        if self.spam_running:
            self.spam_running = False
            self.spam_btn.config(text="▶   Start Spam   (F1)", bg=GREEN)
            self.spam_lbl.config(text="⬤  Gestoppt", fg=RED)
        else:
            self.spam_running = True
            self.spam_btn.config(text="⏸   Stop Spam   (F1)", bg=ORANGE)
            self.spam_lbl.config(text="⬤  Läuft...", fg=GREEN)
            threading.Thread(target=self._spam_loop, daemon=True).start()

    def toggle_tame(self):
        if self.tame_running:
            self.tame_running = False
            self.tame_btn.config(text="▶   Start Tame   (F2)", bg=BLUE)
            self.tame_lbl.config(text="⬤  Gestoppt", fg=RED)
        else:
            self.tame_running = True
            self.tame_btn.config(text="⏸   Stop Tame   (F2)", bg=ORANGE)
            self.tame_lbl.config(text="⬤  Läuft...", fg=GREEN)
            threading.Thread(target=self._tame_loop, daemon=True).start()

    def stop_all(self):
        self.spam_running = False
        self.tame_running = False
        self.root.after(0, self._ui_reset)

    def _ui_reset(self):
        self.spam_btn.config(text="▶   Start Spam   (F1)", bg=GREEN)
        self.spam_lbl.config(text="⬤  Gestoppt", fg=RED)
        self.tame_btn.config(text="▶   Start Tame   (F2)", bg=BLUE)
        self.tame_lbl.config(text="⬤  Gestoppt", fg=RED)
        self.cd_lbl.config(text="")

    def _spam_loop(self):
        while self.spam_running:
            try:
                self.keyboard.tap(self.spam_key.get())
            except Exception:
                pass
            time.sleep(self.spam_interval.get() / 1000.0)

    def _tame_loop(self):
        while self.tame_running:
            try:
                self.keyboard.tap(self.tame_key.get())
            except Exception:
                pass
            self.tame_phase = "tame"
            self._wait(self.tame_wait1.get())
            if not self.tame_running:
                break
            try:
                self.keyboard.tap(self.press_key.get())
            except Exception:
                pass
            self.tame_phase = "press"
            self._wait(self.tame_wait2.get())
        self.tame_phase = ""
        self.tame_countdown = 0.0

    def _wait(self, seconds):
        end = time.time() + seconds
        while self.tame_running and time.time() < end:
            self.tame_countdown = end - time.time()
            time.sleep(0.05)

    def _tick(self):
        if self.tame_running and self.tame_phase:
            label = "Warte nach Tame" if self.tame_phase == "tame" else "Warte nach Drücken"
            filled = max(0, min(10, round(self.tame_countdown / 10 * 10)))
            bar = "█" * filled + "░" * (10 - filled)
            self.cd_lbl.config(text=f"{label}  ·  {self.tame_countdown:.1f}s   {bar}")
        else:
            self.cd_lbl.config(text="")
        self.root.after(100, self._tick)

    def _hotkeys(self):
        def on_press(key):
            try:
                if key == Key.f1:
                    self.root.after(0, self.toggle_spam)
                elif key == Key.f2:
                    self.root.after(0, self.toggle_tame)
                elif key == Key.f12:
                    self.root.after(0, self.stop_all)
            except Exception:
                pass
        lst = Listener(on_press=on_press)
        lst.daemon = True
        lst.start()


if __name__ == "__main__":
    root = tk.Tk()
    MacroApp(root)
    root.mainloop()
