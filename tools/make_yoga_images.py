"""Builds the yoga mini-game pictures from raw_yoga/.   Run from the project root:
      python tools/make_yoga_images.py             builds everything
      python tools/make_yoga_images.py --preview   also writes yoga_preview.jpg (all poses side by side on the floor)

Green-screen pictures of Ana, FULL body, one file per state (same character, same camera as far as possible):
      raw_yoga/start.jpg      relaxed standing (the state before the first success)
      raw_yoga/p1.jpg .. p5.jpg   the 5 poses, easiest first
      raw_yoga/f0.jpg .. f4.jpg   (optional) the "confused / lost balance" version of start, p1..p4
      raw_yoga/bg.jpg         (optional) the studio background (a simple one is drawn when missing)
Output: game/images/gym/yoga_<name>.png (1400x1080, transparent, feet on one floor line), yoga_bg.jpg, arrows.

If one pose sits a little too big / too far left / too high, edit tools/yoga_adjust.json, e.g.
      {"p2": {"scale": 1.08, "dx": -20, "dy": 6}}       (scale 1 = as is, dx/dy in pixels) and run again.
"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from make_pose_camera import edge_despill

OUT = "game/images/gym"
CW, CH = 1400, 1080          # size of every output picture
FLOOR = 1050                 # y of the floor line inside each picture (the lowest foot touches it)
NAMES = ["start", "p1", "p2", "p3", "p4", "p5", "f0", "f1", "f2", "f3", "f4"]

def key(im):
    a = np.asarray(im.convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dom = g - np.maximum(r, b)
    alpha = np.clip(1 - (dom - 45) / 55, 0, 1)
    g2 = np.where(dom > 0, np.minimum(g, np.maximum(r, b) + 6), g)
    k = Image.fromarray(np.dstack([r, g2, b, alpha * 255]).astype(np.uint8), "RGBA")
    return edge_despill(k, 3)

adj = {}
if os.path.exists("tools/yoga_adjust.json"):
    adj = json.load(open("tools/yoga_adjust.json"))

os.makedirs(OUT, exist_ok=True)
made = []
placed = {}                   # base pictures: name -> (scale used, bounding box) so the fail versions line up exactly
BASE = {"f0": "start", "f1": "p1", "f2": "p2", "f3": "p3", "f4": "p4"}
for n in NAMES:                # bases first (NAMES lists them before the f-pictures)
    p = "raw_yoga/%s.jpg" % n
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGB")
    s0 = CH * 0.93 / im.height                       # the whole picture height -> 93% of the output height
    a = adj.get(BASE.get(n, n), {})                  # a fail picture uses the adjustments of its base picture
    sc = a.get("scale", 1.0)
    k = key(im.resize((int(im.width * s0 * sc), int(im.height * s0 * sc)), Image.LANCZOS))
    bb = k.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
    if n in BASE and BASE[n] in placed:
        bb = placed[BASE[n]]                         # same place as the base picture (the comic marks must not move her)
    else:
        placed[n] = bb
    cx = (bb[0] + bb[2]) / 2.0
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    ox = int(CW / 2 - cx + a.get("dx", 0))
    oy = int(FLOOR - bb[3] + a.get("dy", 0))
    canvas.paste(k, (ox, oy), k)
    canvas.save("%s/yoga_%s.png" % (OUT, n))
    made.append(n)
    print("wrote", n)

# background
if os.path.exists("raw_yoga/bg.jpg"):
    bg = Image.open("raw_yoga/bg.jpg").convert("RGB").resize((1920, 1080), Image.LANCZOS)
else:
    bg = Image.new("RGB", (1920, 1080))
    d = ImageDraw.Draw(bg)
    for y in range(1080):
        t = y / 1080.0
        d.line([0, y, 1920, y], fill=(int(235 - 25 * t), int(228 - 25 * t), int(214 - 30 * t)))
    d.rectangle([0, FLOOR - 120, 1920, 1080], fill=(196, 160, 118))        # wooden floor
    for x in range(0, 1920, 140):
        d.line([x, FLOOR - 120, x - 60, 1080], fill=(170, 135, 98), width=3)
    for x in (140, 520, 900):                                               # windows
        d.rectangle([x, 120, x + 280, 620], fill=(205, 226, 245), outline=(250, 250, 250), width=10)
    d.rounded_rectangle([320, FLOOR - 40, 920, FLOOR + 30], 14, fill=(120, 160, 190))   # mat
bg.save(OUT + "/yoga_bg.jpg", quality=90)

# arrows: normal / done / current
def arrow(direction, fill, outline, glow=None):
    S = 160
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if glow:
        d.rounded_rectangle([4, 4, S - 4, S - 4], 28, fill=glow)
    pts = [(80, 22), (134, 84), (100, 84), (100, 136), (60, 136), (60, 84), (26, 84)]   # pointing up
    poly = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(poly).polygon(pts, fill=fill, outline=outline)
    ImageDraw.Draw(poly).line(pts + [pts[0]], fill=outline, width=5)
    rot = {"up": 0, "left": 90, "down": 180, "right": 270}[direction]
    im.alpha_composite(poly.rotate(rot))
    return im
for dname in ("up", "down", "left", "right"):
    arrow(dname, (255, 255, 255, 255), (60, 70, 90, 255), (20, 24, 34, 150)).save("%s/yoga_arrow_%s_n.png" % (OUT, dname))
    arrow(dname, (110, 235, 140, 255), (30, 110, 60, 255), (20, 60, 30, 170)).save("%s/yoga_arrow_%s_d.png" % (OUT, dname))
    arrow(dname, (255, 220, 90, 255), (140, 100, 10, 255), (255, 230, 120, 170)).save("%s/yoga_arrow_%s_c.png" % (OUT, dname))

if "--preview" in sys.argv:
    prev = bg.copy().convert("RGBA")
    W = 6
    sheet = Image.new("RGB", (W * 480, 2 * 400), (30, 30, 30))
    for i, n in enumerate(made):
        t = bg.copy().convert("RGBA")
        t.alpha_composite(Image.open("%s/yoga_%s.png" % (OUT, n)), (260, 0))
        t = t.resize((480, 270))
        sheet.paste(t.convert("RGB"), ((i % W) * 480, (i // W) * 400))
        ImageDraw.Draw(sheet).text(((i % W) * 480 + 8, (i // W) * 400 + 276), n, fill=(255, 255, 255))
    sheet.save("yoga_preview.jpg", quality=88)
    print("wrote yoga_preview.jpg")
