"""Journey hard-cut concat CLI (v2.0).

  python -m edit_worker.journey_cli \\
      --plan plan.json --journey journey.json \\
      --takes-dir path/to/takes/ \\
      --project-name "Oakhill Residence" \\
      --out path/to/final.mp4 \\
      [--boundary-blend-frames 0]           (0 default; 2–4 for visible seams)
      [--captions-json captions.json] [--font /path/to/font.ttf]

Takes-dir convention: one file per segment named seg_{ord:03d}.mp4.

Hard cuts on shared boundary frames by default. If a Seedance generation
missed its end-frame target slightly and the join flickers, pass
--boundary-blend-frames 2 (or 3, 4) to add a brief cross-fade between
consecutive segments. 24 fps, so 2 frames = ~0.08 s.

Labels appear as the camera enters each room: for multi-storey, format
"Floor name · 04 Bedroom"; for single-storey, "04 Bedroom".
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

from .ffmpeg_run import extract_last_frame, ffprobe, run_ffmpeg
from .labels import end_card_text
from .stitch import pick_font, _drawtext_label  # type: ignore

log = logging.getLogger("edit_worker.journey")

WIDTH = 1280
HEIGHT = 720
FPS = 24


def _take_for_segment(takes_dir: Path, seg_ord: int) -> Path | None:
    for name in (f"seg_{seg_ord:03d}.mp4", f"segment_{seg_ord:03d}.mp4"):
        p = takes_dir / name
        if p.exists():
            return p
    return None


def _room_label_for_segment(plan: dict, segment: dict) -> str | None:
    """Return the drawtext label for a segment, or None if no overlay.
    Multi-storey: 'First floor · 04 Bedroom'. Single-storey: '04 Bedroom'."""
    if segment["role"] not in ("walkthrough",):
        return None
    room_id = segment.get("to_room_id")
    if not room_id:
        return None
    # Find the room + its level
    room = None
    level = None
    for lvl in plan["levels"]:
        for r in lvl["rooms"]:
            if r["id"] == room_id:
                room = r
                level = lvl
                break
        if room:
            break
    if room is None:
        return None
    # Numbered room index across the whole journey (walkthrough segments only)
    label_base = room.get("name", room_id)
    if len(plan["levels"]) > 1 and level is not None:
        return f"{level.get('name', level['id'])} · {label_base}"
    return label_base


def _normalise_with_label(src: Path, dst: Path, label: str | None,
                          font_path: str | None) -> None:
    """Normalise one take to 1280x720 24fps h264 no-audio, with optional
    bottom-left room label drawtext."""
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},setsar=1,format=yuv420p"
    )
    if label:
        vf += "," + _drawtext_label(label, font_path, position="bottom-left")
    run_ffmpeg([
        "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-an",
        str(dst),
    ])


def _hard_concat(parts: list[Path], out_path: Path) -> None:
    """Concat demuxer: no re-encode; requires identical codec params."""
    list_file = out_path.parent / "concat.txt"
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", "-movflags", "+faststart", str(out_path),
    ])
    list_file.unlink(missing_ok=True)


def _crossblend_concat(parts: list[Path], out_path: Path, blend_frames: int) -> None:
    """Blended concat: xfade with a very short overlap (blend_frames / FPS seconds)
    between every pair of consecutive takes. More expensive — only when the
    boundary frames visibly mismatch."""
    if blend_frames <= 0 or len(parts) < 2:
        return _hard_concat(parts, out_path)
    blend_s = blend_frames / FPS
    inputs: list[str] = []
    for p in parts:
        inputs += ["-i", str(p)]
    # Build xfade chain
    durations = [ffprobe(p).duration_s for p in parts]
    parts_filter: list[str] = []
    for i in range(len(parts)):
        parts_filter.append(f"[{i}:v]format=yuv420p[v{i}]")
    cumulative = durations[0]
    prev = "v0"
    for i in range(1, len(parts)):
        offset = cumulative - blend_s
        new = f"x{i}"
        parts_filter.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={blend_s:.4f}:offset={offset:.4f}[{new}]"
        )
        cumulative = cumulative + durations[i] - blend_s
        prev = new
    fg = ";".join(parts_filter)
    run_ffmpeg([
        *inputs, "-filter_complex", fg,
        "-map", f"[{prev}]", "-r", str(FPS),
        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-an",
        str(out_path),
    ])


def _append_end_card(stitched: Path, title: str, font: str | None, out_path: Path,
                     duration_s: float = 2.0) -> None:
    """Grab the last frame BEFORE drawtext was applied, then make an end-card clip
    with the project title centred, concat it."""
    # The stitched file already has drawtext burned in; grab its last frame and
    # overlay the title in the centre. The spec notes this is a limitation —
    # proper fix is to render the end card from a clean copy, but for v2.0 we
    # overlay on top (title shows while the room label fades out naturally).
    import os
    tmp_dir = out_path.parent
    last_png = tmp_dir / "_last.png"
    extract_last_frame(stitched, last_png)
    end_card = tmp_dir / "_end_card.mp4"
    text = _drawtext_label(title, font, position="center", fontsize=60)
    fg = (
        f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={duration_s},"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},setsar=1,format=yuv420p,{text}[v]"
    )
    run_ffmpeg([
        "-loop", "1", "-i", str(last_png),
        "-filter_complex", fg,
        "-map", "[v]", "-t", f"{duration_s}",
        "-r", str(FPS),
        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-an",
        str(end_card),
    ])
    _hard_concat([stitched, end_card], out_path)
    last_png.unlink(missing_ok=True)
    end_card.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[edit.journey] %(message)s")
    ap = argparse.ArgumentParser(prog="edit_worker.journey_cli")
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--journey", required=True, type=Path)
    ap.add_argument("--takes-dir", required=True, type=Path)
    ap.add_argument("--project-name", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--boundary-blend-frames", type=int, default=0,
                    help="0 = hard cuts; 2-4 = brief cross-blend to hide boundary mismatches")
    ap.add_argument("--captions-json", type=Path, default=None)
    ap.add_argument("--font", default=None)
    ap.add_argument("--endcard-duration", type=float, default=2.0)
    args = ap.parse_args(argv)

    plan = json.loads(args.plan.read_text())
    journey = json.loads(args.journey.read_text())
    captions = json.loads(args.captions_json.read_text()) if args.captions_json and args.captions_json.exists() else {}
    font = pick_font(args.font)

    segs = sorted(journey["segments"], key=lambda s: int(s["ord"]))
    parts: list[Path] = []

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="edit_journey_") as tmp:
        work = Path(tmp)
        for seg in segs:
            src = _take_for_segment(args.takes_dir, int(seg["ord"]))
            if src is None:
                log.warning("no take for segment %d — skipping", seg["ord"])
                continue
            # Caption override wins; else auto-derived room label; else none.
            label = captions.get(seg["id"]) or _room_label_for_segment(plan, seg)
            dst = work / f"n_{seg['ord']:03d}.mp4"
            _normalise_with_label(src, dst, label, font)
            parts.append(dst)

        if not parts:
            log.error("no takes found")
            return 2

        stitched = work / "stitched.mp4"
        if args.boundary_blend_frames > 0:
            _crossblend_concat(parts, stitched, args.boundary_blend_frames)
        else:
            _hard_concat(parts, stitched)

        _append_end_card(stitched, end_card_text(args.project_name), font,
                         args.out, args.endcard_duration)

    info = ffprobe(args.out)
    log.info("wrote %s  %dx%d  %.1ffps  duration=%.2fs",
             args.out, info.width, info.height, info.fps, info.duration_s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
