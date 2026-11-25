# -*- coding: utf-8 -*-
"""Masar phone: money, messages, tasks, contacts, the photo gallery and the "Snapjob" photo gigs.

Pure Python (no Ren'Py), so it can be tested on its own.  The screens live in masar_phone.rpy.

HOW TO ADD CONTENT YOURSELF
  * subjects, rooms, photo gigs, levels, Ana's boxes -> use the editor:  python tools/masar_editor.py
    (the data is in game/data/snapjob.json and game/data/ana_regions.json; see masar_data.py)
  * a message from the game -> phone.add_message("Sender", "Text", day, day_part)
  * a task                -> phone.add_task("task_id", "Title", "Description", due_day)
  * money in / out        -> phone.pay(amount, "Title", day, day_part)  /  phone.spend(...)
"""
import random

START_MONEY = 100          # money at the start of the game

TIME_NAMES = ["Morning", "Afternoon", "Evening", "Night"]

# ---------------------------------------------------------------------------------------------------
#  Content: subjects, gigs, levels.  It lives in game/data/snapjob.json - edit it with the editor
#  (python tools/masar_editor.py) or by hand.  Here it is only loaded.
#    subjects: id -> (label, category, box)   box = (x, y, w, h) as fractions 0..1 of the room picture
#    ROOM_SUBJECTS: (place, room) -> subject ids      GIGS: list of dicts      LEVELS: level -> (name, followers)
# ---------------------------------------------------------------------------------------------------
import masar_data

_D = masar_data.load("snapjob")
MATCH_REQUIRED = _D.get("match_required", 80)      # a photo is accepted by a client if its match is at least this (percent)
BOARD_SIZE = _D.get("board_size", 5)               # how many gigs the Snapjob board shows each day
CATEGORIES = [tuple(c) for c in _D.get("categories", [])]      # [(id, label)] of subject categories
SUBJECTS = dict((k, (v["label"], v["category"], tuple(v["box"]))) for k, v in _D["subjects"].items())
ROOM_SUBJECTS = dict(((r["place"], r["room"]), list(r["subjects"])) for r in _D["rooms"])
# A subject may exist only at some times of day (e.g. a fisherman in the morning): "times": ["morning"] in snapjob.json.
SUBJECT_TIMES = dict((k, [t for t in v.get("times", [])]) for k, v in _D["subjects"].items() if v.get("times"))
TIME_KEYS = ["morning", "afternoon", "evening", "night"]
part_now = None                                    # set by the game: function returning the current time slot
GIGS = list(_D["gigs"])
LEVELS = dict((int(k), (v["name"], v["followers"])) for k, v in _D["levels"].items())

GIG_BY_ID = dict((g["id"], dict(g, level=g.get("level", 1))) for g in GIGS)

# People in the contacts app (id -> name, role). The player owns the ids listed in Phone.contacts.
CONTACT_INFO = {
    "ana": ("Ana", "Landlord"),
}

FILTERS = [("all", "All"), ("ana", "Ana")] + CATEGORIES + [("random", "Random")]
# sub-filters of Ana's photos (shot type, see TYPE_GROUP in masar_shot.py)
FILTERS_ANA = [("any", "All"), ("face", "Face"), ("upper", "Upper"), ("lower", "Lower"), ("feet", "Feet"),
               ("hands", "Hands"), ("full", "Full"), ("other", "Other")]


# ---------------------------------------------------------------------------------------------------
def subject_label(subject):
    if subject == "ana":
        return "Ana"
    if subject == "random":
        return "Random shot"
    return SUBJECTS[subject][0] if subject in SUBJECTS else "Scenery"


def category_of(subject):
    if subject == "ana":
        return "ana"
    if subject == "random":
        return "random"
    return SUBJECTS[subject][1] if subject in SUBJECTS else "places"


def subject_in_time(sid, part=None):
    """Is this subject there at this time slot (default: the current one)?  No 'times' = always."""
    times = SUBJECT_TIMES.get(sid)
    if not times:
        return True
    if part is None:
        try:
            part = part_now() if part_now is not None else None
        except Exception:
            part = None
    if part is None:
        return True
    return TIME_KEYS[int(part) % len(TIME_KEYS)] in times


def subject_ref_part(sid):
    """The time slot whose room picture shows this subject (its first allowed time); None = any (the current one)."""
    times = [TIME_KEYS.index(t) for t in SUBJECT_TIMES.get(sid, []) if t in TIME_KEYS]
    return min(times) if times else None


def subjects_here(place, room, part=None):
    """Subject ids the camera offers in this room right now (empty list = no choice, ordinary photo)."""
    return [s for s in ROOM_SUBJECTS.get((place, room), []) if subject_in_time(s, part)]


