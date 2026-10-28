from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from api.deps import (current_user, get_config, get_db, get_prices,
                       get_queue_end_frame, get_queue_export, get_queue_extract,
                       get_queue_render, get_queue_video,
                       get_runpod, get_storage)
from api.main import create_app
from fpv_common.auth import AuthedUser
from fpv_common.config import Config


class FakeDb:
    """In-memory DB. Each table is a dict keyed by id (str)."""
    def __init__(self):
        self.projects: dict[str, dict] = {}
        self.plans: dict[str, dict] = {}
        self.shots: dict[str, dict] = {}
        self.generations: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.exports: dict[str, dict] = {}

    # execute: used for mutating sql; returns rowcount
    def execute(self, sql: str, params: tuple = ()) -> int:
        if "update projects set spent_usd" in sql:
            pid = params[1]
            self.projects[pid]["spent_usd"] = float(self.projects[pid]["spent_usd"]) + float(params[0])
            return 1
        if "delete from projects where id=" in sql:
            pid = params[0]
            return 1 if self.projects.pop(pid, None) else 0
        if "update plans set approved" in sql:
            pid = params[0]
            if pid in self.plans:
                self.plans[pid]["approved"] = True
                return 1
            return 0
        if "update shots set end_frame_approved" in sql:
            sid = params[0]
            if sid in self.shots:
                self.shots[sid]["end_frame_approved"] = True
                return 1
            return 0
        if "update generations set selected=false" in sql:
            for g in self.generations.values():
                if g["shot_id"] == params[0]:
                    g["selected"] = False
            return 1
        if "update generations set selected=true" in sql:
            gid = params[0]
            if gid in self.generations:
                self.generations[gid]["selected"] = True
                return 1
            return 0
        if "delete from shots" in sql:
            pid = params[0]
            for sid in list(self.shots.keys()):
                if self.shots[sid]["project_id"] == pid:
                    del self.shots[sid]
            return 1
        return 1

    def fetchrow(self, sql: str, params: tuple = ()) -> dict | None:
        if "insert into projects" in sql:
            pid = str(uuid4())
            row = {
                "id": pid, "owner_id": params[0], "name": params[1],
                "style_preset": {}, "project_type": params[3],
                "budget_usd": params[4], "spent_usd": 0.0, "status": "draft",
            }
            self.projects[pid] = row
            return row
        if "select * from projects where id=" in sql:
            pid, owner = params
            r = self.projects.get(pid)
            return r if r and r["owner_id"] == owner else None
        if "coalesce(max(version),0)+1" in sql:
            pid = params[0]
            v = 1 + sum(1 for p in self.plans.values() if p["project_id"] == pid)
            return {"v": v}
        if "insert into plans" in sql:
            plid = str(uuid4())
            self.plans[plid] = {
                "id": plid, "project_id": params[0], "version": params[1],
                "source_path": params[2], "plan_json": None, "approved": False,
            }
            return self.plans[plid]
        if "select * from plans where id=" in sql:
            return self.plans.get(params[0])
        if "select * from plans where project_id=" in sql:
            pid = params[0]
            for p in sorted(self.plans.values(), key=lambda x: -x["version"]):
                if p["project_id"] == pid:
                    return p
            return None
        if "insert into shots" in sql:
            import json
            sid = str(uuid4())
            camera = params[6]
            if isinstance(camera, str):
                camera = json.loads(camera)
            self.shots[sid] = {
                "id": sid, "project_id": params[0], "plan_id": params[1],
                "ord": params[2], "kind": params[3], "room_id": params[4],
                "label": params[5], "camera": camera, "end_frame_approved": False,
            }
            return self.shots[sid]
        if "select * from shots where id=" in sql:
            return self.shots.get(params[0])
        if "insert into generations" in sql:
            gid = str(uuid4())
            self.generations[gid] = {
                "id": gid, "shot_id": params[0], "kind": params[1],
                "provider": params[2], "model": params[3], "resolution": params[4],
                "prompt": params[5], "status": "queued", "selected": False,
                "est_cost_usd": params[6], "take": 1,
            }
            return self.generations[gid]
        if "select * from generations where id=" in sql:
            return self.generations.get(params[0])
        if "select shot_id from generations where id=" in sql:
            g = self.generations.get(params[0])
            return {"shot_id": g["shot_id"]} if g else None
        if "insert into jobs" in sql:
            jid = str(uuid4())
            self.jobs[jid] = {"id": jid, "project_id": params[0], "type": params[1],
                              "ref_id": params[2], "status": "queued"}
            return self.jobs[jid]
        if "insert into exports" in sql:
            eid = str(uuid4())
            self.exports[eid] = {"id": eid, "project_id": params[0],
                                  "generation_ids": params[1], "status": "queued"}
            return self.exports[eid]
        return None

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        if "select * from projects where owner_id=" in sql:
            owner = params[0]
            return [p for p in self.projects.values() if p["owner_id"] == owner]
        if "select * from shots where project_id=" in sql:
            pid = params[0]
            return sorted((s for s in self.shots.values() if s["project_id"] == pid),
                          key=lambda s: s["ord"])
        if "select g.id from generations g join shots s" in sql:
            pid = params[0]
            out = []
            for g in self.generations.values():
                s = self.shots.get(g["shot_id"])
                if s and s["project_id"] == pid and g["selected"]:
                    out.append({"id": g["id"]})
            return out
        if "select key, unit, usd from pricing" in sql:
            return []  # tests use seed fallback
        return []

    def tx(self):
        from contextlib import contextmanager

        db = self

        class _Cur:
            def __enter__(self_cur): return self_cur
            def __exit__(self_cur, *a): return False

            def execute(self_cur, sql, params):
                # Route inserts through the fetchrow dispatch so rows actually
                # land in the fake tables.
                if sql.lstrip().lower().startswith("insert into"):
                    db.fetchrow(sql, params)
                else:
                    db.execute(sql, params)

        class _Conn:
            def cursor(self_conn): return _Cur()

        @contextmanager
        def _tx():
            yield _Conn()
        return _tx()


