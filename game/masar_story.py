# -*- coding: utf-8 -*-
"""Masar story engine, version 1: Ana's love, the day ledger and the end-of-day review.

Pure Python (no Ren'Py needed), so the simulator (tools/masar_sim.py) and the game use the very same code.
The rules are NOT in this file: they are in game/data/story.json (numbers, conditions, rent...).

How it works
  * During the day the game writes what the player did into the LEDGER:   story.log("dishes_done", day, part)
  * When the clock passes from Night to the next Morning the game calls   story.end_of_day(day, phone)
    which reads the ledger of that day, applies the rules, and returns a REPORT (a dict) for the player.
  * Love only rises up to the next gate that was not crossed yet (gates: 5, 15, 25...). A gate is crossed by a
    story quest:  story.cross_gate(5)  sets love to 5 and the gate stays crossed even if love falls later.
  * Love never passes version_cap (30): at that point the "end of this version" message is shown once.
"""
import masar_data

DEFAULT_RULES = {
    "show_numbers": True, "dev_tools": False, "version_cap": 30,
    "end_message": "You have reached the end of the current version.",
    "start": {"love": 2, "ana_followers": 0}, "gates": [5, 15, 25],
    "daily": [], "weekly": [],
}

_cache = {}


def rules(reload=False):
    """The content of game/data/story.json (cached). Missing file -> built-in defaults."""
    if reload or "r" not in _cache:
        data = dict(DEFAULT_RULES)
        try:
            data.update(masar_data.load("story"))
        except IOError:
            pass
        _cache["r"] = data
    return _cache["r"]


def weekday(day):
    """0 = Monday ... 6 = Sunday (Day 1 is a Monday)."""
    return (day - 1) % 7


def _holds(cond, st):
    """Conditions of a rule ("if": {...}); every key must be true."""
    for key, val in (cond or {}).items():
        if key == "love_lt" and not st.love < val:
            return False
        if key == "love_gte" and not st.love >= val:
            return False
        if key == "ana_followers_lt" and not st.ana_followers < val:
            return False
        if key == "ana_followers_gte" and not st.ana_followers >= val:
            return False
        if key == "gate_crossed" and val not in st.gates_crossed:
            return False
        if key == "gate_not_crossed" and val in st.gates_crossed:
            return False
    return True


