from __future__ import annotations


def test_create_project(client):
    r = client.post("/v1/projects", json={"name": "Oakhill",
                                           "style_preset": {"materials": "oak"},
                                           "project_type": "house"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Oakhill"
    assert body["project_type"] == "house"
    assert body["budget_usd"] == 40.0
    assert body["spent_usd"] == 0.0


def test_list_empty(client):
    r = client.get("/v1/projects")
    assert r.status_code == 200
    assert r.json() == []


def test_list_after_create(client):
    client.post("/v1/projects", json={"name": "A"})
    client.post("/v1/projects", json={"name": "B"})
    r = client.get("/v1/projects")
    assert r.status_code == 200
    assert {p["name"] for p in r.json()} == {"A", "B"}


def test_get_project_not_found(client):
    r = client.get("/v1/projects/00000000-0000-0000-0000-000000000099")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "not_found", "message": "project not found"}}


def test_delete_project(client):
    created = client.post("/v1/projects", json={"name": "Z"}).json()
    r = client.delete(f"/v1/projects/{created['id']}")
    assert r.status_code == 204
    r2 = client.get(f"/v1/projects/{created['id']}")
    assert r2.status_code == 404
