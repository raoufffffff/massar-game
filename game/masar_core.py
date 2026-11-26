# -*- coding: utf-8 -*-
"""Masar core: place data and time logic (pure Python, testable outside Ren'Py)."""
import random
import masar_data

# Reference size the coordinates were measured on (stored as ratios, so any resolution works)
REF_W, REF_H = 1998.0, 1116.0

TIME_NAMES = ["Morning", "Afternoon", "Evening", "Night"]


class Place(object):
    def __init__(self, pid, name, area, x, y):
        self.id = pid
        self.name = name
        self.area = area
        self.fx = x / REF_W   # horizontal ratio 0..1
        self.fy = y / REF_H   # vertical ratio 0..1


# (id, name, area, x, y) - coordinates on the 1998x1116 map image
PLACES = [
    # Area 1
    Place("park", "Park", 1, 450, 350),
    Place("univ", "University", 1, 750, 260),
    Place("studios", "Studios", 1, 700, 410),
    Place("cafe", "John's Cafe", 1, 925, 270),
    Place("hq", "Supernova HQ", 1, 1110, 280),
    Place("beachbar", "Beach Bar", 1, 965, 150),
    Place("restaurant", "Fine Dining", 1, 1010, 400),
    # Area 2
    Place("gym", "Gym", 2, 1430, 200),
    Place("cinema", "Cinema", 2, 1440, 360),
    Place("beach", "Beach", 2, 1780, 190),
    Place("stadium", "Stadium", 2, 1780, 440),
    # Area 3
    Place("library", "Library", 3, 1340, 940),
    Place("clothes", "Clothing Store", 3, 595, 650),
    Place("mall", "Mall", 3, 925, 610),
    Place("bakery", "Bakery", 3, 555, 860),
    Place("casino", "Casino", 3, 740, 740),
    Place("bar", "Bar", 3, 760, 990),
    Place("hotel", "Hotel", 3, 1230, 640),
    Place("club", "Nightclub", 3, 975, 870),
    Place("bank", "Bank", 3, 390, 750),
    # Area 4
    Place("home", "Home", 4, 1620, 760),
    Place("police", "Police Station", 4, 1820, 880),
]

BY_ID = dict((p.id, p) for p in PLACES)

# Places unlocked at the start of Part 1 (the editor's "Places" tab edits this list in data/places.json)
PART1_UNLOCKED = ["home", "univ", "library", "cafe", "park",
                  "studios", "gym", "clothes", "mall"]

# ---------------------------------------------------------------- Opening hours (data/places.json)
#   {"unlocked": [...], "places": {"library": {"open": [0, 1, 2], "message": "The library closes at night."}},
#    "rooms": {"gym/combat": {"open": [0, 1, 2], "message": "..."}}}       open = time slots 0 Morning .. 3 Night
try:
    _PLACES = masar_data.load("places")
except Exception:
    _PLACES = {}
if isinstance(_PLACES.get("unlocked"), list):
    PART1_UNLOCKED = [p for p in _PLACES["unlocked"]]


def _hours(entry, part):
    """True if this settings entry is open at the time slot (no 'open' list = always open)."""
    hrs = (entry or {}).get("open")
    return True if hrs is None else int(part) in hrs


def place_open(pid, part):
    """Is this place open at this time slot?  (Opening hours only; story locks are is_available.)"""
    return _hours(_PLACES.get("places", {}).get(pid), part)


def room_open(pid, rid, part):
    """Is this room open: the place is open AND the room's own hours (if any) allow it."""
    return place_open(pid, part) and _hours(_PLACES.get("rooms", {}).get("%s/%s" % (pid, rid)), part)


def closed_text(pid, rid=None, part=0, unlocked=None):
    """What the player reads when a place or room is closed / locked."""
    if unlocked is not None and not is_available(unlocked, pid):
        return "%s is not available yet." % (BY_ID[pid].name if pid in BY_ID else pid)
    if rid is not None and place_open(pid, part):
        e = _PLACES.get("rooms", {}).get("%s/%s" % (pid, rid), {})
        return e.get("message") or "%s is closed right now." % room_name(pid, rid)
    e = _PLACES.get("places", {}).get(pid, {})
    return e.get("message") or "%s is closed right now." % (BY_ID[pid].name if pid in BY_ID else pid)


