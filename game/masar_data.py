# -*- coding: utf-8 -*-
"""Reads the game's content files (game/data/*.json).  Used by the game AND by tools/masar_editor.py.

The files are edited with the editor (python tools/masar_editor.py), or by hand: they are plain JSON.
Pure Python (no Ren'Py needed).  Inside the game it also works from packed archives (renpy.open_file).
"""
import io
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load(name):
    """Load game/data/<name>.json -> dict.  Raises a clear error if the file is missing or broken."""
    path = os.path.join(DATA_DIR, name + ".json")
    try:
        if os.path.exists(path):
            with io.open(path, encoding="utf-8") as f:
                return json.load(f)
        try:
            import renpy
            with renpy.exports.open_file("data/%s.json" % name) as f:
                return json.loads(f.read().decode("utf-8"))
        except ImportError:
            pass
    except ValueError as e:
        raise ValueError("game/data/%s.json is not valid JSON: %s (check commas and quotes near that line; "
                         "the editor keeps backups in game/data/_backup)" % (name, e))
    raise IOError("game/data/%s.json is missing" % name)


def save(name, data, backup=True):
    """Write game/data/<name>.json (a copy of the old file goes to game/data/_backup first)."""
    import time
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)
    path = os.path.join(DATA_DIR, name + ".json")
    if backup and os.path.exists(path):
        bdir = os.path.join(DATA_DIR, "_backup")
        if not os.path.isdir(bdir):
            os.makedirs(bdir)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        with io.open(path, "rb") as f, io.open(os.path.join(bdir, "%s_%s.json" % (name, stamp)), "wb") as g:
            g.write(f.read())
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp, path)
