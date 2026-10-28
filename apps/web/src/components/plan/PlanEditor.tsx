"use client";

import * as React from "react";
import type { Plan, Pt } from "@/lib/mock-data";
import { cn } from "@/lib/cn";

/**
 * SVG wall-overlay editor. Draggable wall endpoints, visible openings, rooms
 * as semi-transparent fills with labels at centroids. Units = metres; the
 * SVG viewBox is set from the plan bbox so no manual scaling is needed.
 */
export function PlanEditor({
  plan,
  onChange,
  className,
}: {
  plan: Plan;
  onChange: (p: Plan) => void;
  className?: string;
}) {
  const bbox = React.useMemo(() => bboxOf(plan), [plan]);
  const PAD = 0.6;
  const vb = `${bbox.min[0] - PAD} ${bbox.min[1] - PAD} ${
    bbox.max[0] - bbox.min[0] + PAD * 2
  } ${bbox.max[1] - bbox.min[1] + PAD * 2}`;

  const [dragging, setDragging] = React.useState<{ wallId: string; end: "a" | "b" } | null>(null);
  const svgRef = React.useRef<SVGSVGElement>(null);

  const svgToWorld = (clientX: number, clientY: number): Pt => {
    const svg = svgRef.current;
    if (!svg) return [0, 0];
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const m = svg.getScreenCTM()?.inverse();
    if (!m) return [0, 0];
    const p = pt.matrixTransform(m);
    return [round01(p.x), round01(bbox.max[1] + bbox.min[1] - p.y)]; // flip y
  };

  function onPointerMove(e: React.PointerEvent) {
    if (!dragging) return;
    const [x, y] = svgToWorld(e.clientX, e.clientY);
    onChange({
      ...plan,
      walls: plan.walls.map((w) =>
        w.id === dragging.wallId ? { ...w, [dragging.end]: [x, y] as Pt } : w,
      ),
    });
  }

  return (
    <div className={cn("relative overflow-hidden bg-paper-dim/50", className)}>
      <GridBackdrop />
      <svg
        ref={svgRef}
        viewBox={vb}
        preserveAspectRatio="xMidYMid meet"
        className="relative z-10 h-full w-full select-none"
        style={{
          transform: "scale(1, -1)",   // flip so y goes up
          transformOrigin: "center",
        }}
        onPointerMove={onPointerMove}
        onPointerUp={() => setDragging(null)}
        onPointerLeave={() => setDragging(null)}
      >
        {/* rooms (filled underneath) */}
        {plan.rooms.map((r) => (
          <polygon
            key={r.id}
            points={r.polygon.map((p) => `${p[0]},${p[1]}`).join(" ")}
            fill="rgb(31 58 95 / 0.04)"
            stroke="rgb(31 58 95 / 0.25)"
            strokeWidth={0.02}
          />
        ))}

        {/* walls */}
        {plan.walls.map((w) => (
          <line
            key={w.id}
            x1={w.a[0]}
            y1={w.a[1]}
            x2={w.b[0]}
            y2={w.b[1]}
            stroke={w.exterior ? "rgb(20 19 17)" : "rgb(20 19 17 / 0.6)"}
            strokeWidth={w.thickness}
            strokeLinecap="square"
          />
        ))}

        {/* openings — overlay segments that look like gaps in the wall */}
        {plan.openings.map((op) => {
          const w = plan.walls.find((x) => x.id === op.wall_id);
          if (!w) return null;
          const seg = segmentForOpening(w, op);
          return (
            <line
              key={op.id}
              x1={seg.a[0]}
              y1={seg.a[1]}
              x2={seg.b[0]}
              y2={seg.b[1]}
              stroke={op.main_entrance ? "rgb(163 66 28)" : "rgb(245 241 234)"}
              strokeWidth={w.thickness + 0.04}
              strokeLinecap="butt"
            />
          );
        })}

        {/* draggable endpoints — one per wall end */}
        {plan.walls.flatMap((w) =>
          (["a", "b"] as const).map((end) => (
            <circle
              key={`${w.id}-${end}`}
              cx={w[end][0]}
              cy={w[end][1]}
              r={0.09}
              fill="rgb(20 19 17)"
              stroke="rgb(245 241 234)"
              strokeWidth={0.03}
              className="cursor-grab touch-none transition-standard duration-micro hover:fill-sienna active:cursor-grabbing"
              onPointerDown={(e) => {
                (e.target as Element).setPointerCapture?.(e.pointerId);
                setDragging({ wallId: w.id, end });
              }}
            />
          )),
        )}
      </svg>

      {/* Room labels overlaid using HTML so they stay upright (SVG is flipped) */}
      <RoomLabels plan={plan} bbox={bbox} pad={PAD} />
    </div>
  );
}

/* ---------- helpers ---------- */

function bboxOf(plan: Plan) {
  const xs: number[] = [];
  const ys: number[] = [];
  for (const w of plan.walls) {
    xs.push(w.a[0], w.b[0]);
    ys.push(w.a[1], w.b[1]);
  }
  return {
    min: [Math.min(...xs), Math.min(...ys)] as Pt,
    max: [Math.max(...xs), Math.max(...ys)] as Pt,
  };
}

function segmentForOpening(w: { a: Pt; b: Pt }, op: { offset: number; width: number }): { a: Pt; b: Pt } {
  const dx = w.b[0] - w.a[0];
  const dy = w.b[1] - w.a[1];
  const len = Math.hypot(dx, dy) || 1;
  const t0 = (op.offset - op.width / 2) / len;
  const t1 = (op.offset + op.width / 2) / len;
  return {
    a: [w.a[0] + dx * t0, w.a[1] + dy * t0],
    b: [w.a[0] + dx * t1, w.a[1] + dy * t1],
  };
}

function round01(v: number) { return Math.round(v * 100) / 100; }

function GridBackdrop() {
  // 1 m major grid, drawn via background-size — matches the SVG metre scale.
  return (
    <div
      aria-hidden
      className="absolute inset-0 opacity-70"
      style={{
        backgroundImage:
          "repeating-linear-gradient(0deg, rgba(31,58,95,0.07) 0 1px, transparent 1px 24px), " +
          "repeating-linear-gradient(90deg, rgba(31,58,95,0.07) 0 1px, transparent 1px 24px)",
      }}
    />
  );
}

function RoomLabels({ plan, bbox, pad }: { plan: Plan; bbox: { min: Pt; max: Pt }; pad: number }) {
  const w = bbox.max[0] - bbox.min[0] + pad * 2;
  const h = bbox.max[1] - bbox.min[1] + pad * 2;
  return (
    <div className="pointer-events-none absolute inset-0">
      {plan.rooms.map((r) => {
        const c = centroid(r.polygon);
        const left = ((c[0] - (bbox.min[0] - pad)) / w) * 100;
        const bottom = ((c[1] - (bbox.min[1] - pad)) / h) * 100;
        return (
          <div
            key={r.id}
            className="absolute -translate-x-1/2 translate-y-1/2 text-center"
            style={{ left: `${left}%`, bottom: `${bottom}%` }}
          >
            <div className="font-display text-[14px] italic text-ink/85">{r.name}</div>
            <div className="caption text-ink/50">{r.type}</div>
          </div>
        );
      })}
    </div>
  );
}

function centroid(pts: Pt[]): Pt {
  const xs = pts.reduce((s, p) => s + p[0], 0) / pts.length;
  const ys = pts.reduce((s, p) => s + p[1], 0) / pts.length;
  return [xs, ys];
}
