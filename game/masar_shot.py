# -*- coding: utf-8 -*-
"""Masar: what is in a photo?  (pure Python, testable outside Ren'Py)

The free camera gives us the rectangle the lens shows (the "view", in world pixels, 1920x1080).  From it we work out
  * in a room: which named subjects (see SUBJECTS in masar_phone.py) are in the frame and how well they are framed,
  * with Ana in the frame: what part of her was photographed (face, upper body, lower body, feet, hands, full body,
    an object she holds) and what her face was doing at that instant (neutral, smiling, shy, eyes closed).

HOW TO ADJUST (no other code needed)
  * ANA_REGIONS: the rectangles of Ana's body parts for each photo scene, in the 800x1080 picture of that scene.
    They live in game/data/ana_regions.json: edit them with  python tools/masar_editor.py  (tab "Ana boxes").
  * DETECT_COVER / DETECT_SHARE: how much of a subject must be in the frame to count as photographed.
  * TYPE_COVER / TYPE_SHARE: the same for the parts of Ana.
"""
import masar_photo as mp
import masar_phone as mph

ASPECT = mp.WIN_W / float(mp.WIN_H)          # the lens window is wider than tall
FULL_W = mp.WIN_W / mp.BASE                  # world width visible at zoom 1
FULL_H = mp.WIN_H / mp.BASE                  # world height visible at zoom 1
ZMAX_ROOM = 3.4                              # how far the camera may zoom in a room without Ana
ZMAX_ANA = 2.6                               # ... and with Ana (her pictures are sharper)

VIEW_MARGIN = 1.10                           # the ideal frame leaves 10% around a subject
DETECT_COVER = 0.55                          # a subject counts if this much of it is in the frame ...
DETECT_SHARE = 0.10                          # ... and fills at least this much of the frame
ANA_MIN_SHARE = 0.05                         # Ana is "in the photo" if she fills at least this much of the frame
FULL_COVER = 0.80                            # whole figure in the frame = full body ...
FULL_SHARE = 0.18                            # ... if she is also big enough (else: wide shot)
TYPE_COVER = 0.50                            # a body part counts if this much of it is in the frame ...
TYPE_SHARE = 0.06                            # ... and it fills at least this much of the frame
OBJECT_SHARE = 0.03                          # (small things she holds need less: the zoom is limited)
FACE_COVER = 0.60                            # the face is "visible" (expression recorded) above this

EXPR_LABELS = {"neutral": "Neutral", "smile": "Smiling", "shy": "Shy"}
TYPE_LABELS = {"face": "Face", "upper": "Upper body", "lower": "Lower body", "feet": "Feet", "hands": "Hands",
               "full": "Full body", "wide": "Wide shot", "object": "Object", "detail": "Body detail"}
# gallery groups for Ana's photos (see FILTERS_ANA in masar_phone.py)
TYPE_GROUP = {"face": "face", "upper": "upper", "lower": "lower", "feet": "feet", "hands": "hands",
              "full": "full", "wide": "other", "object": "other", "detail": "other"}

# ---------------------------------------------------------------------------------------------------
#  Ana's body parts in each photo scene.  Rectangles (x, y, w, h) in the 800x1080 picture of the scene.
#  figure = the whole of her (and what she holds); the other parts are lists of rectangles.
#  objects = [(name, rectangle)]: things she holds or uses.
# ---------------------------------------------------------------------------------------------------
def _load_regions():
    """game/data/ana_regions.json -> {scene id: {figure, face, torso, legs, feet, hands, objects}} (tuples)."""
    import masar_data
    out = {}
    for sid, r in masar_data.load("ana_regions")["scenes"].items():
        out[sid] = {"figure": tuple(r["figure"]),
                    "face": [tuple(x) for x in r.get("face", [])],
                    "torso": [tuple(x) for x in r.get("torso", [])],
                    "legs": [tuple(x) for x in r.get("legs", [])],
                    "feet": [tuple(x) for x in r.get("feet", [])],
                    "hands": [tuple(x) for x in r.get("hands", [])],
                    "objects": [(o["name"], tuple(o["box"])) for o in r.get("objects", [])]}
    return out


