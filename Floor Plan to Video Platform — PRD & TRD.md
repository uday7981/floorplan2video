# Floor Plan to Video Platform — PRD & TRD

Oct 27, 2026 · @uday

## How to use this doc

Build the MVP in the order given in the last section, and treat the PRD as what to build and the TRD as how. Where the doc is silent, pick the simplest option that works and leave a `TODO(decision)` comment.

Rules for the builder:

- Use only the locked vendors: Anthropic, Together AI, OpenAI, RunPod, Supabase, Upstash, Vercel. Add no other paid service.
- Every paid call (image, video) goes through a provider adapter and writes a cost row before and after the call.
- Ship a working end-to-end path for one floor plan before polishing any screen.
- Never put secret keys in frontend code. Only `NEXT_PUBLIC_*` values reach the browser.
- Write a short README per service with run commands and required env vars.

## PRD: overview and goals

The product turns a 2D floor plan into a 30–60 second architectural walkthrough video in under an hour, at about $15–35 per video. It automates a manual workflow: the user models the house in Blender, renders camera previews, generates photoreal frames, and has an AI video model animate a CAD-to-photoreal transition per room.

Problem: architectural animation takes days of modelling, materials, lighting, and rendering. The manual AI workflow is faster, but still needs Blender skills and hand-wiring across several tools.

Goals for the MVP:

1. Upload a floor plan and get an editable 3D model without opening Blender.
2. Auto-generate one camera shot per room, plus an opening shot and an exterior orbit.
3. Produce a stitched MP4 with room labels and titles.
4. Show cost before every paid step and keep the cost of a finished video under $35.
5. Keep geometry and camera paths true to the plan. The AI controls style and light, never layout.

Non-goals for the MVP:

- Furniture placement, landscaping, or multi-storey buildings beyond a single floor
- Interactive 3D walkthroughs for end viewers
- Team accounts, billing, or a public marketplace
- Audio, music, or voice-over
- Any video model other than Seedance 2.5 through Together AI

## PRD: users and core flow

The primary user is an architect, interior designer, or real-estate marketer who has a floor plan but no Blender skills or time. The secondary user is the internal operator (you), who runs test plans and tunes prompts.

Core flow, with a human checkpoint before every paid step:

1. **Create project.** Enter a name, pick a project type (House or Interior), and pick a style preset (default: oak, black aluminium, natural white, 3000K).
2. **Upload plan.** PNG, JPG, PDF, or DXF, one floor, up to 20 MB.
3. **Extract.** Claude reads the plan and returns plan JSON: walls, openings, rooms, scale.
4. **Review plan (checkpoint 1).** The user sees the extracted walls overlaid on the original image beside a live 3D preview, fixes any errors, and approves.
5. **Shot list.** The system proposes shots: an opening blueprint shot, one per room, and an exterior orbit. The user reorders, removes, or tweaks them.
6. **Render previews.** Blender builds the scene and renders, per shot, a driving clip, a CAD-style start frame, and a clay reference of the last frame.
7. **Approve end frames (checkpoint 2).** One photoreal end frame per shot. The user approves or regenerates each.
8. **Generate videos (checkpoint 3).** The user sees the estimated cost, picks draft (480p) or final (720p), and confirms. Shots run in parallel.
9. **Pick takes.** The user picks the best take per shot or re-rolls a shot.
10. **Export.** The system stitches the chosen takes with titles, room labels, and an end card, and returns a downloadable MP4.

## PRD: functional requirements

P0 items make up the MVP; P1 items follow once one plan runs end to end.

