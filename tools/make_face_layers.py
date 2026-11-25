"""Face layers: eyes and mouth patches cut from the full expression pictures of a pose.

Why: every full expression picture is re-drawn by the image generator, so the head, jaw and hair
lines drift by a few pixels between pictures. Cross-fading whole pictures makes the face "wobble".
Here only the eyes and the mouth change: each patch is aligned to the neutral picture, colour
matched and feathered, and the game puts it on top of the neutral picture.

Input  (1600x2160, from make_cook_camera.py): game/images/camera/<pose>_{neutral,smile,shy,closed}.png
Output: game/images/camera/<pose>_<eyes|mouth>_<expr>.png and game/face_layers.py (positions).
Run from the project root:  python tools/make_face_layers.py [cook]
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

CAM = "game/images/camera"
# regions in the 1600x2160 picture: (x0, y0, x1, y1)
POSES = {
    "cook": {
        "regions": {"eyes": (765, 300, 985, 430), "mouth": (815, 462, 950, 545)},
        "exprs": {"eyes": ["closed", "smile", "shy"], "mouth": ["smile", "shy"]},
    },
    "eat": {
        "regions": {"eyes": (740, 310, 960, 430), "mouth": (800, 465, 940, 548)},
        "exprs": {"eyes": ["closed", "smile"], "mouth": ["smile"]},
    },
}
FEATHER = 12
PAD = 40


def load(pose, name):
    return np.asarray(Image.open("%s/%s_%s.png" % (CAM, pose, name)).convert("RGBA"))


def gray(a):
    rgb = a[..., :3].astype(np.float32) * (a[..., 3:] / 255.0) + 128 * (1 - a[..., 3:] / 255.0)
    return cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY)


def _ecc(gb, go, box, margin):
    """Affine transform that puts the surroundings of the box of picture 'go' onto 'gb'."""
    x0, y0, x1, y1 = box
    h, w = gb.shape
    X0, Y0, X1, Y1 = max(0, x0 - margin), max(0, y0 - margin), min(w, x1 + margin), min(h, y1 + margin)
    t = cv2.GaussianBlur(gb[Y0:Y1, X0:X1], (0, 0), 1.5).astype(np.float32)
    s = cv2.GaussianBlur(go[Y0:Y1, X0:X1], (0, 0), 1.5).astype(np.float32)
    m = np.full(t.shape, 255, np.uint8)
    m[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = 0          # ignore the box itself: only the surroundings
    A = np.eye(2, 3, dtype=np.float32)
    _, A = cv2.findTransformECC(t, s, A, cv2.MOTION_AFFINE,
                                (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), m, 5)
    T = np.array([[1, 0, X0], [0, 1, Y0], [0, 0, 1]], np.float32)
    return (T @ np.vstack([A, [0, 0, 1]]) @ np.linalg.inv(T))[:2]


def align(gb, go, box, margin=45):
    """Try a small surrounding first; on flat skin (little texture) widen it; as a last resort no shift."""
    for mg in (margin, 70, 100, 140, 200):
        try:
            return _ecc(gb, go, box, mg)
        except cv2.error:
            continue
    print("   warning: could not align this patch, using no shift (check the box position)")
    return np.eye(2, 3, dtype=np.float32)


def global_align(base, expr_img):
    """The generator may re-frame an expression picture (shifted / slightly scaled). Register the whole picture
    onto the neutral one first (coarse to fine), so the local patch alignment starts from a good guess."""
    gb, go = gray(base), gray(expr_img)
    A = np.eye(2, 3, dtype=np.float32)
    for sc in (1 / 8, 1 / 4, 1 / 2):
        t = cv2.GaussianBlur(cv2.resize(gb, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA), (0, 0), 2).astype(np.float32)
        s_ = cv2.GaussianBlur(cv2.resize(go, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA), (0, 0), 2).astype(np.float32)
        Ai = A.copy()
        Ai[:, 2] *= sc
        try:
            _, Ai = cv2.findTransformECC(t, s_, Ai, cv2.MOTION_AFFINE,
                                         (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
            A = Ai.copy()
            A[:, 2] /= sc
        except cv2.error:
            pass
    h, w = base.shape[:2]
    moved = abs(A[0, 2]) + abs(A[1, 2]) + 100 * (abs(A[0, 0] - 1) + abs(A[1, 1] - 1) + abs(A[0, 1]) + abs(A[1, 0]))
    if moved < 1.0:
        return expr_img
    print("   registered picture onto the neutral one: shift (%.1f, %.1f) px, scale (%.3f, %.3f)" % (A[0, 2], A[1, 2], A[0, 0], A[1, 1]))
    return cv2.warpAffine(expr_img, A, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def make_patch(base, expr_img, box):
    h, w = base.shape[:2]
    gb, go = gray(base), gray(expr_img)
    M = align(gb, go, box)
    warped = cv2.warpAffine(expr_img, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                            borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    x0, y0, x1, y1 = box
    m = np.zeros((h, w), np.float32)
    m[y0:y1, x0:x1] = 1
    m = cv2.GaussianBlur(m, (0, 0), FEATHER)
    # colour match on the border zone of the box, fading out toward its centre
    inner = np.zeros((h, w), np.uint8)
    inner[y0 + 22:y1 - 22, x0 + 22:x1 - 22] = 1
    outer = np.zeros((h, w), np.uint8)
    outer[y0 + 6:y1 - 6, x0 + 6:x1 - 6] = 1
    zone = (outer - inner) > 0
    off = (base[..., :3][zone].astype(np.float32) - warped[..., :3][zone]).mean(0)
    edge = 1 - cv2.GaussianBlur(inner.astype(np.float32), (0, 0), 10)
    warped[..., :3] += off[None, None, :] * edge[..., None]
    alpha = m * (warped[..., 3] / 255.0)
    out = np.dstack([warped[..., :3].clip(0, 255), alpha * 255]).astype(np.uint8)
    bx0, by0, bx1, by1 = max(0, x0 - PAD), max(0, y0 - PAD), min(w, x1 + PAD), min(h, y1 + PAD)
    return out[by0:by1, bx0:bx1], (bx0, by0)


def run(pose):
    cfg = POSES[pose]
    base = load(pose, "neutral")
    layers = {}
    for kind, box in cfg["regions"].items():
        layers[kind] = {}
        for expr in cfg["exprs"][kind]:
            patch, (px, py) = make_patch(base, global_align(base, load(pose, expr)), box)
            path = "images/camera/%s_%s_%s.png" % (pose, kind, expr)
            Image.fromarray(patch).save("game/" + path, optimize=True)
            layers[kind][expr] = (px, py, path)
            print(pose, kind, expr, "at", (px, py), patch.shape[1], "x", patch.shape[0])
    return layers


if __name__ == "__main__":
    names = sys.argv[1:] or list(POSES)
    allv = {}
    if os.path.exists("game/face_layers.py"):
        ns = {}
        exec(open("game/face_layers.py", encoding="utf-8").read(), ns)
        allv = ns.get("LAYERS", {})
    for n in names:
        allv[n] = run(n)
    with open("game/face_layers.py", "w", encoding="utf-8") as f:
        f.write("# Generated by tools/make_face_layers.py - do not edit.\n"
                "# LAYERS[pose][eyes|mouth][expression] = (x, y, path) in the 1600x2160 pose picture.\n")
        f.write("LAYERS = " + json.dumps(allv, indent=1, sort_keys=True).replace("[", "(").replace("]", ")") + "\n")