def can_enter(unlocked, pid, part):
    """May the player walk into this place now?  (unlocked by the story AND open at this time)"""
    return is_available(unlocked, pid) and place_open(pid, part)


def first_open_room(pid, part):
    """The first room of the place that is open now, or None."""
    for rid, _n in rooms_of(pid):
        if room_open(pid, rid, part):
            return rid
    return None


def advance_time(day, part):
    """Advance one time slot: morning > afternoon > evening > night > next morning."""
    part += 1
    if part >= len(TIME_NAMES):
        part = 0
        day += 1
    return day, part


def is_night(part):
    return part >= 2


def is_available(unlocked, pid):
    return pid in BY_ID and pid in unlocked


# Rooms inside each place: (room id, name). The first room is the entry point.
# Any place not listed has a single room "main".
ROOMS = {
    "home": [("outside", "Entrance"), ("living", "Living Room"), ("kitchen", "Kitchen"), ("my_room", "My Room"), ("bathroom", "Bathroom"), ("ana_door", "Upstairs Hallway")],
    "univ": [("yard", "Campus Yard"), ("lecture", "Lecture Hall"), ("lab", "Lab")],
    "library": [("hall", "Main Hall"), ("study", "Study Room")],
    "cafe": [("main", "Inside"), ("terrace", "Terrace")],
    "gym": [("floor", "Training Floor"), ("pool", "Pool"), ("lockers", "Locker Rooms"), ("combat", "Combat Ring")],
    "studios": [("lobby", "Reception"), ("studio1", "Studio 1"), ("studio2", "Studio 2")],
    "mall": [("hall", "Mall Hall"), ("salon", "Barber Salon"), ("gifts", "Gift Shop"), ("food", "Food Court"), ("store", "General Store")],
    "clothes": [("main", "Showroom"), ("fitting", "Fitting Room")],
    "hq": [("lobby", "Reception"), ("office", "Office"), ("hall", "Meeting Room")],
    "hotel": [("lobby", "Reception"), ("room", "Room")],
    "park": [("lake", "Lake"), ("playground", "Playground"), ("trail", "Forest Trail"), ("lawn", "Picnic Lawn")],
    "beach": [("sand", "Sand"), ("pier", "Pier")],
    "restaurant": [("main", "Outside"), ("inside", "Inside")],
}


MAP_ART_ALIAS = {"restaurant": "fine"}      # the place was called 'fine': its map pictures may still be images/map/fine_*.png


def map_art(pid):
    """File prefix of a place's map pictures (<prefix>_idle / _hover / _lock .png): its own id, else an older name."""
    alias = MAP_ART_ALIAS.get(pid)
    if alias and bg_exists is not None and not bg_exists("images/map/%s_idle.png" % pid) and bg_exists("images/map/%s_idle.png" % alias):
        return alias
    return pid


def rooms_of(pid):
    return ROOMS.get(pid, [("main", "Inside")])


def room_name(pid, rid):
    for r, n in rooms_of(pid):
        if r == rid:
            return n
    return rid


def first_room(pid):
    return rooms_of(pid)[0][0]


BG_EXTS = ("jpg", "png", "jpeg", "webp")      # accepted picture formats of a room (the first one found is used)
bg_exists = None                              # set by the game (renpy.loadable) so that bg_path can look for the file


# Pictures by time of day:  <place>_<room>_<time>.<ext>   (time = morning / afternoon / evening / night).
# Order tried for the current time: that time's picture -> the plain picture <place>_<room> -> the nearest other time.
TIME_KEYS = ["morning", "afternoon", "evening", "night"]
TIME_ALIASES = {"morning": [], "afternoon": ["noon", "midday", "day"], "evening": ["dusk", "sunset"], "night": []}
part_now = None                               # set by the game: a function returning the current time slot (0..3)