ANA_REGIONS = _load_regions()


# A scene without boxes in ana_regions.json (a new pose you added) gets these rough proportions of its 800x1080 picture,
# so the camera still works.  Draw its boxes in the editor to make it exact.
DEFAULT_REGIONS = {
    "figure": (0, 0, 800, 1080),
    "face": [(250, 40, 300, 250)],
    "torso": [(100, 250, 600, 350)],
    "legs": [(100, 600, 600, 350)],
    "feet": [(100, 950, 600, 130)],
    "hands": [],
    "objects": [],
}


def regions_for(scene_id):
    return ANA_REGIONS.get(scene_id, DEFAULT_REGIONS)


# ---------------------------------------------------------------------------------------------------
#  Geometry
# ---------------------------------------------------------------------------------------------------
def view_rect(cx, cy, z):
    """The world rectangle the lens shows when its centre is at (cx, cy) with zoom z."""
    w = mp.WIN_W / (mp.BASE * z)
    h = mp.WIN_H / (mp.BASE * z)
    return (cx - w / 2.0, cy - h / 2.0, w, h)


def area(r):
    return max(0.0, r[2]) * max(0.0, r[3])


def inter_area(a, b):
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    return ix * iy


def ideal_rect(target, zmax=ZMAX_ROOM):
    """The best frame for a subject: it fills the lens with a little room around it (as far as the zoom allows)."""
    tx, ty, tw, th = target
    w = max(tw * VIEW_MARGIN, th * VIEW_MARGIN * ASPECT)
    z = max(1.0, min(zmax, FULL_W / w))
    w, h = FULL_W / z, FULL_H / z
    x = max(0.0, min(mp.WORLD_W - w, tx + tw / 2.0 - w / 2.0))
    y = max(0.0, min(mp.WORLD_H - h, ty + th / 2.0 - h / 2.0))
    return (x, y, w, h)


def sharpness(steady):
    """0..100 from the camera steadiness (hand shake)."""
    return int(round(100.0 * (0.45 + 0.55 * max(0.0, min(1.0, steady)))))


# ---------------------------------------------------------------------------------------------------
#  Rooms: which subjects are in the frame
# ---------------------------------------------------------------------------------------------------
def detect_subjects(place, room, view, steady, zmax=ZMAX_ROOM):
    """{subject id: match 0..100} for every subject of this room that is in the frame."""
    found = {}
    va = area(view)
    for sid in mph.subjects_here(place, room):
        t = mph.crop_px(sid, mp.WORLD_W, mp.WORLD_H)      # boxes are fractions of the room picture (the whole panorama)
        ia = inter_area(view, t)
        if area(t) <= 0 or va <= 0:
            continue
        # a tiny subject (a squirrel high in a tree) can never fill 10% of even the tightest frame: it needs less
        need = min(DETECT_SHARE, 0.5 * area(t) / ((FULL_W / zmax) * (FULL_H / zmax)))
        if ia / area(t) >= DETECT_COVER and ia / va >= need:
            q = mp.framing_quality(view, ideal_rect(t, zmax))
            found[sid] = int(round(100.0 * q * (0.6 + 0.4 * max(0.0, min(1.0, steady)))))
    return found


def analyze_room(place, room, view, steady, zmax=ZMAX_ROOM):
    found = detect_subjects(place, room, view, steady, zmax)
    sharp = sharpness(steady)
    if found:
        primary = max(found, key=lambda s: found[s])
        props = [("Subject", mph.subject_label(primary)), ("Match", "%d%%" % found[primary]),
                 ("Sharpness", "%d%%" % sharp)]
        others = [mph.subject_label(s) for s in found if s != primary]
        if others:
            props.append(("Also in the frame", ", ".join(others)))
        return {"kind": "room", "subject": primary, "matches": found, "score": found[primary],
                "shot_type": "", "layers": [], "props": props, "sharp": sharp}
    return {"kind": "room", "subject": "random", "matches": {}, "score": sharp, "shot_type": "", "layers": [],
            "props": [("Subject", "Random shot"), ("Sharpness", "%d%%" % sharp)], "sharp": sharp}


