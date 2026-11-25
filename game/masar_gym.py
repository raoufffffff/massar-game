"""Gym mini-game rules. Pure Python (no Ren'Py), so they can be tested on their own.

Bench press (the player): a marker sweeps back and forth over a bar at the bottom of the screen.
SPACE stops it:  green = smooth lift (+2),  orange = hard lift (+1),  red = failed lift (0).
"""

# Things to do in a room: (place, room) -> [(label to call, button text)].  Add a line here to add an activity;
# the label is a "label gym_..." in a .rpy file.  The room screen shows the buttons under "Pass time".
ROOM_ACTIONS = {
    ("gym", "floor"): [("gym_bench_press", "Bench press"), ("gym_run_ana", "Run (Ana test)"), ("gym_run_player", "Run (Player test)"), ("gym_yoga", "Yoga (Ana test)")],
}


def actions_here(pid, rid):
    return list(ROOM_ACTIONS.get((pid, rid), []))


# ---- numbers you may want to tune ------------------------------------------------------------------------
LIFT_ATTEMPTS = 5          # lifts per session
LIFT_FAIL_LIMIT = 3        # this many failed lifts end the session early
ANIM_SPEED = 1.6          # speed of the lift animation: 1.0 = original, bigger = faster
POINTS = {"green": 2, "orange": 1, "red": 0}

# One entry per level of the bench press.  To make level 2 harder, copy level 1 and change the numbers.
#   sweep   seconds for the marker to cross the whole bar once (smaller = faster = harder)
#   green   the green zone along the bar, 0 = left end, 1 = right end
#   orange  the orange zone (it includes the green; anything outside is red)
LEVELS = {
    1: {"sweep": 1.7, "green": (0.44, 0.56), "orange": (0.30, 0.70)},
}
# -----------------------------------------------------------------------------------------------------------

CUR = dict(LEVELS[1])      # the level being played right now


def set_level(n):
    CUR.clear()
    CUR.update(LEVELS.get(n, LEVELS[1]))


def marker_pos(t, period=None):
    """Position 0..1 of the marker t seconds after the attempt started (goes there and back)."""
    period = period or CUR["sweep"]
    ph = (t / period) % 2.0
    return ph if ph <= 1.0 else 2.0 - ph


def zone_at(p):
    g, o = CUR["green"], CUR["orange"]
    if g[0] <= p <= g[1]:
        return "green"
    if o[0] <= p <= o[1]:
        return "orange"
    return "red"


class LiftSession(object):
    def __init__(self):
        self.done = 0           # lifts attempted so far
        self.fails = 0
        self.score = 0
        self.history = []       # zones in order

    @property
    def finished(self):
        return self.done >= LIFT_ATTEMPTS or self.fails >= LIFT_FAIL_LIMIT

    def press(self, zone):
        """Register one lift; returns the points it gave."""
        pts = POINTS[zone]
        self.done += 1
        self.score += pts
        self.history.append(zone)
        if zone == "red":
            self.fails += 1
        return pts

    @property
    def max_score(self):
        return LIFT_ATTEMPTS * POINTS["green"]

    def rating(self):
        """Short verdict for the end screen."""
        if self.fails >= LIFT_FAIL_LIMIT:
            return "Too many failed lifts. Time to rest."
        r = self.score / float(self.max_score)
        if r >= 0.9:
            return "Perfect session!"
        if r >= 0.6:
            return "Solid session."
        if r >= 0.3:
            return "Not bad. Keep training."
        return "Rough day. Next time."
