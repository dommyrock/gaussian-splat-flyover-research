"""Prune obvious junk from a Brush .ply: near-camera floaters, needles, faint and huge splats.

usage: clean_splat.py in.ply out.ply [--stats] [--near F] [--opa A] [--aniso R] [--big F]
Distances are fractions of the median camera->scene depth (from the COLMAP points).
"""
import json, sys, argparse, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("inp"); ap.add_argument("out", nargs="?")
ap.add_argument("--stats", action="store_true")
ap.add_argument("--near", type=float, default=0.15)   # drop splats closer than this x depth to any camera
ap.add_argument("--opa", type=float, default=0.05)    # drop if sigmoid(opacity) below
ap.add_argument("--aniso", type=float, default=8)     # drop needles: max/mid scale above ...
ap.add_argument("--needle", type=float, default=0.01) # ... and max scale above this x depth
ap.add_argument("--big", type=float, default=0.08)    # drop any splat with max scale above this x depth
a = ap.parse_args()

raw = open(a.inp, "rb").read()
end = raw.index(b"end_header\n") + len(b"end_header\n")
hdr = raw[:end].decode()
props = [l.split()[-1] for l in hdr.splitlines() if l.startswith("property")]
n = int([l for l in hdr.splitlines() if l.startswith("element vertex")][0].split()[-1])
d = np.frombuffer(raw, dtype=np.float32, offset=end, count=n * len(props)).reshape(n, len(props))
col = {p: i for i, p in enumerate(props)}

xyz = d[:, [col["x"], col["y"], col["z"]]]
opa = 1 / (1 + np.exp(-d[:, col["opacity"]]))
sc = np.exp(d[:, [col["scale_0"], col["scale_1"], col["scale_2"]]])
ss = np.sort(sc, 1); smin, smid, smax = ss[:, 0], ss[:, 1], ss[:, 2]

cams = np.array([p["position"] for p in json.load(open("viewer/poses.json"))["poses"]], np.float32)
near = np.full(n, np.inf, np.float32)
for c in cams:
    near = np.minimum(near, np.linalg.norm(xyz - c, axis=1))
depth = float(np.median(near[opa > 0.5]))  # typical distance from the path to solid scene content

def q(v): return " ".join(f"{x:.3g}" for x in np.percentile(v, [1, 10, 50, 90, 99]))
if a.stats:
    print(f"n={n} depth≈{depth:.3g} cam_step≈{np.median(np.linalg.norm(np.diff(cams,axis=0),axis=1)):.3g}")
    print("near/depth  p1 10 50 90 99:", q(near / depth))
    print("opacity                  :", q(opa))
    print("smax/depth               :", q(smax / depth))
    print("needle ratio max/mid     :", q(smax / smid))

drop = {
    "near camera": near < a.near * depth,
    "faint": opa < a.opa,
    "needle": (smax / smid > a.aniso) & (smax > a.needle * depth),
    "huge": smax > a.big * depth,
}
keep = ~np.logical_or.reduce(list(drop.values()))
for k, m in drop.items(): print(f"{k:12s} {m.sum():>9,} ({m.mean():.1%})")
print(f"keep         {keep.sum():>9,} of {n:,} ({keep.mean():.1%})")
if a.out:
    hdr2 = hdr.replace(f"element vertex {n}", f"element vertex {int(keep.sum())}")
    with open(a.out, "wb") as f:
        f.write(hdr2.encode()); f.write(np.ascontiguousarray(d[keep]).tobytes())
    print("wrote", a.out)
