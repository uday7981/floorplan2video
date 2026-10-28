from __future__ import annotations


def _project_with_approved_plan(client, fake_db) -> tuple[str, str]:
    pid = client.post("/v1/projects", json={"name": "P"}).json()["id"]
    client.post(f"/v1/projects/{pid}/plans/extract", json={"source_path": "x"})
    plan_id = list(fake_db.plans.keys())[0]
    fake_db.plans[plan_id]["approved"] = True
    return pid, plan_id


def test_replace_shots(client, fake_db):
    pid, plan_id = _project_with_approved_plan(client, fake_db)
    r = client.put(f"/v1/projects/{pid}/shots", json={"shots": [
        {"ord": 0, "kind": "opening", "label": "Welcome",
         "camera": {"move": "crane", "duration_s": 5, "lens_mm": 35, "fps": 24}},
        {"ord": 1, "kind": "room", "room_id": "r1", "label": "01 Living",
         "camera": {"move": "dolly", "duration_s": 5, "lens_mm": 18, "fps": 24}},
    ]})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_start_render_ensures_pod_and_enqueues(client, fake_db, fake_queue, fake_runpod):
    pid, _ = _project_with_approved_plan(client, fake_db)
    r = client.post(f"/v1/projects/{pid}/render")
    assert r.status_code == 200
    assert "job_id" in r.json()
    assert fake_runpod.started == ["pod-1"]
    assert fake_queue.enqueued[-1]["func"] == "blender_worker.queue_wrapper.run"


def test_end_frame_enqueue_and_approve(client, fake_db, fake_queue):
    pid, plan_id = _project_with_approved_plan(client, fake_db)
    client.put(f"/v1/projects/{pid}/shots", json={"shots": [
        {"ord": 0, "kind": "room", "room_id": "r1", "label": "01 Living",
         "camera": {"move": "dolly", "duration_s": 5, "lens_mm": 18, "fps": 24}},
    ]})
    shot_id = list(fake_db.shots.keys())[0]
    r = client.post(f"/v1/shots/{shot_id}/end-frame")
    assert r.status_code == 200
    assert any(c["func"] == "image_worker.queue_wrapper.run" for c in fake_queue.enqueued)

    r2 = client.post(f"/v1/shots/{shot_id}/end-frame/approve")
    assert r2.status_code == 200
    assert fake_db.shots[shot_id]["end_frame_approved"] is True
