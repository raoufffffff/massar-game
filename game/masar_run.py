"""Running mini-game rules (Chrome-Dino style).  Pure Python, no Ren'Py.

The runner stays at the same x; the world scrolls.  SPACE / click = jump.  Obstacles come one by one;
clearing one = it counts, hitting one = a hit.  The session ends after all obstacles passed or too many hits.
Points (0..10) = cleared obstacles / total obstacles * 10.
"""
import math
import random

SCREEN_W = 1920
GROUND_Y = 850             # the ground line on the screen (same number as in tools/make_run_images.py)
PLAYER_X = 420             # where the runner stands
GRAVITY = 3200.0           # px/s^2
JUMP_SPEED = 1250.0        # px/s upwards at take-off (apex ~ 240 px, ~0.8 s in the air)
# How the runner is animated:
#   "bounce"  one running pose that bobs and tilts like a cartoon jog, the ponytail flutters (run1 <-> run1b)
#   "swap"    run1 <-> run2 (legs and arms swapped) -- needs a good run2 picture
RUN_MODE = "bounce"
BOB_HEIGHT = 16.0          # px the runner rises on every step
BOB_TILT = 3.0             # degrees of forward/back rocking
STRIDE = 70.0              # px of road per running frame (smaller = legs move faster)

RUN_HIT_LIMIT = 3          # hits that end the session early

# One entry per level.  speed0/speed1: scroll speed (px/s) at the start / at the last obstacle.
# total: obstacles in the session.   gap_min/gap_max: seconds between two obstacles (random).
RUN_LEVELS = {
    1: {"speed0": 620.0, "speed1": 900.0, "total": 20, "gap_min": 1.05, "gap_max": 1.75},
}

# kind -> (width, height) on screen; they match the pictures run_obs_<kind>.png (the images are shown 1:1)
OBSTACLES = {1: (200, 120), 2: (116, 120), 3: (137, 130)}


class Obstacle(object):
    def __init__(self, kind, x):
        self.kind = kind
        self.x = x                       # centre
        self.w, self.h = OBSTACLES[kind]
        self.hit = False                 # touched the runner (or passed through while protected)
        self.passed = False              # cleared


class RunSession(object):
    def __init__(self, level=1):
        self.cfg = RUN_LEVELS.get(level, RUN_LEVELS[1])
        self.total = self.cfg["total"]
        self.dist = 0.0                  # road travelled (px)
        self.speed = self.cfg["speed0"]
        self.y = 0.0                     # height above the ground (px)
        self.vy = 0.0
        self.obstacles = []
        self.spawned = 0
        self.spawn_in = 900.0            # px of road until the next obstacle appears
        self.hits = 0
        self.cleared = 0
        self.protect = 0.0               # seconds of protection after a hit
        self.hit_show = 0.0              # seconds the 'hit' picture is shown
        self.t = 0.0

    @property
    def on_ground(self):
        return self.y <= 0.0 and self.vy <= 0.0

    @property
    def finished(self):
        if self.hits >= RUN_HIT_LIMIT:
            return True
        return self.spawned >= self.total and not self.obstacles

    @property
    def points(self):
        return int(round(10.0 * self.cleared / float(self.total)))

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_SPEED

    def frame(self):
        """Which picture of the runner to show: run1 / run2 / jump / hit."""
        if self.hit_show > 0:
            return "hit"
        if not self.on_ground:
            return "jump"
        odd = int(self.dist / STRIDE) % 2 == 1
        if RUN_MODE == "swap":
            return "run2" if odd else "run1"
        return "run1b" if odd else "run1"

    def bob(self):
        """(lift px, tilt degrees, vertical zoom) of the running bounce; flat when in the air or hit."""
        if not self.on_ground or self.hit_show > 0:
            return 0.0, 0.0, 1.0
        ph = (self.dist / STRIDE) * 3.14159265
        s = abs(math.sin(ph))                     # 0 when a foot lands, 1 at the top of the step
        return BOB_HEIGHT * s, BOB_TILT * math.sin(ph * 0.5 + 0.8), 1.0 - 0.035 * (1.0 - s)

    def step(self, dt):
        dt = min(dt, 0.05)               # a long stall must not teleport the runner through obstacles
        self.t += dt
        progress = min(1.0, self.spawned / float(self.total))
        self.speed = self.cfg["speed0"] + (self.cfg["speed1"] - self.cfg["speed0"]) * progress
        move = self.speed * dt
        self.dist += move
        # jump physics
        if not self.on_ground:
            self.vy -= GRAVITY * dt
            self.y += self.vy * dt
            if self.y <= 0.0:
                self.y, self.vy = 0.0, 0.0
        self.protect = max(0.0, self.protect - dt)
        self.hit_show = max(0.0, self.hit_show - dt)
        # obstacles
        for o in self.obstacles:
            o.x -= move
        self.spawn_in -= move
        if self.spawn_in <= 0 and self.spawned < self.total:
            self.obstacles.append(Obstacle(random.choice(list(OBSTACLES)), SCREEN_W + 150))
            self.spawned += 1
            gap = random.uniform(self.cfg["gap_min"], self.cfg["gap_max"])
            self.spawn_in = gap * self.speed
        # collisions: the runner's box is a bit smaller than the picture
        px0, px1 = PLAYER_X - 45, PLAYER_X + 45
        py0, py1 = self.y, self.y + 190
        for o in self.obstacles:
            if o.hit or o.passed:
                continue
            ox0, ox1 = o.x - o.w / 2.0 + 14, o.x + o.w / 2.0 - 14
            oy1 = o.h - 14
            if px1 > ox0 and px0 < ox1 and py0 < oy1 and py1 > 0:
                o.hit = True
                if self.protect <= 0:
                    self.hits += 1
                    self.protect = 1.2
                    self.hit_show = 0.7
            elif o.x + o.w / 2.0 < px0:
                o.passed = True
                self.cleared += 1
        self.obstacles = [o for o in self.obstacles if o.x > -300]

    def rating(self):
        if self.hits >= RUN_HIT_LIMIT:
            return "Out of breath. Try again!"
        r = self.cleared / float(self.total)
        if r >= 0.95:
            return "Flawless run!"
        if r >= 0.7:
            return "Great run."
        if r >= 0.4:
            return "Not bad. Keep training."
        return "Rough run. Next time."
