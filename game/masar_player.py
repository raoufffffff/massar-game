# -*- coding: utf-8 -*-
"""The player's own numbers (fitness, charisma, intelligence) and his bag.  Pure Python.

Numbers and rules are in game/data/player.json:
  start         the values at the beginning of the game
  training      gym points (0..10) -> fitness gain, first matching row wins (10 -> +2, 6..9 -> +1, 5 or less -> 0)
  talk          charisma after a talk game: win +1, fail -1 (it never fades by itself)
  daily_decay   what fades every day (fitness -0.5), applied in the end-of-day report
Changes are IMMEDIATE (the methods return a short text the game shows as a notification).
"""
import masar_data

DEFAULTS = {
    "start": {"fitness": 5, "charisma": 5, "intelligence": 15}, "max": 100,
    "labels": {"fitness": "Fitness", "charisma": "Charisma", "intelligence": "Intelligence"},
    "daily_decay": {"fitness": 0.5},
    "training": [{"min_points": 10, "gain": 2}, {"min_points": 6, "gain": 1}],
    "talk": {"win": 1, "fail": -1},
}
_cache = {}


def rules(reload=False):
    if reload or "r" not in _cache:
        data = dict(DEFAULTS)
        try:
            data.update(masar_data.load("player"))
        except IOError:
            pass
        _cache["r"] = data
    return _cache["r"]


def _fmt(v):
    return ("%d" % v) if abs(v - round(v)) < 1e-9 else ("%.1f" % v)


class Player(object):
    """Saved with the game (new fields must be read with getattr)."""

    def __init__(self):
        self.stats = dict(rules()["start"])
        self.bag = {}                   # item id -> how many

    # ------------------------------------------------------------------ numbers
    def get(self, key):
        return self.stats.get(key, 0)

    def label(self, key):
        return rules()["labels"].get(key, key.title())

    def change(self, key, delta):
        """Change a number (kept between 0 and max).  Returns a short text like 'Charisma +1', or '' if nothing changed."""
        old = self.get(key)
        new = max(0.0, min(float(rules()["max"]), old + delta))
        self.stats[key] = new
        d = new - old
        return ("%s %s%s" % (self.label(key), "+" if d > 0 else "-", _fmt(abs(d)))) if d else ""

    def training(self, points):
        """After a gym game with 0..10 points."""
        for row in rules()["training"]:
            if points >= row["min_points"]:
                return self.change("fitness", row["gain"])
        return ""

    def talk(self, success):
        t = rules()["talk"]
        return self.change("charisma", t["win"] if success else t["fail"])

    def end_of_day(self):
        """Fading at the end of the day -> list of (label, text) for the report."""
        out = []
        for key, amount in rules().get("daily_decay", {}).items():
            txt = self.change(key, -amount)
            if txt:
                out.append((self.label(key), txt.split(" ", 1)[1] if " " in txt else txt))
        return out

    # ------------------------------------------------------------------ the bag
    def has(self, item):
        return self.bag.get(item, 0) > 0

    def give(self, item, n=1):
        self.bag[item] = self.bag.get(item, 0) + n

    def take(self, item, n=1):
        if self.bag.get(item, 0) < n:
            return False
        self.bag[item] -= n
        if self.bag[item] <= 0:
            del self.bag[item]
        return True
