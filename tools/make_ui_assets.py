# Builds UI art: navigation tags, number badges, panel, camera icon, Ana hover glows.
# usage: python tools/make_ui_assets.py <game_dir>
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
game = sys.argv[1]
ui = os.path.join(game, "images", "ui"); os.makedirs(ui, exist_ok=True)
S = 4  # supersampling

def poly(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]

def tag(path, top, bot, outline, hi):
    W, H = 240, 92
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    x0, y0, x1, y1, c = 8, 6, 232, 78, 17
    P = lambda dx=0, dy=0, inset=0: [((x + dx) * S, (y + dy) * S) for x, y in poly(x0 + inset, y0 + inset, x1 - inset, y1 - inset, max(2, c - inset))]
    # shadow
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon(P(0, 9), fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(3 * S))
    img.alpha_composite(sh)
    # gradient body
    grad = np.zeros((H * S, W * S, 4), np.uint8)
    for yy in range(H * S):
        k = min(1.0, max(0.0, (yy - y0 * S) / float((y1 - y0) * S)))
        grad[yy, :, :3] = [int(top[i] + (bot[i] - top[i]) * k) for i in range(3)]
        grad[yy, :, 3] = 255
    mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).polygon(P(), fill=255)
    body = Image.fromarray(grad, "RGBA"); body.putalpha(mask)
    img.alpha_composite(body)
    d = ImageDraw.Draw(img)
    # gloss on the upper half
    gl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gm = Image.new("L", img.size, 0)
    ImageDraw.Draw(gm).polygon(P(0, 0, 5), fill=255)
    ImageDraw.Draw(gm).rectangle([0, (y0 + 38) * S, W * S, H * S], fill=0)
    ImageDraw.Draw(gl).rectangle([0, 0, W * S, H * S], fill=(255, 255, 255, 40))
    gl.putalpha(ImageChops.multiply(gm, gl.split()[3]))
    img.alpha_composite(gl)
    # inner light rim + dark outline
    d.polygon(P(0, 0, 7), outline=hi + (110,), width=2 * S)
    d.polygon(P(), outline=outline + (255,), width=5 * S)
    img.resize((W, H), Image.LANCZOS).save(path)

tag(os.path.join(ui, "nav_tag.png"), (234, 34, 90), (166, 10, 50), (58, 10, 24), (255, 140, 170))
tag(os.path.join(ui, "nav_tag_hover.png"), (255, 70, 120), (204, 24, 72), (58, 10, 24), (255, 200, 215))
tag(os.path.join(ui, "nav_tag_current.png"), (255, 206, 70), (214, 140, 12), (92, 52, 0), (255, 240, 170))

# number badge
B = 64
img = Image.new("RGBA", (B * S, B * S), (0, 0, 0, 0))
sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
ImageDraw.Draw(sh).ellipse([6 * S, 9 * S, 58 * S, 61 * S], fill=(0, 0, 0, 140))
img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(2 * S)))
d = ImageDraw.Draw(img)
d.ellipse([4 * S, 4 * S, 58 * S, 58 * S], fill=(20, 20, 24, 255))
d.ellipse([8 * S, 8 * S, 54 * S, 54 * S], fill=(255, 255, 255, 255))
d.ellipse([11 * S, 11 * S, 51 * S, 51 * S], outline=(225, 225, 232, 255), width=2 * S)
img.resize((B, B), Image.LANCZOS).save(os.path.join(ui, "nav_num.png"))

# translucent rounded panel (9-slice)
W, H, R = 120, 90, 18
img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([1 * S, 1 * S, (W - 1) * S, (H - 1) * S], radius=R * S, fill=(14, 15, 24, 205), outline=(255, 255, 255, 70), width=2 * S)
img.resize((W, H), Image.LANCZOS).save(os.path.join(ui, "panel.png"))

# camera icon
def cam(path, ring):
    N = 88
    img = Image.new("RGBA", (N * S, N * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([3 * S, 3 * S, 85 * S, 85 * S], fill=(14, 15, 24, 225), outline=ring + (255,), width=4 * S)
    d.rounded_rectangle([20 * S, 31 * S, 68 * S, 64 * S], radius=6 * S, fill=(255, 255, 255, 255))
    d.rounded_rectangle([32 * S, 24 * S, 50 * S, 33 * S], radius=3 * S, fill=(255, 255, 255, 255))
    d.ellipse([34 * S, 37 * S, 54 * S, 57 * S], fill=(14, 15, 24, 255))
    d.ellipse([38 * S, 41 * S, 50 * S, 53 * S], fill=(90, 140, 255, 255))
    d.ellipse([58 * S, 35 * S, 63 * S, 40 * S], fill=(232, 30, 80, 255))
    img.resize((N, N), Image.LANCZOS).save(path)
cam(os.path.join(ui, "cam_icon.png"), (255, 255, 255))
cam(os.path.join(ui, "cam_icon_hover.png"), (255, 213, 74))

# Ana hover glow: the sprite with a soft warm outline around the body only.
# Covers the expressions and every activity picture (pose_*.png).
import glob
for sp in sorted(glob.glob(os.path.join(game, "images", "ana", "*.png"))):
    base = os.path.basename(sp)
    if base.endswith("_glow.png") or base.endswith("_blink.png"):
        continue
    spr = Image.open(sp).convert("RGBA")
    a = spr.split()[3]
    big = a.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(5))
    g = Image.new("RGBA", spr.size, (255, 238, 200, 0))
    g.putalpha(big.point(lambda v: min(255, int(v * 1.1))))
    g.alpha_composite(spr)
    g.save(sp[:-4] + "_glow.png")
print("ok")