def rooms_for(subject):
    """The (place, room) pairs where this subject can be photographed."""
    return [k for k, v in ROOM_SUBJECTS.items() if subject in v]


def crop_px(subject, w=1920, h=1080):
    """Crop box in pixels of a room picture of size w x h for this subject."""
    if subject in SUBJECTS:
        fx, fy, fw, fh = SUBJECTS[subject][2]
    else:
        fx, fy, fw, fh = 0.0, 0.0, 1.0, 1.0
    return (int(fx * w), int(fy * h), max(1, int(fw * w)), max(1, int(fh * h)))


def tint(score):
    """(brightness, saturation) of a room photo: a low match = a dull picture (same look as the viewfinder)."""
    s = max(0, min(100, score))
    return (-0.40 + 0.55 * s / 100.0, 0.55 + 0.45 * s / 100.0)


def when_text(day, part):
    return "Day %d, %s" % (day, TIME_NAMES[part % len(TIME_NAMES)])


def level_for(followers):
    """The Snapjob level a player with this many followers has reached."""
    best = 1
    for lv, (_name, need) in LEVELS.items():
        if followers >= need and lv > best:
            best = lv
    return best


def level_name(level):
    return LEVELS[level][0] if level in LEVELS else "Level %d" % level


def next_level_info(level, followers):
    """(next level number, followers still needed) or None when this is the last level."""
    nxt = level + 1
    if nxt not in LEVELS:
        return None
    return (nxt, max(0, LEVELS[nxt][1] - followers))


def gigs_for_day(day, level=1):
    """The gig ids on the board on this day: the same list all day, a new random one each day.
    Gigs of the player's level come first; easier levels fill the board if there are too few."""
    rng = random.Random(day * 7919 + 17 + level * 101)
    ids = []
    for lv in range(level, 0, -1):
        pool = [g["id"] for g in GIGS if g.get("level", 1) == lv]
        rng.shuffle(pool)
        ids += pool
        if len(ids) >= BOARD_SIZE:
            break
    return ids[:BOARD_SIZE]