| ID | Area | Requirement | Priority |
| --- | --- | --- | --- |
| FR-01 | Projects | Create, list, rename, and delete projects. Each project stores a style preset and a project type: House (opening, rooms, exterior orbit, roof built) or Interior (opening and rooms only, no exterior orbit, no roof). | P0 |
| FR-02 | Upload | Accept any image (PNG, JPG, WEBP, HEIC), any PDF (vector or scanned, any page count), and any DXF (any units, layers, or drafting style) up to 50 MB. Show a page picker for multi-page PDFs and a layer picker for DXFs. Store the original file. | P0 |
| FR-03 | Extract | Produce plan JSON that validates against the schema. On failure, show the error and allow a retry. | P0 |
| FR-04 | Extract | Ask for one known dimension (e.g. overall width in metres) if the plan has no readable scale. | P0 |
| FR-05 | Review | Overlay walls, doors, and windows on the source image. Users can move wall endpoints, change thickness, and add or delete openings. | P0 |
| FR-06 | Review | Live three.js preview that updates within 200 ms of each edit. | P0 |
| FR-07 | Review | Every save creates a new plan version. Users can revert to an earlier one. | P1 |
| FR-08 | Shots | Auto-generate shots by project type: the opening shot and one shot per room over 4 m² for both types, plus the exterior orbit for House. Users can still toggle the opening and exterior shots on or off. | P0 |
| FR-09 | Shots | Users reorder, delete, rename, and choose a move per shot (dolly, pan, crane, or orbit) and a duration (5 s default, or 8 s for large spaces). | P0 |
| FR-10 | Render | Per shot, produce a 24 fps, 1280x720 driving clip at the shot's duration (5 or 8 s), a CAD start frame, and a clay end-frame reference. | P0 |
| FR-11 | End frames | Generate one photoreal end frame per shot from the clay reference and style prompt. Approve or regenerate each. | P0 |
| FR-12 | Video | Show estimated cost before submitting. Draft runs at 480p and final at 720p. | P0 |
| FR-13 | Video | Submit all approved shots in parallel. Show live status per take. | P0 |
| FR-14 | Video | Users re-roll a single shot without touching the others. | P0 |
| FR-15 | Takes | Gallery per shot with all takes playable. Users mark one as selected. | P0 |
| FR-16 | Export | Stitch selected takes in shot order, add title, room labels, captions, and an end card. Output an H.264 MP4. | P0 |
| FR-17 | Cost | Running cost per project, shown on every screen. | P0 |
| FR-18 | Cost | Block paid jobs when a project passes its budget cap (default $40) unless the user raises it. | P0 |
| FR-19 | Auth | Email magic-link sign-in. Users only see their own projects. | P1 |
| FR-20 | Notify | Email when an export is ready. | P1 |

## PRD: non-functional requirements, cost, and success

A plan should go from upload to exported MP4 in under 60 minutes of wall-clock time, excluding time the user spends on review.

| Area | Requirement |
| --- | --- |
| Speed | Extraction under 60 s. All Blender previews for 9 shots under 10 min. Video jobs run in parallel. |
| Reliability | Every job is retryable and idempotent. A failed shot never blocks other shots. |
| Cost visibility | Every paid call logs provider, model, units, and USD cost. Estimates show before each paid step. |
| Security | API keys server-side only. Signed URLs for files, expiring in 1 hour. Row-level security in Postgres. |
| Data | Originals, renders, and takes kept for 30 days in the MVP. |
| Browsers | Latest Chrome, Edge, and Safari on desktop. Mobile is view-only. |

Cost guardrails, based on indicative October 2026 rates:

| Item | Indicative rate | Per video (9 shots x 5 s, 2.5 takes) |
| --- | --- | --- |
| Seedance 2.5 draft, 480p | \~$0.10/s | \~$11 |
| Seedance 2.5 final, 720p | \~$0.23/s | \~$26 |
| End frames (OpenAI images) | \~$0.05–0.20 each | \~$2–4 |
| Blender GPU (RunPod RTX 4090) | \~$0.34–0.69/hr | <$0.50 |
| Claude extraction | per token | <$1 |

Rates change often. Store them in a `pricing` config table, never hard-coded.

Success metrics for the MVP:

- 4 of your 5 test plans reach an exported MP4.
- Geometry matches the source plan within 5% on overall dimensions.
- Average takes per usable shot is 2.5 or fewer.
- Cost per final 720p video is under $35, including drafts.

## TRD: architecture, stack, and environment

A Next.js app on Vercel calls a FastAPI service, which writes to Supabase and enqueues jobs in Upstash Redis. Five Python workers consume the queue; the Blender and edit workers run on a RunPod GPU pod, and the others can run anywhere.

