"""Segment-based video CLI (v2.0).

  python -m video_worker.segment_cli \\
      --plan plan.json --journey journey.json --segment-ord N \\
      --start boundary_{N}.png --end boundary_{N+1}.png \\
      --resolution 480p --out take.mp4 [--yes-i-approve-cost]

The segment's role picks the prompt variant:
  opening | descent  → CAD-to-photoreal transition (used ONCE per video)
  walkthrough | stair | exterior | ending → photoreal-to-photoreal

Shared boundary frames: segment N's end frame is boundary N+1; segment N+1's
start frame is the same boundary N+1 — the file is used on both sides.
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
from .providers.base import SubmitRequest
from .providers.together import TogetherVideoProvider, encode_png_data_url


MOVE_WORDS = {
    "opening":    ("floats slowly down",    "~15 m vertical descent from above"),
    "descent":    ("glides down to the entrance", "~3 m forward and down, settling at 1.6 m eye height"),
    "walkthrough":("moves slowly forward, panning", "~0.7 m/s through the doorway, ending at the room centre"),
    "stair":      ("walks slowly up the stairs", "~0.5 m/s, head leading up and forward"),
    "exterior":   ("orbits the building smoothly", "90° arc around the exterior"),
    "ending":     ("pulls back slowly", "~1 m/s backward retreat"),
}

PROMPTS = {
    "transition": (
        "Camera {words} through the space, {detail}. Style transition from "
        "CAD drawing to photorealistic, progressively. Start with the first "
        "frame and finish with this exact shot: the last frame."
    ),
    "photoreal": (
        "Camera {words} through the space, {detail}. Fully photorealistic "
        "throughout — no stylisation changes. Start with the first frame "
        "and finish with this exact shot: the last frame."
    ),
}


def _segment_at_ord(journey: dict, ord_: int) -> dict:
    for s in journey["segments"]:
        if int(s["ord"]) == int(ord_):
            return s
    raise KeyError(f"segment ord {ord_} not in journey")


def prompt_for_segment(segment: dict) -> str:
    role = segment["role"]
    words, detail = MOVE_WORDS.get(role, ("moves smoothly", ""))
    tpl = PROMPTS["transition"] if role in ("opening", "descent") else PROMPTS["photoreal"]
    return tpl.format(words=words, detail=detail)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[video.segment] %(message)s")
    log = logging.getLogger("video_worker.segment")

    ap = argparse.ArgumentParser(prog="video_worker.segment_cli")
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--journey", required=True, type=Path)
    ap.add_argument("--segment-ord", required=True, type=int)
    ap.add_argument("--start", required=True, type=Path, help="boundary_{N}.png")
    ap.add_argument("--end", required=True, type=Path, help="boundary_{N+1}.png")
    ap.add_argument("--resolution", choices=["480p", "720p"], default="480p")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--poll-interval", type=int, default=15)
    ap.add_argument("--timeout", type=int, default=20 * 60)
    ap.add_argument("--yes-i-approve-cost", action="store_true")
    args = ap.parse_args(argv)

    journey = json.loads(args.journey.read_text())
    segment = _segment_at_ord(journey, args.segment_ord)
    duration_s = int(segment["duration_s"])
    prompt = prompt_for_segment(segment)
    log.info("segment %s role=%s dur=%ds", segment["id"], segment["role"], duration_s)
    log.info("prompt: %s", prompt)

    est = seedance_cost(args.resolution, duration_s)
    log.info("ESTIMATED COST: $%.4f", est.usd)
    if not args.yes_i_approve_cost:
        log.info("dry run (no --yes-i-approve-cost); exiting 0.")
        return 0
    if not args.start.exists() or not args.end.exists():
        log.error("boundary frame(s) missing")
        return 2

    provider = TogetherVideoProvider()
    req = SubmitRequest(
        prompt=prompt,
        resolution=args.resolution,
        duration_s=duration_s,
        start_frame_url=encode_png_data_url(args.start.read_bytes()),
        end_frame_url=encode_png_data_url(args.end.read_bytes()),
        idempotency_key=f"fpv-seg-{segment['id']}",
    )
    submitted_at = time.time()
    sr = provider.submit(req)
    log.info("submitted job_id=%s", sr.provider_job_id)

    deadline = submitted_at + args.timeout
    while time.time() < deadline:
        time.sleep(args.poll_interval)
        pr = provider.poll(sr.provider_job_id)
        log.info("status=%s elapsed=%ds", pr.status, int(time.time() - submitted_at))
        if pr.status == "succeeded":
            r = requests.get(pr.output_url, timeout=300)
            r.raise_for_status()
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_bytes(r.content)
            log.info("wrote %s; ACTUAL COST: $%.4f", args.out, est.usd)
            return 0
        if pr.status == "failed":
            log.error("provider failed: %s", pr.error)
            return 1
    log.error("timed out after %ds", args.timeout)
    return 1


if __name__ == "__main__":
    sys.exit(main())
