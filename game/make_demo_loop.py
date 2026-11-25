"""Build a PLACEHOLDER 10-second loop video of Ana from the sprites (breathing + expression changes),
to test the photo mechanic before real AI-generated video exists.
Run from project root:  python tools/make_demo_loop.py
Requires: pillow numpy ffmpeg
"""
import math, os, subprocess
import numpy as np
from PIL import Image

W, H, FPS, LENGTH = 1920, 1080, 20, 10.0
CX = 1250                         # horizontal centre of Ana in the frame
FADE = 0.4                        # seconds to cross-fade between expressions
# (start second, expression). Best moments ~2s and ~8s (smiles). Worst: the angry end (10s).
TIMELINE = [(0, "neutral"), (1, "smile"), (3, "neutral"), (5, "shy"), (7, "smile"), (9, "angry")]

bg = Image.open("game/images/bg/park_trail.jpg").convert("RGB").resize((W, H))
bg = np.asarray(bg).astype(np.float32)
sprites = {n: Image.open("game/images/ana/ana_casual_%s.png" % n).convert("RGBA")
           for n in {e for _, e in TIMELINE}}

def pose(name, t):
    """Sprite with a gentle breathing motion, anchored at the bottom centre."""
    im = sprites[name]
    s = 1.0 + 0.010 * math.sin(2 * math.pi * t / 4.0)
    w, h = round(im.width * s), round(im.height * s)
    return im.resize((w, h), Image.BILINEAR), h

def expr_at(t):
    idx = max(i for i, (st, _) in enumerate(TIMELINE) if st <= t)
    st, cur = TIMELINE[idx]
    if idx > 0 and t - st < FADE:
        return TIMELINE[idx - 1][1], cur, (t - st) / FADE
    return cur, cur, 1.0

def frame(t):
    a, b, k = expr_at(t)
    canvas = bg.copy()
    layers = [(a, 1.0 - k), (b, k)] if a != b else [(b, 1.0)]
    for name, wgt in layers:
        if wgt <= 0:
            continue
        im, h = pose(name, t)
        arr = np.asarray(im).astype(np.float32)
        al = arr[..., 3:4] / 255.0 * wgt
        x0, y0 = CX - im.width // 2, H - h
        x1, y1 = x0 + im.width, y0 + h
        sx0, sy0 = max(0, -x0), max(0, -y0)
        dx0, dy0 = max(0, x0), max(0, y0)
        dx1, dy1 = min(W, x1), min(H, y1)
        sub = arr[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)]
        asub = al[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)]
        canvas[dy0:dy1, dx0:dx1] = canvas[dy0:dy1, dx0:dx1] * (1 - asub) + sub[..., :3] * asub
    return canvas.astype(np.uint8)

out = "game/videos/ana_loop_demo.webm"
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
       "-r", str(FPS), "-i", "-", "-c:v", "libvpx-vp9", "-crf", "36", "-b:v", "0",
       "-pix_fmt", "yuv420p", "-row-mt", "1", "-cpu-used", "4", "-an", out]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for i in range(int(LENGTH * FPS)):
    p.stdin.write(frame(i / FPS).tobytes())
p.stdin.close(); p.wait()
print(out, os.path.getsize(out) // 1024, "KB")
