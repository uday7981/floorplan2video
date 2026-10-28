"""Pod idle watchdog — self-stops the GPU pod after POD_IDLE_SHUTDOWN_MINUTES
of consecutive empty queues.

Runs on the GPU pod as a sidecar (`python idle_watchdog.py &`). Each tick:
  - Count jobs in the 'render' and 'export' RQ queues
  - If zero AND no RQ worker is currently busy, increment the idle counter
  - When counter reaches the configured minutes, call RunPod stop_pod on self

Resets on any sign of activity.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

# Allow running from the pod without pip install -e by adding src/ to path.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parents[2] / "common" / "src"))

from fpv_common.config import load_config
from fpv_common.queue import rq_queue, redis_from_url
from fpv_common.runpod import RunPodClient

TICK_SECONDS = 60  # one check per minute
RELEVANT_QUEUES = ("render", "export")

log = logging.getLogger("idle_watchdog")


def _busy(redis_conn) -> bool:
    """Return True if any RQ worker on these queues currently has a job."""
    from rq.worker import Worker
    for w in Worker.all(connection=redis_conn):
        if w.get_state() == "busy":
            if any(q in w.queue_names() for q in RELEVANT_QUEUES):
                return True
    return False


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[watchdog] %(asctime)s %(message)s")
    cfg = load_config()
    if not cfg.runpod_api_key or not cfg.runpod_gpu_pod_id:
        log.error("RUNPOD_API_KEY and RUNPOD_GPU_POD_ID must be set")
        return 2

    idle_limit = cfg.pod_idle_shutdown_minutes
    log.info("watchdog started; idle_limit=%d min, pod=%s", idle_limit, cfg.runpod_gpu_pod_id)

    conn = redis_from_url(cfg.upstash_redis_url)
    runpod = RunPodClient(api_key=cfg.runpod_api_key)
    idle_minutes = 0

    while True:
        time.sleep(TICK_SECONDS)
        pending = sum(len(rq_queue(q, connection=conn)) for q in RELEVANT_QUEUES)  # type: ignore[arg-type]
        busy = _busy(conn)
        if pending > 0 or busy:
            if idle_minutes:
                log.info("activity resumed (pending=%d busy=%s); resetting idle counter", pending, busy)
            idle_minutes = 0
            continue
        idle_minutes += 1
        log.info("idle %d/%d min", idle_minutes, idle_limit)
        if idle_minutes >= idle_limit:
            log.warning("idle threshold reached — stopping pod %s", cfg.runpod_gpu_pod_id)
            try:
                runpod.stop_pod(cfg.runpod_gpu_pod_id)
            except Exception as e:
                log.exception("stop_pod failed: %s — will retry next tick", e)
                continue
            # Pod stop is in progress; this process will terminate shortly.
            log.info("stop_pod requested; watchdog exiting")
            return 0


if __name__ == "__main__":
    sys.exit(main())
