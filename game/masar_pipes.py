# -*- coding: utf-8 -*-
"""Pipe repair mini-game (rules only, pure Python, no Ren'Py needed).

The player sees a broken pipe with shadows where the missing pieces go, and a tray with the pieces.  He clicks a piece, then
clicks the shadow it belongs to: the right one snaps in, a wrong one does not stick.  No timer, no fail state: it is the first
challenge, so the player takes his time.  He may leave and come back later (the placed pieces are kept by the caller).

The puzzles are data: game/data/pipes.json, made by `python tools/make_pipe_scene.py` (see that file to add another one).
Each piece has an `id`, its final `x`,`y` on the 1920x1080 screen, its picture, its shadow and a place `tray` in the tray.
The screen is in masar_pipes.rpy.
"""
import masar_data

HINT_AFTER = 3        # wrong clicks in a row before the right shadow starts to pulse
_cache = {}


def load_game(name, reload=False):
    """The puzzle called `name` (a dict) or None when it does not exist."""
    if reload or "all" not in _cache:
        try:
            _cache["all"] = masar_data.load("pipes")
        except IOError:
            _cache["all"] = {}
    return _cache["all"].get("games", {}).get(name)


class PipeGame(object):
    """State of one puzzle.  Small and picklable (only ids): the saved game keeps it."""

    def __init__(self, name, placed=None):
        self.name = name
        self.placed = list(placed or [])
        self.selected = None
        self.flash = None          # the shadow that was just tried wrongly (shown red until the next click)
        self.streak = 0            # wrong clicks in a row
        self.message = ""

    # ---- queries
    def spec(self):
        return load_game(self.name) or {"pieces": []}

    def ids(self):
        return [p["id"] for p in self.spec()["pieces"]]

    def remaining(self):
        return [i for i in self.ids() if i not in self.placed]

    @property
    def done(self):
        return bool(self.ids()) and not self.remaining()

    def progress(self):
        return len(self.placed), len(self.ids())

    def hint_slot(self):
        """The shadow to pulse: only after several wrong clicks, only for the selected piece."""
        if self.selected and self.streak >= HINT_AFTER:
            return self.selected
        return None

    # ---- actions
    def select(self, piece_id):
        if piece_id not in self.remaining():
            return False
        self.selected = piece_id
        self.flash = None
        self.message = "Now click the shadow where it fits."
        return True

    def click_slot(self, slot_id):
        """The player clicked a shadow.  Returns "ok" (snapped in), "wrong", "none" (no piece in hand) or "filled"."""
        if slot_id in self.placed:
            return "filled"
        if not self.selected:
            self.message = "Pick a piece from the tray first."
            return "none"
        if slot_id == self.selected:
            self.placed.append(slot_id)
            self.selected = None
            self.flash = None
            self.streak = 0
            self.message = "Click! It fits." if not self.done else "That was the last piece."
            return "ok"
        self.flash = slot_id
        self.streak += 1
        self.message = "That piece does not fit there."
        return "wrong"
