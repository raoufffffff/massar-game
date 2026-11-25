"""Generate placeholder backgrounds (1920x1080) for every room into game/images/bg/.
Run from the project root:  python tools/make_placeholders.py
Requires: pip install pillow
"""
import os, sys, colorsys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import masar_core as mc
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..", "game", "images", "bg")
os.makedirs(OUT, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
if not os.path.exists(FONT):
    FONT = "DejaVuSans-Bold.ttf"

def draw(pid, rid, area, pname, rname, idx):
    hue = ((area - 1) * 0.22 + idx * 0.035) % 1.0
    r, g, b = [int(255 * c) for c in colorsys.hsv_to_rgb(hue, 0.35, 0.55)]
    im = Image.new("RGB", (1920, 1080), (r, g, b))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 760, 1920, 1080), fill=(max(r - 30, 0), max(g - 30, 0), max(b - 30, 0)))
    big = ImageFont.truetype(FONT, 120)
    small = ImageFont.truetype(FONT, 56)
    for text, font, y in ((pname, big, 380), (rname, small, 540), ("placeholder", small, 640)):
        w = d.textlength(text, font=font)
        d.text(((1920 - w) / 2, y), text, font=font, fill=(255, 255, 255))
    im.save(os.path.join(OUT, "%s_%s.jpg" % (pid, rid)), quality=88)

n = 0
for i, p in enumerate(mc.PLACES):
    for rid, rname in mc.rooms_of(p.id):
        draw(p.id, rid, p.area, p.name, rname, i)
        n += 1
print("generated", n)
