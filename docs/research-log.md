# Research log: plan and decisions

This is the original working plan for adding a 3D aerial view to the VI-map project (an interactive 2D map of GTA VI's Leonida), kept as written, plus the dated decision log through to the end of the project.

> **Status: concluded after Phase 0 (2026-11-22).** Phases 1–4 were never started. See [results-and-sizes.md](results-and-sizes.md) for the outcome and [knowledge-base.md](knowledge-base.md) for everything learned.

`leonida-px@1` is the pixel coordinate space of the VI-map 2D map. `MapView` is that app's map-view interface.

## Goal

An optional 3D aerial view (pan, rotate, fly) next to the existing 2D map. It is reconstructed from flyover footage as Gaussian splats and aligned to the `leonida-px@1` map space, so POIs, filters and regions work the same as in 2D.

## Verdict (research 2026-11-22)

- This is feasible as a **corridor along the flight path, not the whole map**.
- The footage is a single forward chase-cam pass, so views look good only near the flight line. Turning more than about 30–45° away from it shows smears and holes.
- Coverage is about 25–30% of the land, about 10–15% at good quality. Port Gellhorn and Grassrivers are absent.
- Expected results:
  - Downtown Vice City and the bay, viewed from near the path: **likely (~75%)**.
  - The whole flight in one scene aligned to the map within ±20–60 px: **~40–50%**.
  - Free orbit anywhere or full-map coverage: **no**.

## Source footage

- https://www.youtube.com/watch?v=dEJSn2ZctTo: "How BIG Is the GTA 6 Map? I Flew Across It in a Helicopter!" by GameV (an aggregator, not Rockstar). 8:48 long, up to 2160p60, real PS5 Pro gameplay, one continuous flight with no cuts.
- Things to mask: the minimap (bottom left), the "DEPLOY LANDING GEAR" prompt (bottom right), the watermark (top left), the helicopter and rotor (centre), and the sky.
- Weather: storms and haze around 0:30–2:00 and 5:15–6:40.
- Route:

| Time | What's in frame |
| --- | --- |
| 0:45–2:10 | Ambrosia: marsh, racetrack, rail yard, farms |
| 2:15–2:55 | Approach to the Vice City skyline, stadium |
| **3:00–3:40** | **Low pass between downtown towers and over the bay (best parallax)** |
| 3:45–4:25 | Marinas, Vice Beach |
| 4:30–5:10 | Canal, power plant, causeway |
| 5:15–6:20 | Keys towns and bridges, radar-dome island |
| 6:25–6:45 | Air station |
| 6:45–8:25 | Islands, landing (the helicopter fills the frame, unusable) |

- Better long-term source: record our own flight, since the game is out. Fly a lawnmower pattern with the camera about 45° down, in clear weather, with the HUD hidden.

## Hardware and tools

- Mac: **Apple M5 Pro, 64 GB** unified memory, enough for 2–3M-splat chunks locally.
- Installed: `yt-dlp`. Still needed: `ffmpeg`, `colmap` (4.x, Homebrew), Brush v0.3 (wgpu/Metal), Python with OpenCV and PySceneDetect.
- Optional: Depth Anything 3 / VGGT-Long on MPS as a fallback for segments COLMAP can't pose. gsplat on a rented RTX 4090 for the final quality pass.

## Pipeline

```
video → ffmpeg frames → sharpest-frame sampling → masks (HUD, helicopter, sky)
 → segments → COLMAP poses per segment → splat training (Brush) → cleanup (SuperSplat)
 → align to leonida-px (minimap as GPS + landmarks) → LoD and compression (Spark build-lod)
 → static chunks + manifest → three.js + Spark view at ?view=3d
```

## Phases

### Phase 0: spike, go/no-go (approved, 1–2 days, $0)
- Clip 2:30–3:40 (downtown and bay), about 200 frames at 1920 px (3 fps, keeping the sharpest frame in each window).
- Mask the HUD and helicopter, then run COLMAP (sequential matcher + global mapper).
- Train in Brush for about 30k steps, then render views 20–50 m off the flight path.
- **Exit:** ≥80% of frames posed, reprojection error ≤1.5 px, a plausible trajectory, and recognizable off-path renders. **If it fails, stop the splat track** and ship the cheap wins instead.

### Phase 1: poses for the whole flight, in segments (NOT approved yet: decided after the Phase 0 prototype, 3–5 days)
- Use 0:30–8:20, split into about 6–10 overlapping segments by content. Run COLMAP per segment, with the learned fallback for weak ones.
- Merge segments using overlapping frames. Accept gaps over open water and at takeoff/landing.
- **Exit:** downtown, waterfront and at least two other segments are posed and connected.

### Phase 2: splat training (open question, see below)
- Train each segment in Brush locally (about 30k steps each, roughly 20–60 min per segment on the M5 Pro, unverified).
- An optional final pass with gsplat on a cloud RTX 4090 (about $5–15) adds appearance compensation for the storm and exposure changes.
- The earlier "3–5 days" estimate is calendar time for retries and cleanup, not compute. Actual compute is a few hours.
- **Exit:** clean views within the corridor, with no large seams between segments.

### Phase 3: alignment to the map (2–4 days)
- Read the HUD minimap in each frame to get a 2D track, by matching water/land masks against `leonida-map.jpg`.
- Add 8–15 landmarks (racetrack, stadium, bridges, power plant, radar dome, runway), then fit a Sim(3) transform.
- If the illustrated map is warped, bend the POIs and regions with a thin-plate spline rather than warping the splat.
- **Exit:** median landmark error ≤40 map px.

### Phase 4: web view (5–8 days)
- Add `src/views/splat/` implementing the existing `MapView` interface, plus a `viewMode` atom, `?view=3d`, and a header toggle that only appears on capable devices.
- Use the 2D map as a textured ground plane, show POIs as sprites wired to the existing stores, and keep the camera near the flight path.
- Fly-to a POI uses the nearest training view.
- Host the splat chunks **outside the repo** (Cloudflare R2 or Hugging Face) and never commit binaries.
- **Exit:** under 3 s to first render, 30+ fps on a recent iPhone, and the 2D view unchanged.

## Cheap wins (independent of the spike)
1. **Fly-along mode:** draw the route line on the 2D map, sync it with an embedded YouTube player, and click the line to seek. No footage re-hosted.
2. **Pitch and rotate on the current map:** MapLibre `dragRotate`/`touchPitch`, `maxPitch` about 60, plus a compass. A few hours.
3. **Extruded downtown buildings** using heights from the SfM points (after Phase 1).

## Risks
- Pose breaks over water, sky or haze. Mitigation: masks, segments, the learned fallback.
- Lighting drift between segments. Mitigation: appearance embeddings.
- Unknown chase-cam focal length. Mitigation: refine it per segment.
- YouTube compression. Mitigation: train at 1080–1440p.
- Poor novel views from a single pass. Mitigation: a camera kept near the flight path, with the ground-plane fallback.
- The illustrated map isn't metrically accurate. Mitigation: warp the vectors, not the splat.
- Bandwidth and mobile memory. Mitigation: LoD, an opt-in toggle, external hosting.

## Legal (user decides)
- Rockstar's policy allows non-commercial gameplay footage. A splat is a navigable 3D copy of the game world, closer to an asset rip, so the DMCA risk is higher.
- A takedown notice could disable the whole GitHub repo. Host the splat elsewhere.
- YouTube's terms prohibit downloading without permission. Our own capture avoids both the ToS issue and the third-party rights holder.
- Open decisions: own capture vs. this video; whether to publish the splat or keep it local; donation links next to the 3D view.

## Decisions log
- 2026-11-22: Research done. README updated: GTA VI released 19 Nov 2026.
- 2026-11-22: User approved Phase 0 (isolated 200-frame spike on the downtown segment). ~~and Phase 1~~ (corrected below).
- 2026-11-22: User asked why Phase 2 takes so long. Answer: it's mostly retries and cleanup, and compute is only a few hours. Phase 2 is not yet approved beyond the local Brush runs needed for Phase 0.
- 2026-11-22: User approved the downloads and installs. The spike workspace is `~/git/vi-map-3d-spike` (outside the repo): ffmpeg 9.0.2, COLMAP 4.2.1 (CPU), Brush v0.3.0, and a `.venv` with OpenCV.
- 2026-11-22: **Phase 0 results.**
  - Clip 2:30–3:44 at 1440p60 (format 308, 120 MB). 896 candidates at 12 fps → 200 sharpest frames at 1920×1080 (`script_examples/prep_frames.py`).
  - Masks cover the HUD boxes plus a circle over the helicopter (it banks about 45°, so a box doesn't cover it).
  - COLMAP (sequential matcher, overlap 15, then `global_mapper`): **200/200 frames registered, 78k points, reprojection error 0.43 px**, horizontal FOV about 91°, smooth trajectory. The pose exit criteria are met.
  - Brush training: 30k steps, every 10th frame held out for evaluation.
- 2026-11-22: The session closed by accident and killed training after the 10k snapshot. Restarted from scratch at 15:23 under `nohup` (Brush can't resume weights from a .ply). About 10 min per 10k steps.
- 2026-11-22: User queued **option B** (a stylized 3D `.glb` of the whole map from `leonida-map.jpg` and existing data) to start after this plan. Details in [scaling-and-tooling.md](scaling-and-tooling.md).
- 2026-11-22: **Correction from the user:** Phase 1 is NOT approved. Phase 0 is only the downtown/centre test render. Phase 1 gets approved later, if the Phase 0 prototype works out.
- 2026-11-22: **Phase 0, first render (30k, 1.19M splats):** the skyline looks good near the path. The centre is smeared and there are dark shards. Cause: the fixed safety-circle mask hid the same screen area (the ground ahead of and below the helicopter) in every frame, and the rotor blades reached past it. Pruning after training (`script_examples/clean_splat.py`) made it worse, because the ground is built from many faint splats. Dropped that approach.
- 2026-11-22: User chose AI segmentation. SAM 2.1 (base+, `.venv-sam` on Python 3.15, MPS) tracks the helicopter across all 200 frames, plus a thin, nearly level band for the rotor (`script_examples/sam_heli_masks.py` → `dataset_v2`). The masked area is 28% of the old circle. Retrain v2 started at 16:22 (`out/v2_{iter}.ply`). The sky is still unmasked, because Brush's ignore-masks would leave sky floaters unpenalised.
- 2026-11-22: Trainer choice for later phases: Brush (Burn/wgpu) is the right tool on the Mac, but not optimal on NVIDIA. For cloud runs (Phase 2 option), use **gsplat** (CUDA). See [knowledge-base.md](knowledge-base.md) → "Which trainer, on which hardware?" and [scaling-and-tooling.md](scaling-and-tooling.md) → "Cloud training on Google Colab via MCP".
- 2026-11-22: v2 training finished at 17:08: 1,527,578 Gaussians (v1: 1,187,446), 361 MB, 46 min. Awaiting user visual check for the go/no-go.
- 2026-11-22: **User visual check of v2: good enough for Phase 0.** Off-path views hold up in the flight direction, the far side streaks (expected for single-pass footage). The centre smear and rotor shards from v1 are fixed by the SAM 2 masks. Remaining for Phase 0: held-out frame metrics + saved off-path screenshots, then the go/no-go.
- 2026-11-22: **Phase 0 evaluation complete.**
  - Held-out frames (20): Brush render **27.2 dB PSNR / SSIM 0.878**.
  - The viewer was the weak link: Spark's default `maxPixelRadius` 512 clipped the sky/background splats (19.0 dB). Fixed in `viewer/index.html` (`maxPixelRadius: 4096`, `clipXY: 3`), giving **23.7 dB**.
  - Off-path renders at ±20–50 m and 50 m up hold up. Looking back (yaw −45°) streaks.
  - Scale estimate ≈ 326 m/unit (HUD altitude).
  - Tools: `script_examples/render_eval.mjs`, `script_examples/eval_metrics.py`. Outputs in `eval/`.
  - **All Phase 0 exit criteria are met. The go/no-go for Phase 1 is the user's decision.**
- 2026-11-22: **Project concluded.** Single-angle flyover footage gives good on-path views (27 dB held out), but no freely explorable scene. Pivot: keep docs, scripts and media in this repo for future multi-angle projects; delete large artifacts.
