"""Builds the pictures of the running mini-game from raw_run/.  Run from the project root:
      python tools/make_run_images.py

Per character (ana, later player): green-screen pictures, SIDE view facing RIGHT, one pose each
      raw_run/<who>_run1.jpg   the running pose
      raw_run/<who>_run1b.jpg  (optional) the same pose with the ponytail flying differently (hair flutter)
      raw_run/<who>_run2.jpg   (optional) legs/arms swapped (only used when RUN_MODE = "swap")
      raw_run/<who>_jump.jpg   raw_run/<who>_hit.jpg
Optional (a simple drawn placeholder is made when missing):
      raw_run/bg.jpg       the wide background (path/park/track); the script makes it endless by mirroring
      raw_run/obs_1.jpg  obs_2.jpg  obs_3.jpg   obstacles on green (dumbbell, cone, bag...)
Output: game/images/gym/run_<who>_<pose>.png, run_bg.jpg (3840x1080), run_obs_1..3.png
"""
import os, sys, glob
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from make_pose_camera import edge_despill

OUT = "game/images/gym"
CHAR_H = 640          # character height in the files (the game shows them at half size)
GROUND = 850          # y of the ground line in run_bg.jpg (the game uses the same number)
POSES = ["run1", "run1b", "run2", "jump", "hit"]   # run1b / run2 are optional

def key(im):
    a = np.asarray(im.convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dom = g - np.maximum(r, b)
    alpha = np.clip(1 - (dom - 45) / 55, 0, 1)
    g2 = np.where(dom > 0, np.minimum(g, np.maximum(r, b) + 6), g)
    k = Image.fromarray(np.dstack([r, g2, b, alpha * 255]).astype(np.uint8), "RGBA")
    return edge_despill(k, 3)

def find(base):
    for ext in ("jpg", "png", "jpeg", "webp"):
        p = "raw_run/%s.%s" % (base, ext)
        if os.path.exists(p):
            return p

os.makedirs(OUT, exist_ok=True)
for who in sorted(set(os.path.basename(p).split("_")[0] for p in glob.glob("raw_run/*_run1.*"))):
    frames = {}
    for pose in POSES:
        p = find("%s_%s" % (who, pose))
        if p:
            im = Image.open(p).convert("RGB")
            # every picture comes at a different size: bring them to one canvas size first
            frames[pose] = key(im.resize((1200, int(1200 * im.height / im.width)), Image.LANCZOS))
    # one common crop box for all poses, so they keep their relative size and position
    boxes = [f.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox() for f in frames.values()]
    bx = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    k = CHAR_H / float(bx[3] - bx[1])
    for pose, f in frames.items():
        c = f.crop(bx)
        c = c.resize((int(c.width * k), CHAR_H), Image.LANCZOS)
        c.save("%s/run_%s_%s.png" % (OUT, who, pose))
        print("wrote", who, pose, c.size)

# background: endless by mirroring (picture + its mirror image = 3840 wide)
p = find("bg")
if p:
    bg = Image.open(p).convert("RGB").resize((1920, 1080), Image.LANCZOS)
else:
    bg = Image.new("RGB", (1920, 1080))
    d = ImageDraw.Draw(bg)
    for y in range(GROUND):
        t = y / float(GROUND)
        d.line([0, y, 1920, y], fill=(int(150 + 80 * t), int(200 + 40 * t), 245))
    for cx, cy in ((250, 160), (900, 110), (1500, 210)):
        for dx, dy, r in ((0, 0, 60), (60, 15, 48), (-60, 20, 44)):
            d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=(255, 255, 255))
    for cx, h in ((300, 260), (800, 340), (1350, 280), (1800, 330)):
        d.ellipse([cx - 380, GROUND - h, cx + 380, GROUND + h], fill=(120, 190, 130))
    d.rectangle([0, GROUND - 14, 1920, 1080], fill=(150, 205, 120))
    d.rectangle([0, GROUND + 6, 1920, 1080], fill=(206, 170, 130))
    for x in range(0, 1920, 160):
        d.rectangle([x, GROUND + 60, x + 80, GROUND + 70], fill=(235, 215, 185))
wide = Image.new("RGB", (3840, 1080))
wide.paste(bg, (0, 0))
wide.paste(bg.transpose(Image.FLIP_LEFT_RIGHT), (1920, 0))
wide.save(OUT + "/run_bg.jpg", quality=90)
print("wrote run_bg.jpg", "(placeholder)" if not p else "")

# obstacles
def obstacle(n):
    p = find("obs_%d" % n)
    if p:
        k = key(Image.open(p).convert("RGB"))
        return k.crop(k.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox())
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if n == 1:      # dumbbell
        d.rounded_rectangle([20, 85, 180, 115], 8, fill=(90, 90, 100), outline=(30, 30, 40), width=4)
        for x in (10, 140):
            d.rounded_rectangle([x, 50, x + 50, 150], 14, fill=(60, 60, 70), outline=(20, 20, 28), width=4)
        return im.crop((0, 40, 200, 160))
    if n == 2:      # cone
        d.polygon([(100, 20), (160, 170), (40, 170)], fill=(255, 140, 40), outline=(120, 60, 10))
        d.rectangle([70, 90, 130, 115], fill=(255, 255, 255))
        d.rectangle([20, 170, 180, 190], fill=(230, 110, 30), outline=(120, 60, 10))
        return im.crop((10, 10, 190, 195))
    d.rounded_rectangle([20, 50, 180, 170], 30, fill=(70, 120, 200), outline=(20, 40, 90), width=5)
    d.arc([55, 10, 145, 90], 180, 360, fill=(20, 40, 90), width=8)
    d.rectangle([40, 105, 160, 120], fill=(255, 255, 255))
    return im.crop((10, 5, 190, 175))

for n in (1, 2, 3):
    o = obstacle(n)
    k = 120.0 / o.height if n != 3 else 130.0 / o.height
    o = o.resize((int(o.width * k), int(o.height * k)), Image.LANCZOS)
    o.save("%s/run_obs_%d.png" % (OUT, n))
    print("wrote obstacle", n, o.size)