# ---------------------------------------------------------------------------------------------------
class Phone(object):
    """Everything the phone remembers. One object, saved with the game."""

    def __init__(self):
        self.money = START_MONEY
        self.photos = []          # gallery: dicts (see add_photo)
        self.next_photo = 1
        self.random_count = 0     # numbering of "Random shot N"
        self.messages = []        # dicts: id, sender, text, day, part, read
        self.next_message = 1
        self.transactions = []    # dicts: day, part, title, amount
        self.tasks = []           # dicts: id, title, text, due, done
        self.contacts = ["ana"]
        self.gig_done = {}        # (day, gig id) -> photo id
        self.transactions.append({"day": 1, "part": 0, "title": "Opening balance", "amount": START_MONEY})
        self.add_message("Snapjob", "Welcome to Snapjob! Clients post photo gigs here: five new ones every day. "
                         "Take the photo in the right place, then open the gig and upload it from your gallery. "
                         "A photo is accepted if it matches the request %d%% or more." % MATCH_REQUIRED, 1, 0)

    # ------------------------------------------------------------------ money
    def pay(self, amount, title, day, part):
        self.money += amount
        self.transactions.append({"day": day, "part": part, "title": title, "amount": amount})

    def spend(self, amount, title, day, part):
        """Returns False (and does nothing) if there is not enough money."""
        if amount > self.money:
            return False
        self.money -= amount
        self.transactions.append({"day": day, "part": part, "title": title, "amount": -amount})
        return True

    # ------------------------------------------------------------------ messages
    def add_message(self, sender, text, day, part):
        m = {"id": self.next_message, "sender": sender, "text": text, "day": day, "part": part, "read": False}
        self.next_message += 1
        self.messages.append(m)
        return m

    def unread(self):
        return sum(1 for m in self.messages if not m["read"])

    def mark_read(self):
        for m in self.messages:
            m["read"] = True

    # ------------------------------------------------------------------ tasks and contacts
    def add_task(self, tid, title, text, due=None):
        if not any(t["id"] == tid for t in self.tasks):
            self.tasks.append({"id": tid, "title": title, "text": text, "due": due, "done": False})

    def finish_task(self, tid):
        for t in self.tasks:
            if t["id"] == tid:
                t["done"] = True

    def open_tasks(self):
        return [t for t in self.tasks if not t["done"]]

    def add_contact(self, cid):
        if cid in CONTACT_INFO and cid not in self.contacts:
            self.contacts.append(cid)

    # ------------------------------------------------------------------ gallery
    def add_photo(self, subject, kind, place, room, score, day, part, img, crop, label=None, matches=None,
                  layers=None, view=None, props=None, shot_type="", expression="", bgblur=0.0, anablur=0.0, rating=None):
        """Put a new photo in the gallery. kind = "room" (a place) or "ana" (a photo of Ana).
        img = picture file, crop = (x, y, w, h) in pixels of that picture, score = match 0..100.
        Free-camera photos also keep: matches {subject id: match}, layers [(file, x, y, alpha)] (Ana's pictures),
        view (x, y, w, h) = what the lens showed (world pixels), props [(name, value)], shot_type, expression."""
        if not label:
            if subject == "random":
                self.random_count = getattr(self, "random_count", 0) + 1     # (old saves have no counter yet)
                label = "Random shot %d" % self.random_count
            else:
                label = subject_label(subject)
        p = {"id": self.next_photo, "subject": subject, "kind": kind, "place": place, "room": room,
             "score": int(score), "day": day, "part": part, "img": img, "crop": tuple(crop),
             "label": label, "sold": False, "matches": dict(matches or {}), "layers": list(layers or []),
             "view": tuple(view) if view else None, "props": list(props or []), "shot_type": shot_type,
             "expression": expression, "bgblur": bgblur, "anablur": anablur, "rating": rating}
        self.next_photo += 1
        self.photos.append(p)
        return p

    def photo(self, pid):
        for p in self.photos:
            if p["id"] == pid:
                return p
        return None

    def delete_photo(self, pid):
        self.photos = [p for p in self.photos if p["id"] != pid]

    def photos_in(self, flt="all", sub="any"):
        """Photos of a gallery filter (and for Ana a shot-type sub-filter), newest first."""
        out = [p for p in self.photos if flt == "all" or category_of(p["subject"]) == flt]
        if flt == "ana" and sub != "any":
            out = [p for p in out if p.get("shot_type", "other") == sub or (sub == "other" and not p.get("shot_type"))]
        return list(reversed(out))

    @staticmethod
    def match_for(p, subject):
        """How well a photo shows a subject (0 = it does not show it). Old photos only know their one subject."""
        m = p.get("matches")
        if m:
            return int(m.get(subject, 0))
        return p["score"] if p["subject"] == subject else 0

    # ------------------------------------------------------------------ Snapjob
    def board(self, day, level=1):
        """The gigs of today as dicts with a 'done' flag."""
        out = []
        for gid in gigs_for_day(day, level):
            g = dict(GIG_BY_ID[gid])
            g["done"] = (day, gid) in self.gig_done
            out.append(g)
        return out

    def pick_list(self, gig_id):
        """Unsold photos for the upload picker: photos that show the subject first (best match first)."""
        subject = GIG_BY_ID[gig_id]["subject"]
        free = [p for p in self.photos if not p["sold"]]
        right = sorted([p for p in free if self.match_for(p, subject) > 0], key=lambda p: -self.match_for(p, subject))
        other = [p for p in reversed(free) if self.match_for(p, subject) <= 0]
        return right + other

    def submit(self, gig_id, photo_id, day, part, level=1):
        """Upload a photo for a gig. Returns a dict: ok, reason ("accepted" / "low" / "wrong" / "closed"),
        match, reward, text."""
        g = GIG_BY_ID.get(gig_id)
        p = self.photo(photo_id)
        if g is None or p is None or gig_id not in gigs_for_day(day, level) or (day, gig_id) in self.gig_done or p["sold"]:
            return {"ok": False, "reason": "closed", "match": 0, "reward": 0,
                    "text": "This gig or photo is no longer available."}
        m = self.match_for(p, g["subject"])
        if m <= 0:
            return {"ok": False, "reason": "wrong", "match": 0, "reward": 0,
                    "text": "Rejected: the client asked for \"%s\", but this photo does not show it (\"%s\")."
                            % (subject_label(g["subject"]), p["label"])}
        if m < MATCH_REQUIRED:
            return {"ok": False, "reason": "low", "match": m, "reward": 0,
                    "text": "Rejected: the match is %d%% and the client needs at least %d%%. "
                            "Frame the subject better, keep the camera steady, and try again." % (m, MATCH_REQUIRED)}
        p["sold"] = True
        self.gig_done[(day, gig_id)] = photo_id
        self.pay(g["reward"], "Snapjob: " + g["title"], day, part)
        self.add_message("Snapjob", "Payment received: $%d for \"%s\" (%s). Thanks for the great photo!"
                         % (g["reward"], g["title"], g["client"]), day, part)
        return {"ok": True, "reason": "accepted", "match": m, "reward": g["reward"],
                "text": "Accepted! $%d was added to your account." % g["reward"]}
