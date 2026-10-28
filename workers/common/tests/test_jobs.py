from __future__ import annotations

from uuid import uuid4

import pytest

from fpv_common.jobs import JobContext, mark_failed, mark_running, mark_succeeded, run_job


def _ctx() -> JobContext:
    return JobContext(job_id=uuid4(), project_id=uuid4(), job_type="extract", ref_id=None)


def test_run_job_marks_running_then_succeeded(mem_db):
    ctx = _ctx()
    ran = []

    def work():
        ran.append(1)

    run_job(mem_db, ctx, work)

    assert ran == [1]
    sqls = [sql for sql, _ in mem_db.calls]
    assert any("status='running'" in s for s in sqls)
    assert any("status='succeeded'" in s for s in sqls)


def test_run_job_marks_failed_and_reraises(mem_db):
    ctx = _ctx()

    def work():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        run_job(mem_db, ctx, work)

    sqls = [sql for sql, _ in mem_db.calls]
    assert any("status='failed'" in s for s in sqls)


def test_mark_helpers_target_correct_row(mem_db):
    jid = uuid4()
    mark_running(mem_db, jid)
    mark_succeeded(mem_db, jid)
    mark_failed(mem_db, jid, "x")
    assert all(str(jid) in str(params) for _, params in mem_db.calls)
