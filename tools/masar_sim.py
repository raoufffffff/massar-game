# -*- coding: utf-8 -*-
"""Masar simulator: plays many days of Ana's love without starting the game.

Run from the project root (it only needs Python):
    python tools/masar_sim.py                      # default: a diligent player, 30 days
    python tools/masar_sim.py --days 20 --no-dishes
    python tools/masar_sim.py --days 40 --cross 5@6 --cross 15@14 --cross 25@24 --quiet

What the player does every day is chosen with the flags:
    --no-talk      never plays the talk game          --no-dishes   never washes the dishes
    --no-rent      never pays the rent                --money N     starting money (default: the game's, 100)
    --cross G@D    a story quest crosses gate G on day D (may be repeated)
    --earn D=N     the player earns N dollars on day D (may be repeated, e.g. --earn 3=200)
    --followers N  Ana's followers (the dishes penalty exists only below 500)
    --quiet        print only a one-line summary per day
The rules are read from game/data/story.json, so change the numbers there and run again.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "tools" else HERE
sys.path.insert(0, os.path.join(ROOT, "game"))

import masar_story as ms          # noqa: E402
import masar_phone as mph         # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--no-talk", action="store_true")
    ap.add_argument("--no-dishes", action="store_true")
    ap.add_argument("--no-rent", action="store_true")
    ap.add_argument("--money", type=int, default=None)
    ap.add_argument("--followers", type=int, default=None)
    ap.add_argument("--cross", action="append", default=[], help="G@D: cross gate G on day D")
    ap.add_argument("--earn", action="append", default=[], help="D=N: earn N dollars on day D")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    ms.rules(reload=True)
    st = ms.Story()
    phone = mph.Phone()
    if a.money is not None:
        phone.money = a.money
    if a.followers is not None:
        st.ana_followers = a.followers
    cross = {}
    for c in a.cross:
        g, d = c.split("@")
        cross.setdefault(int(d), []).append(int(g))
    earn = {}
    for e in a.earn:
        d, n = e.split("=")
        earn[int(d)] = earn.get(int(d), 0) + int(n)

    print("Start: love %d, money $%d, Ana's followers %d" % (st.love, phone.money, st.ana_followers))
    for day in range(1, a.days + 1):
        if day in earn:
            phone.pay(earn[day], "Earned (simulation)", day, 1)
        if st.rent_due(day) and not a.no_rent:
            ok, text = st.pay_rent(phone, day, 1)
            if not a.quiet:
                print("   [day %d] %s" % (day, text))
        if not a.no_talk:
            st.log("talk_game", day, 1)
        if not a.no_dishes:
            st.log("dishes_done", day, 2)
        for g in cross.get(day, []):
            st.cross_gate(g, day, 2)
            if not a.quiet:
                print("   [day %d] story quest crosses gate %d" % (day, g))
        rep = st.end_of_day(day, phone)
        if a.quiet:
            print("day %2d  love %2d (%+d)  money $%d%s" % (day, st.love, rep["delta"], phone.money,
                                                      "  END OF VERSION" if rep["ended"] else ""))
        else:
            print(ms.report_text(rep))
            for sender, text in rep["messages"]:
                print("   Message from %s: %s" % (sender, text))
            print("   Money: $%d" % phone.money)
    print("\nEnd of simulation: love %d, gates crossed %s, money $%d" % (st.love, sorted(st.gates_crossed), phone.money))


if __name__ == "__main__":
    main()
