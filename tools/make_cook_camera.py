"""Camera-resolution cooking pictures (1600x2160, shown at zoom 0.5 so the lens can zoom sharply).
Source: raw_blink/pose_cooking_<neutral|smile|shy|blink>.jpg (green screen). Run from the project root.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from key_sprites import key
from PIL import Image
for k, name in {"neutral": "neutral", "smile": "smile", "shy": "shy", "blink": "closed"}.items():
    im = Image.open("raw_blink/pose_cooking_%s.jpg" % k)
    k2 = key(im).resize((round(im.width * 0.9), 2160), Image.LANCZOS)
    c = Image.new("RGBA", (1600, 2160)); c.paste(k2, (4, 0), k2)
    c.save("game/images/camera/cook_%s.png" % name, optimize=True)