| Layer | Choice | Notes |
| --- | --- | --- |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind, react-three-fiber | Hosted on Vercel |
| API | FastAPI, Python 3.11, Pydantic v2 | Shares the plan schema package with workers |
| DB, auth, storage, realtime | Supabase (Postgres 15) | Realtime pushes job status to the UI |
| Queue | Upstash Redis + RQ | One queue per worker type |
| Extract worker | Anthropic API, Claude vision with tool-use JSON output | Model name set in env |
| Blender worker | Blender 4.2 LTS headless in Docker | RunPod RTX 4090 pod, EGL rendering |
| Image worker | OpenAI Images API, edit endpoint with reference image | Model name set in env |
| Video worker | Together AI, Seedance 2.5 | Reference video + first/last frame |
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
```

The Seedance model string comes from Together's quickstart docs; confirm it on the first test call.

## TRD: data model

Seven tables in Postgres. All ids are UUIDs, all tables have `created_at` and `updated_at`, and row-level security limits rows to `owner_id = auth.uid()` through `projects`.

```sql
create table projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users,
  name text not null,
  style_preset jsonb not null,        -- materials, light, prompt suffix
  project_type text not null default 'house', -- house|interior
  budget_usd numeric not null default 40,
  spent_usd numeric not null default 0,
  status text not null default 'draft' -- draft|plan_review|shots|rendering|frames|video|exported
);

create table plans (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  version int not null,
  source_path text not null,          -- storage path of uploaded file
  plan_json jsonb,                    -- validated plan schema
  plan_hash text,                     -- sha256 of canonical plan_json
  approved boolean not null default false,
  unique (project_id, version)
);

create table shots (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  plan_id uuid not null references plans,
  ord int not null,
  kind text not null,                 -- opening|room|exterior
  room_id text,                       -- id from plan_json.rooms
  label text not null,
  camera jsonb not null,              -- move, path, lens, duration_s
  render_hash text,                   -- hash(plan_hash + camera)
  driving_clip_path text,
  start_frame_path text,
  clay_ref_path text,
  end_frame_path text,
  end_frame_approved boolean not null default false
);

create table generations (
  id uuid primary key default gen_random_uuid(),
  shot_id uuid not null references shots on delete cascade,
  kind text not null,                 -- end_frame|video
  provider text not null,             -- openai|together
  model text not null,
  resolution text,                    -- 480p|720p
  prompt text not null,
  provider_job_id text,
  status text not null,               -- queued|running|succeeded|failed
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
  type text not null,                 -- extract|render|end_frame|video|export
  ref_id uuid,                        -- plan, shot or generation id
  status text not null,               -- queued|running|succeeded|failed
  attempts int not null default 0,
  error text,
  started_at timestamptz,
  finished_at timestamptz
);

create table exports (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects on delete cascade,
  generation_ids uuid[] not null,
  output_path text,
  status text not null
);

