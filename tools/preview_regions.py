# -*- coding: utf-8 -*-
"""Draws the rectangles of ANA_REGIONS (masar_shot.py) over Ana's camera pictures, so you can see what each part covers.

Run from the project root:   python tools/preview_regions.py
Writes tools/regions_<scene>.png.  Colours: face = red, torso = yellow, legs = green, feet = blue,
hands = magenta, objects = white (with their names), whole figure = grey outline.
Change a rectangle in ANA_REGIONS, run again, look again.  Numbers are x, y, width, height in the 800x1080 picture.
"""
import os
import sys
from PIL import Image, ImageDraw

sys.path.insert(0, "game")
import masar_photo as mp
import masar_shot as sh

COLORS = {"face": "#ff3b3b", "torso": "#ffd54a", "legs": "#3bd16f", "feet": "#3b8cff", "hands": "#ff3bd5"}

for sid, sc in mp.SCENES.items():
    path = os.path.join("game", sc["images"]["neutral"])
    if not os.path.exists(path):
        print("missing picture:", path)
        continue
    img = Image.open(path).convert("RGB").resize((800, 1080))
    d = ImageDraw.Draw(img)
    reg = sh.regions_for(sid)
    if sid not in sh.ANA_REGIONS:
        print(sid, "has no entry in ANA_REGIONS: showing the default proportions")
    x, y, w, h = reg["figure"]
    d.rectangle((x, y, x + w, y + h), outline="#aaaaaa", width=2)
    for key, col in COLORS.items():
        for x, y, w, h in reg[key]:
            d.rectangle((x, y, x + w, y + h), outline=col, width=3)
    for name, (x, y, w, h) in reg["objects"]:
        d.rectangle((x, y, x + w, y + h), outline="#ffffff", width=3)
        d.text((x + 4, y + 4), name, fill="#ffffff")
    out = "tools/regions_%s.png" % sid
    img.save(out)
    print("wrote", out)
