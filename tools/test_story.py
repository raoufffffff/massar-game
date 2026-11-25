# -*- coding: utf-8 -*-
"""Quick checks of the story engine (python tools/test_story.py). Prints OK or the first failure."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "game"))
import masar_story as ms
import masar_phone as mph


class P(object):
    def __init__(self, m): self.money = m; self.msgs = []
    def spend(self, a, t, d, p):
        if a > self.money: return False
        self.money -= a; return True
    def add_message(self, s, t, d, p): self.msgs.append((s, t, d, p))


def fresh(money=100):
    ms.rules(reload=True)
    return ms.Story(), P(money)

# 1. start values and the cap before any gate
st, ph = fresh()
assert (st.love, st.ana_followers) == (2, 0) and st.cap() == 4
# 2. a diligent day gives +2 but never passes the cap (4)
st.log("talk_game", 1); st.log("dishes_done", 1)
r = st.end_of_day(1, ph); assert st.love == 4 and r["delta"] == 2
st.log("talk_game", 2); st.log("dishes_done", 2)
r = st.end_of_day(2, ph); assert st.love == 4 and r["capped"]
# 3. a gate sets love and stays crossed after love falls
st.cross_gate(5, 3)
assert st.love == 5 and st.cap() == 14
st.love = 0; assert 5 in st.gates_crossed and st.cap() == 14
# 4. skipping the dishes costs 1 only while Ana has < 500 followers
st, ph = fresh(); st.love = 4
st.end_of_day(1, ph); assert st.love == 3
st.ana_followers = 500
st.end_of_day(2, ph); assert st.love == 3
# 5. love never drops below 0
st, ph = fresh(); st.love = 0; st.end_of_day(1, ph); assert st.love == 0
# 6. rent: first Monday is day 8, message on the morning of day 8, unpaid -> -5, paid -> 0
st, ph = fresh(200)
for d in range(1, 8):
    st.log("dishes_done", d); st.end_of_day(d, ph)
assert st.rent_due(8) == 150 and ph.msgs and ph.msgs[-1][2] == 8
ok, _ = st.pay_rent(ph, 8, 1); assert ok and ph.money == 50 and st.rent_due(8) == 0
st.log("dishes_done", 8); r = st.end_of_day(8, ph)
assert ("Rent paid", 0) in r["lines"]
assert st.rent_due(15) == 150
# 7. not enough money to pay
st, ph = fresh(100); assert st.pay_rent(ph, 8, 1)[0] is False
# 8. the version cap at 30 shows the end message once
st, ph = fresh(); st.gates_crossed = [5, 15, 25]; st.love = 29
st.log("talk_game", 1); st.log("dishes_done", 1); r = st.end_of_day(1, ph)
assert st.love == 30 and r["ended"]
st.log("talk_game", 2); st.log("dishes_done", 2); r = st.end_of_day(2, ph)
assert st.love == 30 and not r["ended"]
# 9. the ledger of old days is cleared
assert all(e["day"] > 2 for e in st.ledger)
print("OK: all story checks passed")
