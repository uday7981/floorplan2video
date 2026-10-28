from __future__ import annotations

import pytest
from types import SimpleNamespace


class InMemoryDb:
    """Minimal db stand-in for jobs/pricing tests. Supports execute/fetchrow/fetchall
    for a fixed set of pre-canned queries."""

    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.rows_by_sql_substring: dict[str, list[dict]] = {}

    def register(self, sql_substring: str, rows: list[dict]):
        self.rows_by_sql_substring[sql_substring] = rows

    def _match(self, sql: str) -> list[dict] | None:
        for key, rows in self.rows_by_sql_substring.items():
            if key in sql:
                return rows
        return None

    def execute(self, sql: str, params: tuple = ()) -> int:
        self.calls.append((sql, params))
        return 1

    def fetchrow(self, sql: str, params: tuple = ()):
        self.calls.append((sql, params))
        rows = self._match(sql) or []
        return rows[0] if rows else None

    def fetchall(self, sql: str, params: tuple = ()):
        self.calls.append((sql, params))
        return self._match(sql) or []


@pytest.fixture
def mem_db() -> InMemoryDb:
    return InMemoryDb()


@pytest.fixture
def mock_cfg(monkeypatch):
    for k, v in {
        "SUPABASE_URL": "https://x.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
        "UPSTASH_REDIS_URL": "redis://localhost:6379",
    }.items():
        monkeypatch.setenv(k, v)
    from fpv_common.config import load_config
    return load_config()
