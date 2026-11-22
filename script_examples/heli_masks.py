"""Per-frame tight helicopter masks: the heli is static in screen space while the scene moves.

A pixel inside the old safety circle is 'heli' if it barely changes vs frames i-k and i+k.
Writes dataset_v2/masks/fNNNN.png (white = keep) with the HUD boxes copied from the old mask.
usage: heli_masks.py [preview_out.jpg]
"""
import cv2, glob, numpy as np, pathlib, shutil, sys

old = cv2.imread("dataset/masks/f0000.png", 0)
H, W = old.shape
yy, xx = np.nonzero(old == 0)
# the old safety circle = largest masked component of the old mask; the rest are HUD boxes
n0, lab0, st0, cen0 = cv2.connectedComponentsWithStats((old == 0).astype(np.uint8))
big = 1 + int(np.argmax(st0[1:, cv2.CC_STAT_AREA]))
circle = ((lab0 == big) * 255).astype(np.uint8)
C0 = cen0[big]; R0 = float(np.sqrt(st0[big, cv2.CC_STAT_AREA] / np.pi))
hud = (old == 0) & (circle == 0)

files = sorted(glob.glob("dataset/images/*.jpg"))
g = [cv2.GaussianBlur(cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.int16) for f in files]
out = pathlib.Path("dataset_v2"); (out / "masks").mkdir(parents=True, exist_ok=True)
if not (out / "images").exists(): (out / "images").symlink_to(pathlib.Path("dataset/images").resolve())
if not (out / "sparse").exists(): shutil.copytree("dataset/sparse", out / "sparse")

k1, k2, thr = 3, 6, 10
ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
areas, masks = [], []
for i in range(len(g)):
    diffs = [np.abs(g[i] - g[j]) for j in (i - k2, i - k1, i + k1, i + k2) if 0 <= j < len(g)]
    static = (np.max(diffs, axis=0) < thr).astype(np.uint8) * 255  # unchanged vs ALL neighbours
    static &= circle
    static = cv2.morphologyEx(static, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    static = cv2.morphologyEx(static, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    # keep the blob(s) near the circle centre, drop stray static patches (flat water, haze)
    n, lab, st, cen = cv2.connectedComponentsWithStats(static)
    keepm = np.zeros_like(static)
    for l in range(1, n):
        if st[l, cv2.CC_STAT_AREA] > 800 and np.linalg.norm(cen[l] - C0) < 0.65 * R0:
            keepm[lab == l] = 255
    heli = cv2.dilate(keepm, ker, iterations=3)  # ~13 px safety margin for rotor blur / edges
    masks.append(heli)
for i, f in enumerate(files):
    # union with neighbours: a frame where detection fails borrows the shape from nearby frames
    heli = np.max(masks[max(0, i - 2):i + 3], axis=0)
    m = np.full((H, W), 255, np.uint8); m[hud] = 0; m[heli > 0] = 0
    areas.append((heli > 0).sum() / (circle > 0).sum())
    cv2.imwrite(str(out / "masks" / (pathlib.Path(f).stem + ".png")), m)
a = np.array(areas)
print(f"heli mask area vs old circle: median {np.median(a):.0%}, min {a.min():.0%}, max {a.max():.0%}")

if len(sys.argv) > 1:
    tiles = []
    for i in [0, 30, 63, 100, 140, 190]:
        im = cv2.imread(files[i]); m = cv2.imread(str(out / "masks" / f"f{i:04d}.png"), 0)
        o = im.copy(); o[m == 0] = (o[m == 0] * .35 + np.array([0, 0, 255]) * .65).astype(np.uint8)
        cv2.circle(o, (int(C0[0]), int(C0[1])), int(R0), (0, 255, 255), 2)
        o = cv2.resize(o[int(C0[1]-R0-40):int(C0[1]+R0+40), int(C0[0]-R0*1.6):int(C0[0]+R0*1.6)], (900, 500)); cv2.putText(o, str(i), (15, 45), 0, 1.4, (0, 255, 0), 3); tiles.append(o)
    cv2.imwrite(sys.argv[1], np.vstack([np.hstack(tiles[k:k + 2]) for k in range(0, 6, 2)]), [cv2.IMWRITE_JPEG_QUALITY, 80])
