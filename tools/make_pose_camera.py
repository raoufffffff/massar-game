"""Camera-resolution pictures of a pose (1600x2160, shown at zoom 0.5 so the lens can zoom sharply)
and the room picture (800x1080) from the green-screen originals in raw_blink/.
Run from the project root:  python tools/make_pose_camera.py [cook|eat]
raw_blink/<raw>_<neutral|smile|shy|blink>.jpg -> game/images/camera/<key>_<neutral|smile|shy|closed>.png
(the room picture game/images/ana/pose_<name>.png is made only if 'room' is set)
xoff: horizontal paste offset (in camera pixels). A pose whose picture is cut by its right edge
(the table of 'eat') is pasted flush to the right edge so the game can put it at the screen edge.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from key_sprites import key
from PIL import Image

POSES = {
    "cook": {"raw": "pose_cooking", "xoff": 4, "room": None},      # pose_cooking.png is already installed
    "eat":  {"raw": "pose_eating", "xoff": "right", "room": "pose_eating"},
}
def fit_34(im):
    """The pipeline expects a 3:4 portrait. Any other shape is padded with the picture's own green:
    too wide -> extra green on TOP (her feet stay at the bottom); too narrow -> extra green on the sides."""
    w, h = im.size
    bg = im.convert("RGB").getpixel((3, 3))
    if w * 4 > h * 3:                       # wider than 3:4
        nh = round(w * 4 / 3)
        c = Image.new("RGB", (w, nh), bg)
        c.paste(im.convert("RGB"), (0, nh - h))
    elif w * 4 < h * 3:                     # narrower than 3:4
        nw = round(h * 3 / 4)
        c = Image.new("RGB", (nw, h), bg)
        c.paste(im.convert("RGB"), ((nw - w) // 2, 0))
    else:
        c = im.convert("RGB")
    return c.resize((1792, 2400), Image.LANCZOS) if c.size != (1792, 2400) else c


def edge_despill(k, width=4):
    """Remove the green fringe on the silhouette: near transparent pixels, green is clamped to max(r,b)."""
    import numpy as np
    from PIL import ImageFilter
    a = np.asarray(k).astype(float)
    alpha = k.getchannel("A").filter(ImageFilter.MinFilter(2 * width + 1))
    near = np.asarray(alpha) < 250
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    g2 = np.where(near, np.minimum(g, np.maximum(r, b)), g)
    a[..., 1] = g2
    return Image.fromarray(a.astype('uint8'), "RGBA")


EXPR = {"neutral": "neutral", "smile": "smile", "shy": "shy", "blink": "closed"}


def run(name):
    cfg = POSES[name]
    for src, dst in EXPR.items():
        path = "raw_blink/%s_%s.jpg" % (cfg["raw"], src)
        if not os.path.exists(path):
            continue
        im = fit_34(Image.open(path))
        k = key(im)
        if cfg.get('despill'):
            k = edge_despill(k)
        for scale, canvas_w, out in ((0.9, 1600, "game/images/camera/%s_%s.png" % (name, dst)),
                                     (0.45, 800, "game/images/ana/%s.png" % cfg["room"] if cfg["room"] and src == "neutral" else None)):
            if out is None:
                continue
            k2 = k.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
            xoff = cfg["xoff"]
            if xoff == "right":
                xoff = canvas_w - k2.width
            elif scale == 0.45:
                xoff = xoff // 2
            c = Image.new("RGBA", (canvas_w, k2.height))
            c.paste(k2, (xoff, 0), k2)
            c.save(out, optimize=True)
            print(out, c.size)


if __name__ == "__main__":
    for n in sys.argv[1:] or POSES:
        run(n)
