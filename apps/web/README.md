# apps/web — Next.js 14 (App Router)

Six routes, built in **M6**:
- `/` project list
- `/p/[id]/upload`
- `/p/[id]/plan`
- `/p/[id]/shots`
- `/p/[id]/video`
- `/p/[id]/export`

Only `NEXT_PUBLIC_*` env vars reach the bundle. Supabase realtime pushes job
status; no polling.