class FakeQueue:
    def __init__(self):
        self.enqueued: list[dict] = []

    def enqueue(self, func_path, kwargs=None, job_timeout=None):
        self.enqueued.append({"func": func_path, "kwargs": kwargs or {}})
        return SimpleNamespace(id="rq_fake")


class FakeStorage:
    def __init__(self):
        self.uploads: list[str] = []
        self.read_requests: list[str] = []

    def create_signed_upload_url(self, bucket, path):
        self.uploads.append(f"{bucket}/{path}")
        return SimpleNamespace(url=f"https://signed/upload/{bucket}/{path}",
                                path=path, expires_in_s=3600)

    def create_signed_read_url(self, bucket, path, expires_in_s=3600):
        self.read_requests.append(f"{bucket}/{path}")
        return SimpleNamespace(url=f"https://signed/read/{bucket}/{path}",
                                path=path, expires_in_s=expires_in_s)


class FakeRunPod:
    def __init__(self):
        self.started: list[str] = []

    def ensure_running(self, pod_id):
        self.started.append(pod_id)


@pytest.fixture
def fake_db() -> FakeDb:
    return FakeDb()


@pytest.fixture
def fake_queue() -> FakeQueue:
    return FakeQueue()


@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def fake_runpod() -> FakeRunPod:
    return FakeRunPod()


@pytest.fixture
def fake_config() -> Config:
    return Config(
        supabase_url="https://x.supabase.co",
        supabase_service_role_key="k",
        supabase_jwt_secret="",
        upstash_redis_url="redis://x",
        anthropic_api_key="", anthropic_model="claude-opus-5-5",
        openai_api_key="", openai_image_model="gpt-image-2.5-sunburst",
        together_api_key="", together_video_model="ByteDance/Seedance-2.5",
        runpod_api_key="", runpod_gpu_pod_id="pod-1",
        default_project_budget_usd=40.0,
        pod_idle_shutdown_minutes=15,
        video_mode="frames_only",
        bucket_uploads="uploads", bucket_renders="renders",
        bucket_frames="frames", bucket_takes="takes", bucket_exports="exports",
    )


@pytest.fixture
def fake_user() -> AuthedUser:
    return AuthedUser(user_id=UUID("00000000-0000-0000-0000-000000000001"),
                       email="t@test.com")


@pytest.fixture
def client(fake_db, fake_queue, fake_storage, fake_runpod, fake_config, fake_user):
    app = create_app()
    app.dependency_overrides[current_user]    = lambda: fake_user
    app.dependency_overrides[get_db]          = lambda: fake_db
    app.dependency_overrides[get_storage]     = lambda: fake_storage
    app.dependency_overrides[get_runpod]      = lambda: fake_runpod
    app.dependency_overrides[get_config]      = lambda: fake_config
    for q in (get_queue_extract, get_queue_render, get_queue_end_frame,
              get_queue_video, get_queue_export):
        app.dependency_overrides[q] = lambda: fake_queue
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