class Story(object):
    """Everything the story remembers (saved with the game; new fields must be read with getattr)."""

    def __init__(self):
        start = rules()["start"]
        self.love = start.get("love", 0)
        self.ana_followers = start.get("ana_followers", 0)
        self.gates_crossed = []       # gates (love values) already crossed by a story quest
        self.ledger = []              # today's events: {"event", "day", "part", ...}
        self.history = []             # one report per finished day
        self.pending = None           # the last report, until the player has seen it
        self.ended = False            # version cap reached (message shown)
        self.rent_paid_day = 0        # day of the last rent payment

    # ------------------------------------------------------------------ ledger
    def log(self, event, day, part=0, **info):
        """Write something the player did into today's ledger."""
        e = {"event": event, "day": day, "part": part}
        e.update(info)
        self.ledger.append(e)
        return e

    def count(self, event, day):
        return sum(1 for e in self.ledger if e["event"] == event and e["day"] == day)

    # ------------------------------------------------------------------ gates and caps
    def next_gate(self):
        """The first gate that was not crossed yet (None if there is none)."""
        for g in sorted(rules()["gates"]):
            if g not in self.gates_crossed:
                return g
        return None

    def cap(self):
        """Highest love the normal daily gains may reach now."""
        top = rules()["version_cap"]
        g = self.next_gate()
        return top if g is None else min(top, g - 1)

    def cross_gate(self, gate, day=0, part=0):
        """A story quest breaks a gate: love becomes the gate value (if lower) and the gate stays crossed."""
        if gate not in self.gates_crossed:
            self.gates_crossed.append(gate)
        if self.love < gate:
            self.love = gate
        self.log("gate_crossed", day, part, gate=gate)

    # ------------------------------------------------------------------ rent
    def rent_rule(self):
        for w in rules().get("weekly", []):
            if w.get("id") == "rent":
                return w
        return None

    def rent_active(self):
        """Rent exists only before the player crosses the gate in 'until_gate' (50 = not in version 1)."""
        w = self.rent_rule()
        return bool(w) and w.get("until_gate", 50) not in self.gates_crossed

    def rent_due(self, day):
        """Amount to pay today, or 0."""
        w = self.rent_rule()
        if not w or not self.rent_active():
            return 0
        if day >= w.get("first_day", 1) and weekday(day) == w.get("weekday", 0) and self.rent_paid_day != day:
            return w.get("amount", 0)
        return 0

    def pay_rent(self, phone, day, part):
        """The player pays today's rent from the phone's money. Returns (ok, text)."""
        amount = self.rent_due(day)
        if not amount:
            return False, "There is no rent to pay today."
        if not phone.spend(amount, "Rent to Ana", day, part):
            return False, "Not enough money: the rent is $%d." % amount
        self.rent_paid_day = day
        self.log("rent_paid", day, part, amount=amount)
        return True, "You paid the rent: $%d." % amount

    # ------------------------------------------------------------------ the end of a day
    def end_of_day(self, day, phone=None):
        """Review the ledger of `day`, apply the rules, return the report (also kept in self.pending)."""
        r = rules()
        lines = []
        delta = 0
        before = self.love
        # --- daily rules
        for rule in r.get("daily", []):
            if not _holds(rule.get("if"), self):
                continue
            if "event" in rule:
                n = min(self.count(rule["event"], day), rule.get("per_day", 99))
                if n:
                    delta += rule.get("love", 0) * n
                    lines.append((rule.get("label", rule["id"]), rule.get("love", 0) * n))
            elif "missing" in rule:
                if not self.count(rule["missing"], day):
                    delta += rule.get("love", 0)
                    lines.append((rule.get("label", rule["id"]), rule.get("love", 0)))
        # --- weekly rules (rent)
        w = self.rent_rule()
        if w and self.rent_active() and day >= w.get("first_day", 1) and weekday(day) == w.get("weekday", 0):
            if self.rent_paid_day != day:
                delta += w.get("missing_love", 0)
                lines.append(("Rent not paid", w.get("missing_love", 0)))
            else:
                lines.append(("Rent paid", 0))
        # --- apply (gains stop at the cap, losses stop at 0)
        love = before + delta
        if delta > 0:
            love = min(love, max(before, self.cap()))
        love = max(0, min(100, love))
        ended_now = False
        top = r["version_cap"]
        if love >= top:
            love = top
            if not self.ended:
                self.ended = True
                ended_now = True
        self.love = love
        # --- messages for the new morning
        messages = []
        nd = day + 1
        due = self.rent_due(nd)
        if due:
            text = w.get("message", "Rent: $%(amount)d") % {"amount": due}
            messages.append((w.get("sender", "Ana"), text))
        if phone is not None:
            for sender, text in messages:
                phone.add_message(sender, text, nd, 0)
        report = {
            "day": day, "love_before": before, "love_after": love, "delta": love - before,
            "lines": lines, "messages": messages, "ended": ended_now,
            "capped": delta > 0 and love < before + delta and not ended_now,
            "show_numbers": r.get("show_numbers", True), "end_message": r.get("end_message", ""),
        }
        self.history.append(report)
        self.ledger = [e for e in self.ledger if e["day"] > day]
        self.pending = report
        return report

    def dismiss(self):
        self.pending = None


def report_text(rep):
    """A readable version of a report (used by the simulator and as a fallback in the game)."""
    out = ["Day %d is over." % rep["day"]]
    for label, v in rep["lines"]:
        out.append("  %s %s" % (label, ("%+d" % v) if rep["show_numbers"] and v else ""))
    if not rep["lines"]:
        out.append("  Nothing special happened.")
    if rep["show_numbers"]:
        out.append("  Ana's love: %d -> %d" % (rep["love_before"], rep["love_after"]))
    if rep["capped"]:
        out.append("  (Her feelings cannot grow further until something changes between you.)")
    if rep["ended"]:
        out.append("  " + rep["end_message"])
    return "\n".join(out)
