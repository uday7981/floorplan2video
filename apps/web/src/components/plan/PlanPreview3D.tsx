"use client";

import * as React from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { Plan, Wall } from "@/lib/mock-data";
import { cn } from "@/lib/cn";

/**
 * The signature "big moment": a live 3D preview of the plan JSON.
 * - Walls are extruded boxes
 * - Floor is a thin slab
 * - When the user isn't interacting, the camera drifts around at 15°/120s,
 *   like the model sits on a drafter's turntable.
 * - OrbitControls take over on drag; auto-rotate pauses while interacting.
 */
export function PlanPreview3D({ plan, className }: { plan: Plan; className?: string }) {
  const center = React.useMemo(() => {
    const xs: number[] = []; const ys: number[] = [];
    for (const w of plan.walls) { xs.push(w.a[0], w.b[0]); ys.push(w.a[1], w.b[1]); }
    return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2] as [number, number];
  }, [plan.walls]);

  const diag = React.useMemo(() => {
    const xs: number[] = []; const ys: number[] = [];
    for (const w of plan.walls) { xs.push(w.a[0], w.b[0]); ys.push(w.a[1], w.b[1]); }
    const dx = Math.max(...xs) - Math.min(...xs);
    const dy = Math.max(...ys) - Math.min(...ys);
    return Math.hypot(dx, dy);
  }, [plan.walls]);

  return (
    <div className={cn("relative overflow-hidden bg-paper", className)}>
      <Canvas
        shadows
        dpr={[1, 2]}
        camera={{ position: [center[0] + diag * 0.9, 7, center[1] + diag * 0.9], fov: 35 }}
        gl={{ antialias: true }}
      >
        <color attach="background" args={["#F5F1EA"]} />
        {/* ambient + a key directional sun */}
        <ambientLight intensity={0.4} />
        <directionalLight
          position={[center[0] + 10, 15, center[1] + 8]}
          intensity={1.4}
          castShadow
          shadow-mapSize={[2048, 2048]}
        />
        <hemisphereLight args={["#F5F1EA", "#141311", 0.35]} />

        {/* floor */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[center[0], 0, center[1]]} receiveShadow>
          <planeGeometry args={[Math.max(diag * 1.3, 15), Math.max(diag * 1.3, 15)]} />
          <meshStandardMaterial color="#E5DFD3" roughness={0.95} metalness={0} />
        </mesh>

        {/* walls */}
        {plan.walls.map((w) => (
          <WallMesh key={w.id} wall={w} />
        ))}

        {/* a thin plinth to give the model a floor silhouette */}
        <mesh position={[center[0], -0.01, center[1]]}>
          <boxGeometry args={[diag * 1.1, 0.02, diag * 1.1]} />
          <meshStandardMaterial color="#F0ECE2" roughness={1} metalness={0} />
        </mesh>

        <TurntableCamera target={[center[0], 1.2, center[1]]} radius={diag * 1.0} height={diag * 0.55 + 3} />
        <OrbitControls
          enablePan={false}
          enableZoom={true}
          minPolarAngle={0.4}
          maxPolarAngle={Math.PI / 2 - 0.1}
          target={[center[0], 1.2, center[1]]}
          makeDefault
        />
      </Canvas>

      {/* Caption rail — tiny architect's label in the corner */}
      <div className="pointer-events-none absolute left-4 top-4 flex flex-col gap-1">
        <span className="caption text-ink/55">Live preview</span>
        <span className="font-display text-[11px] italic text-ink/55">drag to orbit · scroll to zoom</span>
      </div>
    </div>
  );
}

function WallMesh({ wall }: { wall: Wall }) {
  const [ax, ay] = wall.a;
  const [bx, by] = wall.b;
  const dx = bx - ax, dy = by - ay;
  const len = Math.hypot(dx, dy);
  if (len < 1e-4) return null;
  const angle = Math.atan2(dy, dx);  // yaw around Y
  const midX = (ax + bx) / 2;
  const midY = (ay + by) / 2;
  return (
    <mesh
      position={[midX, wall.height / 2, midY]}
      rotation={[0, -angle, 0]}
      castShadow
      receiveShadow
    >
      <boxGeometry args={[len, wall.height, wall.thickness]} />
      <meshStandardMaterial color={wall.exterior ? "#E8E3D5" : "#F0ECE2"} roughness={0.9} metalness={0} />
    </mesh>
  );
}

/**
 * Starts a slow default orbit around the target. The second the user
 * drags OrbitControls, we release. Signature architectural turntable feel.
 */
function TurntableCamera({
  target,
  radius,
  height,
}: {
  target: [number, number, number];
  radius: number;
  height: number;
}) {
  const started = React.useRef(performance.now());
  const dragging = React.useRef(false);

  // OrbitControls fires 'start'/'end' on the host element; capture it via DOM listeners.
  React.useEffect(() => {
    const onDown = () => (dragging.current = true);
    const onUp = () => {
      dragging.current = false;
      // Resume turntable from current camera position.
      started.current = performance.now();
    };
    window.addEventListener("pointerdown", onDown);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
    };
  }, []);

  useFrame(({ camera }) => {
    if (dragging.current) return;
    // 15° per 120s → 0.125°/s → 0.00218 rad/s
    const t = (performance.now() - started.current) * 0.001 * 0.00218;
    const angle = Math.atan2(camera.position.z - target[2], camera.position.x - target[0]) + t * 0.5;
    const x = target[0] + radius * Math.cos(angle);
    const z = target[2] + radius * Math.sin(angle);
    camera.position.set(x, Math.max(height, 3), z);
    camera.lookAt(target[0], target[1], target[2]);
  });
  return null;
}
