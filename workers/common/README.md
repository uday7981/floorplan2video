# workers/common

Shared helpers for every worker: Redis/RQ connection, Supabase client (service role),
Storage upload/download, cost-row logging (`est_cost_usd` before, `actual_cost_usd`
after every paid call), retry/backoff policy (10 s → 60 s → 300 s, max 3), and
structured JSON logging with `project_id` and `job_id` on every line.

Built out in **M5**. Scaffold only.
