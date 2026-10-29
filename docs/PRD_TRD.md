# Floor Plan to Video Platform — PRD & TRD

v2.0 · 2026-10-29 · @uday

## How to use this doc

Build the MVP in the order given in the last section, and treat the PRD as
what to build and the TRD as how. Where the doc is silent, pick the simplest
option that works and leave a `TODO(decision)` comment.

Rules for the builder:

- Use only the locked vendors: Anthropic, Together AI, OpenAI, RunPod, Supabase, Upstash, Vercel.
- Every paid call (image, video) goes through a provider adapter and writes a cost row before and after the call.
- Ship a working end-to-end path for one plan before polishing any screen.
- Never put secret keys in frontend code. Only `NEXT_PUBLIC_*` values reach the browser.
- Write a short README per service with run commands and required env vars.

## PRD: overview and goals

The product turns a 2D floor plan into a **single continuous architectural
walkthrough video** — one camera, no cuts, no crossfades — in under an hour,
at $10–30 per video depending on how many floors the building has. It
automates a manual workflow: the user models the house in Blender, lays a
camera spline through every room, generates photoreal frames at natural cut
points, and has an AI video model fill in the motion between them.

Problem: architectural animation takes days of modelling, materials,
lighting, camera planning, and rendering. Agents and designers want a
first-person walkthrough they can share with a client the same afternoon.

Goals for the MVP:

1. Upload a plan (single- or multi-storey) and get an editable 3D model without opening Blender.
2. Auto-plan one continuous camera journey from the main entrance through every room (and up every stair, for multi-storey).
3. Produce a stitched H.264 MP4 with the whole walkthrough and room labels that pop in as the camera enters each room.
4. Show cost before every paid step and keep the cost of a finished single-storey video under $15 and a two-storey video under $20.
5. Keep geometry, camera paths and route logic true to the plan. The AI controls style and light, never layout.

Non-goals for the MVP:

- Furniture placement, landscaping, and buildings taller than 3 storeys
- Interactive 3D walkthroughs for end viewers
- Team accounts, billing, or a public marketplace
- Audio, music, or voice-over
- Any video model other than Seedance 2.5 through Together AI

## PRD: users and core flow

The primary user is an architect, interior designer, or real-estate marketer
who has a floor plan but no Blender skills or time. The secondary user is
the internal operator (you), who runs test plans and tunes prompts.

Core flow, with a human checkpoint before every paid step:

1. **Create project.** Enter a name, pick a project type (House or Interior) and a storey mode (Single-storey or Multi-storey), then pick a style preset (default: oak, black aluminium, natural white, 3000K).
2. **Upload plan.**
   - *Single-storey:* drop one PNG / JPG / PDF / DXF (up to 50 MB).
   - *Multi-storey:* drop one file per floor, set the floor order (Ground, First, Second, …), and set the floor-to-floor height (default 3.0 m). If one file carries several floors side by side, let the user crop it into separate floors in the browser.
   - A Single-storey project can add a floor later, which flips it to Multi-storey without starting over.
3. **Extract.** Claude reads each floor image and returns level JSON: walls, openings, rooms, scale. For Multi-storey, a second alignment pass checks the scale across floors and whether stairs and exterior walls line up within 0.15 m. Warnings surface in the review screen.
4. **Review plan (checkpoint 1).** The user sees the extracted walls overlaid on the original image beside a live 3D preview. Multi-storey adds a floor tab switcher, a ghost overlay of the floor below, and a per-floor x/y offset for manual alignment. The user approves.
5. **Journey.** The system plans ONE continuous camera path, in this order:
   - Opening: top-down on the ground-floor drawing; pulls up, plan extrudes into 3D; multi-storey upper floors build up and stack, then fade to a cutaway so the ground stays visible.
   - Descent: glides down at an angle to the main entrance; settles at eye height (1.6 m).
   - Walkthrough: enters through the main entrance; visits every room through real doorways and openings using the room-adjacency graph; slow pan inside each room; stair climbs between levels for multi-storey.
   - Ending: for House projects, returns out through the main entrance and rises into an exterior orbit; for Interior projects, a slow pull-back in the last room.
   The user can tweak the room order, drop a room, or change duration, then approves (checkpoint 2).
