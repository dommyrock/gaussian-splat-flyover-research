"""Masked PSNR / SSIM of renders vs the real held-out frames, plus comparison sheets.

usage: eval_metrics.py
Compares eval/brush/eval_30000 (Brush renderer), eval/spark_black and eval/spark_blue (Spark viewer)
against dataset/images, ignoring masked pixels (HUD, helicopter, rotor) from dataset_v2/masks.
Writes eval/metrics.json and eval/sheet_eval.jpg, eval/sheet_offpath.jpg.
"""
import cv2, glob, json, numpy as np, pathlib

def ssim_map(a, b):
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    f = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    ma, mb = f(a), f(b)
    va, vb, cov = f(a * a) - ma * ma, f(b * b) - mb * mb, f(a * b) - ma * mb
    return ((2 * ma * mb + C1) * (2 * cov + C2)) / ((ma * ma + mb * mb + C1) * (va + vb + C2))

def load(p): return cv2.imread(str(p)).astype(np.float32) / 255

frames = [f"f{i:04d}" for i in range(0, 200, 10)]
sources = {"brush": "eval/brush/eval_30000", "spark_tuned": "eval/spark_tuned", "spark_default": "eval/spark_black"}
res = {k: {"psnr": [], "ssim": []} for k in sources}
for fr in frames:
    gt = load(f"dataset/images/{fr}.jpg")
    m = cv2.imread(f"dataset_v2/masks/{fr}.png", 0) > 0
    for k, d in sources.items():
        r = load(f"{d}/{fr}.png")
        mse = ((r - gt) ** 2)[m].mean()
        res[k]["psnr"].append(float(10 * np.log10(1 / mse)))
        s = np.mean([ssim_map(r[..., c], gt[..., c]) for c in range(3)], axis=0)
        res[k]["ssim"].append(float(s[m].mean()))
summary = {k: {"psnr_mean": round(float(np.mean(v["psnr"])), 2), "psnr_min": round(float(np.min(v["psnr"])), 2),
               "psnr_max": round(float(np.max(v["psnr"])), 2), "ssim_mean": round(float(np.mean(v["ssim"])), 3)}
           for k, v in res.items()}
json.dump({"frames": frames, "per_frame": res, "summary": summary}, open("eval/metrics.json", "w"), indent=1)
print(f"{'renderer':12s} {'PSNR mean':>9s} {'min':>6s} {'max':>6s} {'SSIM':>6s}")
for k, s in summary.items():
    print(f"{k:12s} {s['psnr_mean']:9.2f} {s['psnr_min']:6.2f} {s['psnr_max']:6.2f} {s['ssim_mean']:6.3f}")

def lab(img, t):
    img = cv2.resize(img, (640, 360)); cv2.rectangle(img, (0, 0), (640, 34), (0, 0, 0), -1)
    cv2.putText(img, t, (10, 25), 0, 0.75, (255, 255, 255), 2); return img

# eval sheet: real | Brush | Spark for 5 held-out frames
rows = []
for fr in ["f0020", "f0060", "f0100", "f0140", "f0180"]:
    i = frames.index(fr)
    rows.append(np.hstack([lab(cv2.imread(f"dataset/images/{fr}.jpg"), f"{fr} real (held out)"),
                           lab(cv2.imread(f"eval/brush/eval_30000/{fr}.png"), f"Brush render  {res['brush']['psnr'][i]:.1f} dB"),
                           lab(cv2.imread(f"eval/spark_tuned/{fr}.png"), f"Spark (tuned)  {res['spark_tuned']['psnr'][i]:.1f} dB")]))
cv2.imwrite("eval/sheet_eval.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])

# off-path sheet: per position, v1 vs v2 for selected offsets
tags = ["onpath", "right50m", "up50m", "yaw+30", "yaw-45"]
for p in [63, 140]:
    rows = []
    for v, d in [("v1", "eval/offpath_v1"), ("v2", "eval/offpath")]:
        rows.append(np.hstack([lab(cv2.imread(f"{d}/p{p:03d}_{t}.png"), f"{v} frame {p} {t}") for t in tags]))
    cv2.imwrite(f"eval/sheet_offpath_p{p:03d}.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
print("sheets written")
