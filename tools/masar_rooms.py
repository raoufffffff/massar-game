# -*- coding: utf-8 -*-
"""Room pictures for the editor: size, panorama info, start view, shifting rectangles, safety checks.

A room picture is game/images/bg/<place>_<room>.jpg (.png / .jpeg / .webp are accepted too).
The game fits its HEIGHT to 1080; a picture wider than 16:9 becomes a PANORAMA whose width (in world pixels) is
    width = picture width * 1080 / picture height.
The player sees 1920 world pixels at a time.  Rectangles of subjects are stored as FRACTIONS of the whole picture.
Per-room settings are in game/data/rooms.json:  {"version": 1, "rooms": {"park/lake": {"start": 0.5}}}
(start = where the view begins when the player enters: 0 = far left ... 1 = far right).
"""
import os

EXTS = ("jpg", "png", "jpeg", "webp")        # same list as masar_core.BG_EXTS
BASE_W = 1920
WORLD_H = 1080
RECOMMENDED = (1920, 2880, 3840, 4800)       # comfortable widths (1x, 1.5x, 2x, 2.5x of the screen)
BIG_PICTURE = 6000                           # wider than this may not load on old graphics cards
# camera limits (same numbers as game/masar_shot.py): the widest/tallest thing the lens can frame at all
LENS_W = 1260.0 / (820.0 / 1080.0)           # world width seen at zoom 1
ZMAX = 3.4                                   # most the camera zooms in a room
FRAME_MARGIN = 1.10                          # the ideal frame leaves 10% around a subject
MIN_SIDE = 24                                # a subject rectangle smaller than this (world px) is hopeless


TIME_KEYS = ("morning", "afternoon", "evening", "night")        # same as masar_core.TIME_KEYS (slots 0..3)
TIME_LABELS = ("Morning", "Afternoon", "Evening", "Night")
TIME_ALIASES = {"morning": (), "afternoon": ("noon", "midday", "day"), "evening": ("dusk", "sunset"), "night": ()}


def reserved_stems(pid, rid, room_ids):
    """Plain picture names of the OTHER rooms of this place (a room 'combat_night' is not the night of 'combat')."""
    return set("%s_%s" % (pid, r) for r in room_ids) - set(["%s_%s" % (pid, rid)])


def _find_stem(game_dir, stem):
    for ext in EXTS:
        p = os.path.join(game_dir, "images", "bg", "%s.%s" % (stem, ext))
        if os.path.exists(p):
            return p
    return None


def time_files(game_dir, pid, rid, room_ids=()):
    """{0: path, ...}: the picture of each time slot that has its OWN picture (morning .. night)."""
    res = reserved_stems(pid, rid, room_ids)
    out = {}
    for i, k in enumerate(TIME_KEYS):
        for name in (k,) + TIME_ALIASES[k]:
            st = "%s_%s_%s" % (pid, rid, name)
            if st in res:
                continue
            p = _find_stem(game_dir, st)
            if p:
                out[i] = p
                break
    return out


def find_bg(game_dir, pid, rid, part=None, room_ids=()):
    """Path of the room picture, or None.  part = a time slot 0..3: that time's picture, else the plain picture, else the
    nearest time that has one (the same order the game uses).  part None = the plain picture, else the first time found."""
    own = time_files(game_dir, pid, rid, room_ids)
    plain = _find_stem(game_dir, "%s_%s" % (pid, rid))
    if part is not None and part in own:
        return own[part]
    if plain:
        return plain
    if own:
        if part is None:
            return own[min(own)]
        return own[min(own, key=lambda i: (abs(i - part), i))]
    return None


def size_problems(game_dir, pid, rid, room_ids=()):
    """Notes when the pictures of one room (plain + times) are not all the same size."""
    files = []
    plain = _find_stem(game_dir, "%s_%s" % (pid, rid))
    if plain:
        files.append(("plain", plain))
    for i, p in sorted(time_files(game_dir, pid, rid, room_ids).items()):
        files.append((TIME_KEYS[i], p))
    sizes = {}
    for name, p in files:
        try:
            sizes[name] = picture_size(p)
        except Exception:
            pass
    if len(set(sizes.values())) > 1:
        return ("its pictures have different sizes (%s): keep every time of one room at the SAME size or the subject rectangles "
                "and Ana's places will not line up." % ", ".join("%s %dx%d" % (n, s[0], s[1]) for n, s in sizes.items()))
    return None


def missing_times(game_dir, pid, rid, room_ids=()):
    """Names of the times that fall back to another picture (empty if all four have their own)."""
    own = time_files(game_dir, pid, rid, room_ids)
    return [TIME_LABELS[i] for i in range(4) if i not in own]


def name_clash(pid, rid, room_ids=()):
    """A note when a room id ends with a time word (it can be confused with a time picture of a shorter room name)."""
    for k in TIME_KEYS + tuple(a for v in TIME_ALIASES.values() for a in v):
        if rid.endswith("_" + k):
            short = rid[:-len(k) - 1]
            if short in room_ids:
                return ("the rooms '%s' and '%s' clash: '%s_%s_%s' would be the %s picture of '%s' AND the plain picture of '%s'. "
                        "Rename one of the rooms." % (short, rid, pid, short, k, k, short, rid))
            return None
    return None


_size_cache = {}


def picture_size(path):
    """(width, height) in pixels of a picture file, cached by modification time."""
    key = (path, os.path.getmtime(path))
    if key not in _size_cache:
        from PIL import Image
        with Image.open(path) as im:
            _size_cache[key] = im.size
    return _size_cache[key]


