from __future__ import annotations


def _project_with_selected_take(client, fake_db) -> str:
    pid = client.post("/v1/projects", json={"name": "P"}).json()["id"]
    client.post(f"/v1/projects/{pid}/plans/extract", json={"source_path": "x"})
    plan_id = list(fake_db.plans.keys())[0]
    fake_db.plans[plan_id]["approved"] = True
    client.put(f"/v1/projects/{pid}/shots", json={"shots": [
        {"ord": 0, "kind": "room", "room_id": "r1", "label": "01 Living",
         "camera": {"move": "dolly", "duration_s": 5, "lens_mm": 18, "fps": 24}},
    ]})
    sid = list(fake_db.shots.keys())[0]
    client.post(f"/v1/projects/{pid}/videos",
                json={"resolution": "480p", "shot_ids": [sid],
                      "confirm_usd": 0.575})
    gid = list(fake_db.generations.keys())[0]
    client.post(f"/v1/generations/{gid}/select")
    return pid


def test_export_requires_selected_take(client, fake_db):
    pid = client.post("/v1/projects", json={"name": "P"}).json()["id"]
    r = client.post(f"/v1/projects/{pid}/export", json={"project_name": "Oakhill"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "no_takes_selected"


def test_export_happy_path(client, fake_db, fake_queue, fake_runpod):
    pid = _project_with_selected_take(client, fake_db)
    r = client.post(f"/v1/projects/{pid}/export", json={"project_name": "Oakhill"})
    assert r.status_code == 200
    assert "job_id" in r.json()
    assert any(c["func"] == "edit_worker.queue_wrapper.run" for c in fake_queue.enqueued)
    assert fake_runpod.started == ["pod-1"]


def test_files_sign_url(client, fake_storage):
    r = client.get("/v1/files/sign", params={"path": "pid/thing.png", "bucket": "renders"})
    assert r.status_code == 200
    assert "signed/read/renders/pid/thing.png" in r.json()["url"]
    assert len(fake_storage.read_requests) == 1


def test_files_sign_rejects_unknown_bucket(client):
    r = client.get("/v1/files/sign", params={"path": "p/x.png", "bucket": "secret"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_bucket"


def test_missing_auth_header_rejected(fake_db, fake_queue, fake_storage, fake_runpod, fake_config):
    """Smoke the real auth middleware by hitting the app without overrides."""
    from fastapi.testclient import TestClient

    from api.deps import get_config, get_db, get_runpod, get_storage
    from api.main import create_app

    app = create_app()
    app.dependency_overrides[get_db]      = lambda: fake_db
    app.dependency_overrides[get_storage] = lambda: fake_storage
    app.dependency_overrides[get_runpod]  = lambda: fake_runpod
    app.dependency_overrides[get_config]  = lambda: fake_config
    with TestClient(app) as c:
        r = c.get("/v1/projects")
    assert r.status_code == 401
