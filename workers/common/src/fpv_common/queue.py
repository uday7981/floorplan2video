"""Redis + RQ queue factory. One queue per worker type."""
from __future__ import annotations

from typing import Literal

QueueName = Literal["extract", "render", "end_frame", "video", "export"]

QUEUE_NAMES: tuple[QueueName, ...] = ("extract", "render", "end_frame", "video", "export")


def redis_from_url(url: str):
    import redis
    return redis.from_url(url, decode_responses=False)


def rq_queue(queue_name: QueueName, *, connection=None, redis_url: str | None = None):
    """Return an RQ Queue. Pass a mocked connection for tests."""
    from rq import Queue
    if connection is None:
        if redis_url is None:
            raise ValueError("one of connection= or redis_url= is required")
        connection = redis_from_url(redis_url)
    return Queue(name=queue_name, connection=connection)