create table pricing (
  key text primary key,               -- e.g. together.seedance-2.5.720p
  unit text not null,                 -- per_second|per_image|per_mtok
  usd numeric not null,
  updated_at timestamptz not null default now()
);
```

Storage buckets: `uploads`, `renders`, `frames`, `takes`, `exports`. Paths follow `{project_id}/{shot_id}/{file}`.

## TRD: plan JSON schema

Plan JSON is the single source of truth for geometry. Extraction writes it, the review screen edits it, and the Blender script and three.js preview both read it. Define it once as Pydantic models in `packages/plan_schema`, and generate the TypeScript types from its JSON Schema.

Conventions: units are metres, the origin is the plan's bottom-left corner, x points right and y points up, and z is height. All coordinates round to 0.01 m.

```json
{
  "schema_version": "1.0",
  "units": "m",
  "meta": {
    "scale_source": "dimension_text",   // dimension_text | scale_bar | user_input
    "confidence": 0.82,
    "warnings": ["Room 'Store' dimensions unreadable, estimated"]
  },
  "defaults": { "wall_height": 2.8, "floor_thickness": 0.2 },
  "walls": [
    {
      "id": "w1",
      "a": [0, 0], "b": [12.0, 0],
      "thickness": 0.23,
      "height": 2.8,
      "exterior": true
    }
  ],
  "openings": [
    {
      "id": "o1",
      "wall_id": "w1",
      "type": "door",                    // door | window | opening
      "offset": 3.2,                      // metres from wall start (a) to opening centre
      "width": 1.0,
      "height": 2.1,
      "sill": 0.0,
      "main_entrance": true
    }
  ],
  "rooms": [
    {
      "id": "r1",
      "name": "Living",
      "type": "living",                  // living | kitchen | dining | bedroom | bath | terrace | other
      "polygon": [[0.23, 0.23], [6.0, 0.23], [6.0, 5.0], [0.23, 5.0]]
    }
  ]
}
```

Validation rules, enforced server-side on every save:

- Wall length is at least 0.3 m and thickness is between 0.05 and 0.6 m.
- Each opening fits inside its wall: `offset ± width/2` stays within the wall's length, and `sill + height` stays at or below the wall height.
- Room polygons are closed, non-self-intersecting, and have an area of at least 1 m².
- Exactly one opening has `main_entrance: true`; the opening and entry shots start from it.
- Overall bounding box is between 3 m and 60 m on each side; anything outside means the scale is wrong.

## TRD: API endpoints

All endpoints are under `/v1`, take a Supabase JWT in the `Authorization` header, and return JSON. Long work always returns a `job_id`; the client follows progress through Supabase realtime on the `jobs` and `generations` tables.

| Method | Path | Purpose | Returns |
| --- | --- | --- | --- |
| POST | /projects | Create project with name and style preset | project |
| GET | /projects | List own projects | project\[\] |
| GET | /projects/{id} | Project with plan, shots, generations, spend | project detail |
| DELETE | /projects/{id} | Delete project and its files | 204 |
| POST | /projects/{id}/plans/upload-url | Signed upload URL for the floor plan | url, path |
| POST | /projects/{id}/plans/extract | Start extraction for an uploaded file; optional `known_dimension_m` | job\_id |
| PUT | /plans/{id} | Save edited plan JSON as a new version (validated) | plan |
| POST | /plans/{id}/approve | Approve plan and auto-generate shots | shot\[\] |
| PUT | /projects/{id}/shots | Replace shot list (order, camera, labels) | shot\[\] |
| POST | /projects/{id}/render | Render previews for all shots, skipping cache hits | job\_id |
| POST | /shots/{id}/end-frame | Generate or regenerate the end frame | generation |
| POST | /shots/{id}/end-frame/approve | Approve current end frame | shot |
| POST | /projects/{id}/estimate | Cost estimate for video run; body `resolution`, `shot_ids` | usd, breakdown |
| POST | /projects/{id}/videos | Submit video jobs; body `resolution`, `shot_ids`, `confirm_usd` | generation\[\] |
| POST | /generations/{id}/select | Mark take as selected for its shot | generation |
| POST | /projects/{id}/export | Stitch selected takes | job\_id |
| GET | /files/sign?path= | Short-lived signed read URL | url |
| POST | /webhooks/together | Optional: provider completion callback | 200 |

Rules:

- `POST /videos` rejects the request with 409 if `confirm_usd` is lower than the server's fresh estimate, so prices can't drift between estimate and submit.
- Any paid endpoint returns 402 when `spent_usd + estimate > budget_usd`.
- Error body shape is `{ "error": { "code": "...", "message": "..." } }`.

## TRD: workers and job pipeline

Each worker pulls from its own RQ queue, updates the `jobs` row at start and finish, and is safe to re-run. Failures retry 3 times with backoff of 10 s, 60 s, and 300 s, then mark the job `failed` with the error text.

### Extract worker (queue `extract`)

1. Download the upload. Convert PDF page 1 to a 2048 px PNG, and DXF to a PNG plus a direct wall import via `ezdxf` (use the DXF geometry, and the image only for room names).
2. Call Claude with the image and the extraction prompt, forcing a single tool call whose input schema is the plan JSON schema.
3. Validate with Pydantic. On failure, send the validation errors back to Claude once to repair; if it still fails, fail the job with errors shown to the user.
4. Save as plan version 1 with `approved = false`.

Input handling, because uploads can be anything:

- **Images:** convert HEIC and WEBP to PNG, cap the long side at 4096 px, auto-deskew, and boost contrast on photos and scans.
- **PDFs:** render a thumbnail per page and let the user pick the floor plan page. Check whether the page is vector or raster with PyMuPDF. For vector pages, pass the extracted line geometry and text (dimensions, room names) to Claude alongside a 300 dpi render. For raster pages, send the render only.
- **DXFs:** read units from `$INSUNITS`, and ask the user if it is unset. Explode block inserts so door and window symbols become geometry. Guess wall, door, and window layers from names (e.g. WALL, A-WALL, MUR, DOOR, WIN) and from parallel line pairs, then show the layer picker for the user to confirm. Take room names from TEXT and MTEXT. Render a PNG for the review overlay and for Claude.
- **DWG and other CAD formats:** reject with a message to export as DXF.

### Blender worker (queue `render`, on RunPod)

Entry point: `blender -b --factory-startup -P build.py -- --plan plan.json --shots shots.json --out /tmp/out`.

1. Build: extrude each wall as a box from `a` to `b` with its thickness and height, cut openings with boolean modifiers, add a floor slab and, for House projects only, a flat roof slab, and assign materials from the style preset.
2. Exterior: a ground plane, a sun at 35° elevation, and a simple HDRI-free sky colour.
3. Interior light: one area light per room at ceiling height.
4. Cameras per shot type, 24 fps at the shot's duration: 5 s (120 frames) or 8 s (192 frames):
   - Room: camera at 1.6 m height, 0.6 m inside the room from the opening that leads into it, aimed at the room centroid, dollying 1.5 m forward. 18 mm lens.
   - Opening: the source plan image on a desk plane, top-down, craning up 2 m while the 3D line model rises out of the plan. 35 mm lens.
   - Exterior: orbit 90° around the building centre at radius 0.8 x bbox diagonal and height 6 m, aimed at mid-wall height. 28 mm lens.
5. Outputs per shot:
   - `driving.mp4`: Workbench, solid shading, 1280x720, 24 fps
   - `start.png`: frame 1, Freestyle white lines over flat white materials (the CAD look)
   - `clay.png`: last frame, Workbench clay shading, used as the end-frame reference
6. Skip any shot whose `render_hash` already has outputs in storage.

### Image worker (queue `end_frame`)

Send `clay.png` and the end-frame prompt to the OpenAI image edit endpoint at 1280x720 (or the closest supported size, then crop). Save to `frames/`, log cost, and set the shot's `end_frame_path`.

### Video worker (queue `video`)

1. Build the request through a `VideoProvider` adapter: `submit(driving_clip_url, start_url, end_url, prompt, resolution, duration_s) -> provider_job_id` and `poll(provider_job_id) -> status, output_url, usage`.
2. Together implementation: Seedance 2.5 with `frame_images` first = `start.png`, last = end frame, plus `driving.mp4` as a reference video. Disable audio if the API allows it.
3. Poll every 15 s, time out at 20 min, download the output to `takes/`, and log actual cost from the usage field.
4. Fallback mode, behind a flag `VIDEO_MODE=frames_only`: if the provider rejects reference video combined with frames, send first and last frames only and put the camera move in words in the prompt.

### Edit worker (queue `export`, on RunPod)

1. Normalise each selected take to 1280x720, 24 fps, H.264, no audio.
2. Join in shot order with a 0.3 s crossfade (`xfade`).
3. Overlay with `drawtext`: the project title on the opening shot, then per room a numbered label ("01 Living") and an optional one-line caption, bottom-left, Helvetica Bold or Inter Bold.
4. Append a 2 s end card with the project name over the last frame, then upload to `exports/`.

### GPU pod lifecycle

The API starts the RunPod pod through the RunPod API when a `render` or `export` job is queued and the pod is stopped. The worker stops its own pod after `POD_IDLE_SHUTDOWN_MINUTES` with an empty queue.

## TRD: prompt templates

Store templates in a `prompt_templates` config file (or table) with `{placeholders}`, versioned, so prompts change without a redeploy. The style preset supplies `{materials}`, `{light}`, and `{setting}`; the default is "oak, black aluminium, natural white", "3000K light", and "a beautiful forest".

### Extraction (Claude, system prompt)

```
You convert architectural floor plans into structured geometry.
Return the plan only by calling the save_plan tool. Never reply in prose.

