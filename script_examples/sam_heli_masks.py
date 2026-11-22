"""Track the helicopter through all frames with SAM 2 and write tight masks.

Writes dataset_v2/{images->dataset/images, sparse, masks/fNNNN.png} (white = keep).
Mask = HUD boxes (from the old mask) + SAM heli + a tilted band for the rotor sweep, dilated.
usage: sam_heli_masks.py [preview.jpg]
"""
import cv2, glob, numpy as np, os, pathlib, shutil, sys, tempfile, torch
from sam2.build_sam import build_sam2_video_predictor

files = sorted(glob.glob("dataset/images/*.jpg"))
old = cv2.imread("dataset/masks/f0000.png", 0); H, W = old.shape
n0, lab0, st0, _ = cv2.connectedComponentsWithStats((old == 0).astype(np.uint8))
big = 1 + int(np.argmax(st0[1:, cv2.CC_STAT_AREA]))
hud = (old == 0) & (lab0 != big)
circle_area = st0[big, cv2.CC_STAT_AREA]

tmp = tempfile.mkdtemp()
for i, f in enumerate(files): os.symlink(os.path.abspath(f), f"{tmp}/{i:05d}.jpg")
dev = "mps" if torch.backends.mps.is_available() else "cpu"
pred = build_sam2_video_predictor("configs/sam2.1/sam2.1_hiera_b+.yaml", "models/sam2.1_hiera_base_plus.pt", device=dev)
heli = {}
with torch.inference_mode():
    st = pred.init_state(video_path=tmp, offload_video_to_cpu=True, offload_state_to_cpu=True)
    pred.add_new_points_or_box(st, frame_idx=0, obj_id=1, box=np.array([850, 520, 1080, 860], np.float32),
                               points=np.array([[960, 650], [960, 760]], np.float32), labels=np.array([1, 1], np.int32))
    for fi, _, logits in pred.propagate_in_video(st):
        heli[fi] = (logits[0, 0] > 0).cpu().numpy()

out = pathlib.Path("dataset_v2"); (out / "masks").mkdir(parents=True, exist_ok=True)
if not (out / "images").exists(): (out / "images").symlink_to(pathlib.Path("dataset/images").resolve())
if not (out / "sparse").exists(): shutil.copytree("dataset/sparse", out / "sparse")
dil = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
areas, bodies = [], []
for i, f in enumerate(files):
    hm = heli[i].astype(np.uint8)
    body = hm.sum()
    if body < 3000 and i > 0:      # tracking lost -> reuse previous frame's body
        hm = prev_hm
    prev_hm = hm
    ys, xs = np.nonzero(hm)
    m = np.full((H, W), 255, np.uint8); m[hud] = 0
    if len(xs):
        # body axis (bank) from PCA; rotor disk is perpendicular to it, at the top of the body
        c = np.array([xs.mean(), ys.mean()]); v = np.linalg.eigh(np.cov(np.stack([xs - c[0], ys - c[1]])))[1][:, -1]
        if v[1] > 0: v = -v                         # point "up" the body
        ext = ((np.stack([xs, ys], 1) - c) @ v).max()
        hub = c + v * ext * 0.95
        ang = float(np.clip(((np.degrees(np.arctan2(v[1], v[0])) + 90 + 90) % 180) - 90, -15, 15))  # rotor ~level; PCA over-tilts
        band = np.zeros((H, W), np.uint8)
        cv2.ellipse(band, (int(hub[0]), int(hub[1])), (440, 32), ang, 0, 360, 1, -1)
        hm = np.maximum(hm, band)
    hm = cv2.dilate(hm, dil)
    m[hm > 0] = 0
    areas.append((hm > 0).sum() / circle_area); bodies.append(body)
    cv2.imwrite(str(out / "masks" / (pathlib.Path(f).stem + ".png")), m)
a = np.array(areas); b = np.array(bodies)
print(f"mask area vs old circle: median {np.median(a):.0%} min {a.min():.0%} max {a.max():.0%}; "
      f"SAM body px median {int(np.median(b))}, frames with lost track {(b < 3000).sum()}")

if len(sys.argv) > 1:
    tiles = []
    for i in [0, 30, 63, 100, 140, 190]:
        im = cv2.imread(files[i]); mm = cv2.imread(str(out / "masks" / f"f{i:04d}.png"), 0)
        o = im.copy(); o[mm == 0] = (o[mm == 0] * .4 + np.array([0, 0, 255]) * .6).astype(np.uint8)
        o = cv2.resize(o, (960, 540)); cv2.putText(o, str(i), (15, 45), 0, 1.4, (0, 255, 0), 3); tiles.append(o)
    cv2.imwrite(sys.argv[1], np.vstack([np.hstack(tiles[k:k + 2]) for k in range(0, 6, 2)]), [cv2.IMWRITE_JPEG_QUALITY, 80])
