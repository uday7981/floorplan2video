"""Generate tiny test assets for the M0 Seedance spike.

Produces, under scripts/_spike_assets/ :
  start.png  — 480p solid-ish image labelled "START"
  end.png    — 480p solid-ish image labelled "END"
  driving.mp4 — 2-second 480p MP4 that pans between the two colours

Everything is procedural; no paid API calls here.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
except ImportError:
    print("Missing Pillow. Install with: pip install Pillow", file=sys.stderr)
    raise

OUT = Path(__file__).parent / "_spike_assets"
W, H = 854, 480  # 480p @ 16:9


def _write_frame(path: Path, rgb: tuple[int, int, int], label: str) -> None:
    img = Image.new("RGB", (W, H), rgb)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 72)
    except OSError:
        font = ImageFont.load_default()
    tw = draw.textlength(label, font=font)
    draw.text(((W - tw) // 2, H // 2 - 36), label, fill=(255, 255, 255), font=font)
    img.save(path, "PNG")


def main() -> int:
    if shutil.which("ffmpeg") is None:
        print("ffmpeg not on PATH. Install ffmpeg to generate the driving clip.", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    start = OUT / "start.png"
    end = OUT / "end.png"
    drive = OUT / "driving.mp4"

    _write_frame(start, (40, 60, 120), "START")
    _write_frame(end,   (120, 60, 40), "END")

    # 2 s, 24 fps, 480p MP4: smooth crossfade from start to end.
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", "2", "-i", str(start),
        "-loop", "1", "-t", "2", "-i", str(end),
        "-filter_complex",
        "[0:v]format=yuv420p[a];[1:v]format=yuv420p[b];"
        "[a][b]xfade=transition=fade:duration=1.5:offset=0.25[v]",
        "-map", "[v]", "-r", "24", "-t", "2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(drive),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return proc.returncode

    for p in (start, end, drive):
        print(f"wrote {p}  ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