6. **Render + segment.** Blender builds the model and renders the single camera path at 24 fps, splitting it into 5 s (or 8 s where the path naturally runs long) segments at natural cut points — doorways, stair landings, the exterior-orbit mark. Each segment produces a driving.mp4, a clay-shaded end-frame reference, and a shared boundary PNG that is the end of segment N and the start of segment N+1.
7. **Approve boundary frames (checkpoint 3).** One photoreal boundary frame per segment junction. The user approves or regenerates each. The frame is reused on both sides of the junction so segments stay in sync. The CAD-to-photoreal style transition happens exactly once, during the opening + descent; every subsequent boundary is photoreal-to-photoreal.
8. **Generate videos (checkpoint 4).** The user sees the estimated cost, picks draft (480p) or final (720p), and confirms. Segments run in parallel.
9. **Review takes.** The user watches each segment, picks the best take or re-rolls a segment.
10. **Export.** The system joins all segments with hard cuts on the shared boundary frames, adds room labels that pop in on entry (for multi-storey, prefixed with the floor: "First floor · 04 Bedroom"), appends a 2 s end card, and returns a downloadable MP4.

## PRD: functional requirements

P0 items make up the MVP; P1 items follow once one plan runs end to end.

| ID | Area | Requirement | Priority |
| --- | --- | --- | --- |
| FR-01 | Projects | Create, list, rename, and delete projects. Each project stores a style preset, a project type (House or Interior), and a storey mode (Single-storey or Multi-storey). A Single-storey project can be upgraded to Multi-storey by adding levels. | P0 |
| FR-02 | Upload | Single-storey: accept one image (PNG, JPG, WEBP, HEIC), PDF, or DXF up to 50 MB. Multi-storey: accept one file per floor plus manual ordering + floor-to-floor height. Include an in-browser crop tool for multi-floor files that need splitting. | P0 |
| FR-03 | Extract | Produce level JSON per floor that validates against the schema. On failure, show the error and allow a retry. | P0 |
| FR-04 | Extract | Ask for one known dimension (e.g. overall width in metres) if the plan has no readable scale. | P0 |
| FR-05 | Extract | For Multi-storey, run an alignment pass across floors (scale, stair position, exterior walls). Warn when offsets exceed 0.15 m. | P0 |
| FR-06 | Review | Overlay walls, doors, and windows on the source image. Users can move wall endpoints, change thickness, and add or delete openings. | P0 |
| FR-07 | Review | Live three.js preview that updates within 200 ms of each edit. Multi-storey adds a floor tab switcher, a ghost overlay of the floor below, and a per-level x/y offset. | P0 |
| FR-08 | Review | Every save creates a new plan version. Users can revert to an earlier one. | P1 |
| FR-09 | Journey | Auto-plan a continuous camera path through the room-adjacency graph starting at the main entrance, visiting every room over 4 m², climbing stairs between levels in order, and ending per project type. Users reorder, drop, or extend any step and preview the path. | P0 |
| FR-10 | Journey | Split the camera path into 5 s (or 8 s where natural) segments at doorways, stair landings and the exterior-orbit mark. Expose the segment list to the user. | P0 |
| FR-11 | Render | For each segment, produce a 24 fps 1280×720 driving MP4 and a clay-shaded end-frame reference. Produce one shared boundary PNG per segment junction. | P0 |
| FR-12 | Boundary frames | Generate one photoreal boundary frame per junction from the clay reference and style prompt. Approve or regenerate each. The approved frame is used on both sides of the junction. | P0 |
| FR-13 | Video | Show estimated cost before submitting. Draft runs at 480p and final at 720p. | P0 |
| FR-14 | Video | Submit all approved segments in parallel. The CAD-to-photoreal prompt is used only for the opening + descent segments; every subsequent segment uses the photoreal-to-photoreal prompt. Show live status per segment. | P0 |
| FR-15 | Video | Users re-roll a single segment without touching the others. | P0 |
| FR-16 | Takes | Gallery per segment with all takes playable. Users mark one as selected. | P0 |
| FR-17 | Export | Concat selected takes in segment order with hard cuts on the shared boundary frames (optional 2–4 frame blend behind a flag, default off). Overlay a room label as the camera enters each room, prefixed with the floor name for multi-storey. Append a 2 s end card. Output an H.264 MP4. | P0 |
| FR-18 | Cost | Running cost per project, shown on every screen. | P0 |
| FR-19 | Cost | Block paid jobs when a project passes its budget cap (default $40) unless the user raises it. | P0 |
| FR-20 | Auth | Email magic-link sign-in. Users only see their own projects. | P1 |
| FR-21 | Notify | Email when an export is ready. | P1 |

## PRD: non-functional requirements, cost, and success

A single-storey plan should go from upload to exported MP4 in under 60 minutes
of wall-clock time; a two-storey plan under 90 minutes. (Both exclude the time
the user spends on review.)

