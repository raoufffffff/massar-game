# Builds the camera assets: loop video (side-mask webm), lens overlay, target thumbnails.
# usage: python tools/make_camera_assets.py <keyed_rgba_frames_dir> <game_dir>
import sys, os, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFilter
src, game = sys.argv[1], sys.argv[2]
files = sorted(f for f in os.listdir(src) if f.endswith(".png"))
X0, X1 = 400, 880                      # crop of the 1280x720 frame around the character
BK = 820 / 1080.0 * 1.4                # video px -> window px at zoom 1 (must match masar_photo.py)
WIN_W, WIN_H = 1260, 820
frames = [np.array(Image.open(os.path.join(src, f))).astype(np.float32) for f in files]

# ---- 1. seamless loop: the last 12 frames blend toward the first one
n = len(frames)
B = 12
out = []
for i, fr in enumerate(frames):
    if i >= n - B:
        w = (i - (n - B) + 1) / float(B + 1)
        a0, a1 = fr[..., 3:] / 255.0, frames[0][..., 3:] / 255.0
        pm = fr[..., :3] * a0 * (1 - w) + frames[0][..., :3] * a1 * w
        al = a0 * (1 - w) + a1 * w
        rgb = pm / np.maximum(al, 1e-3)
        fr = np.concatenate([np.where(al > 0.01, rgb, 0), al * 255], -1)
    out.append(fr)
tmp = os.path.join(src, "..", "side_crop"); os.makedirs(tmp, exist_ok=True)
for i, fr in enumerate(out):
    c = fr[:, X0:X1]
    rgb = c[..., :3].clip(0, 255).astype(np.uint8)
    al = c[..., 3].clip(0, 255).astype(np.uint8)
    side = np.concatenate([rgb, np.repeat(al[..., None], 3, 2)], 1)
    Image.fromarray(side).save(os.path.join(tmp, "s_%04d.png" % i))
os.makedirs(os.path.join(game, "videos"), exist_ok=True)
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-framerate", "24", "-i", os.path.join(tmp, "s_%04d.png"),
    "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-pix_fmt", "yuv420p", "-an",
    os.path.join(game, "videos", "ana_loop.webm")])

# ---- 2. stills of Ana (480x720, transparent) used to draw the target pictures
EXPR_T = {"neutral": 0.0, "smile": 2.5, "shy": 3.5}
os.makedirs(os.path.join(game, "images", "camera"), exist_ok=True)
for ex, t in EXPR_T.items():
    fr = out[int(round(t * 24))][:, X0:X1]
    Image.fromarray(fr.clip(0, 255).astype(np.uint8), "RGBA").save(
        os.path.join(game, "images", "camera", "ana_%s.png" % ex))
# ---- 3. lens overlay 1920x1080
S = 2
W2, H2 = 1920 * S, 1080 * S
WX, WY = 330 * S, 80 * S
ww, wh = WIN_W * S, WIN_H * S
body = Image.new("RGBA", (W2, H2), (13, 14, 19, 255))
d = ImageDraw.Draw(body)
# subtle body texture: thin horizontal grooves
for y in range(0, H2, 14 * S):
    d.line([(0, y), (W2, y)], fill=(18, 19, 25, 255), width=1)
mask = Image.new("L", (W2, H2), 255)
ImageDraw.Draw(mask).rounded_rectangle([WX, WY, WX + ww, WY + wh], radius=34 * S, fill=0)
body.putalpha(mask)
# window vignette (soft dark edges inside the window)
yy, xx = np.mgrid[0:H2, 0:W2].astype(np.float32)
nx = (xx - (WX + ww / 2)) / (ww / 2); ny = (yy - (WY + wh / 2)) / (wh / 2)
r = np.sqrt(nx ** 2 * 0.9 + ny ** 2)
vig = np.clip((r - 0.62) / 0.55, 0, 1) ** 1.6 * 150
inside = np.array(mask) == 0
a = np.array(body.split()[3]).astype(np.float32)
a[inside] = np.maximum(a[inside], vig[inside])
rgba = np.array(body); rgba[..., 3] = a.astype(np.uint8)
body = Image.fromarray(rgba, "RGBA")
d = ImageDraw.Draw(body)
# window rim
d.rounded_rectangle([WX - 3 * S, WY - 3 * S, WX + ww + 3 * S, WY + wh + 3 * S], radius=36 * S, outline=(60, 64, 78, 255), width=3 * S)
# rule-of-thirds grid
for k in (1, 2):
    x = WX + ww * k // 3; y = WY + wh * k // 3
    d.line([(x, WY + 20 * S), (x, WY + wh - 20 * S)], fill=(255, 255, 255, 38), width=S)
    d.line([(WX + 20 * S, y), (WX + ww - 20 * S, y)], fill=(255, 255, 255, 38), width=S)
# corner brackets
L, T, m = 70 * S, 4 * S, 26 * S
for (cx, cy, sx, sy) in ((WX + m, WY + m, 1, 1), (WX + ww - m, WY + m, -1, 1), (WX + m, WY + wh - m, 1, -1), (WX + ww - m, WY + wh - m, -1, -1)):
    d.line([(cx, cy), (cx + sx * L, cy)], fill=(255, 255, 255, 230), width=T)
    d.line([(cx, cy), (cx, cy + sy * L)], fill=(255, 255, 255, 230), width=T)
# centre focus box (corners only) + cross
cx, cy = WX + ww // 2, WY + wh // 2
hb, ln = 70 * S, 26 * S
for sx in (-1, 1):
    for sy in (-1, 1):
        px, py = cx + sx * hb, cy + sy * hb
        d.line([(px, py), (px - sx * ln, py)], fill=(255, 255, 255, 200), width=3 * S)
        d.line([(px, py), (px, py - sy * ln)], fill=(255, 255, 255, 200), width=3 * S)
d.line([(cx - 9 * S, cy), (cx + 9 * S, cy)], fill=(255, 255, 255, 200), width=2 * S)
d.line([(cx, cy - 9 * S), (cx, cy + 9 * S)], fill=(255, 255, 255, 200), width=2 * S)
# little REC-style dot area top-left of the window
d.ellipse([WX + 60 * S, WY + 62 * S, WX + 74 * S, WY + 76 * S], fill=(230, 50, 50, 255))
body = body.resize((1920, 1080), Image.LANCZOS)
body.save(os.path.join(game, "images", "camera", "lens.png"))
print("ok")
