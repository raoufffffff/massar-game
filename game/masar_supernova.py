# -*- coding: utf-8 -*-
"""Supernova (pure Python, no Ren'Py needed): the in-game photo platform.  The screens are in masar_supernova.rpy.

Two accounts (data: game/data/supernova.json):
  "me"  - the player's own account (photographer): any photo of his gallery.
  "ana" - Ana's account (influencer): opens when the gate-15 quest is done; takes only photos of Ana.
Posting gives followers (quality x followers_per_point).  The caller adds the gain to the right counter
(the player's `followers`, or `story.ana_followers`), because those numbers live elsewhere.
"""
import random
import masar_data

_cache = {}


def data(reload=False):
    if reload or "d" not in _cache:
        d = {"accounts": {}, "likes_per_follower": 0.12}
        try:
            d.update(masar_data.load("supernova"))
        except IOError:
            pass
        _cache["d"] = d
    return _cache["d"]


def account(aid):
    return data()["accounts"].get(aid)


def account_ids():
    return [a for a in ("me", "ana") if a in data()["accounts"]]


def quality(photo):
    """0..100: an Ana photo counts by its rating (/10), any other photo by its match."""
    r = photo.get("rating")
    if r:
        return max(0, min(100, int(round(r * 10))))
    return max(0, min(100, int(photo.get("score", 0))))


class Supernova(object):
    """What the platform remembers (saved with the game).  New fields: read them with getattr."""

    def __init__(self):
        self.posts = {"me": [], "ana": []}      # newest last; a post keeps its photo dict (so it survives gallery deletes)
        self.next_id = 1

    # ------------------------------------------------------------------ queries
    def unlocked(self, aid, gates_crossed):
        a = account(aid)
        if not a:
            return False
        need = a.get("needs_gate")
        return (not need) or need in gates_crossed

    def posts_of(self, aid):
        return list(reversed(self.posts.get(aid, [])))

    def posted_today(self, aid, day):
        return sum(1 for p in self.posts.get(aid, []) if p["day"] == day)

    def already_posted(self, aid, photo_id):
        return any(p["photo"]["id"] == photo_id for p in self.posts.get(aid, []))

    def can_post(self, aid, photo, day, gates_crossed):
        """-> (ok, text)."""
        a = account(aid)
        if not a or photo is None:
            return False, "Nothing to post."
        if not self.unlocked(aid, gates_crossed):
            return False, a.get("locked_text", "This account is not open yet.")
        if a.get("accepts") == "ana" and photo.get("kind") != "ana":
            return False, "Only photos of Ana can go on her account."
        if self.already_posted(aid, photo["id"]):
            return False, "This photo is already on the account."
        if self.posted_today(aid, day) >= a.get("per_day", 1):
            return False, "That is enough for today (%d post%s a day). Try again tomorrow." % (a.get("per_day", 1), "" if a.get("per_day", 1) == 1 else "s")
        return True, ""

    def eligible(self, aid, photos):
        """Photos of the gallery that this account may show (newest first), not yet posted there."""
        a = account(aid) or {}
        out = []
        for p in reversed(photos):
            if a.get("accepts") == "ana" and p.get("kind") != "ana":
                continue
            if self.already_posted(aid, p["id"]):
                continue
            out.append(p)
        return out

    # ------------------------------------------------------------------ action
    def post(self, aid, photo, day, part, followers_now, gates_crossed):
        """Post a photo.  Returns {ok, text, gain, likes}; the caller adds `gain` to the account's followers."""
        ok, text = self.can_post(aid, photo, day, gates_crossed)
        if not ok:
            return {"ok": False, "text": text, "gain": 0, "likes": 0}
        a = account(aid)
        q = quality(photo)
        gain = max(1, int(round(q * a.get("followers_per_point", 0.2))))
        rng = random.Random(self.next_id * 7919 + day)
        likes = int((followers_now + gain) * data().get("likes_per_follower", 0.12) * (0.5 + q / 100.0) * (0.85 + 0.3 * rng.random()))
        self.posts.setdefault(aid, []).append({"id": self.next_id, "photo": photo, "day": day, "part": part,
                                               "gain": gain, "likes": likes, "quality": q})
        self.next_id += 1
        return {"ok": True, "gain": gain, "likes": likes,
                "text": "Posted! %d likes and %d new follower%s." % (likes, gain, "" if gain == 1 else "s")}
