# scripts/

Standalone spikes and operator utilities. These are not part of the pipeline.

## M0

### `generate_test_assets.py`
Builds tiny procedural start/end PNGs + a 2s MP4 for the Seedance spike. No paid calls.
```
pip install Pillow
python scripts/generate_test_assets.py
```

### `spike_seedance.py`
Submits ONE Seedance 2.5 request to Together AI. **Will not submit unless
you pass `--yes-i-approve-cost`.** Without the flag, it prints the estimate
and exits. Minimum cost (4 s @ 480p) is $0.46.

Prerequisites:
- `pip install together`
- `TOGETHER_API_KEY` in your shell env
- Assets exist in `scripts/_spike_assets/` (run the generator first)

Modes:
- `--mode frames_only` (default): what the pipeline uses. First + last frame.
- `--mode reference_guided`: reference video + no first/last. For driving-style transfer.
- `--mode combined_expect_fail`: first+last + reference video — Together's docs
  say this returns an error. Confirms the finding at the same cost.
