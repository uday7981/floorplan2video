"""CLI entry point.

Usage:
  python -m extract --input FILE --output plan.json [--known-dim-m 12.5]

Reads ANTHROPIC_API_KEY and ANTHROPIC_MODEL from env. Writes the validated
plan JSON to --output, prints cost summary to stderr.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .claude_client import ClaudeExtractor
from .cost import claude_cost
from .normalise import normalise

log = logging.getLogger("extract")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="extract")
    ap.add_argument("--input", required=True, type=Path, help="floor plan file (image/PDF/DXF)")
    ap.add_argument("--output", required=True, type=Path, help="where to write plan.json")
    ap.add_argument("--known-dim-m", type=float, default=None,
                    help="known overall width in metres (helps Claude fix scale)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    _setup_logging(args.verbose)

    if not args.input.exists():
        log.error("input file not found: %s", args.input)
        return 2

    log.info("normalising %s", args.input)
    png, mime, info = normalise(args.input)
    log.info("normalised -> %s pixels, info=%s", info.get("pixels"), {k: v for k, v in info.items() if k != "pixels"})

    model = os.environ.get("ANTHROPIC_MODEL")
    log.info("calling Claude (model=%s)", model)
    extractor = ClaudeExtractor()
    try:
        result = extractor.extract(png, known_dim_m=args.known_dim_m)
    except Exception as e:
        log.error("extraction failed: %s", e)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result.plan_json, indent=2, sort_keys=True) + "\n")
    log.info("wrote %s", args.output)

    cost = claude_cost(model, result.input_tokens, result.output_tokens)
    print(
        f"\n[cost] model={cost.model}  in={cost.input_tokens}tok  out={cost.output_tokens}tok  "
        f"USD={cost.total_usd:.4f}  repaired={result.repaired}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
