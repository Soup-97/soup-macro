<div align="center">

<img src="logo.png" width="80" alt="Soup Macro logo">

# Soup Macro

**A lightweight Windows macro automation tool built with Python & tkinter**

[![Version](https://img.shields.io/badge/version-1.7-34d399?style=flat-square)](https://github.com/Soup-97/soup-macro/releases/latest)
[![Python](https://img.shields.io/badge/python-3.10%2B-818cf8?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-c084fc?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-fb923c?style=flat-square&logo=windows&logoColor=white)](https://github.com/Soup-97/soup-macro/releases/latest/download/SoupMacro_Setup.exe)
[![VirusTotal](https://img.shields.io/badge/VirusTotal-0%20%2F%2072-34d399?style=flat-square&logo=virustotal&logoColor=white)](https://www.virustotal.com/gui/url/4cd4a724e55a9600f3a3eeb04ee2d28826960dfb2c43d41e643c88647cb92a84?nocache=1)

[**Download Installer**](https://github.com/Soup-97/soup-macro/releases/latest/download/SoupMacro_Setup.exe) · [**Website**](https://soup-97.github.io/soup-macro) · [**Changelog**](https://soup-97.github.io/soup-macro/changelog.html)

</div>

---

## Features

| Mode | What it does |
|------|-------------|
| ⚡ **Spam** | Rapid-fire single or multi-key pressing with fixed, random or burst intervals |
| 🎯 **Tame** | Alternating two-key sequence (tame → press → wait → repeat) |
| 🛠 **Macro** | Build custom step-based sequences: key presses, waits, clicks, text typing, scrolling |
| ⏺ **Recording** | Record keyboard + mouse events and play them back at adjustable speed |

**Plus:**
- 🌐 Bilingual UI — English & German, auto-detects browser/system language
- 🔔 Sound feedback on start/stop
- 🛡 Overlay window — always-on-top status display
- 📥 System Tray — minimize and keep running in the background
- ⏸ Auto-Pause — pauses automatically when a specific window is active
- 💾 Profiles — save and load all settings (including macros & recordings) as `.json`
- 🕐 Recent Profiles — quick-access list of the last 5 used profiles
- 🔁 Auto-Update — checks GitHub Releases on startup and installs silently
- 🪟 Autostart with Windows — optional registry entry in Settings
- 📤 Settings Export / Import — back up everything as one JSON file
- 🧠 Window position memory — restores last position on launch

---

## Hotkeys

| Key | Action |
|-----|--------|
| `F1` | Toggle Spam |
| `F2` | Toggle Tame |
| `F3` | Toggle Macro |
| `F4` | Toggle Recording |
| `F5` | Toggle Playback |
| `F12` | **Stop All** (Panic key — configurable) |

> Hotkeys work globally in any window while Soup Macro is running.

---

## Installation

### Option A — Installer (recommended)

1. Download **[SoupMacro_Setup.exe](https://github.com/Soup-97/soup-macro/releases/latest/download/SoupMacro_Setup.exe)** from the latest release
2. Run the installer — it creates Start Menu and optional Desktop shortcuts
3. Launch **Soup Macro**

### Option B — Portable `.exe`

Download **[SoupMacro.exe](https://github.com/Soup-97/soup-macro/releases/latest/download/SoupMacro.exe)** and run it directly — no installation needed.

> **Windows Defender / Antivirus warning?**
> The executable is not yet code-signed (signing costs money). It is fully open-source and scanned clean by
> [VirusTotal (0/72)](https://www.virustotal.com/gui/url/4cd4a724e55a9600f3a3eeb04ee2d28826960dfb2c43d41e643c88647cb92a84?nocache=1).
> Click *More info → Run anyway* to proceed.

---

## Running from Source

```bash
# 1. Clone
git clone https://github.com/Soup-97/soup-macro.git
cd soup-macro

# 2. Install dependencies
pip install pynput pillow pystray

# 3. Run
python macro_tool.py
```

**Requirements:** Python 3.10+, Windows 10/11

---

## Building the Installer

```bash
# Install build tools
pip install pyinstaller pillow pynput pystray

# Run the build script (requires Inno Setup 6)
build.bat
```

`build.bat` will:
1. Generate `logo.ico` from `logo.png`
2. Bundle everything into `dist/SoupMacro.exe` via PyInstaller
3. Create `Output/SoupMacro_Setup.exe` via Inno Setup

---

## Macro Step Types

| Step | Description |
|------|-------------|
| ▶ **Key Press** | Tap a keyboard key (supports special keys: `enter`, `space`, `f1`–`f12`, …) |
| ⏱ **Wait** | Pause for N seconds |
| 🖱 **Click** | Left or right click at absolute screen coordinates |
| ⌨ **Type Text** | Type a full string character by character |
| 🖱 **Scroll** | Scroll the mouse wheel up or down by N notches |
| 💬 **Label** | Comment/marker — displayed in the list, skipped during execution |

---

## Configuration

Settings are stored in `%APPDATA%\SoupMacro\config.json` — survives updates and is writable without admin rights.

| Setting | Description |
|---------|-------------|
| Language | DE / EN — persisted across sessions |
| Panic Key | Configurable global stop key (default `F12`) |
| Sound | Beep on start/stop toggle |
| Auto-Pause | Pause when a specific window title is active |
| Autostart | Launch with Windows via registry |

---

## Project Structure

```
soup-macro/
├── macro_tool.py       # Main application
├── build.bat           # Build script (PyInstaller + Inno Setup)
├── setup.iss           # Inno Setup configuration
├── make_icon.py        # logo.png → logo.ico converter
├── logo.png            # App icon
├── version.txt         # Current version string (used by auto-update)
└── docs/               # GitHub Pages website
    ├── index.html
    ├── changelog.html
    ├── impressum.html
    └── datenschutz.html
```

---

## Tech Stack

- **Python 3** — application logic
- **tkinter** — GUI (custom Canvas widgets, scrollable frames)
- **pynput** — global keyboard & mouse listeners/controllers
- **Pillow** — icon loading and tray image generation
- **pystray** — system tray integration
- **PyInstaller** — single-file `.exe` bundling
- **Inno Setup 6** — Windows installer

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
Made with ☕ by <a href="https://github.com/Soup-97">Soup-97</a>
</div>
