from __future__ import annotations


def _project_with_shot(client, fake_db, duration_s=8) -> tuple[str, str]:
    pid = client.post("/v1/projects", json={"name": "P"}).json()["id"]
    client.post(f"/v1/projects/{pid}/plans/extract", json={"source_path": "x"})
    plan_id = list(fake_db.plans.keys())[0]
    fake_db.plans[plan_id]["approved"] = True
    client.put(f"/v1/projects/{pid}/shots", json={"shots": [
        {"ord": 0, "kind": "room", "room_id": "r1", "label": "01 Living",
         "camera": {"move": "dolly", "duration_s": duration_s, "lens_mm": 18, "fps": 24}},
    ]})
    sid = list(fake_db.shots.keys())[0]
    return pid, sid


def test_estimate_video_cost(client, fake_db):
    pid, sid = _project_with_shot(client, fake_db, duration_s=8)
    r = client.post(f"/v1/projects/{pid}/estimate",
                    json={"resolution": "480p", "shot_ids": [sid]})
    assert r.status_code == 200
    body = r.json()
    # 8s @ 480p ($0.115/s) = $0.92
    assert abs(body["usd"] - 0.92) < 1e-3
    assert body["breakdown"][0]["duration_s"] == 8


def test_submit_video_requires_matching_confirmation(client, fake_db):
    pid, sid = _project_with_shot(client, fake_db, duration_s=8)
    # confirm less than actual estimate — reject with 409
    r = client.post(f"/v1/projects/{pid}/videos",
                    json={"resolution": "480p", "shot_ids": [sid], "confirm_usd": 0.5})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "price_drift"


def test_submit_video_blocked_by_budget(client, fake_db):
    pid, sid = _project_with_shot(client, fake_db, duration_s=8)
    # Push project near budget: spent_usd close to 40.
    fake_db.projects[pid]["spent_usd"] = 39.9
    r = client.post(f"/v1/projects/{pid}/videos",
                    json={"resolution": "480p", "shot_ids": [sid], "confirm_usd": 0.92})
    assert r.status_code == 402
    assert r.json()["error"]["code"] == "budget_exceeded"


def test_submit_video_happy_path(client, fake_db, fake_queue):
    pid, sid = _project_with_shot(client, fake_db, duration_s=8)
    r = client.post(f"/v1/projects/{pid}/videos",
                    json={"resolution": "480p", "shot_ids": [sid], "confirm_usd": 0.92})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert any(c["func"] == "video_worker.queue_wrapper.run" for c in fake_queue.enqueued)


def test_select_take(client, fake_db):
    pid, sid = _project_with_shot(client, fake_db, duration_s=8)
    r = client.post(f"/v1/projects/{pid}/videos",
                    json={"resolution": "480p", "shot_ids": [sid], "confirm_usd": 0.92})
    gid = r.json()[0]["generation_id"]
    r2 = client.post(f"/v1/generations/{gid}/select")
    assert r2.status_code == 200
    assert fake_db.generations[gid]["selected"] is True
