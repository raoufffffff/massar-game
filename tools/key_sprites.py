"""Chroma-key green-screen sprites into transparent PNGs, normalised to one size.
Usage (from project root):  python tools/key_sprites.py raw_ana game/images/ana
Requires: pip install pillow numpy
All sprites of one character/outfit are scaled by the SAME factor (taken from the
reference file) so that expressions line up exactly when swapped in the game.
"""
import os, sys
import numpy as np
from PIL import Image

TARGET_H = 1080          # output height in pixels
REF = "neutral"          # expression used as the scale/alignment reference

def key(im):
    a = np.asarray(im.convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dom = g - np.maximum(r, b)
    alpha = np.clip(1 - (dom - 30) / 60, 0, 1)
    g2 = np.where(dom > 0, np.minimum(g, np.maximum(r, b) + 10), g)
    out = np.dstack([r, g2, b, alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")

def bbox_of(rgba):
    return rgba.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()

def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    files = sorted(f for f in os.listdir(src) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    keyed = {f: key(Image.open(os.path.join(src, f))) for f in files}
    ref = [f for f in files if REF in f][0]
    rb = bbox_of(keyed[ref])
    scale = TARGET_H / keyed[ref].height
    ref_cx = (rb[0] + rb[2]) / 2 * scale
    for f, im in keyed.items():
        # per-file scale from its own height keeps the same framing as the reference
        s = TARGET_H / im.height
        im2 = im.resize((round(im.width * s), TARGET_H), Image.LANCZOS)
        bb = bbox_of(im2)
        cx = (bb[0] + bb[2]) / 2
        # align horizontal centre of the body to the reference, on a common-width canvas
        W = 800
        canvas = Image.new("RGBA", (W, TARGET_H), (0, 0, 0, 0))
        canvas.paste(im2, (round(W / 2 - cx), 0), im2)
        name = os.path.splitext(f)[0] + ".png"
        canvas.save(os.path.join(dst, name), optimize=True)
        print(name, "bbox", bb, "scale %.3f" % s)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
