/**
 * Local types for API responses. These mirror apps/api/schemas.py. In M7
 * they'll be generated from packages/plan_schema's exported JSON Schema +
 * api OpenAPI spec; for now they're hand-rolled.
 */

export type ProjectType = "house" | "interior";
export type StoreyMode = "single" | "multi";

export type ProjectStatus =
  | "draft"
  | "plan_review"
  | "journey"
  | "boundary_frames"
  | "rendering"
  | "video"
  | "exported";

export interface Project {
  id: string;
  name: string;
  project_type: ProjectType;
  storey_mode: StoreyMode;
  style_preset: Record<string, string>;
  budget_usd: number;
  spent_usd: number;
  status: ProjectStatus;
}

export interface StylePreset {
  materials: string;
  light: string;
  setting: string;
}
