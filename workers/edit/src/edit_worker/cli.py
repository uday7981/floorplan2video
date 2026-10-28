"""edit CLI.

  python -m edit_worker \\
      --plan     plan.json \\
      --shots    shots.json \\
      --takes-dir path/to/takes/ \\
      --project-name "Oakhill Residence" \\
      --out      path/to/final.mp4 \\
      [--captions-json captions.json] [--font /path/to/font.ttf]

Takes-dir convention: one file per shot named <shot_id>.mp4 (fallback:
<shot_id>_take.mp4). Shots skipped if no file is found.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

from .ffmpeg_run import extract_last_frame, ffprobe, run_ffmpeg
from .labels import end_card_text, label_for_shot
from .stitch import (
    TakeSpec,
    build_endcard_filtergraph,
    build_stitch_filtergraph,
    pick_font,
)

log = logging.getLogger("edit_worker")


def _find_take(takes_dir: Path, shot_id: str) -> Path | None:
    for name in (f"{shot_id}.mp4", f"{shot_id}_take.mp4"):
        p = takes_dir / name
        if p.exists():
            return p
    return None


def _collect(shots: list[dict], takes_dir: Path, project_name: str,
             captions: dict[str, str]) -> list[TakeSpec]:
    out: list[TakeSpec] = []
    for shot in sorted(shots, key=lambda s: s["ord"]):
        p = _find_take(takes_dir, shot["id"])
        if p is None:
            log.warning("no take for shot %s under %s — skipping", shot["id"], takes_dir)
            continue
        label = label_for_shot(shot, project_name, captions)
        out.append(TakeSpec(
            source_path=str(p),
            duration_s=float(shot["camera"]["duration_s"]),
            label_text=label,
        ))
    return out


def _stitch(takes: list[TakeSpec], font: str | None, work: Path) -> Path:
    """Run the normalise+overlay+xfade pass. Returns path to stitched.mp4."""
    fg, final_label, total = build_stitch_filtergraph(takes, font)
    log.info("stitch filtergraph total duration = %.3fs", total)
    out = work / "stitched.mp4"
    inputs: list[str] = []
    for t in takes:
        inputs += ["-i", t.source_path]
    run_ffmpeg([
        *inputs,
        "-filter_complex", fg,
        "-map", f"[{final_label}]",
        "-r", "24",
        "-c:v", "libx264", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(out),
    ])
    return out


def _make_endcard(stitched: Path, project_name: str, font: str | None,
                  work: Path, duration_s: float = 2.0) -> Path:
    """Grab the last frame of stitched.mp4, build a 2s endcard clip."""
    last_png = work / "last_frame.png"
    extract_last_frame(stitched, last_png)
    out = work / "endcard.mp4"
    fg = build_endcard_filtergraph(str(last_png), project_name, font, duration_s)
    run_ffmpeg([
        "-loop", "1", "-i", str(last_png),
        "-filter_complex", fg,
        "-map", "[v]",
        "-t", f"{duration_s}",
        "-r", "24",
        "-c:v", "libx264", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(out),
    ])
    return out


def _concat(parts: list[Path], out_path: Path) -> None:
    """Concat-demuxer: fast, no re-encode. All parts must share codec params."""
    list_file = out_path.parent / "concat.txt"
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", "-movflags", "+faststart",
        str(out_path),
    ])
    list_file.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[edit] %(message)s")
    ap = argparse.ArgumentParser(prog="edit_worker")
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--shots", required=True, type=Path)
    ap.add_argument("--takes-dir", required=True, type=Path)
    ap.add_argument("--project-name", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--captions-json", type=Path, default=None,
                    help="JSON file: { shot_id: caption_text }")
    ap.add_argument("--font", default=None, help="path to a .ttf/.otf for drawtext")
    ap.add_argument("--endcard-duration", type=float, default=2.0)
    args = ap.parse_args(argv)

    _ = json.loads(args.plan.read_text())  # read for schema sanity even if unused
    shots_doc = json.loads(args.shots.read_text())
    captions: dict[str, str] = {}
    if args.captions_json and args.captions_json.exists():
        captions = json.loads(args.captions_json.read_text())
    font = pick_font(args.font)
    if font is None:
        log.warning("no font found; drawtext will use ffmpeg's internal default")

    takes = _collect(shots_doc["shots"], args.takes_dir, args.project_name, captions)
    if not takes:
        log.error("no takes found in %s", args.takes_dir)
        return 2
    log.info("stitching %d take(s) into %s", len(takes), args.out)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="edit_") as tmp:
        work = Path(tmp)
        stitched = _stitch(takes, font, work)
        endcard = _make_endcard(stitched, end_card_text(args.project_name),
                                font, work, args.endcard_duration)
        _concat([stitched, endcard], args.out)

    info = ffprobe(args.out)
    log.info("wrote %s  %dx%d  %.1ffps  duration=%.2fs",
             args.out, info.width, info.height, info.fps, info.duration_s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
