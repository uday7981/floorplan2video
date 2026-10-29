/**
 * Mock data for M6. In M7 these come from apps/api via the real API client
 * + Supabase realtime. Shape mirrors packages/plan_schema.
 */

import type { Project } from "./types";

export type Pt = [number, number];

export interface Wall {
  id: string;
  a: Pt;
  b: Pt;
  thickness: number;
  height: number;
  exterior?: boolean;
}

export interface Opening {
  id: string;
  wall_id: string;
  type: "door" | "window" | "opening";
  offset: number;
  width: number;
  height: number;
  sill: number;
  main_entrance?: boolean;
}

export interface Room {
  id: string;
  name: string;
  type: "living" | "kitchen" | "dining" | "bedroom" | "bath" | "terrace" | "other";
  polygon: Pt[];
}

export interface Plan {
  schema_version: "1.0";
  units: "m";
  meta: { scale_source: string; confidence: number; warnings: string[] };
  defaults: { wall_height: number; floor_thickness: number };
  walls: Wall[];
  openings: Opening[];
  rooms: Room[];
}

export const MOCK_PROJECT: Project = {
  id: "oakhill",
  name: "Oakhill Residence",
  project_type: "house",
  storey_mode: "single",
  style_preset: { materials: "oak, black aluminium, natural white", light: "3000K", setting: "a beautiful forest" },
  budget_usd: 40,
  spent_usd: 1.84,
  status: "plan_review",
};

export const MOCK_PLAN: Plan = {
  schema_version: "1.0",
  units: "m",
  meta: { scale_source: "dimension_text", confidence: 0.86, warnings: [] },
  defaults: { wall_height: 2.8, floor_thickness: 0.2 },
  walls: [
    { id: "w1", a: [0, 0],   b: [10, 0],  thickness: 0.25, height: 2.8, exterior: true },
    { id: "w2", a: [10, 0],  b: [10, 7],  thickness: 0.25, height: 2.8, exterior: true },
    { id: "w3", a: [10, 7],  b: [0, 7],   thickness: 0.25, height: 2.8, exterior: true },
    { id: "w4", a: [0, 7],   b: [0, 0],   thickness: 0.25, height: 2.8, exterior: true },
    { id: "w5", a: [5, 0],   b: [5, 7],   thickness: 0.12, height: 2.8 },
    { id: "w6", a: [0, 4],   b: [5, 4],   thickness: 0.12, height: 2.8 },
  ],
  openings: [
    { id: "o1", wall_id: "w1", type: "door",   offset: 5.0, width: 1.0, height: 2.1, sill: 0.0, main_entrance: true },
    { id: "o2", wall_id: "w1", type: "window", offset: 2.5, width: 1.4, height: 1.2, sill: 0.9 },
    { id: "o3", wall_id: "w1", type: "window", offset: 7.5, width: 1.4, height: 1.2, sill: 0.9 },
    { id: "o4", wall_id: "w3", type: "window", offset: 2.5, width: 1.4, height: 1.2, sill: 0.9 },
    { id: "o5", wall_id: "w3", type: "window", offset: 7.5, width: 1.4, height: 1.2, sill: 0.9 },
    { id: "o6", wall_id: "w5", type: "door",   offset: 2.0, width: 0.9, height: 2.1, sill: 0.0 },
    { id: "o7", wall_id: "w6", type: "door",   offset: 2.5, width: 0.9, height: 2.1, sill: 0.0 },
  ],
  rooms: [
    { id: "r1", name: "Living",   type: "living",  polygon: [[0.25, 0.25], [4.88, 0.25], [4.88, 3.88], [0.25, 3.88]] },
    { id: "r2", name: "Kitchen",  type: "kitchen", polygon: [[0.25, 4.12], [4.88, 4.12], [4.88, 6.75], [0.25, 6.75]] },
    { id: "r3", name: "Bedroom",  type: "bedroom", polygon: [[5.12, 0.25], [9.75, 0.25], [9.75, 6.75], [5.12, 6.75]] },
  ],
};

export interface MockShot {
  id: string;
  ord: number;
  kind: "opening" | "room" | "exterior";
  room_id?: string;
  label: string;
  move: "dolly" | "pan" | "crane" | "orbit";
  duration_s: 5 | 8;
  lens_mm: number;
  end_frame_approved: boolean;
}

export const MOCK_SHOTS: MockShot[] = [
  { id: "s_opening",  ord: 0, kind: "opening",  label: "Welcome",       move: "crane", duration_s: 5, lens_mm: 35, end_frame_approved: false },
  { id: "s_r01",      ord: 1, kind: "room", room_id: "r1", label: "01 Living",  move: "dolly", duration_s: 8, lens_mm: 18, end_frame_approved: true },
  { id: "s_r02",      ord: 2, kind: "room", room_id: "r2", label: "02 Kitchen", move: "dolly", duration_s: 5, lens_mm: 18, end_frame_approved: false },
  { id: "s_r03",      ord: 3, kind: "room", room_id: "r3", label: "03 Bedroom", move: "dolly", duration_s: 8, lens_mm: 18, end_frame_approved: false },
  { id: "s_exterior", ord: 4, kind: "exterior", label: "Exterior",      move: "orbit", duration_s: 8, lens_mm: 28, end_frame_approved: false },
];

export interface MockTake {
  id: string;
  shot_id: string;
  take: number;
  resolution: "480p" | "720p";
  status: "queued" | "running" | "succeeded" | "failed";
  selected: boolean;
  usd: number;
}

export const MOCK_TAKES: MockTake[] = [
  { id: "g1", shot_id: "s_r01", take: 1, resolution: "480p", status: "succeeded", selected: true,  usd: 0.92 },
  { id: "g2", shot_id: "s_r01", take: 2, resolution: "480p", status: "succeeded", selected: false, usd: 0.92 },
  { id: "g3", shot_id: "s_r02", take: 1, resolution: "480p", status: "succeeded", selected: true,  usd: 0.575 },
  { id: "g4", shot_id: "s_r03", take: 1, resolution: "480p", status: "running",   selected: false, usd: 0.92 },
  { id: "g5", shot_id: "s_opening", take: 1, resolution: "480p", status: "queued", selected: false, usd: 0.575 },
];
