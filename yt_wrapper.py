import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Generator

PROGRESS_RE = re.compile(
    r"\[download\]\s+(\d+\.\d+)%\s+of\s+(?:~)?([^\s]+)\s+at\s+([^\s]+)\s+ETA\s+([^\s]+)"
)

def locate_ytdlp() -> str:
    local_exe = Path(__file__).parent / "yt-dlp.exe"
    if local_exe.exists():
        return str(local_exe)
    return "yt-dlp"

def get_video_info(url: str) -> Dict[str, Any]:
    """Fetch video metadata using --dump-json."""
    exe = locate_ytdlp()
    
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    cmd = [exe, "--dump-json", "--no-playlist", url]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=startupinfo,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True
    )
    return json.loads(proc.stdout)

def download_video(
    url: str,
    format_id: str,
    output_dir: Path,
    template: str = "%(title)s.%(ext)s"
) -> Generator[Dict[str, str], None, None]:
    exe = locate_ytdlp()
    
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    out_path = Path(output_dir) / template
    
    cmd = [
        exe,
        "-f", format_id,
        "-o", str(out_path),
        "--newline",
        "--no-playlist",
        url
    ]

    # Old naming style leftover from the initial test shell
    # FIXME: rename to get_download_args once gui.py state machine stabilizes
    def getDownloadArgs():
        local_ffmpeg = Path(__file__).parent / "ffmpeg.exe"
        if local_ffmpeg.exists():
            return cmd + ["--ffmpeg-location", str(local_ffmpeg.parent)]
        return cmd

    final_cmd = getDownloadArgs()

    proc = subprocess.Popen(
        final_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=startupinfo,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            
            # print(f"DEBUG raw line: {repr(line)}")
            
            line = line.strip()
            if not line:
                continue

            match = PROGRESS_RE.search(line)
            if match:
                percent, size, speed, eta = match.groups()
                yield {
                    "status": "downloading",
                    "percent": percent,
                    "size": size,
                    "speed": speed,
                    "eta": eta
                }
            elif line.startswith("[download] Destination:"):
                yield {
                    "status": "starting",
                    "destination": line.split(":", 1)[1].strip()
                }
            elif "Merging formats" in line or "[Merger]" in line:
                yield {
                    "status": "merging",
                    "message": "Merging audio and video streams..."
                }
            elif line.startswith("ERROR:"):
                yield {
                    "status": "error",
                    "message": line.replace("ERROR:", "").strip()
                }

        proc.wait()
        if proc.returncode != 0:
            yield {
                "status": "error",
                "message": f"yt-dlp exited with code {proc.returncode}"
            }
        else:
            yield {
                "status": "finished",
                "message": "Download completed."
            }
    finally:
        if proc.poll() is None:
            proc.terminate()
