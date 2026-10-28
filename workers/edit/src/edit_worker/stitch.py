"""Build the ffmpeg filter_complex that normalises each take, overlays its
label, and xfade-joins them in order. Pure string manipulation — no ffmpeg
process is spawned here (tests can assert the string without the binary).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

WIDTH = 1280
HEIGHT = 720
FPS = 24
XFADE_DUR = 0.3


@dataclass
class TakeSpec:
    """One take as the filtergraph builder sees it."""
    source_path: str          # input mp4
    duration_s: float
    label_text: str           # overlay drawtext (may be empty)


def _escape_drawtext_text(text: str) -> str:
    """Escape chars that drawtext treats specially."""
    return (text.replace("\\", r"\\")
                .replace("'", r"\'")
                .replace(":", r"\:")
                .replace("%", r"\%"))


def _drawtext_label(text: str, font_path: str | None,
                    position: str = "bottom-left", fontsize: int = 36) -> str:
    """Return a drawtext filter string for a label on a video."""
    escaped = _escape_drawtext_text(text)
    opts = [
        f"text='{escaped}'",
        "fontcolor=white",
        f"fontsize={fontsize}",
        "box=1",
        "boxcolor=black@0.45",
        "boxborderw=10",
    ]
    if position == "bottom-left":
        opts += ["x=40", "y=h-th-40"]
    elif position == "center":
        opts += ["x=(w-text_w)/2", "y=(h-text_h)/2"]
    else:
        raise ValueError(f"unknown drawtext position {position!r}")
    if font_path:
        opts.append(f"fontfile='{font_path}'")
    return "drawtext=" + ":".join(opts)


def _normalise_chain(idx: int, text: str, font_path: str | None) -> str:
    """scale → letterbox → fps → sar=1 → yuv420p → optional drawtext."""
    base = (
        f"[{idx}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},setsar=1,format=yuv420p"
    )
    if text:
        base += "," + _drawtext_label(text, font_path, position="bottom-left")
    return f"{base}[v{idx}]"


def build_stitch_filtergraph(takes: list[TakeSpec],
                             font_path: str | None) -> tuple[str, str, float]:
    """Return (filter_complex_str, final_label, total_duration_s).

    filter_complex_str is suitable for `ffmpeg -filter_complex "..."`.
    final_label is the output pad name (e.g. "xf3" or "v0" if N==1).
    total_duration_s is the duration after all xfade overlaps.
    """
    if not takes:
        raise ValueError("no takes to stitch")

    parts: list[str] = [_normalise_chain(i, t.label_text, font_path)
                        for i, t in enumerate(takes)]

    if len(takes) == 1:
        return ";".join(parts), "v0", float(takes[0].duration_s)

    cumulative = float(takes[0].duration_s)
    prev = "v0"
    for i in range(1, len(takes)):
        offset = cumulative - XFADE_DUR
        new = f"xf{i}"
        parts.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={XFADE_DUR}:offset={offset:.3f}[{new}]"
        )
        cumulative = cumulative + takes[i].duration_s - XFADE_DUR
        prev = new

    return ";".join(parts), prev, cumulative


def build_endcard_filtergraph(bg_last_frame_png: str, project_name: str,
                              font_path: str | None,
                              duration_s: float = 2.0) -> str:
    """Filter_complex for a 2s endcard clip from a still PNG + centered title."""
    text = _drawtext_label(project_name, font_path, position="center", fontsize=60)
    return (
        f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={duration_s},"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},setsar=1,format=yuv420p,{text}[v]"
    )


def pick_font(explicit: str | None = None) -> str | None:
    """Try common font paths across macOS + Linux (RunPod)."""
    import os
    if explicit and os.path.exists(explicit):
        return explicit
    candidates = [
        # Linux (ffmpeg deps on Ubuntu install dejavu)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None