def time_stems(pid, rid, part):
    """File stems (without extension) to try for a time slot, in order of preference.
    A stem that is the plain picture of ANOTHER room of this place is skipped (a room called 'combat_night' must not
    be taken for the night picture of the room 'combat')."""
    base = "%s_%s" % (pid, rid)
    reserved = set("%s_%s" % (pid, r) for r, _n in rooms_of(pid)) - set([base])
    order = [part] + sorted([i for i in range(len(TIME_KEYS)) if i != part], key=lambda i: (abs(i - part), i))
    out = []
    for i in order[:1]:
        out += ["%s_%s" % (base, k) for k in [TIME_KEYS[i]] + TIME_ALIASES[TIME_KEYS[i]]]
    out.append(base)
    for i in order[1:]:
        out += ["%s_%s" % (base, k) for k in [TIME_KEYS[i]] + TIME_ALIASES[TIME_KEYS[i]]]
    return [x for x in out if x not in reserved]


def bg_path(pid, rid, part=None):
    """Room picture for a time slot (default: the current one), e.g. images/bg/park_lake_night.jpg; falls back to
    images/bg/park_lake.jpg and then to the nearest time that has a picture.  .png / .jpeg / .webp work too."""
    if part is None:
        try:
            part = part_now() if part_now is not None else 0
        except Exception:
            part = 0
    part = int(part) % len(TIME_KEYS)
    stems = time_stems(pid, rid, part)
    if bg_exists is not None:
        for st in stems:
            for ext in BG_EXTS:
                if bg_exists("images/bg/%s.%s" % (st, ext)):
                    return "images/bg/%s.%s" % (st, ext)
    return "images/bg/%s_%s.jpg" % (pid, rid)


# ---------------------------------------------------------------- Panoramic rooms
# A room picture wider than 16:9 is a panorama: the player scrolls it.  Per-room settings live in data/rooms.json:
#   {"version": 1, "rooms": {"park/lake": {"start": 0.5}}}      start = where the view begins, 0 (left) .. 1 (right)
try:
    _ROOMS = masar_data.load("rooms").get("rooms", {})
except Exception:
    _ROOMS = {}


def room_start(pid, rid):
    """Where the view starts in a panoramic room: 0.0 = far left ... 1.0 = far right (default: the middle)."""
    try:
        return max(0.0, min(1.0, float(_ROOMS.get("%s/%s" % (pid, rid), {}).get("start", 0.5))))
    except (TypeError, ValueError):
        return 0.5


# ---------------------------------------------------------------- Ana
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def weekday(day):
    """Day 1 is a Monday."""
    return (day - 1) % 7


# Where Ana is and what she does, by weekday and time slot.  The table is DATA now: game/data/schedule.json,
# edited with tools/masar_editor.py (tab "Schedule").  Each entry says: which weekdays (0 Monday ... 6 Sunday),
# which time slots (0 Morning, 1 Afternoon, 2 Evening, 3 Night), where (place, room) or "away", and her look:
#   {"type": "pose", "pose": "cooking"}      an activity picture (images/ana/pose_<pose>.png)
#   {"type": "stand"}                        the standing sprite
#   {"type": "char", "char": "ana", "image": "<id>"}   a picture of the character library (game/chars/...)
# Optional "at": {"x", "y", "scale", "flip"} = where she stands in the room (feet position on the 1920x1080 screen).
# When several entries match a time slot the game picks ONE (random, the same all slot long).
import masar_data

_SCHED = masar_data.load("schedule")


def entries_for(day, part, who="ana"):
    """All schedule entries of a character that match this day / time slot, in file order."""
    wd = weekday(day)
    ents = _SCHED.get("characters", {}).get(who, {}).get("entries", [])
    return [e for e in ents if wd in e.get("days", []) and part in e.get("parts", [])]


