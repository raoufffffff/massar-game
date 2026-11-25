"""Yoga mini-game rules (Ana).  Pure Python, no Ren'Py.

Ana starts relaxed (state 0).  Each round shows a random sequence of arrows; the player presses them in order.
  all right  -> Ana moves to the next pose (state + 1)
  a wrong key or the time (ROUND_SECONDS) running out -> the round is lost, Ana stays in her pose, a new sequence follows
There are ROUNDS rounds and FAIL_LIMIT lost rounds end the session.  Points (0..10) = 2 per pose reached.
With 5 rounds: no failure -> pose 5; one failure -> at most pose 4; two -> at most pose 3.
"""
import random

ROUNDS = 5                 # rounds in a session
FAIL_LIMIT = 3             # lost rounds that end the session early
POSES = 5                  # number of poses (pictures yoga_p1 .. yoga_p5)
ROUND_SECONDS = 20.0       # time for one round; running out of time counts as a lost round
ARROWS = ("up", "down", "left", "right")

# Arrows in the sequence, by the pose Ana is in when the round starts (0 = relaxed start).
SEQ_LEN = {0: 3, 1: 3, 2: 4, 3: 4, 4: 5, 5: 5}


class YogaSession(object):
    def __init__(self):
        self.state = 0          # 0 = start, 1..POSES = pose reached
        self.rounds = 0         # rounds played (won or lost)
        self.fails = 0
        self.seq = []
        self.pos = 0            # how many arrows of the sequence are already right
        self.new_round()

    @property
    def finished(self):
        return self.rounds >= ROUNDS or self.fails >= FAIL_LIMIT

    @property
    def points(self):
        return int(round(10.0 * self.state / POSES))

    def new_round(self):
        n = SEQ_LEN.get(self.state, 5)
        self.seq = []
        for i in range(n):
            a = random.choice(ARROWS)
            while len(self.seq) >= 2 and self.seq[-1] == a and self.seq[-2] == a:
                a = random.choice(ARROWS)          # never the same arrow three times in a row
            self.seq.append(a)
        self.pos = 0

    def press(self, direction):
        """Returns None while the sequence is going well, 'win' when it is completed, 'fail' on a wrong key."""
        if self.finished:
            return None
        if direction == self.seq[self.pos]:
            self.pos += 1
            if self.pos >= len(self.seq):
                self.rounds += 1
                self.state = min(POSES, self.state + 1)
                return "win"
            return None
        self.rounds += 1
        self.fails += 1
        return "fail"

    def timeout(self):
        """The time of the round ran out: counts as a lost round."""
        if self.finished:
            return None
        self.rounds += 1
        self.fails += 1
        return "timeout"

    def rating(self):
        if self.state >= POSES:
            return "Perfect balance!"
        if self.state >= 4:
            return "Very graceful."
        if self.state >= 3:
            return "Nice session."
        if self.state >= 1:
            return "A good start. Keep practising."
        return "Not today. Take a deep breath."
