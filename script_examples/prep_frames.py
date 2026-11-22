"""Extract the sharpest ~N frames from the clip and write HUD/helicopter masks.

Usage: .venv/bin/python -I tools/prep_frames.py video/clip.webm dataset 200
Writes dataset/images/fNNNN.jpg, dataset/masks/fNNNN.png (Brush: white=keep)
and colmap/masks/fNNNN.jpg.png (COLMAP: black=ignore, same pixels).
"""
import pathlib, subprocess, sys, tempfile, shutil
import cv2, numpy as np

src, out, n_keep = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3])
W, H = 1920, 1080
s = W / 1280  # boxes below are measured on 1280x720 previews

# (x0, y0, x1, y1) regions to ignore, in 1280x720 coordinates
BOXES = [
    (0, 0, 130, 60),       # GAMEV watermark
    (1170, 0, 1280, 80),   # wanted stars + status icons
    (0, 565, 260, 720),    # minimap + altitude + waypoint icons
]
mask = np.full((H, W), 255, np.uint8)
for x0, y0, x1, y1 in BOXES:
    mask[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = 0
# helicopter + rotor: it banks up to ~45 deg, so use a circle, not a box
cv2.circle(mask, (int(645 * s), int(440 * s)), int(215 * s), 0, -1)

tmp = pathlib.Path(tempfile.mkdtemp())
subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps=12,scale={W}:{H}:flags=lanczos",
                "-q:v", "2", str(tmp / "c%05d.jpg")], check=True)
cands = sorted(tmp.glob("c*.jpg"))

def sharp(p):
    g = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(g, cv2.CV_64F)
    return lap[mask > 0].var()

scores = [sharp(p) for p in cands]
# split candidates into n_keep equal windows, keep the sharpest of each
edges = np.linspace(0, len(cands), n_keep + 1).astype(int)
picked = [max(range(a, b), key=lambda i: scores[i]) for a, b in zip(edges[:-1], edges[1:]) if b > a]

for d in ("images", "masks"):
    (out / d).mkdir(parents=True, exist_ok=True)
cm = pathlib.Path("colmap/masks"); cm.mkdir(parents=True, exist_ok=True)
for k, i in enumerate(picked):
    name = f"f{k:04d}"
    shutil.copy(cands[i], out / "images" / f"{name}.jpg")
    cv2.imwrite(str(out / "masks" / f"{name}.png"), mask)
    cv2.imwrite(str(cm / f"{name}.jpg.png"), mask)
shutil.rmtree(tmp)
print(f"{len(cands)} candidates -> {len(picked)} frames; median sharpness kept "
      f"{np.median([scores[i] for i in picked]):.0f} vs all {np.median(scores):.0f}")