Rules:
- Units are metres. Origin is the bottom-left of the building, x right, y up.
- Read dimension text first. If none is readable, use a scale bar. If neither
  exists, use known_dimension_m from the user if provided. Record which in
  meta.scale_source.
- Model every wall as a centreline segment with thickness. Join walls at
  corners so endpoints match exactly.
- Doors, windows and open passages are openings on a wall, measured from the
  wall's start point to the opening centre.
- Every labelled space becomes a room with a closed polygon inside the walls.
- Mark exactly one exterior door as main_entrance.
- If anything is guessed, lower meta.confidence and add a warning.
```

### End frames (OpenAI image edit, with clay.png as the image)

Room shot:

```
Hybrid of a white CAD model and a professional photorealistic image of an
architecturally designed {room_type} interior, {materials}, {light}.
Hybrid between CAD and photorealistic. Keep the exact walls, openings,
camera angle and framing of the reference image. Background is {setting}.
```

Exterior shot:

```
Hybrid of a professional photorealistic image of an architecturally designed
home exterior, {materials}, {light}. Hybrid between CAD and photorealistic.
Keep the exact building massing, openings, camera angle and framing of the
reference image. Background is {setting}.
```

Opening shot:

```
Photorealistic architectural drawing on a wooden desk, hybrid of CAD line
drawing and photorealistic 3D model rising from the plan, {light}. Keep the
exact plan layout and camera angle of the reference image.
```

### Video (Seedance 2.5)

Standard, with a driving video:

```
Use the reference video as the driving video for camera movement. Camera
{move_words} through the space. Style transition from CAD drawing to
photorealistic, progressively. Start with the first frame and finish with
this exact shot: the last frame.
```

`{move_words}` maps from the shot's camera move: dolly = "moves slowly forward", pan = "pans slowly", crane = "rises slowly", orbit = "orbits the building once".

Fallback, frames only: the same prompt without the first sentence, plus the camera distance and direction in words (for example, "moves 1.5 metres forward at eye height").

## TRD: frontend screens

Six routes, each mapped to one step of the flow. A stepper across the top of every project page shows the current step, and a cost badge in the header shows spend against budget.

| Route | Screen | Key components | Done when |
| --- | --- | --- | --- |
| `/` | Project list | Project cards with status and spend; New project dialog with name and style preset | User opens or creates a project |
| `/p/[id]/upload` | Upload | Drag-and-drop to signed URL; optional known dimension field; extraction progress | Extraction job succeeds |
| `/p/[id]/plan` | Plan review | Left: SVG overlay of walls, openings, room labels on the source image, with draggable endpoints and an inspector panel. Right: react-three-fiber preview with orbit controls. Warnings banner from `meta.warnings` | User clicks Approve plan |
| `/p/[id]/shots` | Shots and frames | Sortable shot list; per shot a camera move dropdown, driving clip player, start frame, clay ref, end frame with Regenerate and Approve | All end frames approved |
| `/p/[id]/video` | Video generation | Resolution toggle (480p draft / 720p final), cost estimate, Confirm button; per-shot take gallery with status, play, Select, Re-roll | One take selected per shot |
| `/p/[id]/export` | Export | Title and caption fields per shot, Export button, progress, final player and Download | MP4 ready |

Implementation notes:

- The 3D preview builds meshes from plan JSON in the browser with the same rules as `build.py`. It never calls Blender.
- Subscribe to Supabase realtime on `jobs` and `generations` filtered by `project_id`. Do not poll.
- Keep the plan editor state local, debounce saves by 1 s, and show unsaved changes.
- Every paid button shows its cost in the label, for example "Generate 9 videos at 480p · \~$4.50".

## TRD: infra, deployment, and repo

One monorepo, with docker-compose running everything locally except the GPU worker. Deployment splits across three hosts: Vercel for the web app, RunPod for GPU work, and an always-on RunPod CPU pod for the API and CPU workers. The GPU pod auto-stops when idle, so the API must not live on it.

```
floorplan-video/
  apps/
    web/                  # Next.js frontend
    api/                  # FastAPI service
  workers/
    common/               # job helpers, storage, cost logging, retries
    extract/
    blender/
      Dockerfile          # Blender 4.2 LTS + ffmpeg + EGL
      build.py            # plan JSON + shots JSON -> renders
      cameras.py
      materials.py
    image/
    video/
      providers/
        base.py           # VideoProvider interface
        together.py
    edit/
  packages/
    plan_schema/          # Pydantic models + exported JSON Schema + TS types
  supabase/
    migrations/           # SQL from the data model section
    seed.sql              # pricing rows, default style preset
  prompts/
    templates.yaml
  fixtures/
    plans/                # your test floor plans + expected plan JSON
  docker-compose.yml      # api, redis, extract, image, video workers
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

