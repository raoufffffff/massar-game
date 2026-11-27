"""Builds the pipe-repair mini-game pictures and layout (game/data/pipes.json).

Run from the project root:   python tools/make_pipe_scene.py
Needs: pip install pillow numpy

Sources (kept in raw_pipes/):
  pieces_sheet.jpg    the 7 pipe pieces on a green background, in a row (left to right):
                      straight, vertical, elbow a, elbow b, T, valve, long vertical
  kitchen_bg_src.jpg  the wall with two pipe stubs (left and right), same height

What it does
  1. cuts the pieces out of the green and measures where their openings (ports) are
  2. edits the wall picture: shortens both stubs (wider gap) and moves the left one down and the
     right one up, so the repair becomes a staircase  (low left -> high right)
  3. builds the pieces at the right size, shortens the straight ones to fit, and chains them:
        H0 - E1 (up) - V - E2 (right) - valve - H1
  4. writes game/images/pipes/kitchen_*.png (pieces and shadows), kitchen_bg.jpg and game/data/pipes.json

To make another puzzle: copy the KITCHEN block, change the numbers / piece order, run again.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.getcwd()
if os.path.basename(ROOT) == "tools":
    ROOT = os.path.dirname(ROOT)
RAW = os.path.join(ROOT, "raw_pipes")
OUT = os.path.join(ROOT, "game", "images", "pipes")
DATA = os.path.join(ROOT, "game", "data", "pipes.json")

SHEET_ORDER = ["h", "v", "elbow_a", "elbow_b", "t", "valve", "vlong"]
GREEN = np.array([10.0, 169.0, 77.0])

# ---------------------------------------------------------------- pieces
def cut_pieces(path):
    """Returns {name: RGBA numpy array (trimmed)} from the green-screen sheet."""
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    d = np.sqrt(((a - GREEN) ** 2).sum(2))
    alpha = np.clip((d - 40) / 60, 0, 1)
    rgb = a.copy()
    spill = (rgb[..., 1] > np.maximum(rgb[..., 0], rgb[..., 2])) & (alpha < 1)
    rgb[..., 1][spill] = np.maximum(rgb[..., 0], rgb[..., 2])[spill]
    rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)
    cols = (alpha > 0.5).any(axis=0)
    runs, start = [], None
    for x, on in enumerate(cols):
        if on and start is None:
            start = x
        if (not on) and start is not None:
            runs.append((start, x))
            start = None
    if start is not None:
        runs.append((start, len(cols)))
    # merge runs closer than 12 px
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < 12:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    if len(merged) != len(SHEET_ORDER):
        sys.exit("expected %d pieces on the sheet, found %d" % (len(SHEET_ORDER), len(merged)))
    pieces = {}
    for name, (x0, x1) in zip(SHEET_ORDER, merged):
        sub = rgba[:, x0:x1]
        ys = np.where((sub[..., 3] > 40).any(axis=1))[0]
        sub = sub[ys.min():ys.max() + 1]
        xs = np.where((sub[..., 3] > 40).any(axis=0))[0]
        pieces[name] = sub[:, xs.min():xs.max() + 1]
    return pieces


def resize_rgba(arr, w, h):
    """Resize with premultiplied alpha (no dark/green fringes)."""
    f = arr.astype(float)
    al = f[..., 3:4] / 255.0
    pre = np.dstack([f[..., :3] * al, f[..., 3:4]])
    im = Image.fromarray(pre.astype(np.float32)[..., 0], mode="F")  # placeholder to keep PIL import honest
    chans = []
    for c in range(4):
        ch = Image.fromarray(pre[..., c].astype(np.float32), mode="F").resize((int(w), int(h)), Image.LANCZOS)
        chans.append(np.asarray(ch))
    pre2 = np.dstack(chans)
    a2 = np.clip(pre2[..., 3:4], 0, 255)
    rgb = np.where(a2 > 0.5, pre2[..., :3] / np.maximum(a2 / 255.0, 1e-3), 0)
    return np.dstack([np.clip(rgb, 0, 255), a2]).astype(np.uint8)


def scale(arr, s):
    h, w = arr.shape[:2]
    return resize_rgba(arr, round(w * s), round(h * s))


def stretch_axis(arr, axis, length, end):
    """Makes a straight piece shorter/longer: keeps `end` px at both ends, re-sizes the middle.
    axis 1 = horizontal piece, axis 0 = vertical piece."""
    n = arr.shape[axis]
    if length == n:
        return arr
    if length < 2 * end + 4:
        raise ValueError("straight piece too short: %d (min %d)" % (length, 2 * end + 4))
    if axis == 1:
        a, mid, b = arr[:, :end], arr[:, end:n - end], arr[:, n - end:]
        mid_len = length - 2 * end
        c0 = max(0, (mid.shape[1] - 8) // 2 - 20)           # a calm slab (the sparkle sits near an end)
        slab = mid[:, c0:c0 + 8]
        mid2 = resize_rgba(slab, mid_len, arr.shape[0])
        return np.concatenate([a, mid2, b], axis=1)
    a, mid, b = arr[:end], arr[end:n - end], arr[n - end:]
    mid_len = length - 2 * end
    c0 = max(0, (mid.shape[0] - 8) // 2 - 20)
    slab = mid[c0:c0 + 8]
    mid2 = resize_rgba(slab, arr.shape[1], mid_len)
    return np.concatenate([a, mid2, b], axis=0)


def rot180(arr):
    return arr[::-1, ::-1]


def shadow_of(arr):
    """Dark silhouette the player sees where a piece belongs."""
    al = arr[..., 3].astype(float) / 255.0
    out = np.zeros(arr.shape, np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = 24, 34, 52
    out[..., 3] = (al * 150).astype(np.uint8)
    # light rim so it reads on the beige wall
    edge = al - np.minimum.reduce([np.roll(al, 1, 0), np.roll(al, -1, 0), np.roll(al, 1, 1), np.roll(al, -1, 1)])
    rim = np.clip(edge * 2.0, 0, 1)
    out[..., 0] = np.where(rim > 0.3, 255, out[..., 0])
    out[..., 1] = np.where(rim > 0.3, 255, out[..., 1])
    out[..., 2] = np.where(rim > 0.3, 255, out[..., 2])
    out[..., 3] = np.maximum(out[..., 3], (rim * 200).astype(np.uint8))
    return out


# ---------------------------------------------------------------- wall picture
def edit_wall(path, p):
    """Shortens the two stubs and moves them: left down, right up.  Everything in source pixels."""
    wall = np.asarray(Image.open(path).convert("RGB")).copy()
    H, W = wall.shape[:2]
    r0, r1 = p["band"]
    mid = p["mid_x"]
    left = wall[r0:r1, :mid].copy()
    right = wall[r0:r1, mid:].copy()
    # erase the old stubs with plain wall rows from above (the wall is flat, only the corner lines run vertically)
    src0 = p["erase_from"]
    wall[r0:r1] = wall[src0:src0 + (r1 - r0)]
    # left stub: cut a slab out of the pipe body; the ring moves left, plain wall fills the right end
    a, b = p["left_slab"]
    ly0 = p["left_y"] - p["stub_y"]
    ry0 = p["right_y"] - p["stub_y"]
    # the wall corner lines are not perfectly vertical: moving a band up/down needs a small sideways correction
    ls = int(round(p["left_slope"] * ly0))
    lpart = left[:, :a]
    if ls < 0:
        lpart = np.concatenate([lpart[:, -ls:], lpart[:, a + ls:a]], axis=1)
    left = np.concatenate([lpart, left[:, b:], left[:, p["left_fill"][0]:p["left_fill"][0] + (b - a)]], axis=1)
    # right stub: cut a slab; the ring moves right, plain wall fills the left end
    a2, b2 = p["right_slab"][0] - mid, p["right_slab"][1] - mid
    fill = right[:, p["right_fill"][0] - mid:p["right_fill"][0] - mid + (b2 - a2)]
    rs = int(round(p["right_slope"] * ry0))
    tail = right[:, b2:]
    if rs < 0:
        tail = np.concatenate([tail[:, -rs:], tail[:, rs:]], axis=1)
    right = np.concatenate([fill, right[:, :a2], tail], axis=1)
    h = r1 - r0
    wall[r0 + ly0:r0 + ly0 + h, :mid] = left
    wall[r0 + ry0:r0 + ry0 + h, mid:] = right
    return wall


# ---------------------------------------------------------------- KITCHEN layout
KITCHEN = {
    "name": "kitchen",
    "title": "Fix the kitchen pipes",
    "S": 1.40,                       # piece scale in source pixels (matches the stub thickness)
    "crop_x": 10,                    # source columns cut on the left so the picture is exactly 16:9
    "wall": {
        "band": (500, 860), "mid_x": 1288, "erase_from": 140, "stub_y": 674,
        "left_slope": -0.0074, "right_slope": 0.0296,
        "left_slab": (400, 560), "left_fill": (1100, 0),
        "right_slab": (1960, 2140), "right_fill": (1300, 0),
        "left_y": 1026, "right_y": 314,
    },
    "left_face": 634,                # x of the left stub opening after editing
    "left_y": 1026,
    "h0": 150, "v": 140, "h1": 176,  # lengths (source px) of the short straight pieces
}


def build(cfg):
    S = cfg["S"]
    pieces = cut_pieces(os.path.join(RAW, "pieces_sheet.jpg"))
    os.makedirs(OUT, exist_ok=True)

    wall = edit_wall(os.path.join(RAW, "kitchen_bg_src.jpg"), cfg["wall"])
    H, W = wall.shape[:2]
    cx = cfg["crop_x"]
    k = 1920.0 / (W - 2 * cx)
    bg = Image.fromarray(wall[:, cx:W - cx]).resize((1920, round((H) * k)), Image.LANCZOS)
    if bg.size[1] != 1080:
        bg = bg.crop((0, 0, 1920, 1080)) if bg.size[1] > 1080 else bg.resize((1920, 1080), Image.LANCZOS)
    bg.save(os.path.join(OUT, cfg["name"] + "_bg.jpg"), quality=93)

    # --- the pieces at scale S (source px)
    h = scale(pieces["h"], S)
    v = scale(pieces["v"], S)
    ea = scale(pieces["elbow_a"], S)
    eb = scale(pieces["elbow_b"], S)
    valve = scale(pieces["valve"], S)
    end = round(64)                  # flange part kept when a straight piece is shortened
    h0 = stretch_axis(h, 1, cfg["h0"], end)
    h1 = stretch_axis(h, 1, cfg["h1"], end)
    vv = stretch_axis(v, 0, cfg["v"], end)
    e1 = rot180(ea)                  # elbow a, native (down,right) -> (up,left): left opening, goes up
    e2 = eb                          # native (down,right): comes from below, leaves to the right

    # port offsets inside each piece image (source px at scale S)
    cy_h = h.shape[0] / 2.0
    ports = {
        "h0": {"L": (0, cy_h), "R": (h0.shape[1], cy_h)},
        "h1": {"L": (0, cy_h), "R": (h1.shape[1], cy_h)},
        "e1": {"L": (0, 206 * S), "U": (191.5 * S, 0)},
        "v": {"U": (72 * S, 0), "D": (72 * S, vv.shape[0])},
        "e2": {"D": (71.5 * S, e2.shape[0]), "R": (e2.shape[1], 69.5 * S)},
        "valve": {"L": (0, 166.5 * S), "R": (valve.shape[1], 167.5 * S)},
    }
    imgs = {"h0": h0, "e1": e1, "v": vv, "e2": e2, "valve": valve, "h1": h1}

    # --- chain them: each piece's entry port sits on the previous exit port
    pos = {}
    px, py = cfg["left_face"], cfg["left_y"]                 # exit of the left stub
    def put(pid, entry, exit_):
        nonlocal px, py
        ex, ey = ports[pid][entry]
        pos[pid] = (px - ex, py - ey)
        xx, yy = ports[pid][exit_]
        px, py = pos[pid][0] + xx, pos[pid][1] + yy
    put("h0", "L", "R")
    put("e1", "L", "U")
    put("v", "D", "U")           # travelling up: enters at the bottom port, leaves at the top
    put("e2", "D", "R")
    put("valve", "L", "R")
    put("h1", "L", "R")
    end_x, end_y = px, py
    want_x = cfg["wall"]["right_slab"][1] - cfg["wall"]["right_slab"][0] + 1767
    print("route ends at x=%.0f y=%.0f ; right stub face at x=%d y=%d" % (end_x, end_y, want_x, cfg["wall"]["right_y"]))

    # --- screen coordinates (1920x1080)
    scr = {}
    layout = []
    order = ["h0", "e1", "v", "e2", "valve", "h1"]
    for pid in order:
        im = imgs[pid]
        w2, h2 = round(im.shape[1] * k), round(im.shape[0] * k)
        small = resize_rgba(im, w2, h2)
        Image.fromarray(small).save(os.path.join(OUT, "%s_%s.png" % (cfg["name"], pid)))
        Image.fromarray(shadow_of(small)).save(os.path.join(OUT, "%s_%s_sh.png" % (cfg["name"], pid)))
        x = round((pos[pid][0] - cx) * k)
        y = round(pos[pid][1] * k)
        scr[pid] = (x, y, w2, h2)
        layout.append({"id": pid, "image": "images/pipes/%s_%s.png" % (cfg["name"], pid),
                       "shadow": "images/pipes/%s_%s_sh.png" % (cfg["name"], pid),
                       "x": x, "y": y, "w": w2, "h": h2})

    # --- tray: shelf packing, right side of the screen
    tray = {"x": 1390, "y": 400, "w": 490, "h": 620, "zoom": 0.62, "gap": 22}
    cursor_x, cursor_y, row_h = 0, 0, 0
    for item in layout:
        tw, th = round(item["w"] * tray["zoom"]), round(item["h"] * tray["zoom"])
        if cursor_x + tw > tray["w"]:
            cursor_x, cursor_y, row_h = 0, cursor_y + row_h + tray["gap"], 0
        item["tray"] = [tray["x"] + cursor_x, tray["y"] + cursor_y]
        cursor_x += tw + tray["gap"]
        row_h = max(row_h, th)
    print("tray needs height", cursor_y + row_h, "of", tray["h"])

    data = {}
    if os.path.exists(DATA):
        data = json.load(open(DATA, encoding="utf-8"))
    data.setdefault("games", {})[cfg["name"]] = {
        "title": cfg["title"], "bg": "images/pipes/%s_bg.jpg" % cfg["name"],
        "tray": {"x": tray["x"], "y": tray["y"], "w": tray["w"], "h": tray["h"], "zoom": tray["zoom"]},
        "pieces": layout,
    }
    json.dump(data, open(DATA, "w", encoding="utf-8"), indent=1)

    # --- previews (scratch, not used by the game)
    solved = bg.convert("RGBA")
    for item in layout:
        solved.alpha_composite(Image.open(os.path.join(ROOT, "game", item["image"])), (item["x"], item["y"]))
    solved.convert("RGB").save(os.path.join(RAW, "preview_solved.jpg"), quality=90)
    start = bg.convert("RGBA")
    for item in layout:
        start.alpha_composite(Image.open(os.path.join(ROOT, "game", item["shadow"])), (item["x"], item["y"]))
        t = Image.open(os.path.join(ROOT, "game", item["image"]))
        t = t.resize((round(t.width * tray["zoom"]), round(t.height * tray["zoom"])), Image.LANCZOS)
        start.alpha_composite(t, tuple(item["tray"]))
    start.convert("RGB").save(os.path.join(RAW, "preview_start.jpg"), quality=90)
    return data


if __name__ == "__main__":
    build(KITCHEN)
    print("done: pictures in", OUT, "and layout in", DATA)
