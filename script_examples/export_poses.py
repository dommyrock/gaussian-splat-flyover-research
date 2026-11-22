"""COLMAP images.txt/cameras.txt -> viewer/poses.json (three.js camera poses).

COLMAP stores world->camera (R, t) in OpenCV axes (x right, y down, z forward).
For three.js we need camera->world with OpenGL axes (y up, z backward).
"""
import json, sys
import numpy as np

txt = sys.argv[1] if len(sys.argv) > 1 else "colmap/txt"
cam = [l.split() for l in open(f"{txt}/cameras.txt") if not l.startswith("#")][0]
w, h, f = int(cam[2]), int(cam[3]), float(cam[4])

def qmat(w_, x, y, z):
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w_), 2*(x*z+y*w_)],
                     [2*(x*y+z*w_), 1-2*(x*x+z*z), 2*(y*z-x*w_)],
                     [2*(x*z-y*w_), 2*(y*z+x*w_), 1-2*(x*x+y*y)]])

poses, ups = [], []
rows = [l.split() for l in open(f"{txt}/images.txt") if not l.startswith("#") and l.strip()][::2]
for r in sorted(rows, key=lambda r: r[9]):
    R = qmat(*map(float, r[1:5])); t = np.array(list(map(float, r[5:8])))
    c2w = R.T
    C = -c2w @ t
    gl = c2w @ np.diag([1, -1, -1])  # OpenCV -> OpenGL camera axes
    poses.append({"name": r[9], "position": C.tolist(), "matrix": gl.T.flatten().tolist()})  # row-major basis vectors
    ups.append(-c2w[:, 1])
up = np.mean(ups, axis=0); up /= np.linalg.norm(up)
json.dump({"vfov": float(np.degrees(2*np.arctan(h/2/f))), "aspect": w/h, "up": up.tolist(), "poses": poses},
          open("viewer/poses.json", "w"))
print(len(poses), "poses, vfov", round(float(np.degrees(2*np.arctan(h/2/f))), 1), "up", up.round(3))