| Area | Requirement |
| --- | --- |
| Speed | Extraction under 60 s per floor. Alignment pass under 15 s. Blender build + camera-path render for single-storey under 6 min; two-storey under 10 min. Segment video jobs run in parallel. |
| Reliability | Every job is retryable and idempotent. A failed segment never blocks other segments. A killed video worker mid-job retries without a duplicate paid generation. |
| Cost visibility | Every paid call logs provider, model, units, and USD cost. Estimates show before each paid step. |
| Security | API keys server-side only. Signed URLs for files, expiring in 1 hour. Row-level security in Postgres. |
| Data | Originals, renders, boundary frames and takes kept for 30 days in the MVP. |
| Browsers | Latest Chrome, Edge, and Safari on desktop. Mobile is view-only. |

Cost guardrails, based on indicative October 2026 rates:

| Item | Indicative rate | Per single-storey video (≈11 segments) | Per two-storey video (≈18 segments) |
| --- | --- | --- | --- |
| Seedance 2.5 draft, 480p | ~$0.115/s | ~$6.70 | ~$10.70 |
| Seedance 2.5 final, 720p | ~$0.249/s | ~$14.00 | ~$22.50 |
| Boundary frames (OpenAI images) | ~$0.25 each | ~$2.50 (10 shared) | ~$4.25 (17 shared) |
| Blender GPU (RunPod RTX 4090) | ~$0.34–0.69/hr | <$0.50 | <$0.80 |
| Claude extraction + alignment pass | per token | <$0.50 | <$1.00 |

Rates change often. Store them in a `pricing` config table, never hard-coded.

Success metrics for the MVP:

- 4 of your 5 test plans (mixed single + multi) reach an exported MP4.
- Geometry matches the source plan within 5% on overall dimensions.
- Average takes per usable segment is 2.0 or fewer.
- Cost per final 720p single-storey video is under $20; per two-storey video under $30.

## TRD: architecture, stack, and environment

A Next.js app on Vercel calls a FastAPI service, which writes to Supabase and
enqueues jobs in Upstash Redis. Five Python workers consume the queue; the
Blender and edit workers run on a RunPod GPU pod, and the others can run
anywhere.

| Layer | Choice | Notes |
| --- | --- | --- |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind, react-three-fiber | Hosted on Vercel |
| API | FastAPI, Python 3.11, Pydantic v2 | Shares the plan schema package with workers |
| DB, auth, storage, realtime | Supabase (Postgres 15) | Realtime pushes job status to the UI |
| Queue | Upstash Redis + RQ | One queue per worker type |
| Extract worker | Anthropic API, Claude vision with tool-use JSON output | Model name set in env |
| Blender worker | Blender 4.2 LTS headless in Docker | RunPod RTX 4090 pod, EGL rendering |
| Image worker | OpenAI Images API, edit endpoint with reference image | Model name set in env |
| Video worker | Together AI, Seedance 2.5 | First/last frame only (frames_only mode) |
| Edit worker | ffmpeg 6 | Runs on the same pod as Blender |

Environment variables:

```
# shared
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=      # server and workers only
UPSTASH_REDIS_URL=

# frontend (public)
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=

# workers
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
OPENAI_API_KEY=
OPENAI_IMAGE_MODEL=
TOGETHER_API_KEY=
TOGETHER_VIDEO_MODEL=ByteDance/Seedance-2.5
RUNPOD_API_KEY=

# guardrails
DEFAULT_PROJECT_BUDGET_USD=40
POD_IDLE_SHUTDOWN_MINUTES=15
VIDEO_MODE=frames_only          # per Seedance 2.5 docs
```

## TRD: data model

Nine tables in Postgres. All ids are UUIDs, all tables have `created_at` and
`updated_at`, and row-level security limits rows to `owner_id = auth.uid()`
through `projects`.

