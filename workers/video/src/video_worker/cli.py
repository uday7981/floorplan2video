"""Video CLI.

  python -m video_worker \
      --plan   plan.json \
      --shots  shots.json \
      --shot-id s_r01 \
      --start  path/to/start.png \
      --end    path/to/end_frame.png \
      --resolution 480p \
      --out    path/to/take.mp4 \
      [--poll-interval 15] [--timeout 1200] \
      [--yes-i-approve-cost]

Reads TOGETHER_API_KEY + TOGETHER_VIDEO_MODEL from env. VIDEO_MODE defaults
to frames_only (set in .env per M0 finding).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

from .cost import seedance_cost
from .prompts import fill_video_prompt
from .providers import SubmitRequest
from .providers.together import TogetherVideoProvider, encode_png_data_url

log = logging.getLogger("video_worker")


def _download(url: str, out: Path) -> None:
    r = requests.get(url, timeout=300, stream=True)
    r.raise_for_status()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        for chunk in r.iter_content(1 << 15):
            if chunk:
                f.write(chunk)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[video] %(message)s")

    ap = argparse.ArgumentParser(prog="video_worker")
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--shots", required=True, type=Path)
    ap.add_argument("--shot-id", required=True)
    ap.add_argument("--start", required=True, type=Path, help="start.png")
    ap.add_argument("--end", required=True, type=Path, help="end_frame.png")
    ap.add_argument("--resolution", choices=["480p", "720p"], default="480p")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--poll-interval", type=int, default=15)
    ap.add_argument("--timeout", type=int, default=20 * 60)
    ap.add_argument("--yes-i-approve-cost", action="store_true")
    args = ap.parse_args(argv)

    _ = args.plan  # not strictly needed by video_worker, but kept for symmetry/validation
    shots_doc = json.loads(args.shots.read_text())
    shot = next((s for s in shots_doc["shots"] if s["id"] == args.shot_id), None)
    if shot is None:
        log.error("shot id %s not found", args.shot_id)
        return 2

    duration_s = int(shot["camera"]["duration_s"])
    camera_move = shot["camera"]["move"]

    mode = os.environ.get("VIDEO_MODE", "frames_only")
    if mode != "frames_only":
        log.warning("VIDEO_MODE=%s but Seedance 2.5 only supports frames_only "
                    "via this adapter; proceeding as frames_only", mode)
        mode = "frames_only"

    prompt = fill_video_prompt(mode, camera_move)
    log.info("prompt: %s", prompt)

    est = seedance_cost(args.resolution, duration_s)
    log.info("resolution=%s duration=%ds  ESTIMATED COST: $%.4f",
             args.resolution, duration_s, est.usd)

    if not args.yes_i_approve_cost:
        log.info("dry run (no --yes-i-approve-cost); exiting 0.")
        return 0

    if not args.start.exists() or not args.end.exists():
        log.error("start/end image missing")
        return 2

    provider = TogetherVideoProvider()
    req = SubmitRequest(
        prompt=prompt,
        resolution=args.resolution,
        duration_s=duration_s,
        start_frame_url=encode_png_data_url(args.start.read_bytes()),
        end_frame_url=encode_png_data_url(args.end.read_bytes()),
    )
    submitted_at = time.time()
    log.info("submitting to Together Seedance 2.5 ...")
    sr = provider.submit(req)
    log.info("submitted job_id=%s", sr.provider_job_id)

    deadline = submitted_at + args.timeout
    while time.time() < deadline:
        time.sleep(args.poll_interval)
        pr = provider.poll(sr.provider_job_id)
        log.info("status=%s elapsed=%ds", pr.status, int(time.time() - submitted_at))
        if pr.status == "succeeded":
            if not pr.output_url:
                log.error("succeeded but no output_url returned")
                return 1
            _download(pr.output_url, args.out)
            log.info("wrote %s; ACTUAL COST (from pricing): $%.4f",
                     args.out, est.usd)
            return 0
        if pr.status == "failed":
            log.error("provider failed: %s", pr.error)
            return 1

    log.error("timed out after %ds", args.timeout)
    return 1


if __name__ == "__main__":
    sys.exit(main())
