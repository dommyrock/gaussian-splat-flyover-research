# Scaling up: trainers, cloud GPUs, meshes and the tool ecosystem

Options we researched but didn't run. They're the starting point for a bigger or better-footage project.

## Which trainer, on which hardware?
Brush trains with **Burn** (Rust ML) on **wgpu**: one binary for Metal, Vulkan, DirectX, mobile and the browser. The price of that portability is no NVIDIA-specific kernels, so it leaves speed unused on A100/H100-class GPUs.

**Rule: Mac → Brush, NVIDIA → gsplat, quick previews → feed-forward models.**

| Hardware | Trainer | Notes |
| --- | --- | --- |
| Mac (Metal) | **Brush** | Used here. ~37–46 min for 30k steps on 180 frames at 1080p (M5 Pro) |
| NVIDIA (CUDA) | **gsplat** (PyTorch + custom CUDA) | Default choice. Appearance embeddings (exposure/weather drift), MCMC densification (fewer floaters, capped count), multi-GPU. Estimated ~5–15 min for the same scene on an A100 (unmeasured) |
| NVIDIA, easiest | **Nerfstudio `splatfacto`** | Full pipeline around gsplat (`ns-train splatfacto`) |
| Reference | graphdeco-inria/gaussian-splatting | Original paper code; slower |
| Speed research | Taming 3DGS, Speedy-Splat and others | Minutes-scale, less polished |
| No training | Feed-forward (VGGT / AnySplat family) | Poses + splats in seconds; lower quality. Also a fallback where COLMAP fails |

## Cloud training on Google Colab via MCP
- **Official MCP:** [googlecolab/colab-mcp](https://github.com/googlecolab/colab-mcp). It bridges a local agent (Claude Code is supported) to a Colab notebook **open in the browser**. Config: `"colab-mcp": {"command": "uvx", "args": ["git+https://github.com/googlecolab/colab-mcp"], "timeout": 30000}`.
- **Catch:** the tab must stay open. It isn't headless, so an idle disconnect kills the run. Keep notebooks private when footage has third-party rights.
- **Split:** frame prep and COLMAP stay local (minutes). Upload `dataset/` (images + masks + sparse), train with gsplat on Colab, download the `.ply`.

| | Mac M5 Pro | Colab A100/H100 (estimate) |
| --- | --- | --- |
| 30k steps, one ~200-frame segment | ~37–46 min (measured) | ~8–15 min |
| Transfers (~150 MB up, ~300 MB down) | – | +2–5 min |
| Full flight, 6–10 segments | ~4–6 h | ~1.5–2 h |
| Cost | $0 | Colab compute units (a few dollars) |

**Full-flight estimate** (≈1,000–1,200 frames): frames ~5 min, SAM 2 ~10 min, COLMAP ~30–60 min (local CPU), transfers ~10–15 min, training ~1.5–2 h on an A100. **≈ 2.5–3.5 h compute.** Calendar time is dominated by retries on weak segments (storms, water), stitching, cleanup and alignment, not compute.

## Alternatives to a splat
- **Mesh from the scan (realistic, corridor only):** fuse rendered depth maps (TSDF), or train 2DGS on a CUDA GPU for cleaner surfaces → `.glb`. Same coverage gaps as the splat; blobby building backs.
- **Stylized 3D from an illustrated map (full coverage):** texture a ground plane with a 2D map, extrude buildings using heights from SfM points where available, export one `.glb`. Small, fast on phones, and needs no footage rights. Queued separately in the VI-map project.

## Web delivery
- **Splats:** trained `.ply` → **SuperSplat** (manual cleanup: floaters, crop) → **splat-transform** (`.sog`/`.spz`, ~10× smaller) → **Spark** (three.js).
  - In Spark, set `maxPixelRadius` ≥ 4096. The default of 512 clips the sky/background splats and cost ~5 dB here.
- **Meshes:** Blender → `.glb` → **glTF-Transform** (mesh compression, smaller textures) → three.js / react-three-fiber.
- Host big binaries outside the git repo (Cloudflare R2, Hugging Face).

## File formats
| Format | Notes |
| --- | --- |
| `.ply` | Standard 3DGS output; 236 B/Gaussian at SH degree 3 |
| `.spz` | Niantic, ~10× smaller |
| `.sog` | PlayCanvas compressed |
| `.ksplat` | GaussianSplats3D |
| glTF `KHR_gaussian_splatting` | Emerging Khronos interchange standard |
| `.glb` | Meshes (glTF binary); Blender imports/exports it natively |

## Tool ecosystem
(Also kept as the GitHub star list "3D reconstruction & rendering".)

| Tool | Role | Used here |
| --- | --- | --- |
| [colmap/colmap](https://github.com/colmap/colmap) | SfM: camera poses + sparse points | ✅ |
| [ArthurBrussee/brush](https://github.com/ArthurBrussee/brush) | Splat trainer, Rust/wgpu, runs on Mac | ✅ |
| [facebookresearch/sam2](https://github.com/facebookresearch/sam2) | Video object segmentation (masks) | ✅ |
| [sparkjsdev/spark](https://github.com/sparkjsdev/spark) | three.js splat renderer | ✅ |
| [playcanvas/supersplat](https://github.com/playcanvas/supersplat) | Manual splat cleanup editor | – |
| [playcanvas/splat-transform](https://github.com/playcanvas/splat-transform) | Convert/compress splats | – |
| [nianticlabs/spz](https://github.com/nianticlabs/spz) | Compressed splat format | – |
| [nerfstudio-project/gsplat](https://github.com/nerfstudio-project/gsplat) | CUDA trainer | – |
| [gfx-rs/wgpu](https://github.com/gfx-rs/wgpu) | GPU API under Brush | indirect |
| [pmndrs/react-three-fiber](https://github.com/pmndrs/react-three-fiber) | React renderer for three.js | – |
| [blender/blender](https://github.com/blender/blender) | Free/OSS (GPL) mesh tool; glTF built in; KIRI 3DGS Render add-on for splats | – |
| [donmccurdy/glTF-Transform](https://github.com/donmccurdy/glTF-Transform) | `.glb` optimisation | – |
| [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) | Community Blender MCP. Avoid look-alike repos with random usernames, a typical malware pattern | – |