```sql
create table projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users,
  name text not null,
  style_preset jsonb not null,
  project_type text not null default 'house'      check (project_type in ('house','interior')),
  storey_mode text not null default 'single'      check (storey_mode in ('single','multi')),
  budget_usd numeric not null default 40,
  spent_usd numeric not null default 0,
  status text not null default 'draft'
    check (status in ('draft','plan_review','journey','boundary_frames','rendering','video','exported'))
);

create table plans (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  version int not null,
  source_paths text[] not null,       -- one storage path per floor (always ≥ 1)
  plan_json jsonb,                    -- schema v2.0 (levels + stairs)
  plan_hash text,
  approved boolean not null default false,
  unique (project_id, version)
);

create table journeys (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  plan_id uuid not null references plans,
  path_spline jsonb not null,         -- the full continuous camera path
  total_duration_s numeric not null,
  approved boolean not null default false
);

create table boundaries (
  id uuid primary key default gen_random_uuid(),
  journey_id uuid not null references journeys on delete cascade,
  ord int not null,                   -- N+1 boundaries for N segments
  kind text not null                  -- cad | photoreal
    check (kind in ('cad','photoreal')),
  frame_path text,
  approved boolean not null default false,
  unique (journey_id, ord)
);

create table segments (
  id uuid primary key default gen_random_uuid(),
  journey_id uuid not null references journeys on delete cascade,
  ord int not null,
  role text not null                  -- opening|descent|walkthrough|stair|exterior|ending
    check (role in ('opening','descent','walkthrough','stair','exterior','ending')),
  level_id text,                      -- level this segment is on (null for exterior)
  from_room_id text,
  to_room_id text,
  duration_s int not null             check (duration_s in (5, 8)),
  camera_segment jsonb not null,      -- the slice of the full spline for this segment
  driving_clip_path text,
  clay_ref_path text,
  start_boundary_id uuid references boundaries,
  end_boundary_id uuid references boundaries,
  unique (journey_id, ord)
);

create table generations (
  id uuid primary key default gen_random_uuid(),
  segment_id uuid references segments on delete cascade,
  boundary_id uuid references boundaries on delete cascade,
  kind text not null                  -- boundary_frame | video
    check (kind in ('boundary_frame','video')),
  provider text not null              check (provider in ('openai','together')),
  model text not null,
  resolution text,
  prompt text not null,
  provider_job_id text,
  status text not null                check (status in ('queued','running','succeeded','failed')),
  error text,
  output_path text,
  take int not null default 1,
  selected boolean not null default false,
  est_cost_usd numeric,
  actual_cost_usd numeric
);

create table jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  type text not null                  -- extract|align|journey_render|boundary_frame|video|export
    check (type in ('extract','align','journey_render','boundary_frame','video','export')),
  ref_id uuid,
  status text not null                check (status in ('queued','running','succeeded','failed')),
  attempts int not null default 0,
  error text,
  started_at timestamptz,
  finished_at timestamptz
);

create table exports (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  journey_id uuid not null references journeys,
  take_generation_ids uuid[] not null,
  output_path text,
  status text not null                check (status in ('queued','running','succeeded','failed'))
);

create table pricing (
  key text primary key,
  unit text not null                  check (unit in ('per_second','per_image','per_mtok')),
  usd numeric not null,
  updated_at timestamptz not null default now()
);
```

Storage buckets: `uploads`, `renders`, `boundaries`, `takes`, `exports`.
Paths follow `{project_id}/{journey_id}/{ord}/{file}` for everything
journey-scoped.

## TRD: plan JSON schema

Plan JSON is the single source of truth for geometry. Extraction writes it,
the review screen edits it, and the Blender script and three.js preview both
read it. Define it once as Pydantic models in `packages/plan_schema`, and
generate the TypeScript types from its JSON Schema.

Conventions: units are metres, the origin is the plan's bottom-left corner,
x points right and y points up, and z is height. All coordinates round to
0.01 m. A single-storey plan has exactly one entry in `levels` at `index 0`
and `elevation 0`; a multi-storey plan has one per floor in ascending order.

```json
{
  "schema_version": "2.0",
  "units": "m",
  "meta": {
    "scale_source": "dimension_text",
    "confidence": 0.86,
    "warnings": []
  },
  "defaults": { "floor_thickness": 0.2 },
  "levels": [
    {
      "id": "ground",
      "name": "Ground Floor",
      "index": 0,
      "elevation": 0.0,
      "floor_to_floor_height": 3.0,
      "walls":    [ /* same shape as before */ ],
      "openings": [ /* same shape as before */ ],
      "rooms":    [ /* same shape as before */ ],
      "voids": [
        { "id": "v1", "polygon": [[4.5,0.5],[5.5,0.5],[5.5,2.5],[4.5,2.5]] }
      ]
    }
  ],
  "stairs": [
    {
      "id": "s1",
      "from_level": "ground",
      "to_level":   "first",
      "footprint":  [[4.5,0.5],[5.5,0.5],[5.5,2.5],[4.5,2.5]],
      "start_point":[4.75,0.6],
      "end_point":  [5.25,2.4],
      "direction":  "up"
    }
  ]
}
```

Validation rules, enforced server-side on every save:

- Wall length ≥ 0.3 m; thickness ∈ [0.05, 0.6]; height ≈ `level.floor_to_floor_height - defaults.floor_thickness` within 0.3 m.
- Each opening fits inside its wall and sits within wall height.
- Room polygons are closed, non-self-intersecting, and have area ≥ 1 m².
- Exactly one opening (across all levels) has `main_entrance: true`.
- Multi-storey only: every upper level must be reachable from the ground via stairs; each stair's `start_point` and `end_point` lie inside a room or corridor polygon on the respective level.
- Overall bbox between 3 m and 60 m per side; multi-storey adds a check that per-level bboxes agree within 0.15 m.
- A plan can be migrated from schema 1.0 (flat walls/openings/rooms) to 2.0 by wrapping into a single level at index 0, elevation 0.

