"""Draws simple placeholder pictures for the bench-press mini-game (POV, lying on the bench looking up).
Replace them with real artwork any time, keeping the file names:
   game/images/gym/lift_bg.jpg    1920x1080  the view from the bench: ceiling lights, the rack uprights
   game/images/gym/lift_bar.png   transparent PNG: the barbell with the player's hands (any size, centred)
Run from the project root:  python tools/make_gym_placeholders.py"""
from PIL import Image, ImageDraw, ImageFilter

# background: ceiling + two rack uprights + vignette
bg = Image.new("RGB", (1920, 1080), (58, 62, 70))
d = ImageDraw.Draw(bg)
for i in range(0, 1080, 6):                       # soft vertical gradient (lighter at the top)
    c = int(48 + 28 * (1 - i / 1080.0))
    d.rectangle([0, i, 1920, i + 6], fill=(c, c + 4, c + 12))
for x in (360, 960, 1560):                         # ceiling light panels
    d.rounded_rectangle([x - 150, 70, x + 150, 120], 10, fill=(235, 238, 225))
for x in (300, 1620):                              # rack uprights
    d.rectangle([x - 28, 0, x + 28, 1080], fill=(34, 36, 42))
    for y in range(120, 1080, 110):
        d.ellipse([x - 7, y, x + 7, y + 14], fill=(18, 18, 22))
vig = Image.new("L", (1920, 1080), 0)
ImageDraw.Draw(vig).ellipse([-300, -250, 2220, 1330], fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(220))
bg = Image.composite(bg, Image.new("RGB", bg.size, (14, 15, 18)), vig)
bg.save("game/images/gym/lift_bg.jpg", quality=92)

# bar with plates and two hands, seen from below
W, H = 1700, 320
bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
b = ImageDraw.Draw(bar)
b.rounded_rectangle([40, 140, W - 40, 180], 18, fill=(170, 174, 182), outline=(60, 62, 68), width=3)
for side in (0, 1):
    for k, (w, h) in enumerate(((46, 300), (36, 250), (30, 200))):
        x0 = 90 + k * 52 if side == 0 else W - 90 - k * 52 - w
        b.rounded_rectangle([x0, H / 2 - h / 2, x0 + w, H / 2 + h / 2], 10, fill=(32 + k * 8, 33 + k * 8, 38 + k * 8), outline=(10, 10, 12), width=3)
for hx in (640, 1060):                              # fists gripping the bar
    b.rounded_rectangle([hx - 70, 112, hx + 70, 210], 34, fill=(224, 176, 148), outline=(96, 60, 44), width=4)
    for f in range(4):
        b.line([hx - 48 + f * 32, 128, hx - 48 + f * 32, 190], fill=(150, 100, 80), width=3)
bar.save("game/images/gym/lift_bar.png")
print("wrote game/images/gym/lift_bg.jpg and lift_bar.png")
