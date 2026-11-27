"""Checks for the pipe mini-game rules and data.  Run from the project root:  python tools/test_pipes.py"""
import os
import sys

ROOT = os.getcwd()
if os.path.basename(ROOT) == "tools":
    ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "game"))

import masar_pipes as mp

fails = []


def check(label, ok):
    print(("ok    " if ok else "FAIL  ") + label)
    if not ok:
        fails.append(label)


spec = mp.load_game("kitchen", reload=True)
check("kitchen puzzle exists", bool(spec))
pieces = spec["pieces"]
check("has pieces", len(pieces) >= 4)
check("piece ids are unique", len(set(p["id"] for p in pieces)) == len(pieces))
check("pictures exist", all(os.path.exists(os.path.join(ROOT, "game", p[k])) for p in pieces for k in ("image", "shadow"))
      and os.path.exists(os.path.join(ROOT, "game", spec["bg"])))
check("slots are on the screen", all(0 <= p["x"] and p["x"] + p["w"] <= 1920 and 0 <= p["y"] and p["y"] + p["h"] <= 1080 for p in pieces))
t = spec["tray"]
z = t["zoom"]
check("tray places are inside the tray", all(t["x"] <= p["tray"][0] and p["tray"][0] + p["w"] * z <= t["x"] + t["w"] + 1
                                             and t["y"] <= p["tray"][1] and p["tray"][1] + p["h"] * z <= t["y"] + t["h"] for p in pieces))
check("missing puzzle is None", mp.load_game("nope") is None)

g = mp.PipeGame("kitchen")
ids = g.ids()
check("not done at the start", not g.done and g.progress() == (0, len(ids)))
check("clicking a shadow without a piece does nothing", g.click_slot(ids[0]) == "none" and g.placed == [])
check("select a loose piece", g.select(ids[0]) and g.selected == ids[0])
check("wrong shadow does not stick", g.click_slot(ids[1]) == "wrong" and g.placed == [] and g.flash == ids[1] and g.selected == ids[0])
check("no hint after one miss", g.hint_slot() is None)
g.click_slot(ids[2])
g.click_slot(ids[3] if len(ids) > 3 else ids[1])
check("hint after three misses in a row", g.hint_slot() == ids[0])
check("right shadow snaps in", g.click_slot(ids[0]) == "ok" and g.placed == [ids[0]] and g.selected is None and g.streak == 0)
check("a placed piece cannot be selected again", not g.select(ids[0]))
check("a filled shadow answers 'filled'", g.click_slot(ids[0]) == "filled")

# leave and come back: a new game with the saved ids continues
g2 = mp.PipeGame("kitchen", list(g.placed))
check("progress is restored", g2.placed == [ids[0]] and not g2.done)
for i in ids[1:]:
    g2.select(i)
    assert g2.click_slot(i) == "ok"
check("done when every piece is in place", g2.done and g2.remaining() == [])

import pickle
check("state pickles (saved games)", pickle.loads(pickle.dumps(g2)).placed == g2.placed)

print("\n%d failure(s)" % len(fails))
sys.exit(1 if fails else 0)
