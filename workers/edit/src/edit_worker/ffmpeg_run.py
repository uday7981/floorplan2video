"""Thin subprocess wrapper for ffmpeg + ffprobe. Keeps CLI argument assembly
and error reporting in one place.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


class FFmpegError(RuntimeError):
    pass


def _require(binary: str) -> str:
    path = shutil.which(binary)
    if path is None:
        raise FFmpegError(f"{binary} not on PATH")
    return path


def run_ffmpeg(args: list[str]) -> None:
    """Run ffmpeg with args; raise FFmpegError on non-zero exit."""
    cmd = [_require("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", *args]
    log.debug("+ %s", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise FFmpegError(f"ffmpeg failed (exit {r.returncode}):\n{r.stderr.strip()}")


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration_s: float


def ffprobe(path: Path) -> VideoInfo:
    cmd = [_require("ffprobe"), "-v", "error",
           "-select_streams", "v:0",
           "-show_entries", "stream=width,height,r_frame_rate",
           "-show_entries", "format=duration",
           "-of", "json", str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise FFmpegError(f"ffprobe failed: {r.stderr.strip()}")
    data = json.loads(r.stdout)
    stream = data["streams"][0]
    num, den = stream["r_frame_rate"].split("/")
    return VideoInfo(
        width=int(stream["width"]),
        height=int(stream["height"]),
        fps=float(num) / float(den) if float(den) else 0.0,
        duration_s=float(data["format"]["duration"]),
    )


def extract_last_frame(input_path: Path, out_png: Path) -> None:
    """Extract the final frame of input_path as a PNG."""
    run_ffmpeg(["-sseof", "-0.1", "-i", str(input_path), "-vframes", "1", str(out_png)])