Logging: structured JSON logs with `project_id` and `job_id` on every line. Add Sentry later.

## TRD: build order, acceptance tests, and risks

Build the pipeline from the command line first, then wrap it in the API, then add screens. Each milestone ends with a passing acceptance test before the next starts.

1. **M0 – Spikes (first hour).** One Together call with reference video + first/last frame; one headless Blender render on the RunPod pod. Results decide `VIDEO_MODE`.
2. **M1 – Plan schema and extraction.** `packages/plan_schema`, extract worker as a CLI on one fixture plan.
3. **M2 – Blender build and renders.** `build.py` produces all three outputs per shot for the M1 plan JSON.
4. **M3 – Paid steps.** Image and video workers as CLIs, with cost logging.
5. **M4 – Edit.** ffmpeg export from local takes.
6. **M5 – API, DB, and queue.** Migrations, endpoints, RQ wiring, pod start/stop.
7. **M6 – Frontend.** Screens in flow order: upload, plan review, shots, video, export.
8. **M7 – Hardening.** Budget caps, retries, signed URLs, then run all test plans.

Acceptance tests:

- [ ] Extraction returns schema-valid JSON for every fixture plan, with overall dimensions within 5% of the drawing.
- [ ] Editing a wall in the review screen updates the 3D preview within 200 ms.
- [ ] `build.py` renders 9 shots in under 10 minutes on an RTX 4090, and re-running with no changes renders nothing.
- [ ] The start frame looks like white CAD lines and matches frame 1 of the driving clip exactly.
- [ ] A video request cannot be submitted without a confirmed estimate, and a project over budget gets a 402.
- [ ] Killing a video worker mid-job leads to a retry, never a duplicate paid generation.
- [ ] Export produces a playable 1280x720 H.264 MP4 with labels in the right order.
- [ ] The GPU pod stops itself after 15 idle minutes.
- [ ] No secret key appears in the built frontend bundle.

Risks and fallbacks:

| Risk | Impact | Fallback |
| --- | --- | --- |
| Together rejects reference video combined with first/last frames | Camera paths drift | `VIDEO_MODE=frames_only`; keep moves short and describe them in words |
| Claude misreads scale or walls on poor scans | Wrong geometry downstream | Ask for a known dimension; the review screen is mandatory before renders |
| Headless Blender can't get a GPU/EGL context | No renders | Use Cycles CPU at low samples for previews; slower but works |
| Seedance re-roll rate is higher than 2.5 per shot | Cost overrun | Budget cap blocks spend; draft at 480p before 720p |
| RunPod RTX 4090 unavailable | Render delays | Allow any 24 GB GPU type in the pod config |
| Provider prices change | Wrong estimates | Rates live in the `pricing` table; estimates read from it |

Open questions:

- None open. Decided: project type House or Interior controls the exterior orbit and roof; shot duration defaults to 5 s, with 8 s selectable per shot.
