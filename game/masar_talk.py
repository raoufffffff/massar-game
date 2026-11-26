# -*- coding: utf-8 -*-
"""Talk game rules (version 1.1: a sitting conversation).  Pure Python, no Ren'Py needed.

A talk is ROUNDS short moments.  In each one she says something, the player answers by pressing a few arrows in order
before the time runs out.  Right = she reacts happily, a wrong key or the time running out = she reacts badly.
The talk is won with NEED_WINS good moments (it stops as soon as it is decided).  One talk per character per day
(the story ledger remembers it) and no points: only success or failure.
Numbers, conversations and her closing lines are in game/data/talk.json; the scenes (pictures) in game/data/talk_scenes.json;
the ledger and love are handled by masar_story.py.
"""
import random

import masar_data

ARROWS = ("up", "down", "left", "right")
DEFAULTS = {"rounds": 3, "need_wins": 2, "arrows": [2, 3, 3], "seconds": 7, "characters": {"ana": {"name": "Ana"}},
            "lines": {}, "conversations": {}}
SCENE_DEFAULTS = {"default": "home/kitchen", "scenes": {}}
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


def scenes(reload=False):
    if reload or "s" not in _cache:
        data = dict(SCENE_DEFAULTS)
        try:
            data.update(masar_data.load("talk_scenes"))
        except IOError:
            pass
        _cache["s"] = data
    return _cache["s"]


def scene_for(place, room, loadable=None):
    """The scene (dict with title and images neutral/smile/annoyed) for a room; falls back to the default scene
    when the room has none or its pictures are missing.  `loadable` = renpy.loadable (or any function path -> bool)."""
    data = scenes()
    ok = loadable or (lambda p: True)

    def good(key):
        sc = data["scenes"].get(key)
        if sc and all(ok(sc["images"].get(k, "")) for k in ("neutral", "smile", "annoyed")):
            return sc
        return None
    return good("%s/%s" % (place, room)) or good(data["default"])


def name_of(who):
    return rules()["characters"].get(who, {}).get("name", who.title())


def pick_line(who, success, day):
    """One of her closing lines, chosen by the day so it stays the same if the screen is redrawn."""
    lines = rules().get("lines", {}).get(who, {}).get("win" if success else "fail", [])
    return lines[day % len(lines)] if lines else ""


def pick_conversations(who, day, n):
    """n different conversation moments for this day (the same ones if asked twice the same day)."""
    pool = list(rules().get("conversations", {}).get(who, []))
    if not pool:
        return [{"ana": "", "you": "", "win": "", "fail": ""} for _ in range(n)]
    rng = random.Random(day * 7919 + 13)
    rng.shuffle(pool)
    while len(pool) < n:
        pool += pool
    return pool[:n]


class TalkSession(object):
    def __init__(self, who="ana", day=1, rng=None, rounds=None, need=None, seconds=None, arrows=None):
        r = rules()
        self.who = who
        self.rounds = int(rounds or r["rounds"])
        self.need = int(need or r["need_wins"])
        self.arrows = list(arrows or r["arrows"])
        self.seconds = float(seconds or r["seconds"])
        self.rng = rng                            # None = the random module (not stored as a module: saves must pickle)
        self.convs = pick_conversations(who, day, self.rounds)
        self.round = 0                            # index of the current moment
        self.wins = 0
        self.fails = 0
        self.history = []                         # "win" / "fail" per finished moment
        self.round_res = None                     # result of the current moment: None while playing, "win" / "fail" / "timeout"
        self.result = None                        # whole talk: None while going on, then "win" or "fail"
        self._new_round()

    # ---- the current moment
    @property
    def conv(self):
        return self.convs[min(self.round, len(self.convs) - 1)]

    @property
    def length(self):
        return len(self.seq)

    def _new_round(self):
        n = self.arrows[min(self.round, len(self.arrows) - 1)]
        self.seq = []
        for _ in range(n):
            a = (self.rng or random).choice(ARROWS)
            while len(self.seq) >= 2 and self.seq[-1] == a and self.seq[-2] == a:
                a = (self.rng or random).choice(ARROWS)       # never the same arrow three times in a row
            self.seq.append(a)
        self.pos = 0                              # arrows already right
        self.round_res = None

    def _end_round(self, res):
        self.round_res = res
        good = res == "win"
        self.history.append("win" if good else "fail")
        if good:
            self.wins += 1
        else:
            self.fails += 1
        if self.wins >= self.need:
            self.result = "win"
        elif self.fails > self.rounds - self.need:
            self.result = "fail"
        return res

    def next_round(self):
        """Call after the reaction was shown: prepares the next moment (nothing happens when the talk is decided)."""
        if self.finished:
            return
        self.round += 1
        self._new_round()

    # ---- the whole talk
    @property
    def finished(self):
        return self.result is not None

    @property
    def success(self):
        return self.result == "win"

    def press(self, direction):
        """Returns None while it goes well, 'win' when the moment is complete, 'fail' on a wrong key."""
        if self.finished or self.round_res is not None:
            return None
        if direction == self.seq[self.pos]:
            self.pos += 1
            if self.pos >= len(self.seq):
                return self._end_round("win")
            return None
        return self._end_round("fail")

    def timeout(self):
        if self.finished or self.round_res is not None:
            return None
        return self._end_round("timeout")
