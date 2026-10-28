"""Generate placeholder MP4 takes for every shot in a shots.json. Useful for
M4 end-to-end testing without paying for Seedance renders on every shot.

Each placeholder is a solid-colour 1280x720 24fps H.264 no-audio clip whose
duration matches the shot. Colours are kind-dependent so you can spot them
in a timeline: opening=slate, room=teal, exterior=olive. The {shot_id}, kind
and duration are burned into the filename only (no in-video label — the
edit worker handles overlays).

Usage:
    python scripts/make_placeholder_takes.py \\
        --shots fixtures/plans/<name>/shots.json \\
        --out   _live_m4/takes/ \\
        [--skip-existing]           # don't overwrite files already there
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

COLORS = {
    "opening":  "0x334155",   # slate
    "room":     "0x14b8a6",   # teal
    "exterior": "0x84cc16",   # olive
}


def make_clip(out_path: Path, duration_s: float, hex_color: str) -> None:
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"color=c={hex_color}:s=1280x720:d={duration_s}:r=24",
        "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(prog="make_placeholder_takes")
    ap.add_argument("--shots", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()

    doc = json.loads(args.shots.read_text())
    args.out.mkdir(parents=True, exist_ok=True)

    for shot in doc["shots"]:
        out_file = args.out / f"{shot['id']}.mp4"
        if args.skip_existing and out_file.exists():
            print(f"skip  {out_file.name}  (already present, {out_file.stat().st_size} bytes)", file=sys.stderr)
            continue
        color = COLORS.get(shot["kind"], "0x6b7280")
        duration = float(shot["camera"]["duration_s"])
        make_clip(out_file, duration, color)
        print(f"wrote {out_file.name}  kind={shot['kind']}  {duration}s  {color}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
