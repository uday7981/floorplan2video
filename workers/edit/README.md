# workers/edit — ffmpeg stitch

Queue `export`. Runs on the same RunPod GPU pod as Blender (ffmpeg is in the
same Docker image). Normalises each take to 1280×720 24fps H.264 no-audio,
joins in shot order with a 0.3 s `xfade`, overlays title + numbered room labels
+ optional caption via `drawtext`, appends 2 s end card, uploads to `exports/`.
Built in **M4**.
