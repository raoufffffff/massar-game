# -*- coding: utf-8 -*-
"""Masar story engine, version 1: Ana's love, the day ledger and the end-of-day review.

Pure Python (no Ren'Py needed), so the simulator (tools/masar_sim.py) and the game use the very same code.
The rules are NOT in this file: they are in game/data/story.json (numbers, conditions, rent...).

How it works
  * During the day the game writes what the player did into the LEDGER:   story.log("dishes_done", day, part)
    Rules with  "when": "now"  (talk game, dishes) change love AT ONCE (a short note is queued: story.pop_notes()).
  * When the clock passes from Night to the next Morning the game calls   story.end_of_day(day, phone, player)
    which applies the rules with  "when": "end_of_day"  (penalties: unwashed dishes, unpaid rent, fitness decay)
    and returns a REPORT (a dict) for the player, with everything that happened that day.
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
        for rule in rules().get("daily", []):
            if rule.get("when", "end_of_day") == "now" and rule.get("event") == event:
                self._apply_now(rule, day)
        return e

    # ------------------------------------------------------------------ immediate effects, notes, the day's lines
    def _lines(self):
        if not hasattr(self, "day_lines"):
            self.day_lines = []
        return self.day_lines

    def _notes(self):
        if not hasattr(self, "notes"):
            self.notes = []
        return self.notes

    def pop_notes(self):
        """Short texts the game should show now (and forget)."""
        n = list(self._notes())
        self.notes = []
        return n

    def _touch_day(self):
        """Remember the love the day started with (before the first change of the day)."""
        if getattr(self, "day_love_start", None) is None:
            self.day_love_start = self.love

    def _apply_now(self, rule, day):
        """An event rule that works at once: per-day limit, conditions, cap, then love changes and a note is queued."""
        n = self.count(rule["event"], day)
        if n > rule.get("per_day", 99) or not _holds(rule.get("if"), self):
            return
        gain = rule.get("love", 0)
        self._touch_day()
        before = self.love
        if gain > 0:
            self.love = min(100, min(before + gain, max(before, self.cap())))
        else:
            self.love = max(0, before + gain)
        delta = self.love - before
        if delta:
            self._lines().append((rule.get("label", rule["id"]), delta))
            self._notes().append("Ana's love %+d" % delta if rules().get("show_numbers", True) else rule.get("label", "Ana"))
        elif gain > 0:
            self.day_capped = True
            self._notes().append("Her feelings cannot grow further until something changes between you.")
        if self.love >= rules()["version_cap"]:
            self.love = rules()["version_cap"]
            if not self.ended:
                self.ended = True
                self._ended_today = True
                self._notes().append(rules().get("end_message", ""))

    def count(self, event, day):
        return sum(1 for e in self.ledger if e["event"] == event and e["day"] == day)

    # ------------------------------------------------------------------ talk games
    def talked_today(self, who, day):
        """True when the player already played the talk game with `who` today (won or lost: one try a day)."""
        return any(e["event"] == "talk_try" and e["day"] == day and e.get("who") == who for e in self.ledger)

    def talk_result(self, who, success, day, part=0):
        """Write the result of a talk game into the ledger.  A win with Ana is the event 'talk_game' (rules in
        story.json give her love +1); wins with other characters are 'talk_game_<who>' and do not touch Ana's love."""
        self.log("talk_try", day, part, who=who, success=bool(success))
        if success:
            self.log("talk_game" if who == "ana" else "talk_game_" + who, day, part, who=who)

    # ------------------------------------------------------------------ gates and caps
    def photo_unlocked(self):
        """Ana agrees to be photographed once the gate 15 quest is done (she opened her Supernova account)."""
        return 15 in self.gates_crossed

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
            self._touch_day()
            self._lines().append(("Something special happened between you", gate - self.love))
            self._notes().append("Ana's love %+d" % (gate - self.love))
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
    def end_of_day(self, day, phone=None, player=None):
        """Apply the end-of-day rules for `day`, return the report (also kept in self.pending).
        The report lists everything that changed love today: what already happened at once, and the penalties."""
        r = rules()
        lines = list(self._lines())
        before = getattr(self, "day_love_start", None)
        if before is None:
            before = self.love
        capped = getattr(self, "day_capped", False)
        delta = 0
        # --- daily rules that work at the end of the day (the "now" ones were applied when they happened)
        for rule in r.get("daily", []):
            if rule.get("when", "end_of_day") == "now" or not _holds(rule.get("if"), self):
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
        love = self.love + delta
        if delta > 0:
            love = min(love, max(self.love, self.cap()))
            capped = True if love < self.love + delta else capped
        love = max(0, min(100, love))
        ended_now = getattr(self, "_ended_today", False)
        top = r["version_cap"]
        if love >= top:
            love = top
            if not self.ended:
                self.ended = True
                ended_now = True
        self.love = love
        # --- the player's own numbers (fitness slowly fades)
        stat_lines = player.end_of_day() if player is not None else []
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
            "lines": lines, "stat_lines": stat_lines, "messages": messages, "ended": ended_now,
            "capped": capped and not ended_now,
            "show_numbers": r.get("show_numbers", True), "end_message": r.get("end_message", ""),
        }
        self.history.append(report)
        self.ledger = [e for e in self.ledger if e["day"] > day]
        self.day_lines = []
        self.day_love_start = None
        self.day_capped = False
        self._ended_today = False
        self.pending = report
        return report

    def dismiss(self):
        self.pending = None


def report_text(rep):
    """A readable version of a report (used by the simulator and as a fallback in the game)."""
    out = ["Day %d is over." % rep["day"]]
    for label, v in rep["lines"]:
        out.append("  %s %s" % (label, ("%+d" % v) if rep["show_numbers"] and v else ""))
    for label, text in rep.get("stat_lines", []):
        out.append("  %s %s" % (label, text))
    if not rep["lines"]:
        out.append("  Nothing special happened.")
    if rep["show_numbers"]:
        out.append("  Ana's love: %d -> %d" % (rep["love_before"], rep["love_after"]))
    if rep["capped"]:
        out.append("  (Her feelings cannot grow further until something changes between you.)")
    if rep["ended"]:
        out.append("  " + rep["end_message"])
    return "\n".join(out)
