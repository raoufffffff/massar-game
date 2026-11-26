# -*- coding: utf-8 -*-
"""Draws the phone pictures (no photos needed): the phone frame, the wallpaper, the HUD button and the app icons.

Run from the project root:   python tools/make_phone_assets.py
Writes to game/images/ui/phone_*.png.  Safe to re-run; change the colours below to restyle the phone.
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont

OUT = "game/images/ui"
FONT = "game/fonts/Anton-Regular.ttf"
os.makedirs(OUT, exist_ok=True)
SS = 4   # supersampling: draw big, shrink for smooth edges


def gradient(w, h, c1, c2, vertical=True):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (y / float(h - 1)) if vertical else ((x + y) / float(w + h - 2))
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (255,)
    return img


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return m


def save_small(img, path, w, h):
    img.resize((w, h), Image.LANCZOS).save(path)
    print("wrote", path)


# ---------------------------------------------------------------- phone frame (overlay with a transparent screen)
def make_body():
    W, H = 640 * SS, 1040 * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, W - 1, H - 1), 78 * SS, fill=hexc("#3a3f4d") + (255,))
    d.rounded_rectangle((5 * SS, 5 * SS, W - 5 * SS, H - 5 * SS), 74 * SS, fill=hexc("#14161c") + (255,))
    # transparent screen window
    win = Image.new("L", (W, H), 255)
    ImageDraw.Draw(win).rounded_rectangle((28 * SS, 28 * SS, 612 * SS, 1012 * SS), 52 * SS, fill=0)
    a = img.getchannel("A")
    a = Image.composite(Image.new("L", (W, H), 0), a, Image.eval(win, lambda v: 255 - v))
    img.putalpha(a)
    d = ImageDraw.Draw(img)
    d.ellipse((310 * SS, 12 * SS, 330 * SS, 28 * SS), fill=hexc("#2a2e3a") + (255,))   # camera dot
    save_small(img, OUT + "/phone_body.png", 640, 1040)


def make_wall():
    img = gradient(584, 984, hexc("#161b3d"), hexc("#4d2c73"))
    # soft glow
    glow = Image.new("RGBA", (584, 984), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-120, 560, 700, 1200), fill=(255, 120, 190, 28))
    img = Image.alpha_composite(img, glow)
    img.save(OUT + "/phone_wall.png")
    print("wrote", OUT + "/phone_wall.png")


# ---------------------------------------------------------------- HUD button (small phone)
def make_button(hover):
    W, H = 84 * SS, 138 * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    edge = "#ffd54a" if hover else "#8a93a8"
    d.rounded_rectangle((0, 0, W - 1, H - 1), 24 * SS, fill=hexc(edge) + (255,))
    d.rounded_rectangle((5 * SS, 5 * SS, W - 5 * SS, H - 5 * SS), 20 * SS, fill=hexc("#14161c") + (255,))
    sc = gradient(W - 18 * SS, H - 18 * SS, hexc("#5f86d8" if hover else "#3d5a99"), hexc("#a56bff" if hover else "#7b4dff"))
    m = rounded_mask(sc.width, sc.height, 16 * SS)
    img.paste(sc, (9 * SS, 9 * SS), m)
    d = ImageDraw.Draw(img)
    for i, y in enumerate((50, 70, 90)):          # tiny app dots
        for j in range(2):
            x = 24 + j * 24
            d.rounded_rectangle((x * SS, y * SS, (x + 15) * SS, (y + 15) * SS), 4 * SS, fill=(255, 255, 255, 200))
    save_small(img, OUT + "/phone_btn_hover.png" if hover else OUT + "/phone_btn.png", 84, 138)


# ---------------------------------------------------------------- app icons
def icon_base(c1, c2):
    S = 124 * SS
    base = gradient(S, S, hexc(c1), hexc(c2), vertical=False)
    return base, S


def finish_icon(base, S, name):
    base.putalpha(rounded_mask(S, S, 30 * SS))
    save_small(base, "%s/phone_app_%s.png" % (OUT, name), 124, 124)


def star_points(cx, cy, r_out, r_in, n=8):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def make_icons():
    k = SS
    # messages
    b, S = icon_base("#43d17a", "#1c9c58")
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((26 * k, 30 * k, 98 * k, 80 * k), 16 * k, fill="white")
    d.polygon([(44 * k, 76 * k), (40 * k, 98 * k), (64 * k, 78 * k)], fill="white")
    for i in range(3):
        x = 45 + i * 17
        d.ellipse((x * k, 49 * k, (x + 9) * k, 58 * k), fill=hexc("#1c9c58"))
    finish_icon(b, S, "messages")
    # gallery
    b, S = icon_base("#ffb347", "#f0553a")
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((22 * k, 26 * k, 102 * k, 98 * k), 12 * k, fill="white")
    d.rectangle((30 * k, 34 * k, 94 * k, 90 * k), fill=hexc("#6ec0f2"))
    d.ellipse((72 * k, 40 * k, 88 * k, 56 * k), fill=hexc("#ffe066"))
    d.polygon([(30 * k, 90 * k), (30 * k, 78 * k), (52 * k, 52 * k), (68 * k, 72 * k), (78 * k, 62 * k), (94 * k, 80 * k), (94 * k, 90 * k)], fill=hexc("#3fae6a"))
    finish_icon(b, S, "gallery")
    # snapjob (camera)
    b, S = icon_base("#ffc233", "#ff7a1a")
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((20 * k, 42 * k, 104 * k, 94 * k), 12 * k, fill="white")
    d.rounded_rectangle((44 * k, 30 * k, 76 * k, 48 * k), 6 * k, fill="white")
    d.ellipse((42 * k, 48 * k, 82 * k, 88 * k), fill=hexc("#2b2f3a"))
    d.ellipse((50 * k, 56 * k, 74 * k, 80 * k), fill=hexc("#4a90e2"))
    d.ellipse((86 * k, 50 * k, 96 * k, 60 * k), fill=hexc("#ff9a2a"))
    finish_icon(b, S, "snapjob")
    # supernova (star)
    b, S = icon_base("#7b4dff", "#ff4d9d")
    d = ImageDraw.Draw(b)
    d.polygon([(x * k, y * k) for x, y in star_points(62, 62, 40, 17)], fill="white")
    d.ellipse((52 * k, 52 * k, 72 * k, 72 * k), fill=hexc("#ff4d9d"))
    finish_icon(b, S, "supernova")
    # bank ($)
    b, S = icon_base("#3a8cff", "#1b4fa8")
    d = ImageDraw.Draw(b)
    f = ImageFont.truetype(FONT, 84 * k)
    d.text((62 * k, 66 * k), "$", font=f, fill="white", anchor="mm")
    finish_icon(b, S, "bank")
    # tasks (checklist)
    b, S = icon_base("#f2575f", "#c22a4a")
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((28 * k, 22 * k, 96 * k, 104 * k), 10 * k, fill="white")
    for i in range(3):
        y = 38 + i * 22
        d.rounded_rectangle((36 * k, y * k, 50 * k, (y + 14) * k), 3 * k, outline=hexc("#c22a4a"), width=3 * k)
        d.rounded_rectangle((56 * k, (y + 3) * k, 88 * k, (y + 11) * k), 3 * k, fill=hexc("#d6dae3"))
    d.line([(38 * k, 45 * k), (42 * k, 49 * k), (49 * k, 40 * k)], fill=hexc("#c22a4a"), width=3 * k)
    finish_icon(b, S, "tasks")
    # contacts (person)
    b, S = icon_base("#7a8aa3", "#3f4a5e")
    d = ImageDraw.Draw(b)
    d.ellipse((44 * k, 28 * k, 80 * k, 64 * k), fill="white")
    d.ellipse((28 * k, 70 * k, 96 * k, 130 * k), fill="white")
    finish_icon(b, S, "contacts")
    # me (stats and bag: a backpack)
    b, S = icon_base("#43c6c6", "#1b7f8f")
    d = ImageDraw.Draw(b)
    d.arc((42 * k, 14 * k, 82 * k, 54 * k), 180, 360, fill="white", width=6 * k)
    d.rounded_rectangle((30 * k, 36 * k, 94 * k, 108 * k), 16 * k, fill="white")
    d.rounded_rectangle((42 * k, 72 * k, 82 * k, 96 * k), 6 * k, outline=hexc("#1b7f8f"), width=4 * k)
    d.line([(30 * k, 62 * k), (94 * k, 62 * k)], fill=hexc("#1b7f8f"), width=4 * k)
    finish_icon(b, S, "me")


if __name__ == "__main__":
    make_body()
    make_wall()
    make_button(False)
    make_button(True)
    make_icons()