# ---------------------------------------------------------------------------------------------------
#  Ana: what part of her is in the frame
# ---------------------------------------------------------------------------------------------------
def picture_view(view, ax):
    """The view rectangle in the coordinates of Ana's 800x1080 picture."""
    left = mp.ana_left(ax)
    return ((view[0] - left) / mp.VK, (view[1] - mp.ANA_TOP) / mp.VK, view[2] / mp.VK, view[3] / mp.VK)


def ana_in_frame(scene_id, ax, view):
    reg = regions_for(scene_id)
    v = picture_view(view, ax)
    return inter_area(v, reg["figure"]) / max(1.0, area(v)) >= ANA_MIN_SHARE


def classify_ana(scene_id, ax, view):
    """What did the photo show of Ana?  {"type": key, "object": name or "", "face": bool}  (None: she is not in it)."""
    reg = regions_for(scene_id)
    v = picture_view(view, ax)
    va = max(1.0, area(v))
    fig = reg["figure"]
    sh_fig = inter_area(v, fig) / va
    if sh_fig < ANA_MIN_SHARE:
        return None
    cov_fig = inter_area(v, fig) / max(1.0, area(fig))
    # is her face in the frame?  (for the expression)
    face_cov = max([inter_area(v, r) / max(1.0, area(r)) for r in reg["face"]] or [0.0])
    torso_cov = max([inter_area(v, r) / max(1.0, area(r)) for r in reg["torso"]] or [0.0])
    face_vis = any(inter_area(v, r) / max(1.0, area(r)) >= FACE_COVER and inter_area(v, r) / va >= 0.05
                   for r in reg["face"])
    if cov_fig >= FULL_COVER:
        return {"type": "full" if sh_fig >= FULL_SHARE else "wide", "object": "", "face": face_vis,
                "face_cov": face_cov, "torso_cov": torso_cov}
    # candidates: parts that are mostly in the frame; the one under the middle of the frame wins (smallest first)
    vcx, vcy = v[0] + v[2] / 2.0, v[1] + v[3] / 2.0
    cands = []             # (centre inside?, distance, area, type, object name)
    parts = [(k, "", r, TYPE_SHARE) for k, rects in (("face", reg["face"]), ("upper", reg["torso"]),
                                                   ("lower", reg["legs"]), ("feet", reg["feet"]),
                                                   ("hands", reg["hands"])) for r in rects]
    parts += [("object", n, r, OBJECT_SHARE) for n, r in reg["objects"]]
    for key, name, r, min_share in parts:
        ia = inter_area(v, r)
        if ia / max(1.0, area(r)) >= TYPE_COVER and ia / va >= min_share:
            inside = r[0] <= vcx <= r[0] + r[2] and r[1] <= vcy <= r[1] + r[3]
            dist = ((r[0] + r[2] / 2.0 - vcx) ** 2 + (r[1] + r[3] / 2.0 - vcy) ** 2) ** 0.5
            cands.append((0 if inside else 1, area(r) if inside else dist, key, name))
    best = min(cands) if cands else None
    if best is None:
        return {"type": "detail", "object": "", "face": face_vis, "face_cov": face_cov, "torso_cov": torso_cov}
    return {"type": best[2], "object": best[3], "face": face_vis, "face_cov": face_cov, "torso_cov": torso_cov}


def face_state(shot, t):
    """What her face is doing at time t of her loop: (key, label)."""
    if mp.blink_weight(t, shot["bl"]) > 0.5:
        return "closed", "Eyes closed"
    w = mp.expr_weights(t, shot["tl"])
    key = max(w, key=lambda k: w[k])
    return key, EXPR_LABELS.get(key, key.title())


