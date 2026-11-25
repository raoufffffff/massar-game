# -*- coding: utf-8 -*-
"""Talk game rules (version 1).  Pure Python, no Ren'Py needed.

The player must press SEQUENCE_LENGTH arrows in the order shown before the time runs out.
Everything right = success.  A wrong key or the time running out = failure.  There is one try per character per day
(the story ledger remembers it) and no points: only success or failure.
Numbers and her lines are in game/data/talk.json; the ledger and love are handled by masar_story.py.
"""
import random

import masar_data

ARROWS = ("up", "down", "left", "right")
DEFAULTS = {"sequence_length": 6, "seconds": 10, "characters": {"ana": {"name": "Ana"}}, "lines": {}}
_cache = {}


def rules(reload=False):
    if reload or "r" not in _cache:
        data = dict(DEFAULTS)
        try:
            data.update(masar_data.load("talk"))
        except IOError:
            pass
        _cache["r"] = data
    return _cache["r"]


def name_of(who):
    return rules()["characters"].get(who, {}).get("name", who.title())


def pick_line(who, success, day):
    """One of her lines, chosen by the day so it stays the same if the screen is redrawn."""
    lines = rules().get("lines", {}).get(who, {}).get("win" if success else "fail", [])
    return lines[day % len(lines)] if lines else ""


class TalkSession(object):
    def __init__(self, length=None, seconds=None, rng=None):
        r = rules()
        self.length = int(length or r["sequence_length"])
        self.seconds = float(seconds or r["seconds"])
        rng = rng or random
        self.seq = []
        for _ in range(self.length):
            a = rng.choice(ARROWS)
            while len(self.seq) >= 2 and self.seq[-1] == a and self.seq[-2] == a:
                a = rng.choice(ARROWS)           # never the same arrow three times in a row
            self.seq.append(a)
        self.pos = 0                              # arrows already right
        self.result = None                        # None while playing, then "win", "fail" or "timeout"

    @property
    def finished(self):
        return self.result is not None

    @property
    def success(self):
        return self.result == "win"

    def press(self, direction):
        """Returns None while it goes well, 'win' when the sequence is complete, 'fail' on a wrong key."""
        if self.finished:
            return None
        if direction == self.seq[self.pos]:
            self.pos += 1
            if self.pos >= len(self.seq):
                self.result = "win"
                return "win"
            return None
        self.result = "fail"
        return "fail"

    def timeout(self):
        if self.finished:
            return None
        self.result = "timeout"
        return "timeout"
