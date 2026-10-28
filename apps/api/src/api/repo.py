"""Thin SQL layer. Keeps every query in one place so routers stay thin."""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fpv_common.db import Db, dumps_jsonb


# ---------- projects ----------

def project_create(db: Db, owner_id: UUID, name: str, style_preset: dict,
                   project_type: str, budget_usd: float) -> dict:
    row = db.fetchrow(
        "insert into projects (owner_id, name, style_preset, project_type, budget_usd) "
        "values (%s, %s, %s::jsonb, %s, %s) returning *",
        (str(owner_id), name, dumps_jsonb(style_preset), project_type, budget_usd),
    )
    assert row is not None
    return row


def project_list(db: Db, owner_id: UUID) -> list[dict]:
    return db.fetchall(
        "select * from projects where owner_id=%s order by created_at desc",
        (str(owner_id),),
    )


def project_get(db: Db, owner_id: UUID, project_id: UUID) -> dict | None:
    return db.fetchrow(
        "select * from projects where id=%s and owner_id=%s",
        (str(project_id), str(owner_id)),
    )


def project_delete(db: Db, owner_id: UUID, project_id: UUID) -> int:
    return db.execute(
        "delete from projects where id=%s and owner_id=%s",
        (str(project_id), str(owner_id)),
    )


def project_bump_spend(db: Db, project_id: UUID, usd: float) -> None:
    db.execute(
        "update projects set spent_usd = spent_usd + %s where id=%s",
        (usd, str(project_id)),
    )


# ---------- plans ----------

def plan_next_version(db: Db, project_id: UUID) -> int:
    row = db.fetchrow(
        "select coalesce(max(version),0)+1 as v from plans where project_id=%s",
        (str(project_id),),
    )
    return int(row["v"]) if row else 1


def plan_create(db: Db, project_id: UUID, source_path: str,
                plan_json: dict | None, plan_hash: str | None,
                version: int) -> dict:
    row = db.fetchrow(
        "insert into plans (project_id, version, source_path, plan_json, plan_hash) "
        "values (%s, %s, %s, %s::jsonb, %s) returning *",
        (str(project_id), version, source_path,
         dumps_jsonb(plan_json) if plan_json is not None else None, plan_hash),
    )
    assert row is not None
    return row


def plan_get(db: Db, plan_id: UUID) -> dict | None:
    return db.fetchrow("select * from plans where id=%s", (str(plan_id),))


def plan_approve(db: Db, plan_id: UUID) -> int:
    return db.execute(
        "update plans set approved=true where id=%s",
        (str(plan_id),),
    )


# ---------- shots ----------

def shots_replace(db: Db, project_id: UUID, plan_id: UUID, shots: list[dict]) -> list[dict]:
    with db.tx() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from shots where project_id=%s", (str(project_id),))
            for s in shots:
                cur.execute(
                    "insert into shots (project_id, plan_id, ord, kind, room_id, label, camera) "
                    "values (%s, %s, %s, %s, %s, %s, %s::jsonb)",
                    (str(project_id), str(plan_id), int(s["ord"]), s["kind"],
                     s.get("room_id"), s["label"], dumps_jsonb(s["camera"])),
                )
    return shots_list(db, project_id)


def shots_list(db: Db, project_id: UUID) -> list[dict]:
    return db.fetchall(
        "select * from shots where project_id=%s order by ord",
        (str(project_id),),
    )


def shot_get(db: Db, shot_id: UUID) -> dict | None:
    return db.fetchrow("select * from shots where id=%s", (str(shot_id),))


def shot_approve_end_frame(db: Db, shot_id: UUID) -> int:
    return db.execute(
        "update shots set end_frame_approved=true where id=%s",
        (str(shot_id),),
    )


# ---------- generations ----------

def generation_create(db: Db, shot_id: UUID, kind: str, provider: str, model: str,
                      prompt: str, est_cost_usd: float, resolution: str | None = None) -> dict:
    row = db.fetchrow(
        "insert into generations (shot_id, kind, provider, model, resolution, prompt, "
        "status, est_cost_usd) values (%s, %s, %s, %s, %s, %s, 'queued', %s) returning *",
        (str(shot_id), kind, provider, model, resolution, prompt, est_cost_usd),
    )
    assert row is not None
    return row


def generation_get(db: Db, gen_id: UUID) -> dict | None:
    return db.fetchrow("select * from generations where id=%s", (str(gen_id),))


def generation_set_selected(db: Db, gen_id: UUID) -> int:
    row = db.fetchrow(
        "select shot_id from generations where id=%s", (str(gen_id),)
    )
    if row is None:
        return 0
    shot_id = row["shot_id"]
    with db.tx() as conn, conn.cursor() as cur:
        cur.execute("update generations set selected=false where shot_id=%s",
                    (shot_id,))
        cur.execute("update generations set selected=true where id=%s",
                    (str(gen_id),))
    return 1


# ---------- jobs ----------

def job_create(db: Db, project_id: UUID, type_: str, ref_id: UUID | None) -> dict:
    row = db.fetchrow(
        "insert into jobs (project_id, type, ref_id, status) "
        "values (%s, %s, %s, 'queued') returning *",
        (str(project_id), type_, str(ref_id) if ref_id else None),
    )
    assert row is not None
    return row
