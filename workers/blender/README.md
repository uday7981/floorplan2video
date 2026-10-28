# workers/blender

Blender 4.2 LTS headless, in a Docker image, on a RunPod RTX 4090 pod.
Also hosts the `edit` worker (ffmpeg lives in the same image).

## Build

Local (CPU render only; no NVIDIA runtime needed):
```
docker build -t fpv-blender:dev workers/blender
docker run --rm -v "$PWD/workers/blender/_test_out:/workspace/out" fpv-blender:dev \
  blender -b --factory-startup -P /workspace/scripts/test_render.py -- --out /workspace/out
```

On the RunPod RTX 4090 pod (expects `--gpus all` and the NVIDIA container runtime):
```
docker build -t fpv-blender:dev .
docker run --rm --gpus all -e NVIDIA_DRIVER_CAPABILITIES=all \
  -v "$PWD/_test_out:/workspace/out" fpv-blender:dev \
  blender -b --factory-startup -P /workspace/scripts/test_render.py -- --out /workspace/out
```

The test script renders:
- `workbench.png` — Workbench engine (used for `driving.mp4` and `clay.png`)
- `freestyle.png` — Workbench + Freestyle white lines on white (used for `start.png`)

Exit code 0 means the pod can render headlessly. Inspect the two PNGs to confirm:
- `workbench.png` shows a solid-shaded cube
- `freestyle.png` shows the cube's silhouette and crease edges as white lines on a plain white background

## Full render pipeline

Entry point for the real pipeline (M2):
```
blender -b --factory-startup -P /workspace/build.py -- \
  --plan plan.json --shots shots.json --out /tmp/out
```

See `build.py`, `cameras.py`, `materials.py` — scaffolded in M2.
