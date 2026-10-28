# plan_schema

Single source of truth for plan JSON. Pydantic v2 models here; the TypeScript types
and the published JSON Schema are generated from them.

Built out in **M1**. For now this is a scaffold only.

Rules enforced here (from TRD):
- walls: length ≥ 0.3 m, thickness ∈ [0.05, 0.6] m
- openings fit inside their wall: `offset ± width/2` within wall length; `sill + height ≤ wall height`
- rooms: closed, non-self-intersecting polygons with area ≥ 1 m²
- exactly one opening with `main_entrance: true`
- building bounding box in [3, 60] m per side (else scale is wrong)