def ana_entry(day, part):
    """The schedule entry that applies to this time slot (random among the matching ones), or None if she is away."""
    pool = entries_for(day, part)
    if not pool:
        return None
    e = random.Random(day * 100 + part * 10 + 3).choice(pool)
    return None if e.get("away") else e


def _ana_choice(day, part):
    """(place, room, pose) for this time slot, or None if she is nowhere."""
    e = ana_entry(day, part)
    if not e:
        return None
    look = e.get("look", {})
    return (e["place"], e["room"], look.get("pose") if look.get("type") == "pose" else None)


def ana_location(day, part):
    """Where Ana is during a time slot, as (place, room), or None (also None when that room is closed then)."""
    ch = _ana_choice(day, part)
    if ch and not room_open(ch[0], ch[1], part):
        return None
    return (ch[0], ch[1]) if ch else None


def ana_is_here(day, part, place, room):
    return ana_location(day, part) == (place, room)


# ---------------------------------------------------------------- Photography
# Rooms where the player can take photos (place, room)
PHOTO_SPOTS = [("park", "lake"), ("park", "trail"), ("park", "lawn"), ("univ", "yard")]


def is_photo_spot(place, room):
    return (place, room) in PHOTO_SPOTS


# ---------------------------------------------------------------- Ana: first words when clicked
GREETINGS_TIME = {
    0: ["Oh, good morning! Did you sleep well?", "Morning. There's coffee if you want some.", "You're up early."],
    1: ["Hey, you. How's your day going?", "Afternoon! Don't tell me you skipped lunch.", "Oh, hi. I was just about to take a break."],
    2: ["Evening. Long day?", "Hi... I was just thinking about dinner.", "There you are."],
    3: ["It's late. Shouldn't you be asleep?", "Oh! You startled me.", "Can't sleep either?"],
}
GREETINGS_ROOM = {
    ("home", "kitchen"): ["Careful, the kitchen is my territory.", "I'm testing a recipe. Don't touch anything!"],
    ("home", "living"): ["Make yourself comfortable.", "I'm just resting my feet for a minute."],
    ("home", "ana_door"): ["Is something wrong? It's a bit late for the hallway."],
    ("gym", "floor"): ["I'm in the middle of a set. Give me a minute."],
}


def ana_greeting(day, part, place, room, salt=0):
    """A short, light line Ana says when the player clicks on her. Varies with time, room and salt."""
    rng = random.Random(day * 100 + part * 10 + salt)
    pool = list(GREETINGS_TIME[part])
    pool += GREETINGS_ROOM.get((place, room), []) * 2   # room lines are a bit more likely
    return rng.choice(pool)


# ---------------------------------------------------------------- Ana: what she is doing in a room
# Activity pictures: images/ana/pose_<name>.png (optional). If a picture does not exist she simply
# stands (the normal sprite), so poses can be added one by one.
ANA_POSES = {
    ("home", "kitchen"): ["coffee"],
    ("home", "living"): ["phone", "photo", "coffee"],
    ("home", "ana_door"): ["sweeping", "watering"],
}
try:
    import poses_data                       # photo poses added with tools/add_pose.py
    for _k, _v in poses_data.ANA_POSES.items():
        ANA_POSES[_k] = list(_v) + [p for p in ANA_POSES.get(_k, []) if p not in _v]
except ImportError:
    pass
ALL_POSES = sorted(set(p for opts in ANA_POSES.values() for p in opts))


def ana_pose(day, part, place, room, available=None):
    """The activity Ana is busy with here and now: the one the schedule names (if its picture exists),
    otherwise a random one of the poses of this room."""
    ch = _ana_choice(day, part)
    if ch and (ch[0], ch[1]) == (place, room) and ch[2] and (available is None or ch[2] in available):
        return ch[2]
    opts = list(ANA_POSES.get((place, room), []))
    if available is not None:
        opts = [o for o in opts if o in available]
    if not opts or (ch and ch[2] is None and (ch[0], ch[1]) == (place, room)):
        return None
    return random.Random(day * 100 + part * 10 + 7).choice(opts)
