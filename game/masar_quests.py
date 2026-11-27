# -*- coding: utf-8 -*-
"""Quests (pure Python).  All quests are in game/data/quests.json.

A quest has STEPS; each step has a condition ("if") that is computed from the game state, never counted separately:
    love_gte N | flag "name" | item "id" | stat_gte {stat, n} | gigs_done_gte {level, n} | money_gte N | quest_done "id"
The quest is complete when all its steps are true.  The first step that is not true yet is the CURRENT step:
its text and hint are what the player reads in the phone, and its optional "action" appears in the game:
    action: {who: "ana" | "room", place, room, title, label (a Ren'Py scene), flag (set when the scene ends),
             time (slots it costs, default 1), needs (conditions to try it), fail_text,
             show (conditions for the choice to appear at all); place / room may be left out = anywhere}
    "ana" = an extra choice when clicking Ana in that room;  "room" = a button under "Pass time".
Reward of a quest: gate (a love gate is crossed), money, message.  Quests may have "requires": [quest ids].
"""
import masar_data

DEFAULTS = {"domains": {}, "quests": []}
_cache = {}


def data(reload=False):
    if reload or "d" not in _cache:
        d = dict(DEFAULTS)
        try:
            d.update(masar_data.load("quests"))
        except IOError:
            pass
        _cache["d"] = d
    return _cache["d"]


def quest(qid):
    for q in data()["quests"]:
        if q["id"] == qid:
            return q
    return None


def make_ctx(story, player, phone):
    """The game state conditions look at."""
    by_level = {}
    try:
        import masar_phone as mph
        for (d, gid) in phone.gig_done:
            lv = mph.GIG_BY_ID.get(gid, {}).get("level", 1)
            by_level[lv] = by_level.get(lv, 0) + 1
    except Exception:
        pass
    return {"love": story.love, "stats": player.stats, "bag": player.bag, "money": phone.money, "gigs": by_level}


def evaluate(cond, ctx, flags, done=()):
    """-> (ok, current, target) ; current/target are numbers for conditions that can show a bar, else None."""
    ok, cur, tgt = True, None, None
    for key, val in (cond or {}).items():
        if key == "love_gte":
            c = ctx["love"]; good = c >= val; cur, tgt = c, val
        elif key == "flag":
            good = val in flags
        elif key == "item":
            good = ctx["bag"].get(val, 0) > 0
        elif key == "stat_gte":
            c = ctx["stats"].get(val["stat"], 0); good = c >= val["n"]; cur, tgt = c, val["n"]
        elif key == "gigs_done_gte":
            c = ctx["gigs"].get(val.get("level", 1), 0); good = c >= val["n"]; cur, tgt = c, val["n"]
        elif key == "money_gte":
            c = ctx["money"]; good = c >= val; cur, tgt = c, val
        elif key == "quest_done":
            good = val in done
        else:
            good = True
        ok = ok and good
    return ok, cur, tgt


class Quests(object):
    def __init__(self):
        self.done = []       # finished quest ids
        self.flags = []      # story flags set by scenes
        self.seen = []       # quests the player was told about ("New quest")

    # ------------------------------------------------------------------ flags
    def set_flag(self, flag):
        if flag not in self.flags:
            self.flags.append(flag)

    # ------------------------------------------------------------------ what is going on
    def is_active(self, q):
        return q["id"] not in self.done and all(r in self.done for r in q.get("requires", []))

    def active(self):
        return [q for q in data()["quests"] if self.is_active(q)]

    def steps(self, q, ctx):
        """List of dicts: text, hint, done, current (number or None), target, action, index."""
        out = []
        for i, st in enumerate(q["steps"]):
            ok, cur, tgt = evaluate(st.get("if"), ctx, self.flags, self.done)
            out.append({"index": i, "text": st["text"], "hint": st.get("hint", ""), "done": ok, "current": cur,
                        "target": tgt, "action": st.get("action")})
        return out

    def current_step(self, q, ctx):
        for s in self.steps(q, ctx):
            if not s["done"]:
                return s
        return None

    def progress(self, q, ctx):
        """(steps done, steps total) for the list in the phone."""
        st = self.steps(q, ctx)
        return sum(1 for s in st if s["done"]), len(st)

    def actions(self, ctx, place, room, who):
        """Actions of current steps that belong here: list of (id 'quest:<id>:<step>', title)."""
        out = []
        for q in self.active():
            s = self.current_step(q, ctx)
            a = s["action"] if s else None
            if a and a.get("who", "room") == who and a.get("place") in (None, place) and a.get("room") in (None, room) \
                    and evaluate(a.get("show"), ctx, self.flags, self.done)[0]:
                out.append(("quest:%s:%d" % (q["id"], s["index"]), a.get("title", s["text"])))
        return out

    @staticmethod
    def action_of(qid, index):
        q = quest(qid)
        return q["steps"][index].get("action") if q else None

    def action_check(self, a, ctx):
        """Can the player do this action now?  -> (ok, text)"""
        ok, _, _ = evaluate(a.get("needs"), ctx, self.flags, self.done)
        return (True, "") if ok else (False, a.get("fail_text", "You are not ready for this yet."))

    # ------------------------------------------------------------------ completion
    def check(self, ctx_fn, story, phone, day, part):
        """Finish quests whose steps are all true, give rewards, announce new quests.  Returns texts to show.
        ctx_fn() builds a fresh state (love and money may change when a reward is given)."""
        notes = []
        changed = True
        while changed:
            changed = False
            ctx = ctx_fn()
            for q in self.active():
                if q["id"] not in self.seen:
                    self.seen.append(q["id"])
                    notes.append("New quest: " + q["title"])
                if all(s["done"] for s in self.steps(q, ctx)):
                    self.done.append(q["id"])
                    notes.append("Quest completed: " + q["title"])
                    rw = q.get("reward", {})
                    if rw.get("gate"):
                        story.cross_gate(rw["gate"], day, part)
                    if rw.get("money"):
                        phone.pay(rw["money"], "Quest: " + q["title"], day, part)
                    if rw.get("message"):
                        notes.append(rw["message"])
                    changed = True
                    break
        return notes
