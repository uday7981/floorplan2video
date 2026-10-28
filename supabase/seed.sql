-- Pricing table seed. Rates from docs.together.ai, openai.com, and anthropic.com
-- as of 2026-10-27. Update here; no code change needed. See docs/PRD_TRD.md.

insert into pricing (key, unit, usd) values
  ('together.seedance-2.5.480p', 'per_second', 0.115),
  ('together.seedance-2.5.720p', 'per_second', 0.249),
  -- OpenAI image edit: real rate varies by output size. TODO(decision): pin to
  -- the gpt-image-1 "medium" tier price; refresh when the model name is set.
  ('openai.gpt-image-1.1280x720', 'per_image', 0.08),
  -- Claude extraction. Pricing per Mtok (Million tokens). TODO(decision):
  -- verify Opus 5.5 rates against Anthropic docs on first live call; adjust here.
  ('anthropic.claude-opus-5-5.input',    'per_mtok', 15.00),
  ('anthropic.claude-opus-5-5.output',   'per_mtok', 75.00),
  ('anthropic.claude-sonnet-4-6.input',  'per_mtok', 3.00),
  ('anthropic.claude-sonnet-4-6.output', 'per_mtok', 15.00)
on conflict (key) do update set usd = excluded.usd, updated_at = now();
