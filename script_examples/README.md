# Script examples

Working scripts from the spike, kept as references. They expect the original workspace layout (`video/`, `dataset/`, `dataset_v2/`, `colmap/`, `out/`, `eval/`, `viewer/`) and run from its root. The command order and flags are in [../docs/pipeline-runbook.md](../docs/pipeline-runbook.md).

| Script | Step | Status | What it does |
| --- | --- | --- | --- |
| `prep_frames.py` | 2 | ✅ | ffmpeg → 12 fps candidates → sharpest frame per window (Laplacian variance) → 200 frames; writes v1 masks for Brush (white = keep) and COLMAP (black = ignore) |
| `export_poses.py` | 4 | ✅ | COLMAP `images.txt`/`cameras.txt` → `viewer/poses.json` (OpenCV → three.js camera axes) |
| `sam_heli_masks.py` | 5 | ✅ | SAM 2.1 video predictor tracks the helicopter from one box + point prompt, adds a tilted rotor band, dilates → `dataset_v2/masks` + preview sheet |
| `viewer/index.html` | 7 | ✅ | three.js + Spark viewer: fly-path replay, free orbit, `?bg=`, `?spark={...}`, `?pose=N` screenshot mode with `window.__shot(pose, offset, yaw)`. Defaults `maxPixelRadius: 4096` |
| `render_clip.mjs` | – | ✅ | Renders `media/splat-clip`'s poster and fallback MP4 frames through its viewer (`?shot=` mode) |
| `render_eval.mjs` | 8 | ✅ | puppeteer-core + system Chrome (WebGL via Metal): loads the splat once, renders a list of shots |
| `eval_metrics.py` | 8 | ✅ | Masked PSNR/SSIM vs real frames for Brush and Spark renders, plus comparison sheets |
| `heli_masks.py` | 5 | ❌ failed approach | "Static pixel" helicopter detection across neighbouring frames. Kept as a lesson: frames 0.3 s apart move too much, and sky also reads as static |
| `clean_splat.py` | – | ❌ failed approach | Post-training pruning (near-camera, faint, needle, huge splats). Made things worse: under-observed surfaces are made of many faint splats. Its `--stats` mode is still useful for inspecting a `.ply` |

`package.json` only pins `puppeteer-core` for `render_eval.mjs`.

## Adapting to new footage
- `prep_frames.py`: change `BOXES` (HUD regions, measured on 1280×720) and the helicopter circle, or drop them when the HUD is hidden.
- `sam_heli_masks.py`: change the frame-0 `box`/`points` prompt. Get coordinates by drawing a pixel grid on frame 0. Drop the rotor band if there's no rotor.
- `eval_metrics.py` / `render_eval.mjs`: the frame names and shot lists are in `../data/*.json`.
