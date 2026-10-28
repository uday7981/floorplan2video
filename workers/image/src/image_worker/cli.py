"""End-frame image CLI.

  python -m image_worker \
      --plan     plan.json \
      --shots    shots.json \
      --shot-id  s_r01 \
      --clay     path/to/clay.png \
      --out      path/to/end_frame.png \
      [--size 1792x1024] \
      [--target 1280x720] \
      [--yes-i-approve-cost]

Reads OPENAI_API_KEY + OPENAI_IMAGE_MODEL from env. Model name is never
hard-coded.
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
from .prompts import fill_end_frame_prompt

log = logging.getLogger("image_worker")


def _parse_wh(s: str) -> tuple[int, int]:
    w, h = s.lower().split("x")
    return int(w), int(h)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[image] %(message)s")

    ap = argparse.ArgumentParser(prog="image_worker")
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--shots", required=True, type=Path)
    ap.add_argument("--shot-id", required=True)
    ap.add_argument("--clay", required=True, type=Path, help="clay.png reference")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--size", default="1792x1024",
                    help="requested OpenAI output size (must match a pricing row)")
    ap.add_argument("--target", default="1280x720",
                    help="final PNG dimensions, cropped/resized from --size")
    ap.add_argument("--yes-i-approve-cost", action="store_true")
    args = ap.parse_args(argv)

    plan = json.loads(args.plan.read_text())
    shots_doc = json.loads(args.shots.read_text())
    shot = next((s for s in shots_doc["shots"] if s["id"] == args.shot_id), None)
    if shot is None:
        log.error("shot id %s not found", args.shot_id)
        return 2

    preset = shots_doc.get("style_preset", {})

    # Derive the free-text descriptor for the room from the plan. Preference
    # order: room.name (specific, matches user's label) → room.type (enum
    # fallback). The schema's RoomType enum is useful but can't cover every
    # vocabulary, so room.name is primary — a well-named room always produces
    # a correct image even when the type is 'other'.
    room_type = None
    if shot["kind"] == "room":
        room = next((r for r in plan["rooms"] if r["id"] == shot["room_id"]), None)
        if room is None:
            log.error("room %s referenced by shot %s not found in plan",
                      shot["room_id"], shot["id"])
            return 2
        room_type = room.get("name") or room.get("type")

    prompt = fill_end_frame_prompt(shot["kind"], preset, room_type=room_type)
    log.info("prompt: %s", prompt)

    model = os.environ.get("OPENAI_IMAGE_MODEL") or ""
    est = openai_image_cost(model, args.size, count=1)
    log.info("model=%s size=%s count=%d  ESTIMATED COST: $%.4f",
             est.model, est.size, est.count, est.usd)

    if not args.yes_i_approve_cost:
        log.info("dry run (no --yes-i-approve-cost); exiting 0.")
        return 0

    if not args.clay.exists():
        log.error("clay reference not found: %s", args.clay)
        return 2

    editor = OpenAIImageEditor()
    log.info("calling OpenAI images.edit ...")
    result = editor.edit(reference_png=args.clay.read_bytes(),
                         prompt=prompt, size=args.size)
    target_wh = _parse_wh(args.target)
    final_png = crop_resize_to(result.png_bytes, target_wh)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(final_png)
    log.info("wrote %s (%d bytes); ACTUAL COST (from pricing): $%.4f",
             args.out, len(final_png), est.usd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
