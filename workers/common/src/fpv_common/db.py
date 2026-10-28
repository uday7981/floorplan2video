"""Postgres access via psycopg3. Server-side only (service-role bypasses RLS;
authorisation happens in the API layer).

Keep SQL inline — no ORM, no migrations layer. The migrations live in
supabase/migrations/.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator, Protocol

import psycopg
from psycopg.rows import dict_row


class ConnectionFactory(Protocol):
    def __call__(self) -> psycopg.Connection: ...


def _dsn_from_supabase_url(supabase_url: str, service_role_key: str) -> str:
    """Supabase's Postgres connection string is derived from the project URL.
    SSL is required. The service-role key doubles as the password on the
    `postgres` user when using the pooler, but for simplicity here we use the
    direct connection with the project-specific db password — resolved via
    `pg://postgres:<service_role_key>@<project>.supabase.co:5432/postgres`.

    NOTE: Supabase recommends the pooled connection (port 6543) for serverless
    callers. Both work; this helper picks direct 5432.
    """
    # https://xxxx.supabase.co
    host = supabase_url.replace("https://", "").replace("http://", "").rstrip("/")
    # The project ref is the <xxxx> part of <xxxx>.supabase.co
    return f"postgresql://postgres:{service_role_key}@db.{host}:5432/postgres?sslmode=require"


class Db:
    """Thin wrapper around a connection factory so tests can inject their own."""

    def __init__(self, connect: ConnectionFactory):
        self._connect = connect

    @contextmanager
    def tx(self) -> Iterator[psycopg.Connection]:
        """Context-managed transaction. Commits on normal exit; rolls back on error."""
        with self._connect() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def fetchrow(self, sql: str, params: tuple = ()) -> dict | None:
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount


def db_from_config(cfg) -> Db:
    """Build a Db from a Config. Used by production code; tests pass their own factory."""
    dsn = _dsn_from_supabase_url(cfg.supabase_url, cfg.supabase_service_role_key)

    def connect() -> psycopg.Connection:
        return psycopg.connect(dsn)

    return Db(connect)


# --- JSON helpers for jsonb columns ---

def dumps_jsonb(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def loads_jsonb(v: Any) -> Any:
    if v is None or isinstance(v, (dict, list)):
        return v
    return json.loads(v)
