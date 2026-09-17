# yt-dlp-gui-windows

A minimal, thread-safe Windows frontend for `yt-dlp`. I wrote this because I got tired of copying URLs to the terminal and typing out format selection arguments every time, and the existing GUI wrappers are either heavy Electron apps or abandoned projects.

It runs `yt-dlp` in a background worker thread, parses its JSON output to let you pick resolutions/formats, and streams stdout directly to a logging pane in the GUI without freezing the window.

## Prerequisites

- Windows 10 or 11
- Python 3.10+
- `yt-dlp` installed and available in your PATH (or placed directly in the same directory as this script).
- `ffmpeg` in your PATH if you want to merge audio/video formats.

## Installation

Clone the repository and install the single dependency:

```cmd
pip install -r requirements.txt
```

## How to run

You can launch it directly from the terminal:

```cmd
python gui.py
```

If you already have a URL in your clipboard, you can pass it as an argument to pre-populate the field:

```cmd
python gui.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Or you can create a shortcut to `pythonw.exe gui.py` on your Desktop to launch it without a background command prompt.

<!-- refreshed: 2026-09-17 -->
