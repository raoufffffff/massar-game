# -*- coding: utf-8 -*-
"""Checks for stats, bag, shops, immediate love, and the quests.  Run from the project root:  python tools/test_quests.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "tools" else HERE
sys.path.insert(0, os.path.join(ROOT, "game"))

import masar_player as mpl    # noqa: E402
import masar_phone as mph     # noqa: E402
import masar_quests as mq     # noqa: E402
import masar_shops as msh     # noqa: E402
import masar_story as ms      # noqa: E402

fails = []


def check(name, cond):
    print(("ok    " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)


# ---- immediate love
st = ms.Story()
st.log("dishes_done", 1, 1)
check("dishes: love +1 at once", st.love == 3 and st.pop_notes() == ["Ana's love +1"])
st.log("dishes_done", 1, 2)
check("dishes: only once a day", st.love == 3)
st.talk_result("ana", True, 1, 2)
check("talk win: love +1 at once, cap 4 reached", st.love == 4)
st.talk_result("ana", True, 2, 2)
st.log("dishes_done", 2, 1)
check("cap: love stays 4 and a note explains", st.love == 4 and any("cannot grow" in n for n in st.pop_notes()))
rep = st.end_of_day(1)
check("report of day 1 shows both gains once", rep["love_before"] == 2 and rep["love_after"] == 4 and sum(v for _, v in rep["lines"]) == 2)
st2 = ms.Story()
rep = st2.end_of_day(1)
check("no dishes: penalty only at the end of the day", rep["delta"] == -1 and st2.love == 1)

# ---- player
p = mpl.Player()
check("start numbers 5/5/15", (p.get("fitness"), p.get("charisma"), p.get("intelligence")) == (5, 5, 15))
check("training 10 points = +2", p.training(10) == "Fitness +2" and p.get("fitness") == 7)
check("training 7 points = +1", p.training(7) == "Fitness +1")
check("training 5 points = 0", p.training(5) == "" and p.get("fitness") == 8)
check("talk win +1, fail -1", p.talk(True) == "Charisma +1" and p.talk(False) == "Charisma -1" and p.get("charisma") == 5)
lines = p.end_of_day()
check("fitness fades 0.5 a day", p.get("fitness") == 7.5 and lines == [("Fitness", "-0.5")])
p.stats["fitness"] = 0
check("never below 0", p.change("fitness", -3) == "" and p.get("fitness") == 0)
for _ in range(100):
    p.change("charisma", 5)
check("never above 100", p.get("charisma") == 100)

# ---- shop
ph = mph.Phone()
p = mpl.Player()
sh = msh.shop_at("mall", "store")
check("the mall has a general store with the toolkit", sh and sh["items"][0]["id"] == "toolkit")
ph.money = 50
check("not enough money", msh.buy(p, ph, "toolkit", 90, 1, 1)[0] is False and not p.has("toolkit"))
ph.money = 100
ok, text = msh.buy(p, ph, "toolkit", 90, 1, 1)
check("buy the toolkit: money 10 and in the bag", ok and ph.money == 10 and p.has("toolkit"))
ph.money = 500
check("unique item cannot be bought twice", msh.buy(p, ph, "toolkit", 90, 1, 1)[0] is False and ph.money == 500)

# ---- quests
st = ms.Story()
p = mpl.Player()
ph = mph.Phone()
qs = mq.Quests()
fn = lambda: mq.make_ctx(st, p, ph)
n = qs.check(fn, st, ph, 1, 0)
check("first quest announced", n == ["New quest: Get to know Ana", "New quest: First steps in photography"])
check("the plumber is locked at first", "ana_plumber" not in [q["id"] for q in qs.active()])
ctx = fn()
cs = qs.current_step(mq.quest("ana_know"), ctx)
check("progress is computed from love (2 of 4)", cs["current"] == 2 and cs["target"] == 4)
st.love = 4
n = qs.check(fn, st, ph, 1, 1)
check("love 4 completes it and unlocks the plumber", "ana_know" in qs.done and "New quest: The Plumber" in n)
check("the Ana option appears in the living room", qs.actions(fn(), "home", "living", "ana") == [("quest:ana_plumber:0", "Is something wrong?")])
check("... and not in the kitchen yet", qs.actions(fn(), "home", "kitchen", "room") == [])
a = qs.action_of("ana_plumber", 0)
qs.set_flag(a["flag"])
qs.check(fn, st, ph, 1, 1)
check("then the current step is the toolkit", qs.current_step(mq.quest("ana_plumber"), fn())["text"].startswith("Buy"))
check("no kitchen action before the toolkit", qs.actions(fn(), "home", "kitchen", "room") == [])
p.give("toolkit")
check("kitchen action appears with the toolkit", qs.actions(fn(), "home", "kitchen", "room") == [("quest:ana_plumber:2", "Fix the kitchen pipes")])
a = qs.action_of("ana_plumber", 2)
p.stats["intelligence"] = 5
check("too little intelligence: it fails with a text", qs.action_check(a, fn())[0] is False)
p.stats["intelligence"] = 15
check("with 15 intelligence it works", qs.action_check(a, fn())[0] is True)
qs.set_flag(a["flag"])
n = qs.check(fn, st, ph, 2, 1)
check("plumber done: gate 5 crossed, love 5", "ana_plumber" in qs.done and 5 in st.gates_crossed and st.love == 5)
check("reward message shown", any("grateful" in x for x in n))

# ---- snapjob quest counted from gigs
gigs = [g for g in mph.GIGS if g.get("level", 1) == 1][:3]
for i, g in enumerate(gigs):
    ph.gig_done[(i + 1, g["id"])] = i
m0 = ph.money
n = qs.check(fn, st, ph, 3, 1)
check("3 level-1 gigs complete the Snapjob quest and pay $50", "snap_first" in qs.done and ph.money == m0 + 50)

# ---- data sanity
ids = [q["id"] for q in mq.data()["quests"]]
check("unique quest ids", len(ids) == len(set(ids)))
check("every requires exists", all(r in ids for q in mq.data()["quests"] for r in q.get("requires", [])))
print("\n%d failure(s)" % len(fails))
sys.exit(1 if fails else 0)
