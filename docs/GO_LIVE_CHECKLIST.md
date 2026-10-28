# Go-live checklist

Everything that must happen before the first real paying user. The
code is in; these are the one-time human/operational steps.

## 1. Rotate the credentials shared in chat (critical, do first)

The following keys were posted into this Claude session's history and
should be considered compromised. Rotate each + update `.env`.

| Service     | Key              | Where to rotate                                                      |
|-------------|------------------|----------------------------------------------------------------------|
| Anthropic   | `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys → revoke + new                     |
| OpenAI      | `OPENAI_API_KEY`    | platform.openai.com → API keys → rotate                             |
| Together AI | `TOGETHER_API_KEY`  | api.together.ai → settings → API keys → regenerate                  |
| RunPod      | `RUNPOD_API_KEY`    | runpod.io → User Settings → API Keys → revoke + new                 |
| Supabase    | `SUPABASE_SERVICE_ROLE_KEY` | project settings → API → Reset service role (also rotates JWT secret) |
| Upstash     | `UPSTASH_REDIS_URL` | console.upstash.com → database → Rotate password                    |

After rotation: update `.env` locally, then push the new values to the
RunPod pod environment (`runpodctl` or the pod's edit screen).

## 2. Apply Supabase migrations

Once per project — creates the 7 tables, RLS policies, triggers, storage buckets.

```bash
# A) migrations
psql "$DATABASE_URL" -f supabase/migrations/0001_init.sql

# B) seed pricing
psql "$DATABASE_URL" -f supabase/seed.sql

# C) create the five storage buckets
#    Via dashboard → Storage → New bucket: uploads, renders, frames, takes, exports
#    All private (no public access); the API returns signed URLs.
```

CORS: Supabase Storage → Settings → add the Vercel preview + prod domains.

## 3. Enable production JWT verification

Set `SUPABASE_JWT_VERIFY=1` and `SUPABASE_JWT_SECRET=<your jwt secret>` on the
API's pod environment. The pod will refuse any unsigned / mis-signed tokens.
Supabase's JWT secret lives at Project Settings → API → JWT Secret (don't
confuse with the service role key).

## 4. Start the pod idle watchdog

On the GPU pod, run alongside the RQ worker:

```bash
nohup python workers/blender/scripts/idle_watchdog.py >> /var/log/idle_watchdog.log 2>&1 &
```

It polls the `render` + `export` queues every 60 s and calls RunPod stop_pod
after `POD_IDLE_SHUTDOWN_MINUTES` of consecutive empty queues (default 15).

## 5. Verify the acceptance tests on live data

Four of the five test plans haven't been exercised yet. Drop them in:

```
fixtures/plans/plan-02/source.<png|jpg|pdf|dxf>
fixtures/plans/plan-03/source...
fixtures/plans/plan-04/source...
fixtures/plans/plan-05/source...
```

Then run the full end-to-end against each. Estimated cost (per plan, 480p):

```
extract (Claude Opus 5.5)   ~$0.35
end frames (×7 shots)       ~$1.75
videos    (×7 shots @ 480p) ~$6.44
                            ────────
                            ~$8.54 per plan
                            ─────────
                      5 plans ≈ $42.70
```

If the budget is tight, run plan-02 and plan-03 at 480p first (~$17) before
committing to all five.

## 6. Verify no secrets in the shipped frontend bundle

Already automated — reproduce any time:

```bash
cd apps/web
npm run build
grep -r -l -E "sk-ant-usr|tgp_v1_|rpa_|sk-proj-|SERVICE_ROLE" .next/ && \
  echo "SECRETS LEAKED" || echo "clean"
```

Expected: `clean`.

## 7. Vercel deployment

```
vercel link
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
vercel env add NEXT_PUBLIC_API_URL      # https://api.<domain>
vercel --prod
```

No server-only secrets (`ANTHROPIC_API_KEY` etc.) belong in Vercel's env —
those stay on the pod with the FastAPI service.
