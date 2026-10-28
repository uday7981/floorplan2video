# workers/extract — Claude vision → plan JSON

Queue `extract` (M5). Standalone CLI for M1:

```
pip install -e packages/plan_schema
pip install -e workers/extract
export ANTHROPIC_API_KEY=...   # already in .env
export ANTHROPIC_MODEL=claude-opus-5-5
python -m extract --input fixtures/plans/house-01/source.pdf --output /tmp/plan.json
```

Normalises PNG / JPG / WEBP / HEIC / PDF (page 1 at 300dpi) / DXF (via ezdxf +
matplotlib). Rejects DWG with a hint to export as DXF.

Calls Claude with the extraction system prompt (from `prompts/templates.yaml`)
and forces a single `save_plan` tool call whose input is the Plan JSON Schema.
On validation failure, sends the Pydantic error list back once as a repair
turn; if the second attempt still fails, the CLI exits non-zero.

Cost printed to stderr. Pricing comes from `supabase/seed.sql`; swaps to the
Supabase `pricing` table in M5.

Hard rules enforced:
- Model name from `ANTHROPIC_MODEL` env, never hard-coded.
- Tests mock the Anthropic client — no paid calls in CI.
