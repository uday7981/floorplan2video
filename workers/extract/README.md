# workers/extract — Claude vision → plan JSON

Queue `extract`. Downloads the upload, normalises PDF/DXF/image per the TRD, calls
Claude with the extraction system prompt + the `save_plan` tool, validates with
Pydantic (`packages/plan_schema`), one repair round if validation fails, saves as
plan version 1. Built in **M1**.
