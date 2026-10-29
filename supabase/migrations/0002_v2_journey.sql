-- v2.0 migration — continuous journey + unified single/multi-storey.
-- Adds `storey_mode` to projects; renames `shots` → `segments` with the role
-- enum; adds `journeys` + `boundaries` tables; updates generations.kind +
-- jobs.type + exports FKs.

begin;

-- 1) projects: storey_mode + status enum updates
alter table projects
  add column if not exists storey_mode text not null default 'single'
    check (storey_mode in ('single', 'multi'));

alter table projects
  drop constraint if exists projects_status_check;
alter table projects
  add constraint projects_status_check check (status in (
    'draft', 'plan_review', 'journey', 'boundary_frames',
    'rendering', 'video', 'exported'
  ));

-- 2) plans: source_paths becomes an array to carry per-floor uploads
alter table plans
  add column if not exists source_paths text[];
update plans set source_paths = array[source_path] where source_paths is null and source_path is not null;
alter table plans alter column source_paths set not null;
alter table plans drop column if exists source_path;

-- 3) journeys table (one per approved plan)
create table if not exists journeys (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  plan_id uuid not null references plans,
  path_spline jsonb not null,
  total_duration_s numeric not null,
  approved boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_journeys_updated before update on journeys
  for each row execute function set_updated_at();

-- 4) boundaries table (N+1 per journey for N segments)
create table if not exists boundaries (
  id uuid primary key default gen_random_uuid(),
  journey_id uuid not null references journeys on delete cascade,
  ord int not null,
  kind text not null check (kind in ('cad', 'photoreal')),
  frame_path text,
  approved boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (journey_id, ord)
);
create trigger trg_boundaries_updated before update on boundaries
  for each row execute function set_updated_at();

-- 5) shots → segments
alter table shots rename to segments;

alter table segments
  add column if not exists journey_id uuid references journeys on delete cascade,
  add column if not exists role text,
  add column if not exists level_id text,
  add column if not exists from_room_id text,
  add column if not exists to_room_id text,
  add column if not exists duration_s int,
  add column if not exists camera_segment jsonb,
  add column if not exists clay_ref_path text,
  add column if not exists start_boundary_id uuid references boundaries,
  add column if not exists end_boundary_id uuid references boundaries;

alter table segments
  drop constraint if exists shots_kind_check,
  drop constraint if exists segments_role_check;
alter table segments
  add constraint segments_role_check check (role in (
    'opening', 'descent', 'walkthrough', 'stair', 'exterior', 'ending'
  ));

alter table segments
  drop column if exists kind,
  drop column if exists camera,
  drop column if exists end_frame_path,
  drop column if exists end_frame_approved,
  drop column if exists start_frame_path;

-- 6) generations: kind enum update + add boundary_id FK
alter table generations drop constraint if exists generations_kind_check;
alter table generations
  add column if not exists boundary_id uuid references boundaries on delete cascade,
  add constraint generations_kind_check check (kind in ('boundary_frame', 'video'));

-- Rename old `end_frame` rows to `boundary_frame` so existing data stays
-- queryable under the new enum.
update generations set kind = 'boundary_frame' where kind = 'end_frame';

-- segment_id FK follows the renamed table automatically; just rename the col.
alter table generations rename column shot_id to segment_id;

-- 7) jobs.type enum update
alter table jobs drop constraint if exists jobs_type_check;
alter table jobs
  add constraint jobs_type_check check (type in (
    'extract', 'align', 'journey_render', 'boundary_frame', 'video', 'export'
  ));
-- Rename old job types for consistency.
update jobs set type = 'journey_render' where type = 'render';
update jobs set type = 'boundary_frame' where type = 'end_frame';

-- 8) exports: journey_id + rename generation_ids column
alter table exports
  add column if not exists journey_id uuid references journeys;
alter table exports rename column generation_ids to take_generation_ids;

commit;