## TRD: API endpoints

All endpoints are under `/v1`, take a Supabase JWT in the `Authorization`
header, and return JSON. Long work always returns a `job_id`; the client
follows progress through Supabase realtime on the `jobs`, `segments`,
`boundaries`, and `generations` tables.

| Method | Path | Purpose | Returns |
| --- | --- | --- | --- |
| POST | /projects | Create project (name, style preset, project_type, storey_mode) | project |
| GET | /projects | List own projects | project[] |
| GET | /projects/{id} | Project with plan, journey, segments, boundaries, generations, spend | project detail |
| DELETE | /projects/{id} | Delete project and its files | 204 |
| POST | /projects/{id}/plans/upload-url | Signed upload URL (call per floor for multi-storey) | url, path |
| POST | /projects/{id}/plans/extract | Start extraction for all uploaded files; auto-runs alignment pass for multi | job_id |
| PUT | /plans/{id} | Save edited plan JSON as a new version (validated) | plan |
| POST | /plans/{id}/approve | Approve plan + auto-build the journey | journey |
| PUT | /journeys/{id} | Edit the journey (room order, drop room, duration tweaks) | journey |
| POST | /journeys/{id}/approve | Approve journey; enqueue Blender spline render | job_id |
| POST | /boundaries/{id}/frame | Generate or regenerate the photoreal boundary frame | generation |
| POST | /boundaries/{id}/approve | Approve current boundary frame | boundary |
| POST | /projects/{id}/estimate | Cost estimate for the full video run; body `resolution` | usd, breakdown |
| POST | /projects/{id}/videos | Submit video jobs for every segment; body `resolution`, `confirm_usd` | generation[] |
| POST | /segments/{id}/reroll | Re-roll one segment | generation |
| POST | /generations/{id}/select | Mark take as selected for its segment | generation |
| POST | /projects/{id}/export | Stitch; body `boundary_blend_frames` (0–4, default 0) | job_id |
| GET | /files/sign?path= | Short-lived signed read URL | url |
| POST | /webhooks/together | Optional: provider completion callback | 200 |

Rules:

- `POST /videos` rejects with 409 if `confirm_usd` is lower than the server's fresh estimate.
- Any paid endpoint returns 402 when `spent_usd + estimate > budget_usd`.
- Error body shape is `{ "error": { "code": "...", "message": "..." } }`.

## TRD: workers and job pipeline

Each worker pulls from its own RQ queue, updates the `jobs` row at start
and finish, and is safe to re-run. Failures retry 3 times with backoff of
10 s, 60 s, and 300 s, then mark the job `failed` with the error text.

### Extract worker (queue `extract`)

1. Download the upload(s). For PDFs, render each page at 300 dpi; for DXFs, extract geometry via `ezdxf` and render a review image.
2. For each floor file: call Claude with the image and the extraction prompt, forcing a single tool call whose input schema is the level JSON schema.
3. Validate with Pydantic. On failure, send errors back to Claude once to repair; if it still fails, fail the job with errors shown to the user.
4. For multi-storey, assemble `levels[]` + initial empty `stairs[]`; run an alignment pass that re-sends all floors with the extracted geometry and asks Claude to locate stairs, confirm scale consistency, and flag any exterior-wall drift > 0.15 m. Append warnings to `meta.warnings`.
5. Save as plan version 1 with `approved = false`.

### Journey builder (part of API `/plans/{id}/approve`)

1. Build the room-adjacency graph for each level: rooms are nodes; two rooms are linked if they share a wall with a non-main-entrance opening.
2. Add a stair edge between the lower-level room containing the stair's `start_point` and the upper-level room containing its `end_point`.
3. Compute a route that starts at the room with the `main_entrance`, visits every room ≥ 4 m² once where possible, climbs stairs in level-index order, and allows corridor backtracking only when a room has no other unvisited neighbour.
4. Emit a continuous camera spline:
   - **Opening** (top-down → extruded 3D → cutaway reveal, multi-storey only): 5 s single / 8 s multi.
   - **Descent** to main_entrance, settle at 1.6 m eye height: 5 s.
   - **Walkthrough**: per visited room, enter through the chosen doorway, slow pan around the centroid, exit through the next doorway. Average ~5 s per room; 8 s for rooms over 20 m².
   - **Stair** (multi-storey only): walk the stair footprint from `start_point` at `from_level.elevation + 1.6 m` to `end_point` at `to_level.elevation + 1.6 m` over 5 s; constant walking pace (0.6–0.8 m/s), slower on stairs; TRACK_TO at the top-landing eye point so the viewer sees where they're going.
   - **Ending**: house → return out through the main entrance (3 s), rise and pull into exterior orbit (8 s); interior → slow pull-back in the last room (5 s).
