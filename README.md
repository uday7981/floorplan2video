# Floor Plan to Video

Turns a 2D floor plan into a 30–60s architectural walkthrough MP4.

Spec: [`docs/PRD_TRD.md`](docs/PRD_TRD.md). Build in milestone order (M0 → M7); do not start a milestone until the previous one passes its acceptance checks.

## Layout

```
apps/
  web/        Next.js 14 frontend (Vercel)
  api/        FastAPI service (RunPod CPU pod)
workers/
  common/     job helpers, storage, cost logging, retries
  extract/    Claude vision → plan JSON
  blender/    Blender 4.2 LTS headless on RunPod RTX 4090 (Dockerfile here)
  image/      OpenAI image edit → photoreal end frames
  video/      Together AI Seedance 2.5 (provider adapters in providers/)
  edit/       ffmpeg stitch + labels + end card
packages/
  plan_schema/  Pydantic models + exported JSON Schema + TS types (SSOT)
supabase/
  migrations/
  seed.sql
prompts/
  templates.yaml
fixtures/
  plans/      test floor plans + expected plan JSON
scripts/
  spike_*     M0 spikes
docs/
  PRD_TRD.md  product + technical spec (source of truth)
```

## Local dev

1. `cp .env.example .env` and fill in keys.
2. `docker compose up -d` (API, Redis, extract/image/video workers).
3. Blender + edit workers run on a RunPod RTX 4090 pod; see `workers/blender/README.md`.

## Vendor allowlist (hard rule)

Anthropic, Together AI, OpenAI, RunPod, Supabase, Upstash, Vercel. No other paid service.