def world_width(iw, ih):
    """Width of the room world for a picture of iw x ih pixels (1920 unless it is wider than 16:9)."""
    ww = int(round(iw * float(WORLD_H) / max(1, ih)))
    return ww if ww > BASE_W + 20 else BASE_W


def info(game_dir, pid, rid, part=None, room_ids=()):
    """Facts about one room picture: {path, size, W, pano, visible, ratio, stretched} (path None if missing)."""
    path = find_bg(game_dir, pid, rid, part, room_ids)
    if path is None:
        return {"path": None, "size": None, "W": BASE_W, "pano": False, "visible": 100, "ratio": 16 / 9.0, "stretched": False}
    iw, ih = picture_size(path)
    W = world_width(iw, ih)
    ratio = iw / float(max(1, ih))
    return {"path": path, "size": (iw, ih), "W": W, "pano": W > BASE_W, "visible": int(round(100.0 * BASE_W / W)),
            "ratio": ratio, "stretched": W == BASE_W and abs(ratio - 16 / 9.0) > 0.03}


def start_px(W, start):
    """World x where the view starts (left edge of the 1920 wide window)."""
    return int((W - BASE_W) * max(0.0, min(1.0, start))) if W > BASE_W else 0


def get_start(rooms_data, pid, rid):
    try:
        return max(0.0, min(1.0, float(rooms_data.get("rooms", {}).get("%s/%s" % (pid, rid), {}).get("start", 0.5))))
    except (TypeError, ValueError):
        return 0.5


def set_start(rooms_data, pid, rid, start):
    rooms_data.setdefault("version", 1)
    r = rooms_data.setdefault("rooms", {}).setdefault("%s/%s" % (pid, rid), {})
    r["start"] = round(max(0.0, min(1.0, float(start))), 3)


def width_note(i):
    """A note (or None) about a room picture's size."""
    if i["path"] is None:
        return None
    iw, ih = i["size"]
    if i["stretched"]:
        return ("the picture is %dx%d (not 16:9): the game will STRETCH it to 16:9. Use 16:9 or a wider panorama." % (iw, ih))
    if i["W"] > BIG_PICTURE:
        return ("the panorama is %d world pixels wide (%dx%d picture): very wide pictures can fail on older graphics cards; "
                "%d is a comfortable maximum." % (i["W"], iw, ih, BIG_PICTURE))
    if i["pano"] and i["W"] not in RECOMMENDED:
        return ("panorama %dx%d (player sees %d%% at a time). Comfortable widths are %s; any width works, this is only a hint."
                % (iw, ih, i["visible"], ", ".join(str(w) for w in RECOMMENDED)))
    return None


# ----------------------------------------------------------------------------------------- subjects: safety checks
def box_px(box, W):
    return box[2] * W, box[3] * WORLD_H


DETECT_COVER = 0.55                          # same as game/masar_shot.py: this much of a subject must be in the frame


def max_cover(box, W):
    """The largest share of a subject rectangle the lens can have in its frame at once (the camera's widest view)."""
    bw, bh = max(1.0, box[2] * W), max(1.0, box[3] * WORLD_H)
    return min(1.0, LENS_W / bw) * min(1.0, WORLD_H / bh)


def box_problems(label, box, W):
    """[(kind, text)] about one subject rectangle in a room of world width W."""
    out = []
    bw, bh = box_px(box, W)
    if bw < MIN_SIDE or bh < MIN_SIDE:
        out.append(("warn", "Subject '%s': the rectangle is tiny (%dx%d px): the player will hardly be able to frame it. Draw it a bit larger." % (label, bw, bh)))
    cov = max_cover(box, W)
    if cov < DETECT_COVER * 1.05:
        out.append(("error", "Subject '%s': the rectangle (%dx%d px) is too big: even zoomed out the lens covers only %d%% of it, and %d%% is needed, "
                    "so it can never be photographed. Make it smaller (the lens sees about %dx%d px at most)."
                    % (label, bw, bh, cov * 100, DETECT_COVER * 100, LENS_W, WORLD_H)))
    elif cov < 0.8:
        out.append(("warn", "Subject '%s': the rectangle (%dx%d px) is nearly as big as the lens can see, so it is awkward to frame. Consider making it smaller." % (label, bw, bh)))
    return out


# ----------------------------------------------------------------------------------------- shifting rectangles
def shift_subjects(snap, pid, rid, dx, old_w, new_w):
    """Move the rectangles of this room by dx WORLD pixels (positive = right) after its picture changed.
    old_w / new_w = world widths before / after (boxes are fractions of the whole picture). Returns {sid: old box}."""
    undo = {}
    for r in snap.get("rooms", []):
        if r["place"] == pid and r["room"] == rid:
            for sid in r["subjects"]:
                b = snap["subjects"].get(sid, {}).get("box")
                if not b:
                    continue
                undo[sid] = list(b)
                x = (b[0] * old_w + dx) / float(new_w)
                w = b[2] * old_w / float(new_w)
                x = max(0.0, min(1.0 - 0.001, x))
                w = max(0.001, min(1.0 - x, w))
                snap["subjects"][sid]["box"] = [round(x, 4), b[1], round(w, 4), b[3]]
    return undo


def shift_schedule(sched, pid, rid, dx):
    """Move Ana's own placements (entries with 'at') in this room by dx world pixels. Returns how many moved."""
    n = 0
    for c in sched.get("characters", {}).values():
        for e in c.get("entries", []):
            if e.get("place") == pid and e.get("room") == rid and e.get("at"):
                e["at"]["x"] = int(e["at"]["x"] + dx)
                n += 1
    return n