5. Split the spline into segments of 5 s (or 8 s where the path naturally runs long) at natural cut points: doorways, stair landings, exterior-orbit mark. Each cut defines a boundary.

Motion rules enforced by the builder:

- Constant slow walking speed (0.6–0.8 m/s indoors, slower on stairs).
- Ease in and out of turns; look direction leads into each turn.
- Camera stays ≥ 0.4 m from any wall, slab, tread or door frame.
- 16–18 mm lens inside, 28–35 mm outside.

### Blender worker (queue `journey_render`, on RunPod)

Entry point:
```
blender -b --factory-startup -P build.py -- \
    --plan plan.json --journey journey.json --out /tmp/out
```

1. Build: extrude each wall per level at its elevation, cut openings with boolean modifiers, add a floor slab per level, cut each `level.voids` polygon from the slab above, add stair treads along each stair's `footprint`, add a flat roof above the top level for House projects, assign materials from the style preset.
2. Exterior: a ground plane, a sun at 35° elevation, HDRI-free sky colour.
3. Interior light: one area light per room at that level's ceiling height.
4. Camera: load the single continuous spline from `journey.json`. Set `scene.frame_end = total_duration_s × fps`. Animate camera transform along the spline with ease curves at turns.
5. For each segment N, outputs:
   - `seg_{ord}/driving.mp4` — Workbench solid shading, 1280×720, 24 fps, the slice of the spline for this segment.
   - `seg_{ord}/clay_end.png` — the final frame of this segment in Workbench clay shading (end-frame reference for OpenAI image edit).
   - `boundary_{ord}.png` — the exact camera frame at the cut point. Boundary 0 is the CAD-style opening frame (Freestyle lines on flat white). All subsequent boundaries render in Workbench; the user approves photoreal variants per boundary.
6. Skip any segment whose `render_hash` already has outputs in storage.

### Image worker (queue `boundary_frame`)

Send `boundary_{ord}.png` + the appropriate boundary-frame prompt (room /
exterior / stair-landing variant) to the OpenAI image-edit endpoint at
1280×720 (or the closest supported size, cropped). Save to `boundaries/`,
log cost, set `boundaries.frame_path`. Shared frame: the same approved
image is referenced by both segment N (as its end frame) and segment N+1
(as its start frame).

### Video worker (queue `video`)

1. One Seedance 2.5 call per segment, through the `VideoProvider` adapter, with the shared boundary frames as `frame_images` first/last.
2. The prompt differs by segment role:
   - `opening` + `descent`: CAD-to-photoreal transition prompt. Used only here, once per video.
   - `walkthrough` / `stair` / `exterior` / `ending`: photoreal-to-photoreal motion prompt describing the camera's path through this slice (direction, distance, pace).
3. Idempotency: `fpv-gen-<generation_id>` key on every submit; if the worker is retried mid-poll it resumes from the stored `provider_job_id` rather than re-submitting.
4. Poll every 15 s, time out at 20 min; download the output to `takes/`, log actual cost from the usage field.

### Edit worker (queue `export`, on RunPod)

