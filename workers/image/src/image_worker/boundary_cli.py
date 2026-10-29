"""Boundary-frame CLI (v2.0).

  python -m image_worker.boundary_cli \\
      --plan     plan.json \\
      --journey  journey.json \\
      --boundary-ord N \\
      --clay-ref path/to/boundary_N.png \\
      --out      path/to/boundary_N_photoreal.png \\
      [--size 1792x1024] [--target 1280x720] [--yes-i-approve-cost]

A boundary frame is shared between segment N-1 (its end frame) and
segment N (its start frame). This CLI generates ONE photoreal frame per
boundary; the video worker then references the same URL on both sides.

Boundary 0 is the opening-shot CAD frame — do not call this CLI for it;
the Blender renderer produces it directly.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .cost import openai_image_cost
from .openai_client import OpenAIImageEditor, crop_resize_to
from .prompts import fill_boundary_frame_prompt

log = logging.getLogger("image_worker.boundary")


def _parse_wh(s: str) -> tuple[int, int]:
    w, h = s.lower().split("x")
    return int(w), int(h)


def _segment_at_ord(journey: dict, ord_: int) -> dict:
    for s in journey["segments"]:
        if int(s["ord"]) == int(ord_):
            return s
    raise KeyError(f"segment ord {ord_} not in journey")


def _room_descriptor(plan: dict, segment: dict) -> str | None:
    """Pick room.name (or type) for the room/stair boundary variants."""
    room_id = segment.get("to_room_id") or segment.get("from_room_id")
    if not room_id:
        return None
    for lvl in plan["levels"]:
        for r in lvl["rooms"]:
            if r["id"] == room_id:
                return r.get("name") or r.get("type")
    return None


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[image.boundary] %(message)s")
    ap = argparse.ArgumentParser(prog="image_worker.boundary_cli")
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--journey", required=True, type=Path)
    ap.add_argument("--boundary-ord", required=True, type=int,
                    help="which boundary (0..N). Boundary 0 is the CAD opening; skip.")
    ap.add_argument("--clay-ref", required=True, type=Path,
                    help="path to the Blender-rendered boundary PNG")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--size", default="1792x1024")
    ap.add_argument("--target", default="1280x720")
    ap.add_argument("--yes-i-approve-cost", action="store_true")
    args = ap.parse_args(argv)

    plan = json.loads(args.plan.read_text())
    journey = json.loads(args.journey.read_text())

    if args.boundary_ord == 0:
        log.error("boundary 0 is the CAD opening frame — it is produced by "
                  "Blender render_cad_frame_at; do not generate a photoreal "
                  "variant for it.")
        return 2

    # The boundary is the junction between segment N-1 (end) and segment N (start).
    # Use the role of the segment we're ENTERING (segment N) to pick the prompt.
    entering_ord = args.boundary_ord
    try:
        segment = _segment_at_ord(journey, entering_ord)
    except KeyError:
        # If this is the final boundary (after the last segment), use the last
        # segment's role instead.
        n_segs = len(journey["segments"])
        segment = _segment_at_ord(journey, n_segs - 1)

    preset = journey.get("style_preset", {})
    room_descriptor = _room_descriptor(plan, segment)
    prompt = fill_boundary_frame_prompt(segment["role"], preset, room_descriptor)
    log.info("role=%s  prompt=%s", segment["role"], prompt)

    model = os.environ.get("OPENAI_IMAGE_MODEL") or ""
    est = openai_image_cost(model, args.size, count=1)
    log.info("model=%s size=%s  ESTIMATED COST: $%.4f", est.model, est.size, est.usd)

    if not args.yes_i_approve_cost:
        log.info("dry run (no --yes-i-approve-cost); exiting 0.")
        return 0

    if not args.clay_ref.exists():
        log.error("clay reference not found: %s", args.clay_ref)
        return 2

    editor = OpenAIImageEditor()
    result = editor.edit(reference_png=args.clay_ref.read_bytes(),
                         prompt=prompt, size=args.size)
    final_png = crop_resize_to(result.png_bytes, _parse_wh(args.target))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(final_png)
    log.info("wrote %s (%d bytes); ACTUAL COST: $%.4f",
             args.out, len(final_png), est.usd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
