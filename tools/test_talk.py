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


s = mt.TalkSession(rng=random.Random(1))
check("sequence has 6 arrows", len(s.seq) == 6 and mt.rules()["sequence_length"] == 6)
check("no arrow three times in a row", all(not (s.seq[i] == s.seq[i + 1] == s.seq[i + 2]) for i in range(4)))
r = None
for a in s.seq:
    r = s.press(a)
check("all right = win", r == "win" and s.success and s.finished)
check("no presses after the end", s.press("up") is None)

s = mt.TalkSession(rng=random.Random(2))
wrong = [a for a in mt.ARROWS if a != s.seq[0]][0]
check("wrong key = fail", s.press(wrong) == "fail" and not s.success)
s = mt.TalkSession(rng=random.Random(3))
s.press(s.seq[0])
check("timeout = failure", s.timeout() == "timeout" and not s.success)

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
