# -*- coding: utf-8 -*-
"""Shops (pure Python).  Every shop is in game/data/shops.json:  "shops": {"<place>/<room>": {title, seller, greeting, items:[{id, price}]}}
and every item once in "items": {id: {name, text, unique}}.  A shop is simply a room that has an entry here:
the room shows the action "Shop" (see story_actions in masar_story.rpy).  Buying takes no time.
"""
import masar_data

_cache = {}


def data(reload=False):
    if reload or "d" not in _cache:
        try:
            _cache["d"] = masar_data.load("shops")
        except IOError:
            _cache["d"] = {"items": {}, "shops": {}}
    return _cache["d"]


def shop_at(pid, rid):
    """The shop of this room (dict) or None."""
    return data()["shops"].get("%s/%s" % (pid, rid))


def item(iid):
    return data()["items"].get(iid, {"name": iid.title(), "text": ""})


def buy(player, phone, iid, price, day, part):
    """Returns (ok, text)."""
    it = item(iid)
    if it.get("unique") and player.has(iid):
        return False, "You already have the %s." % it["name"].lower()
    if not phone.spend(price, "Shop: " + it["name"], day, part):
        return False, "Not enough money: it costs $%d." % price
    player.give(iid)
    return True, "You bought the %s for $%d." % (it["name"].lower(), price)