# ---------------------------------------------------------------------------------------------------
#  Influencer rating (1..10) of a photo of Ana: how good it is as a post.  First version - tune the numbers freely.
#  base = what the photo is about; then the camera work adds or takes away points; each type has a ceiling.
# ---------------------------------------------------------------------------------------------------
RATING_BASE = {"face": 7, "upper": 7, "full": 7, "wide": 5, "lower": 4, "feet": 4, "object": 3, "hands": 1, "detail": 1}
RATING_MAX = {"face": 10, "upper": 10, "full": 9, "wide": 6, "lower": 5, "feet": 5, "object": 4, "hands": 1, "detail": 1}


def influencer_rating(cls, sharp, expr, portrait):
    """cls = classify_ana result, sharp = 0..100, expr = face key ("", neutral, smile, shy, closed), portrait = bool."""
    t = cls["type"]
    r = RATING_BASE[t]
    if t == "face" and cls.get("torso_cov", 0.0) >= 0.15:
        r += 1                                   # face with the shoulders: a proper portrait
    if t == "upper" and not cls["face"]:
        r -= 3                                   # a body without a face
    if sharp < 55:
        r -= 2
    elif sharp < 85:
        r -= 1
    if cls["face"] and t in ("face", "upper", "full", "wide"):
        if expr in ("smile", "shy"):
            r += 1
        elif expr == "closed":
            r -= 2
        if cls.get("face_cov", 1.0) < 0.9 and t in ("face", "upper"):
            r -= 1                               # the face is cut by the edge of the frame
    if portrait and t in ("face", "upper"):
        r += 1
    return max(1, min(RATING_MAX[t], r))


def analyze_ana(scene_id, ax, shot, view, t, steady, bgb):
    cls = classify_ana(scene_id, ax, view)
    if cls is None:
        return None
    sc = mp.SCENES[scene_id]
    sharp = sharpness(steady)
    type_label = TYPE_LABELS[cls["type"]]
    if cls["object"]:
        type_label = "%s: %s" % (type_label, cls["object"])
    quality = sharp
    if cls["face"]:
        key, expr_label = face_state(shot, t)
        if key == "closed":
            quality = int(round(sharp * 0.4))
    else:
        key, expr_label = "", "Face not visible"
    portrait = bgb >= 0.7
    rating = influencer_rating(cls, sharp, key, portrait)
    props = [("Influencer rating", "%d / 10" % rating), ("Subject", "Ana"), ("Activity", sc["title"]),
             ("Shot type", type_label), ("Expression", expr_label),
             ("Style", "Portrait (blurred background)" if portrait else "Standard"), ("Sharpness", "%d%%" % sharp)]
    layers = [(p, int(round(x)), int(round(y)), round(a, 3)) for p, x, y, a in mp.layer_draws(shot, t)]
    return {"kind": "ana", "subject": "ana", "matches": {}, "score": quality, "shot_type": TYPE_GROUP[cls["type"]],
            "type_label": type_label, "expression": key, "rating": rating, "layers": layers, "props": props, "sharp": sharp}


def analyze(place, room, ana_ctx, t, cx, cy, z, steady, bgb):
    """Everything about a photo taken with the lens centred on (cx, cy) at zoom z at time t of Ana's loop.
    ana_ctx = {"scene": scene id, "ax": x, "shot": timeline dict} when Ana is in the room, else None."""
    view = view_rect(cx, cy, z)
    res = None
    if ana_ctx:
        res = analyze_ana(ana_ctx["scene"], ana_ctx["ax"], ana_ctx["shot"], view, t, steady, bgb)
    if res is None:
        res = analyze_room(place, room, view, steady, ZMAX_ANA if ana_ctx else ZMAX_ROOM)
    res["view"] = tuple(int(round(v)) for v in view)
    res["place"] = place
    res["room"] = room
    return res
