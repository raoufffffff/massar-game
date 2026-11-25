"""Builds the bench-press pictures from raw_gym/ (green-screen POV frames + the ceiling background).
Run from the project root:  python tools/make_bench_images.py

  raw_gym/pov_1.jpg .. pov_5.jpg   the bar going up: 1 = on the chest ... 5 = arms fully extended
  raw_gym/pov_fail.jpg             a failed lift (arms trembling, bar stuck low)
  raw_gym/pov_shake.jpg            (optional) trembling arms, used for the 'hard lift'
  raw_gym/bg.jpg                   the ceiling / rack background
Output: game/images/gym/gym_pov_*.png (1920x1080, transparent) and gym_bg.jpg
To add a frame: put the new green-screen picture in raw_gym/ with the same name and run the script again."""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from make_pose_camera import edge_despill

OUT = "game/images/gym"
W, H = 1920, 1080

def key(im):
    a = np.asarray(im.convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dom = g - np.maximum(r, b)
    # the AI green is uneven (darker patches), so the tolerance is wide
    alpha = np.clip(1 - (dom - 45) / 55, 0, 1)
    g2 = np.where(dom > 0, np.minimum(g, np.maximum(r, b) + 6), g)
    k = Image.fromarray(np.dstack([r, g2, b, alpha * 255]).astype(np.uint8), "RGBA")
    return edge_despill(k, 3)

def fit(im):
    return im.resize((W, H), Image.LANCZOS)

os.makedirs(OUT, exist_ok=True)
for name in ["pov_1", "pov_2", "pov_3", "pov_4", "pov_5", "pov_fail", "pov_shake"]:
    p = "raw_gym/%s.jpg" % name
    if not os.path.exists(p):
        print("skip", name); continue
    k = key(fit(Image.open(p)))
    k.save("%s/gym_%s.png" % (OUT, name))
    print("wrote", name)
if os.path.exists("raw_gym/bg.jpg"):
    fit(Image.open("raw_gym/bg.jpg").convert("RGB")).save(OUT + "/gym_bg.jpg", quality=92)
    print("wrote gym_bg")
