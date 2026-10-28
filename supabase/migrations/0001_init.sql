-- Initial schema. See docs/PRD_TRD.md § "TRD: data model".
-- RLS: rows filter to owner_id = auth.uid() through projects.

create extension if not exists "pgcrypto";

create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create table projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users,
  name text not null,
  style_preset jsonb not null,
  project_type text not null default 'house' check (project_type in ('house','interior')),
  budget_usd numeric not null default 40,
  spent_usd numeric not null default 0,
  status text not null default 'draft'
    check (status in ('draft','plan_review','shots','rendering','frames','video','exported')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_projects_updated before update on projects
  for each row execute function set_updated_at();

create table plans (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  version int not null,
  source_path text not null,
  plan_json jsonb,
  plan_hash text,
  approved boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, version)
);
create trigger trg_plans_updated before update on plans
  for each row execute function set_updated_at();

create table shots (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  plan_id uuid not null references plans,
  ord int not null,
  kind text not null check (kind in ('opening','room','exterior')),
  room_id text,
  label text not null,
  camera jsonb not null,
  render_hash text,
  driving_clip_path text,
  start_frame_path text,
  clay_ref_path text,
  end_frame_path text,
  end_frame_approved boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_shots_updated before update on shots
  for each row execute function set_updated_at();

create table generations (
  id uuid primary key default gen_random_uuid(),
  shot_id uuid not null references shots on delete cascade,
  kind text not null check (kind in ('end_frame','video')),
  provider text not null check (provider in ('openai','together')),
  model text not null,
  resolution text,
  prompt text not null,
  provider_job_id text,
  status text not null check (status in ('queued','running','succeeded','failed')),
  error text,
  output_path text,
  take int not null default 1,
  selected boolean not null default false,
  est_cost_usd numeric,
  actual_cost_usd numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_generations_updated before update on generations
  for each row execute function set_updated_at();

create table jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  type text not null check (type in ('extract','render','end_frame','video','export')),
  ref_id uuid,
  status text not null check (status in ('queued','running','succeeded','failed')),
  attempts int not null default 0,
  error text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_jobs_updated before update on jobs
  for each row execute function set_updated_at();

create table exports (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  generation_ids uuid[] not null,
  output_path text,
  status text not null check (status in ('queued','running','succeeded','failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_exports_updated before update on exports
  for each row execute function set_updated_at();

create table pricing (
  key text primary key,
  unit text not null check (unit in ('per_second','per_image','per_mtok')),
  usd numeric not null,
  updated_at timestamptz not null default now()
);
create trigger trg_pricing_updated before update on pricing
  for each row execute function set_updated_at();

-- Row-level security
alter table projects    enable row level security;
alter table plans       enable row level security;
alter table shots       enable row level security;
alter table generations enable row level security;
alter table jobs        enable row level security;
alter table exports     enable row level security;

create policy projects_owner on projects
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());

create policy plans_owner on plans
  using (project_id in (select id from projects where owner_id = auth.uid()));
create policy shots_owner on shots
  using (project_id in (select id from projects where owner_id = auth.uid()));
create policy generations_owner on generations
  using (shot_id in (select id from shots where project_id in
    (select id from projects where owner_id = auth.uid())));
create policy jobs_owner on jobs
  using (project_id in (select id from projects where owner_id = auth.uid()));
create policy exports_owner on exports
  using (project_id in (select id from projects where owner_id = auth.uid()));
