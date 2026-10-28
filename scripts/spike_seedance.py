"""M0.2 — Seedance 2.5 spike.

The user's spec asks: does Together AI accept a reference video together with
first + last frames in one request? If yes, VIDEO_MODE=standard; if no, fallback
to VIDEO_MODE=frames_only.

PRIOR FINDING (from Together's live docs, 2026-10-27):
  https://docs.together.ai/docs/seedance2.5-quickstart
  "Frame images cannot combine with reference inputs."
  Allowed modes:
    - Text-to-video                 (no media)
    - Image-to-video                (frame_images only)   <- what we use (frames_only)
    - Reference-guided              (reference_videos + reference_images)
    - Audio-guided                  (+ reference_audios)

This script lets you verify that finding or run a frames-only confirmation
at the same cost. Default MODE is `frames_only` because that is what the
pipeline will actually use.

HARD RULE: never run without `--yes-i-approve-cost`. The script estimates
cost first and exits 2 unless the flag is present.

Required env:
  TOGETHER_API_KEY           your Together AI key
  TOGETHER_VIDEO_MODEL       default ByteDance/Seedance-2.5
  (optional) START_URL, END_URL, REF_VIDEO_URL   HTTP URLs for assets

If asset URLs are not provided, the script base64-encodes
scripts/_spike_assets/{start.png,end.png,driving.mp4} (run
scripts/generate_test_assets.py first).

Cost table (per_second, from pricing seed):
  480p: $0.115/s   720p: $0.249/s
Minimum duration: 4 s. So the floor is 4 x 0.115 = $0.46 at 480p.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

PRICING = {
    "480p": 0.115,  # USD / second
    "720p": 0.249,
}
ASSETS = Path(__file__).parent / "_spike_assets"
MIN_DURATION = 4
DEFAULT_DURATION = 4
DEFAULT_RESOLUTION = "480p"


def estimate_cost(resolution: str, duration_s: int) -> float:
    return PRICING[resolution] * duration_s


def _data_url(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def build_media(mode: str) -> dict[str, Any]:
    """Build the Seedance `media` object for the chosen mode."""
    start_url = os.environ.get("START_URL") or _data_url(ASSETS / "start.png", "image/png")
    end_url   = os.environ.get("END_URL")   or _data_url(ASSETS / "end.png",   "image/png")
    ref_video_url = os.environ.get("REF_VIDEO_URL") or _data_url(ASSETS / "driving.mp4", "video/mp4")

    if mode == "frames_only":
        return {"frame_images": [
            {"input_image": start_url, "frame": "first"},
            {"input_image": end_url,   "frame": "last"},
        ]}
    if mode == "reference_guided":
        return {"reference_videos": [{"video": ref_video_url}]}
    if mode == "combined_expect_fail":
        # The spec explicitly asked us to confirm this returns an error.
        return {
            "frame_images": [
                {"input_image": start_url, "frame": "first"},
                {"input_image": end_url,   "frame": "last"},
            ],
            "reference_videos": [{"video": ref_video_url}],
        }
    raise ValueError(f"unknown mode: {mode}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["frames_only", "reference_guided", "combined_expect_fail"],
                    default="frames_only")
    ap.add_argument("--resolution", choices=list(PRICING.keys()), default=DEFAULT_RESOLUTION)
    ap.add_argument("--seconds", type=int, default=DEFAULT_DURATION)
    ap.add_argument("--prompt", default="A short abstract transition from a cool blue frame to a warm red frame.")
    ap.add_argument("--yes-i-approve-cost", action="store_true",
                    help="Required to actually submit. Without it, prints the estimate and exits.")
    args = ap.parse_args()

    if args.seconds < MIN_DURATION:
        print(f"Seedance minimum duration is {MIN_DURATION}s", file=sys.stderr)
        return 2

    est = estimate_cost(args.resolution, args.seconds)
    print(f"[spike] mode={args.mode} resolution={args.resolution} seconds={args.seconds}")
    print(f"[spike] ESTIMATED COST: ${est:.2f} USD")

    if not args.yes_i_approve_cost:
        print("[spike] dry run (no --yes-i-approve-cost). Not submitting. Exiting 0.")
        return 0

    api_key = os.environ.get("TOGETHER_API_KEY")
    model = os.environ.get("TOGETHER_VIDEO_MODEL", "ByteDance/Seedance-2.5")
    if not api_key:
        print("TOGETHER_API_KEY not set", file=sys.stderr)
        return 2

    try:
        from together import Together  # type: ignore
    except ImportError:
        print("Missing dependency: pip install together", file=sys.stderr)
        return 2

    media = build_media(args.mode)

    client = Together(api_key=api_key)
    print(f"[spike] POST /videos  model={model}")
    submit_t0 = time.time()
    try:
        job = client.videos.create(
            model=model,
            prompt=args.prompt,
            resolution=args.resolution,
            seconds=str(args.seconds),
            media=media,
        )
    except Exception as e:
        print(f"[spike] submit FAILED after {time.time()-submit_t0:.1f}s")
        print(f"[spike] error: {e!r}")
        if args.mode == "combined_expect_fail":
            print("[spike] This is the expected result per docs; VIDEO_MODE=frames_only confirmed.")
        return 1

    job_id = getattr(job, "id", None) or job["id"]  # type: ignore[index]
    print(f"[spike] submitted job_id={job_id}")

    out_dir = Path(__file__).parent / "_spike_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Poll
    deadline = time.time() + 20 * 60
    while time.time() < deadline:
        status_obj = client.videos.retrieve(job_id)
        status = getattr(status_obj, "status", None) or status_obj.get("status")  # type: ignore[union-attr]
        print(f"[spike] status={status}  elapsed={int(time.time()-submit_t0)}s")
        if status in ("completed", "succeeded"):
            break
        if status == "failed":
            print(f"[spike] FAILED: {status_obj!r}")
            return 1
        time.sleep(15)
    else:
        print("[spike] timed out at 20 minutes", file=sys.stderr)
        return 1

    (out_dir / "status.json").write_text(json.dumps(status_obj if isinstance(status_obj, dict)
                                                    else status_obj.__dict__, default=str, indent=2))
    print(f"[spike] wrote {out_dir / 'status.json'}")
    print(f"[spike] ACTUAL COST (from provider): see status.json 'usage' / 'billed_seconds'")
    print("[spike] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
