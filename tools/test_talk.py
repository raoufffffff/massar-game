# -*- coding: utf-8 -*-
"""Checks for the talk game and its ledger rules.  Run from the project root:  python tools/test_talk.py"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "tools" else HERE
sys.path.insert(0, os.path.join(ROOT, "game"))

import masar_story as ms   # noqa: E402
import masar_talk as mt    # noqa: E402

fails = []


def check(name, cond):
    print(("ok    " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)


def play(s, plan):
    """plan = list of 'w' (right) / 'f' (wrong key) / 't' (timeout), one per moment."""
    out = []
    for p in plan:
        if s.finished:
            break
        if p == "w":
            for a in list(s.seq):
                s.press(a)
        elif p == "f":
            s.press([a for a in mt.ARROWS if a != s.seq[0]][0])
        else:
            s.timeout()
        out.append(s.round_res)
        s.next_round()
    return out


s = mt.TalkSession("ana", 1, rng=random.Random(1))
check("3 moments, 2 wins needed", s.rounds == 3 and s.need == 2)
check("first moment has 2 arrows", len(s.seq) == 2 and s.length == 2)
check("no arrow three times in a row", all(not (q[i] == q[i + 1] == q[i + 2]) for q in [mt.TalkSession("ana", d, rng=random.Random(d)).seq for d in range(40)] for i in range(len(q) - 2)))
r = play(s, ["w", "w", "w"])
check("two right moments win at once (stops early)", s.success and s.finished and len(r) == 2 and s.wins == 2)
check("no presses after the end", s.press("up") is None and s.timeout() is None)

s = mt.TalkSession("ana", 2, rng=random.Random(2))
play(s, ["f", "f", "w"])
check("two wrong moments lose at once", s.finished and not s.success and s.fails == 2)
s = mt.TalkSession("ana", 3, rng=random.Random(3))
play(s, ["w", "t", "w"])
check("win, timeout, win = success on the third", s.success and s.history == ["win", "fail", "win"])
s = mt.TalkSession("ana", 3, rng=random.Random(4))
play(s, ["t", "w", "f"])
check("timeout, win, wrong = failure", s.finished and not s.success and s.wins == 1)
s = mt.TalkSession("ana", 5, rng=random.Random(5))
s.press(s.seq[0])
check("a half-finished moment is not decided", s.round_res is None and not s.finished and s.pos == 1)
check("moments use different conversations", len(set(c["ana"] for c in s.convs)) == 3)
check("same day = same conversations", [c["ana"] for c in mt.TalkSession("ana", 7).convs] == [c["ana"] for c in mt.TalkSession("ana", 7).convs])
check("every conversation has all four texts", all(all(c.get(k) for k in ("ana", "you", "win", "fail")) for c in mt.rules()["conversations"]["ana"]))
sc = mt.scene_for("home", "kitchen")
check("kitchen scene with 3 pictures", sc and set(sc["images"]) >= {"neutral", "smile", "annoyed"})
check("other rooms use the default scene", mt.scene_for("home", "living") == sc)
check("scene falls back when pictures are missing", mt.scene_for("home", "kitchen", lambda p: False) is None)
import json  # noqa: E402
for k, path in sc["images"].items():
    check("picture exists: " + path, os.path.exists(os.path.join(ROOT, "game", path)))

st = ms.Story()
check("not talked at the start", not st.talked_today("ana", 1))
st.talk_result("ana", False, 1, 1)
check("a failed try uses the day", st.talked_today("ana", 1) and st.count("talk_game", 1) == 0)
check("another day is free", not st.talked_today("ana", 2))
st2 = ms.Story()
st2.talk_result("ana", True, 1, 1)
rep = st2.end_of_day(1)
check("a win gives love +1 and no dishes: -1", rep["love_after"] == st2.love and any(l[0] == "Talked with Ana" for l in rep["lines"]))
st3 = ms.Story()
st3.talk_result("carlos", True, 1, 1)
check("a win with another character does not give Ana love", st3.count("talk_game", 1) == 0)
check("a line exists for each outcome", mt.pick_line("ana", True, 3) and mt.pick_line("ana", False, 3))
print("\n%d failure(s)" % len(fails))
sys.exit(1 if fails else 0)
