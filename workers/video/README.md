# workers/video — Together AI Seedance 2.5

Queue `video`. Routes through the `VideoProvider` adapter in `providers/`. The
pipeline mode is `VIDEO_MODE=frames_only` because Together's Seedance 2.5 API
forbids combining frame_images with reference_videos in a single request (per
their docs, confirmed in M0). Built in **M3**.
