from __future__ import annotations


def _create_project(client) -> str:
    return client.post("/v1/projects", json={"name": "P"}).json()["id"]


def test_upload_url_requires_project(client):
    r = client.post("/v1/projects/00000000-0000-0000-0000-000000000099/plans/upload-url")
    assert r.status_code == 404


def test_upload_url_signed(client, fake_storage):
    pid = _create_project(client)
    r = client.post(f"/v1/projects/{pid}/plans/upload-url")
    assert r.status_code == 200
    body = r.json()
    assert body["url"].startswith("https://signed/upload/uploads/")
    assert len(fake_storage.uploads) == 1


def test_start_extract_enqueues_job(client, fake_queue, fake_db):
    pid = _create_project(client)
    r = client.post(f"/v1/projects/{pid}/plans/extract",
                    json={"source_path": "uploads/x.pdf", "known_dimension_m": 12.5})
    assert r.status_code == 200
    assert "job_id" in r.json()
    assert len(fake_queue.enqueued) == 1
    call = fake_queue.enqueued[0]
    assert call["func"] == "extract.queue_wrapper.run"
    assert call["kwargs"]["source_path"] == "uploads/x.pdf"
    assert call["kwargs"]["known_dimension_m"] == 12.5


def test_save_plan_versioning(client, fake_db):
    pid = _create_project(client)
    # Seed one plan via the extract endpoint path which creates version 1.
    client.post(f"/v1/projects/{pid}/plans/extract",
                json={"source_path": "uploads/x.pdf"})
    plan_id = list(fake_db.plans.keys())[0]
    r = client.put(f"/v1/plans/{plan_id}",
                   json={"plan_json": {"walls": [], "rooms": []}})
    assert r.status_code == 200
    assert r.json()["version"] == 2


def test_approve_plan(client, fake_db):
    pid = _create_project(client)
    client.post(f"/v1/projects/{pid}/plans/extract", json={"source_path": "x"})
    plan_id = list(fake_db.plans.keys())[0]
    r = client.post(f"/v1/plans/{plan_id}/approve")
    assert r.status_code == 200
    assert r.json()["approved"] is True
    assert fake_db.plans[plan_id]["approved"] is True