1. Normalise each selected take to 1280×720, 24 fps, H.264, no audio.
2. **Hard concat** in segment order on the shared boundary frames (no xfade by default). Optional 2–4 frame cross-blend behind a `--boundary-blend-frames` flag for when a Seedance generation slightly misses its end frame.
3. Overlay with `drawtext`: room labels appear as the camera enters each room — multi-storey format `"Floor name · 04 Bedroom"`; single-storey format `"04 Bedroom"`. Title on the opening segment. Bottom-left, Helvetica Bold or Inter Bold.
4. Append a 2 s end card with the project name over the last frame (grab the last frame BEFORE drawtext is applied so the end card doesn't inherit the final room label), upload to `exports/`.

### GPU pod lifecycle

Unchanged from v1: API wakes the pod via RunPod GraphQL when a
`journey_render` or `export` job is queued; the pod self-stops after
`POD_IDLE_SHUTDOWN_MINUTES` of empty queues via the sidecar watchdog in
`workers/blender/scripts/idle_watchdog.py`.

## TRD: prompt templates

Templates live in `prompts/templates.yaml`, versioned, with `{placeholders}`
filled per segment. The style preset supplies `{materials}`, `{light}`, and
`{setting}`.

### Extraction (Claude, system prompt)

Unchanged in intent — add alignment-pass rules at the end for multi-storey:

> Multi-storey rule: after extracting each floor, locate every stair and
> record its from_level, to_level, footprint, start_point, end_point. Confirm
> that exterior walls on upper floors sit within 0.15 m of the ground floor's
> exterior walls; raise a warning in meta.warnings if not.

### Boundary frames (OpenAI image edit)

Three variants (room / exterior / stair-landing); same shape as v1 end-frame
prompts, with the `{room_type}` slot sourced from `room.name` (specific)
with `room.type` fallback.

### Video segments (Seedance 2.5)

Two variants only:

**Opening + descent — CAD-to-photoreal transition (one-shot per video):**
```
Camera {move_words} through the space, {move_detail}. Style transition from
CAD drawing to photorealistic, progressively. Start with the first frame
and finish with this exact shot: the last frame.
```

**Walkthrough / stair / exterior / ending — photoreal-to-photoreal:**
```
Camera {move_words} through the space, {move_detail}. Fully photorealistic
throughout — no stylisation changes. Start with the first frame and finish
with this exact shot: the last frame.
```

`{move_words}` + `{move_detail}` are built from the segment's camera slice
and role. For a stair: `"walks slowly up the stairs"` + `"~0.6 m/s, head
leading up and forward"`. For a room: `"moves slowly forward, panning
right"` + `"~0.7 m/s through the doorway, ending at the room centre"`.

## TRD: frontend screens

Seven routes, one per flow step. A stepper across the top of every project
page shows the current step, and a cost badge in the header shows spend
against budget.

| Route | Screen | Key components | Done when |
| --- | --- | --- | --- |
| `/` | Project list | Project cards with status, storey mode, and spend; New project dialog with name, project type and storey mode | User opens or creates a project |
| `/p/[id]/upload` | Upload | Single-storey: one drag-and-drop zone. Multi-storey: one zone per floor + ordering (Ground / First / Second) + floor-to-floor height field + an in-browser crop tool for multi-floor files. Extraction progress per floor + alignment-pass progress. | Extraction (and alignment for multi) succeeds |
| `/p/[id]/plan` | Plan review | Left: SVG overlay with draggable endpoints + inspector. Right: react-three-fiber preview with orbit controls. Multi-storey: floor-tab switcher above the SVG, ghost overlay of the floor below, per-floor x/y offset slider. Warnings banner from `meta.warnings` | User clicks Approve plan |
| `/p/[id]/journey` | Journey review | Linear visualisation of the camera path through rooms + stairs. Reorderable room list; per-room duration override; drop-room toggle; "Preview journey" plays the Blender turntable along the path. | User clicks Approve journey |
| `/p/[id]/boundaries` | Boundary frames | Per-junction tile with clay reference ↔ photoreal boundary, Approve / Regenerate buttons. Shared frame badge shows which two segments each boundary feeds. | All boundaries approved |
| `/p/[id]/video` | Video generation | Resolution toggle (480p/720p), total cost estimate, Confirm button; per-segment status cards + take gallery + Select + Re-roll | One take selected per segment |
| `/p/[id]/export` | Export | Title + per-room caption overrides, boundary-blend-frames toggle (0–4), Export button, progress, final player, Download | MP4 ready |

Implementation notes:

- The 3D preview builds meshes from plan JSON in the browser with the same rules as `build.py`. It never calls Blender.
- Subscribe to Supabase realtime on `jobs`, `segments`, `boundaries`, and `generations` filtered by `project_id`. Do not poll.
- Every paid button shows its cost in the label.
- Multi-storey plan editor adds a floor tab bar + ghost overlay opacity slider + x/y offset for each floor (keyboard arrows nudge by 0.1 m).

## TRD: infra, deployment, and repo

One monorepo, docker-compose running everything locally except the GPU
worker. Deployment splits across three hosts: Vercel for the web app,
RunPod GPU pod for Blender + edit, always-on RunPod CPU pod for the
API + CPU workers.

```
floorplan2video/
  apps/
    web/
    api/
  workers/
    common/
    extract/
    blender/
      Dockerfile
      build.py
      cameras.py          # single journey_camera builder
      scene.py            # multi-level walls/slabs/stairs/voids
      scripts/
        idle_watchdog.py
    image/
    video/
      providers/
        base.py
        together.py
    edit/
  packages/
    plan_schema/          # Pydantic + JSON Schema + TS types (v2.0)
  supabase/
    migrations/
    seed.sql
  prompts/
    templates.yaml
  fixtures/
    plans/                # ≥ one single-storey + ≥ one multi-storey
  scripts/
    make_journey.py       # plan.json -> journey.json
    merge_levels.py       # per-level extracts -> v2 plan.json
    spike_seedance.py
  docker-compose.yml
  .env.example
```

Deployment:

| Component | Where | How |
| --- | --- | --- |
| Web | Vercel, Hobby plan | Git push to `main` |
| API + extract, image, video workers | RunPod CPU pod, always on | `docker compose up -d` |
| Blender + edit workers | RunPod RTX 4090 pod, Community Cloud | Custom image from `workers/blender/Dockerfile` |
| Database, auth, storage | Supabase, Free plan | `supabase db push` |
| Queue | Upstash Redis, Free plan | URL in env |

Logging: structured JSON logs with `project_id` and `job_id` on every line.

## TRD: build order, acceptance tests, and risks

Build the pipeline from the command line first, then wrap it in the API,
then add screens. Each milestone ends with a passing acceptance test
before the next starts.

1. **M0 – Spikes.** Together Seedance call to confirm `VIDEO_MODE=frames_only`; one headless Blender render.
2. **M1 – Plan schema v2.0 + extract.** `packages/plan_schema` with levels/stairs/voids; extract worker as a CLI; alignment pass for multi-storey; `scripts/merge_levels.py` for the per-floor workflow.
3. **M2 – Blender build + journey camera.** `scene.py` iterates levels, cuts voids from slabs, builds stair treads. `cameras.py` builds the single continuous spline. `build.py` outputs per-segment driving/clay/boundary files.
4. **M3 – Paid steps.** Image worker (boundary frames), video worker (per-segment Seedance frames-only), cost logging.
5. **M4 – Edit.** ffmpeg hard concat with optional boundary-blend-frames.
6. **M5 – API, DB, and queue.** Migrations, endpoints, RQ wiring, pod start/stop. Tables: projects, plans, journeys, boundaries, segments, generations, jobs, exports, pricing.
7. **M6 – Frontend.** Seven screens in flow order; multi-storey upload branch; plan-editor floor tabs + ghost overlay; journey screen with route reordering; boundary-frame approval grid.
8. **M7 – Hardening.** Budget caps, idempotency, signed URLs, pod idle watchdog, JWT verification, secret-leak scan; then run all test plans.

Acceptance tests:

- [ ] Extraction returns schema-valid JSON for every fixture plan (single + multi), with overall dimensions within 5% of the drawing.
- [ ] Multi-storey alignment pass flags any exterior-wall or stair drift > 0.15 m.
- [ ] Editing a wall in the review screen updates the 3D preview within 200 ms.
- [ ] `build.py` renders a single-storey journey (≤ 12 segments) in under 6 min on an RTX 4090; two-storey (≤ 20 segments) in under 10 min; re-running with no changes renders nothing.
- [ ] The opening + descent segments contain the single CAD-to-photoreal transition; every subsequent segment is photoreal-to-photoreal.
- [ ] Camera never clips a wall, slab, tread or door frame (≥ 0.4 m clearance from walls).
- [ ] Multi-storey: every upper level is reachable from ground via stairs; both ends of every stair sit inside a room or corridor.
- [ ] A video request cannot be submitted without a confirmed estimate; a project over budget gets a 402.
- [ ] Killing a video worker mid-job leads to a retry via the stored provider_job_id, never a duplicate paid generation.
- [ ] Export produces a playable 1280×720 H.264 MP4 with hard cuts on boundary frames (no visible seams after approval) + per-room labels in correct order.
- [ ] The GPU pod stops itself after 15 idle minutes.
- [ ] No secret key appears in the built frontend bundle.

Risks and fallbacks:

| Risk | Impact | Fallback |
| --- | --- | --- |
| Boundary frames don't match perfectly on both sides, causing a visible seam | Jank at segment junctions | Flip the `--boundary-blend-frames 2–4` flag on; re-roll the problem segment at a different seed |
| Multi-storey alignment pass can't locate stairs in Claude's extraction | Wrong vertical connections | Fall back to the review screen's stair-polygon editor; user draws stairs manually |
| Together rejects reference video combined with frames | Camera-path drift | Already-decided: VIDEO_MODE=frames_only, with camera motion in words in the prompt |
| Seedance safety filter flags a boundary pair | Lost spend on one segment | Automatic single retry on content-filter errors (same assets, filter is non-deterministic) |
| RunPod RTX 4090 unavailable | Render delays | Allow any 24 GB GPU type in the pod config |
| Provider prices change | Wrong estimates | Rates live in the `pricing` table; estimates read from it |

Open questions:

- None open. Decided: single-storey → one level at index 0; multi-storey → N levels + stairs. One continuous camera; segments only at natural cut points. CAD→photoreal once; everything else photoreal→photoreal.
