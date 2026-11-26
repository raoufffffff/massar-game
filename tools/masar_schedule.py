# -*- coding: utf-8 -*-
"""Weekly schedule of a character (editor tab "Schedule"): who is where, when, and how she is shown.

Data: game/data/schedule.json
  {"version": 1, "characters": {"ana": {"entries": [ENTRY, ...]}}}
  ENTRY = {"id", "days": [0..6], "parts": [0..3], "away": false, "place": "home", "room": "kitchen",
           "look": {"type": "pose", "pose": "cooking"} | {"type": "stand"} | {"type": "char", "char": "ana", "image": "<id>"},
           "at": {"x", "y", "scale", "flip"}   (optional: feet position on the 1920x1080 screen)}
Days: 0 Monday ... 6 Sunday.  Time slots: 0 Morning, 1 Afternoon, 2 Evening, 3 Night.
When several entries match a day + slot, the game picks ONE of them at random (the same all slot long).
"""
import copy
import glob
import os
import re

import masar_rooms

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PARTS = ["Morning", "Afternoon", "Evening", "Night"]
POSE_SUFFIX = ("_glow", "_blink", "_shy", "_smile", "_closed")
PLACE_COLORS = ["#cfe8ff", "#d8f0d0", "#ffe3c4", "#f1d4f5", "#ffd9d9", "#d9f5f0", "#fff3b8", "#e0e0ff"]
AWAY_COLOR = "#e4e4e4"
EMPTY_COLOR = "#f4f4f4"


def place_color(pid):
    """Every place has its own pastel colour in the week grid (the same place always gets the same one)."""
    return PLACE_COLORS[sum(ord(c) for c in (pid or "?")) % len(PLACE_COLORS)]


def empty():
    return {"version": 1, "characters": {"ana": {"entries": []}}}


def entries(data, who):
    return data.setdefault("characters", {}).setdefault(who, {"entries": []}).setdefault("entries", [])


def cell_entries(data, who, wd, part):
    return [e for e in entries(data, who) if wd in e.get("days", []) and part in e.get("parts", [])]


def new_id(data, who):
    used = set(e["id"] for e in entries(data, who))
    n = 1
    while "e%d" % n in used:
        n += 1
    return "e%d" % n


def pose_names(root):
    out = []
    for p in sorted(glob.glob(os.path.join(root, "game", "images", "ana", "pose_*.png"))):
        n = os.path.splitext(os.path.basename(p))[0][5:]
        if not n.endswith(POSE_SUFFIX):
            out.append(n)
    return out


def standing_picture(root):
    d = os.path.join(root, "game", "images", "ana")
    for name in ("ana_casual_neutral.png", "ana_plain_neutral.png"):
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    c = sorted(glob.glob(os.path.join(d, "ana_*_neutral.png")))
    return c[0] if c else None


def look_picture(root, look, chars):
    """(path, bottom margin in picture pixels) of the picture that shows this look, or (None, 0)."""
    t = look.get("type")
    if t == "pose":
        p = os.path.join(root, "game", "images", "ana", "pose_%s.png" % look.get("pose"))
        return (p if os.path.exists(p) else None), 0
    if t == "char":
        e = chars.get(look.get("char"), {}).get("images", {}).get(look.get("image"))
        if e:
            p = os.path.join(root, "game", e["file"])
            return (p if os.path.exists(p) else None), e.get("params", {}).get("margin", 48)
        return None, 0
    return standing_picture(root), 0


def look_text(look, chars):
    t = look.get("type")
    if t == "pose":
        return look.get("pose", "?")
    if t == "char":
        e = chars.get(look.get("char"), {}).get("images", {}).get(look.get("image"))
        return e["label"] if e else "(missing picture)"
    return "standing"


def entry_text(e, room_label, chars):
    if e.get("away"):
        return "Away"
    return "%s: %s" % (room_label(e.get("place"), e.get("room")), look_text(e.get("look", {}), chars))


def validate(root, data, room_label, rooms, chars):
    """[(kind, text)] kind = 'error' | 'warn'."""
    out = []
    known = set((p, r) for p, r, _l in rooms)
    poses = set(pose_names(root))
    for who, c in data.get("characters", {}).items():
        for e in c.get("entries", []):
            if not e.get("days") or not e.get("parts"):
                out.append(("warn", "Schedule: an entry of '%s' has no days or no time slots (it never happens)." % who))
            if e.get("away"):
                continue
            if (e.get("place"), e.get("room")) not in known:
                out.append(("error", "Schedule: '%s' is in a room that does not exist (%s / %s)." % (who, e.get("place"), e.get("room"))))
            look = e.get("look", {})
            if look.get("type") == "pose" and look.get("pose") not in poses:
                out.append(("warn", "Schedule: activity picture '%s' is missing in game/images/ana (she will just stand)." % look.get("pose")))
            if look.get("type") == "char" and look_picture(root, look, chars)[0] is None:
                out.append(("error", "Schedule: library picture %s/%s does not exist." % (look.get("char"), look.get("image"))))
    return out


# ----------------------------------------------------------------------------------------------- the tab
def build_tab(ctx):
    tk, ttk = ctx["tk"], ctx["ttk"]
    messagebox = ctx["messagebox"]
    ImageTk = ctx["ImageTk"]
    from PIL import Image
    root, nb, status, ROOT = ctx["root"], ctx["nb"], ctx["status"], ctx["ROOT"]
    rooms = ctx["rooms"]
    mark = ctx["mark"]
    masar_data = ctx["masar_data"]
    get_chars = ctx["get_chars"]                           # -> {char id: {"name", "images": {...}}}
    default_at = ctx["default_at"]                         # (look) -> {"x","y","scale","flip"} the game uses when "at" is missing
    room_start = ctx.get("room_start") or (lambda pid, rid: 0.5)      # where the view starts in a panoramic room (0..1)
    hours = ctx.get("hours") or (lambda pid, rid, part: True)         # is this room open at this time slot? (Places tab)
    GAMEDIR = os.path.join(ROOT, "game")

    try:
        data = masar_data.load("schedule")
    except IOError:
        data = empty()
    entries(data, "ana")

    try:
        import masar_core as _mc
    except Exception:                                      # noqa: BLE001
        _mc = None

    def room_ids_of(pid):
        try:
            return [r for r, _n in _mc.rooms_of(pid)]
        except Exception:                                  # noqa: BLE001
            return []

    def room_label(pid, rid):
        for p, r, lab in rooms:
            if (p, r) == (pid, rid):
                return lab
        return "%s / %s" % (pid, rid)

    def chars():
        return get_chars()

    # ------------------------------------------------------------------ pictures (thumbnails are cached)
    thumbs = {}
    pil_cache = {}

    def load_rgba(path):
        if path not in pil_cache:
            pil_cache[path] = Image.open(path).convert("RGBA")
        return pil_cache[path]

    def thumb(path, h):
        """A small picture of a character, trimmed to the body. None when the file is missing."""
        if not path or not os.path.exists(path):
            return None
        key = (path, h)
        if key not in thumbs:
            im = load_rgba(path)
            bb = im.getchannel("A").getbbox()
            if bb:
                im = im.crop(bb)
            w = max(1, int(im.width * h / float(max(1, im.height))))
            thumbs[key] = ImageTk.PhotoImage(im.resize((w, h), Image.LANCZOS))
        return thumbs[key]

    def look_thumb(look, h):
        return thumb(look_picture(ROOT, look, chars())[0], h)

    def bg_path(pid, rid, part):
        return masar_rooms.find_bg(GAMEDIR, pid, rid, part, room_ids_of(pid))

    # ------------------------------------------------------------------ warnings about an entry
    def closed_parts(e):
        """Time slots of this entry in which its room is closed (the game would send her away / hide her)."""
        if e.get("away") or not e.get("place"):
            return []
        return [p for p in e.get("parts", []) if not hours(e["place"], e["room"], p)]

    def entry_warnings(e):
        out = []
        if not e.get("days") or not e.get("parts"):
            out.append("never happens (no day or no time slot)")
        if e.get("away"):
            return out
        if (e.get("place"), e.get("room")) not in set((p, r) for p, r, _l in rooms):
            out.append("the room does not exist")
            return out
        cl = closed_parts(e)
        if cl:
            out.append("room closed at: " + ", ".join(PARTS[p] for p in cl))
        look = e.get("look", {})
        if look.get("type") == "pose" and look.get("pose") not in set(pose_names(ROOT)):
            out.append("activity picture missing (she just stands)")
        if look.get("type") == "char" and look_picture(ROOT, look, chars())[0] is None:
            out.append("library picture missing")
        if bg_path(e["place"], e["room"], (e.get("parts") or [None])[0]) is None:
            out.append("the room has no picture yet")
        return out

    # ------------------------------------------------------------------ undo
    undo_stack = []

    def snap():
        undo_stack.append(copy.deepcopy(data))
        del undo_stack[:-60]

    def undo(*_):
        if not undo_stack:
            status.set("Schedule: nothing to undo.")
            return
        old = undo_stack.pop()
        data.clear()
        data.update(old)
        mark("schedule")
        status.set("Schedule: undone.")
        refresh()

    tab = ttk.Frame(nb)
    nb.add(tab, text="Schedule")
    st = {"who": "ana", "cell": (0, 0), "keep": [], "ids": []}

    # ------------------------------------------------------------------ top bar
    top = ttk.Frame(tab)
    top.pack(fill="x", padx=8, pady=(8, 2))
    ttk.Label(top, text="Character:").pack(side="left")
    who_v = tk.StringVar(value="ana")
    who_cb = ttk.Combobox(top, textvariable=who_v, state="readonly", width=14)
    who_cb.pack(side="left", padx=(4, 14))
    btn_new = ttk.Button(top, text="+ New entry", command=lambda: add_entry())
    btn_new.pack(side="left", padx=2)
    btn_dup = ttk.Button(top, text="Duplicate", command=lambda: dup_entry())
    btn_dup.pack(side="left", padx=2)
    btn_copy = ttk.Button(top, text="Copy this slot to...", command=lambda: copy_slot())
    btn_copy.pack(side="left", padx=2)
    btn_del = ttk.Button(top, text="Delete", command=lambda: delete_entry())
    btn_del.pack(side="left", padx=2)
    ttk.Button(top, text="Undo (Ctrl+Z)", command=undo).pack(side="left", padx=(14, 2))
    summary_v = tk.StringVar()
    ttk.Label(top, textvariable=summary_v, foreground="#444").pack(side="right")
    ttk.Label(tab, foreground="#666", text="Click a time slot, then + New entry to say what she does there. Several entries in one slot = "
              "the game picks one at random (yellow). Red ! = something to check (closed room, missing picture).").pack(anchor="w", padx=10)

    # ------------------------------------------------------------------ week grid (pictures in every cell)
    CW, CH = 120, 104
    grid = ttk.Frame(tab)
    grid.pack(anchor="w", padx=8, pady=4)
    cells = {}

    class Cell(tk.Frame):
        def invoke(self):
            select_cell(*self.slot)

    ttk.Label(grid, text="").grid(row=0, column=0)
    for wd, d in enumerate(DAYS):
        ttk.Label(grid, text=d, anchor="center", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=wd + 1, sticky="we")
    for part, pn in enumerate(PARTS):
        ttk.Label(grid, text=pn, width=9).grid(row=part + 1, column=0, sticky="w")
        for wd in range(7):
            c = Cell(grid, width=CW, height=CH, highlightthickness=0, bd=0)
            c.slot = (wd, part)
            c.grid(row=part + 1, column=wd + 1, padx=1, pady=1)
            c.grid_propagate(False)
            c.pack_propagate(False)
            cells[(wd, part)] = c

    def bind_click(w, slot):
        w.bind("<Button-1>", lambda ev, slot=slot: select_cell(*slot))
        w.bind("<Double-Button-1>", lambda ev, slot=slot: (select_cell(*slot), add_entry()))

    def fill_cell(c, wd, part):
        for w in c.winfo_children():
            w.destroy()
        ents = cell_entries(data, st["who"], wd, part)
        warn = any(entry_warnings(e) for e in ents)
        if not ents:
            bg = EMPTY_COLOR
        elif len(ents) > 1:
            bg = "#fff2cc"
        elif ents[0].get("away"):
            bg = AWAY_COLOR
        else:
            bg = place_color(ents[0].get("place"))
        c.config(bg=bg, highlightthickness=3 if (wd, part) == st["cell"] else 1,
                 highlightbackground="#2a7fff" if (wd, part) == st["cell"] else "#c8c8c8")
        if not ents:
            lab = tk.Label(c, text="nobody", bg=bg, fg="#999", font=("TkDefaultFont", 9, "italic"))
            lab.pack(expand=True)
            bind_click(lab, (wd, part))
        else:
            row = tk.Frame(c, bg=bg)
            row.pack(fill="x", pady=(3, 0))
            bind_click(row, (wd, part))
            for e in ents[:3]:
                im = None if e.get("away") else look_thumb(e.get("look", {}), 46 if len(ents) == 1 else 40)
                if im is not None:
                    l = tk.Label(row, image=im, bg=bg)
                else:
                    l = tk.Label(row, text="away" if e.get("away") else "?", bg=bg, fg="#777", width=5, height=2)
                l.pack(side="left", padx=1)
                bind_click(l, (wd, part))
            e0 = ents[0]
            txt = "Away" if e0.get("away") else room_label(e0.get("place"), e0.get("room"))
            if len(ents) > 1:
                txt += "  +%d" % (len(ents) - 1)
            lab = tk.Label(c, text=txt, bg=bg, fg="#222", font=("TkDefaultFont", 8), wraplength=CW - 8, justify="left", anchor="w")
            lab.pack(fill="x", padx=3, pady=(2, 0))
            bind_click(lab, (wd, part))
        if warn:
            w = tk.Label(c, text="!", bg="#e53935", fg="white", font=("TkDefaultFont", 9, "bold"), width=2)
            w.place(relx=1.0, x=-2, y=2, anchor="ne")
            bind_click(w, (wd, part))
        bind_click(c, (wd, part))

    # ------------------------------------------------------------------ this slot: list + preview
    bot = ttk.LabelFrame(tab, text="This slot")
    bot.pack(fill="both", expand=True, padx=8, pady=6)
    style = ttk.Style()
    style.configure("Sched.Treeview", rowheight=52)
    leftb = ttk.Frame(bot)
    leftb.pack(side="left", fill="both", expand=True, padx=6, pady=6)
    lst = ttk.Treeview(leftb, columns=("where", "look", "when", "note"), show="tree headings", height=4,
                       selectmode="browse", style="Sched.Treeview")
    lst.heading("#0", text="")
    lst.column("#0", width=64, stretch=False)
    for col, txt, w in (("where", "Where", 170), ("look", "How she looks", 150), ("when", "When", 230), ("note", "Notes", 300)):
        lst.heading(col, text=txt)
        lst.column(col, width=w)
    lst.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(leftb, orient="vertical", command=lst.yview)
    sb.pack(side="left", fill="y")
    lst.configure(yscrollcommand=sb.set)
    rightb = ttk.Frame(bot)
    rightb.pack(side="left", padx=6, pady=6)
    mini = tk.Canvas(rightb, width=384, height=216, bg="#222", highlightthickness=0)
    mini.pack()
    mini_txt = tk.StringVar(value="Select an entry to see it in its room.")
    ttk.Label(rightb, textvariable=mini_txt, foreground="#555", wraplength=380).pack(anchor="w", pady=2)

    def ana_geometry(e):
        """(x, y, scale, flip) of her feet in the room (world px): the entry's own place, or the game's default."""
        look = e.get("look", {})
        a = e.get("at") or default_at(look)
        return a.get("x", 960), a.get("y", 1080), a.get("scale", 1.0), bool(a.get("flip", False))

    def render_mini(e):
        """Small picture of the entry: the room (first time slot of the entry) with her in it."""
        mini.delete("all")
        st["mini"] = None
        if e is None or e.get("away"):
            mini.create_text(192, 108, text="(she is away)" if e else "", fill="#aaa")
            return
        part = (e.get("parts") or [None])[0]
        path = bg_path(e["place"], e["room"], part)
        if not path:
            mini.create_text(192, 108, text="The room has no picture yet", fill="#ff8080")
            return
        bgim = Image.open(path).convert("RGB")
        W = max(1920, int(round(bgim.width * 1080.0 / bgim.height)))
        k = 216.0 / 1080.0
        scene = bgim.resize((int(W * k), 216), Image.LANCZOS)
        pth, mb = look_picture(ROOT, e.get("look", {}), chars())
        x, y, sc, flip = ana_geometry(e)
        if pth:
            src = load_rgba(pth)
            w, h = max(1, int(src.width * sc * k)), max(1, int(src.height * sc * k))
            im = src.resize((w, h), Image.LANCZOS)
            if flip:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            scene = scene.convert("RGBA")
            scene.alpha_composite(im, (int(x * k - w / 2.0), int(y * k + mb * sc * k - h)) if (x * k - w / 2.0) >= 0 and (y * k + mb * sc * k - h) >= 0
                                  else (max(0, int(x * k - w / 2.0)), max(0, int(y * k + mb * sc * k - h))))
            scene = scene.convert("RGB")
        # the part of the room the player sees when entering (a panorama is wider than the screen)
        home = masar_rooms.start_px(W, room_start(e["place"], e["room"])) * k
        view = scene.crop((int(home), 0, int(min(scene.width, home + 384)), 216)) if W > 1920 else scene
        st["mini"] = ImageTk.PhotoImage(view.resize((min(384, view.width), 216)))
        mini.create_image(0, 0, image=st["mini"], anchor="nw")

    def refresh():
        who = st["who"]
        for (wd, part), c in cells.items():
            fill_cell(c, wd, part)
        n_empty = sum(1 for wd in range(7) for part in range(4) if not cell_entries(data, who, wd, part))
        summary_v.set("%d of 28 slots have nobody (she is away)" % n_empty if n_empty else "every slot is filled")
        refresh_list()

    def entry_when(e):
        days = "every day" if len(e["days"]) == 7 else ", ".join(DAYS[d] for d in e["days"])
        return "%s / %s" % (days, ", ".join(PARTS[p] for p in e["parts"]))

    def refresh_list():
        for i in lst.get_children():
            lst.delete(i)
        wd, part = st["cell"]
        ents = cell_entries(data, st["who"], wd, part)
        st["ids"] = [e["id"] for e in ents]
        st["rows"] = []
        bot.config(text="%s %s: %s" % (DAYS[wd], PARTS[part].lower(),
                                       "nobody (she is away)" if not ents else "%d option%s (one is picked at random)" % (len(ents), "" if len(ents) == 1 else "s")))
        for e in ents:
            im = None if e.get("away") else look_thumb(e.get("look", {}), 44)
            if im is not None:
                st["rows"].append(im)
            w = entry_warnings(e)
            lst.insert("", "end", iid=e["id"], image=im if im is not None else "",
                       values=("Away" if e.get("away") else room_label(e.get("place"), e.get("room")),
                               "" if e.get("away") else look_text(e.get("look", {}), chars()),
                               entry_when(e),
                               ("placed by hand" if e.get("at") else "default place") if not e.get("away") else ""
                               if not w else ("! " + "; ".join(w))))
            if w:
                lst.set(e["id"], "note", "! " + "; ".join(w))
        if ents:
            lst.selection_set(ents[0]["id"])
        else:
            render_mini(None)
        on_pick()

    def on_pick(*_):
        e = sel_entry()
        render_mini(e)
        if e is not None and not e.get("away"):
            x, y, sc, flip = ana_geometry(e)
            mini_txt.set("%s (%s)" % (room_label(e["place"], e["room"]), PARTS[(e.get("parts") or [0])[0]].lower()))
        elif e is not None:
            mini_txt.set("Away: nobody can find her.")

    lst.bind("<<TreeviewSelect>>", on_pick)

    def select_cell(wd, part):
        st["cell"] = (wd, part)
        refresh()

    def sel_entry():
        s = lst.selection()
        if not s:
            return None
        for e in entries(data, st["who"]):
            if e["id"] == s[0]:
                return e
        return None

    # ------------------------------------------------------------------ the studio: one window to set everything
    def studio(e=None, new=False, title="Schedule entry"):
        """Create (e is None or new=True) or edit an entry. One window: the room is shown big with her in it, and
        everything on the right changes the picture at once. Returns the entry dict or None."""
        win = tk.Toplevel(root)
        win.title(title)
        win.transient(root)
        win.grab_set()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        SC = max(0.3, min(0.55, (sh - 250) / 1080.0, (sw - 520) / 1920.0))
        VW, VH = int(1920 * SC), int(1080 * SC)
        wd0, part0 = st["cell"]
        creating = e is None or new
        days_v = [tk.BooleanVar(value=(d in e["days"]) if e else d == wd0) for d in range(7)]
        parts_v = [tk.BooleanVar(value=(p in e["parts"]) if e else p == part0) for p in range(4)]
        away_v = tk.BooleanVar(value=bool(e and e.get("away")))
        labels = [r[2] for r in rooms]
        cur_room = room_label(e["place"], e["room"]) if e and not e.get("away") else (labels[0] if labels else "")
        room_v = tk.StringVar(value=cur_room)
        look_st = {"look": dict(e["look"]) if e and not e.get("away") else {"type": "stand"}}
        pose_list = pose_names(ROOT)
        if not e and pose_list:
            look_st["look"] = {"type": "pose", "pose": pose_list[0]}
        at_state = {"at": dict(e["at"]) if e and e.get("at") else None}
        prev_v = tk.StringVar(value="Automatic")
        keep = {"bg": None, "ana": {}, "path": None}

        # ---- left: the room
        left = ttk.Frame(win)
        left.grid(row=0, column=0, sticky="nw", padx=(8, 4), pady=8)
        cv = tk.Canvas(left, width=VW, height=VH, bg="#222", highlightthickness=0, xscrollincrement=20)
        cv.pack()
        hbar = ttk.Scrollbar(left, orient="horizontal", command=cv.xview)
        hbar.pack(fill="x")
        cv.configure(xscrollcommand=hbar.set)
        help_v = tk.StringVar(value="Click or drag in the room: her FEET (red dot) go there.  Mouse wheel = her size.  "
                                    "Shift + wheel scrolls a panoramic room.")
        ttk.Label(left, textvariable=help_v, foreground="#666", wraplength=VW).pack(anchor="w", pady=2)
        pos_v = tk.StringVar()
        ttk.Label(left, textvariable=pos_v, foreground="#333").pack(anchor="w")
        row = ttk.Frame(left)
        row.pack(fill="x", pady=2)
        sv = tk.DoubleVar(value=1.0)
        fv = tk.BooleanVar(value=False)
        ttk.Label(row, text="Size").pack(side="left")
        ttk.Scale(row, from_=0.05, to=1.6, variable=sv, orient="horizontal", length=260).pack(side="left", padx=6)
        ttk.Checkbutton(row, text="Mirror", variable=fv).pack(side="left", padx=8)
        ttk.Button(row, text="Use the default place", command=lambda: (at_state.update(at=None), redraw(reset=True))).pack(side="left", padx=8)
        trow = ttk.Frame(left)
        trow.pack(fill="x", pady=2)
        ttk.Label(trow, text="Show the room at:").pack(side="left")
        ttk.Combobox(trow, textvariable=prev_v, values=["Automatic"] + list(masar_rooms.TIME_LABELS) + ["Plain picture"],
                     state="readonly", width=14).pack(side="left", padx=6)

        # ---- right: when, where, how she looks
        right = ttk.Frame(win)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        win.columnconfigure(1, weight=1)
        win.rowconfigure(0, weight=1)
        fr = ttk.LabelFrame(right, text="1. When")
        fr.pack(fill="x", pady=(0, 6))
        dr = ttk.Frame(fr)
        dr.pack(anchor="w", padx=4, pady=2)
        for i, d in enumerate(DAYS):
            ttk.Checkbutton(dr, text=d, variable=days_v[i], command=lambda: redraw()).pack(side="left", padx=1)
        q = ttk.Frame(fr)
        q.pack(anchor="w", padx=4)

        def f_days(vals):
            for i, v in enumerate(days_v):
                v.set(i in vals)
            redraw()

        for txt, vals in (("Every day", range(7)), ("Weekdays", range(5)), ("Weekend", [5, 6])):
            ttk.Button(q, text=txt, command=lambda vals=vals: f_days(vals)).pack(side="left", padx=2)
        pr = ttk.Frame(fr)
        pr.pack(anchor="w", padx=4, pady=3)
        for i, pn in enumerate(PARTS):
            ttk.Checkbutton(pr, text=pn, variable=parts_v[i], command=lambda: redraw(reset=False)).pack(side="left", padx=1)

        fw = ttk.LabelFrame(right, text="2. Where")
        fw.pack(fill="x", pady=6)
        room_cb = ttk.Combobox(fw, textvariable=room_v, values=labels, state="readonly", width=40)
        room_cb.pack(anchor="w", padx=6, pady=(4, 2))
        ttk.Checkbutton(fw, text="She is away (nobody can find her)", variable=away_v, command=lambda: redraw()).pack(anchor="w", padx=6, pady=(0, 4))

        fl = ttk.LabelFrame(right, text="3. How she looks (click a picture)")
        fl.pack(fill="both", expand=True, pady=6)
        gcv = tk.Canvas(fl, width=460, height=250, highlightthickness=0)
        gsb = ttk.Scrollbar(fl, orient="vertical", command=gcv.yview)
        gcv.configure(yscrollcommand=gsb.set)
        gsb.pack(side="right", fill="y")
        gcv.pack(side="left", fill="both", expand=True)
        gin = ttk.Frame(gcv)
        gcv.create_window((0, 0), window=gin, anchor="nw")
        gin.bind("<Configure>", lambda ev: gcv.configure(scrollregion=gcv.bbox("all")))
        gal = []                                            # (button, look)

        def same_look(a, b):
            return a.get("type") == b.get("type") and a.get("pose") == b.get("pose") and a.get("char") == b.get("char") \
                and a.get("image") == b.get("image")

        def pick_look(look):
            old = look_st["look"]
            look_st["look"] = look
            for b, lk in gal:
                b.config(relief="solid" if same_look(lk, look) else "flat", bg="#bfe0ff" if same_look(lk, look) else "#f0f0f0")
            if at_state["at"] is not None and not same_look(old, look):      # keep where she stands, fit the size to the new picture
                at_state["at"]["scale"] = default_at(look).get("scale", at_state["at"]["scale"])
            redraw(reset=at_state["at"] is not None and not same_look(old, look))

        def add_section(title_, items, r0):
            ttk.Label(gin, text=title_, font=("TkDefaultFont", 9, "bold")).grid(row=r0, column=0, columnspan=5, sticky="w", pady=(6, 1))
            r, c = r0 + 1, 0
            for caption, look in items:
                im = look_thumb(look, 78)
                f = tk.Button(gin, image=im, text=caption, compound="top", font=("TkDefaultFont", 7), width=84 if im else 12,
                              wraplength=84, relief="flat", bg="#f0f0f0", command=lambda look=look: pick_look(dict(look)))
                if im is not None:
                    f.image = im
                f.grid(row=r, column=c, padx=2, pady=2)
                gal.append((f, look))
                c += 1
                if c == 5:
                    c, r = 0, r + 1
            return r + 1

        ch = chars()
        rr = add_section("Standing", [("standing", {"type": "stand"})], 0)
        if pose_list:
            rr = add_section("Activity pictures (photo scene poses)", [(n, {"type": "pose", "pose": n}) for n in pose_list], rr)
        for cid, cd in ch.items():
            items = [("%s" % v["label"], {"type": "char", "char": cid, "image": k}) for k, v in cd.get("images", {}).items()]
            if items:
                rr = add_section("Library: %s" % cd.get("name", cid), items, rr)

        def wheel_g(ev):
            gcv.yview_scroll(-1 if (getattr(ev, "delta", 0) > 0 or getattr(ev, "num", 0) == 4) else 1, "units")

        for wdg in (gcv, gin):
            wdg.bind("<MouseWheel>", wheel_g)
            wdg.bind("<Button-4>", wheel_g)
            wdg.bind("<Button-5>", wheel_g)

        warn_v = tk.StringVar()
        warn_l = tk.Label(right, textvariable=warn_v, fg="#c62828", justify="left", anchor="w", wraplength=440)
        warn_l.pack(fill="x", pady=2)
        out = {"v": None}

        def selected_parts():
            return [i for i, v in enumerate(parts_v) if v.get()]

        def room_pair():
            lab = room_v.get()
            pair = [(p, rr_) for p, rr_, l in rooms if l == lab]
            return pair[0] if pair else None

        def cur_part():
            """Which time of day the preview shows."""
            v = prev_v.get()
            if v in masar_rooms.TIME_LABELS:
                return masar_rooms.TIME_LABELS.index(v)
            if v == "Plain picture":
                return None
            sp = selected_parts()
            return sp[0] if sp else None

        # ---- the preview
        state = {"W": 1920, "home": 0, "pair": None, "part": "x"}
        cur = {"x": 960, "y": 1080, "scale": 1.0, "flip": False}

        def load_room():
            pair = room_pair()
            part = cur_part()
            if pair == state["pair"] and part == state["part"]:
                return False
            state["pair"], state["part"] = pair, part
            keep["bg"] = None
            if pair is None or away_v.get():
                state["W"] = 1920
                return True
            ri = masar_rooms.info(GAMEDIR, pair[0], pair[1], part, room_ids_of(pair[0]))
            state["W"] = ri["W"]
            state["home"] = masar_rooms.start_px(ri["W"], room_start(pair[0], pair[1]))
            if ri["path"]:
                keep["bg"] = ImageTk.PhotoImage(Image.open(ri["path"]).convert("RGB").resize((int(ri["W"] * SC), VH), Image.LANCZOS))
            cv.configure(scrollregion=(0, 0, int(ri["W"] * SC), VH))
            cv.xview_moveto(state["home"] / float(ri["W"]) if ri["W"] > 1920 else 0)      # open on the view the player starts with
            return True

        def init_position():
            """Her place: the entry's own, or the game's default for this picture (relative to the start view)."""
            if at_state["at"]:
                cur.update(at_state["at"])
            else:
                d = dict(default_at(look_st["look"]))
                d["x"] = int(d["x"] + (state["home"] if state["W"] > 1920 else 0))
                cur.update(d)
            sv.set(cur.get("scale", 1.0))
            fv.set(bool(cur.get("flip", False)))

        def redraw(*_, reset=False):
            changed = load_room()
            if changed or reset:
                init_position()
            cur["scale"] = round(sv.get(), 3)
            cur["flip"] = fv.get()
            W = state["W"]
            cv.delete("all")
            if away_v.get():
                cv.create_text(VW // 2, VH // 2, text="She is away: nobody finds her anywhere in this slot.", fill="#ddd", font=("TkDefaultFont", 14))
            else:
                if keep["bg"] is not None:
                    cv.create_image(0, 0, image=keep["bg"], anchor="nw")
                else:
                    cv.create_text(VW // 2, VH // 2, text="This room has no picture yet (images/bg/<place>_<room>.jpg)", fill="#ff9090")
                if W > 1920:
                    cv.create_rectangle(state["home"] * SC, 1, state["home"] * SC + VW, VH - 1, outline="#00e5ff", dash=(6, 4), width=2)
                pth, mb = look_picture(ROOT, look_st["look"], chars())
                if pth:
                    k = (pth, round(cur["scale"], 2), cur["flip"])
                    if k not in keep["ana"]:
                        src = load_rgba(pth)
                        w, h = max(1, int(src.width * cur["scale"] * SC)), max(1, int(src.height * cur["scale"] * SC))
                        im = src.resize((w, h), Image.LANCZOS)
                        if cur["flip"]:
                            im = im.transpose(Image.FLIP_LEFT_RIGHT)
                        keep["ana"] = {k: ImageTk.PhotoImage(im)}
                    cv.create_image(cur["x"] * SC, cur["y"] * SC + mb * cur["scale"] * SC, image=keep["ana"][k], anchor="s")
                else:
                    cv.create_rectangle(cur["x"] * SC - 30, cur["y"] * SC - 90, cur["x"] * SC + 30, cur["y"] * SC, fill="#888")
                cv.create_oval(cur["x"] * SC - 4, cur["y"] * SC - 4, cur["x"] * SC + 4, cur["y"] * SC + 4, fill="#ff3b6b", outline="")
            custom = "placed by hand" if at_state["at"] else "the game's default place"
            pos_v.set("Feet at x=%d, y=%d, size %.2f%s   -   %s" % (cur["x"], cur["y"], cur["scale"], ", mirrored" if cur["flip"] else "", custom))
            # live check of what is set now
            msgs = []
            pr_ = room_pair()
            sp = selected_parts()
            if not away_v.get() and pr_:
                cl = [p for p in sp if not hours(pr_[0], pr_[1], p)]
                if cl:
                    msgs.append("This room is closed at: %s (see the Places tab). She would not be there." % ", ".join(PARTS[p] for p in cl))
                if keep["bg"] is None:
                    msgs.append("This room has no picture yet.")
            if not any(v.get() for v in days_v) or not sp:
                msgs.append("Tick at least one day and one time slot.")
            warn_v.set("\n".join("! " + m for m in msgs))

        def place_at(ev):
            if ev.x > VW - 20:
                cv.xview_scroll(1, "units")
            elif ev.x < 20:
                cv.xview_scroll(-1, "units")
            cur["x"] = int(max(0, min(state["W"], cv.canvasx(ev.x) / SC)))
            cur["y"] = int(max(0, min(1500, ev.y / SC)))
            at_state["at"] = {"x": cur["x"], "y": cur["y"], "scale": round(sv.get(), 3), "flip": bool(fv.get())}
            redraw()

        def wheel(ev):
            up = getattr(ev, "delta", 0) > 0 or getattr(ev, "num", 0) == 4
            if ev.state & 0x1:                               # Shift + wheel: scroll a wide room
                cv.xview_scroll(-3 if up else 3, "units")
                return
            sv.set(max(0.05, min(1.6, sv.get() + (0.02 if up else -0.02))))
            if at_state["at"]:
                at_state["at"]["scale"] = round(sv.get(), 3)
            redraw()

        def size_changed(*_):
            if at_state["at"] is None and abs(sv.get() - cur.get("scale", 1.0)) > 1e-6:
                at_state["at"] = {"x": cur["x"], "y": cur["y"], "scale": round(sv.get(), 3), "flip": bool(fv.get())}
            elif at_state["at"]:
                at_state["at"]["scale"] = round(sv.get(), 3)
                at_state["at"]["flip"] = bool(fv.get())
            redraw()

        cv.bind("<Button-1>", place_at)
        cv.bind("<B1-Motion>", place_at)
        cv.bind("<MouseWheel>", wheel)
        cv.bind("<Button-4>", wheel)
        cv.bind("<Button-5>", wheel)
        sv.trace_add("write", lambda *a: size_changed())
        fv.trace_add("write", lambda *a: size_changed())
        room_cb.bind("<<ComboboxSelected>>", lambda ev: redraw(reset=True))
        for v in parts_v + days_v:
            pass

        def ok():
            days = [i for i, v in enumerate(days_v) if v.get()]
            parts = selected_parts()
            if not days or not parts:
                messagebox.showerror("Schedule", "Tick at least one day and one time slot.", parent=win)
                return
            ent = {"id": new_id(data, st["who"]) if creating else e["id"], "days": days, "parts": parts, "away": bool(away_v.get())}
            if away_v.get():
                ent.update(place=None, room=None, look={"type": "stand"})
            else:
                pair = room_pair()
                if not pair:
                    messagebox.showerror("Schedule", "Choose where she is.", parent=win)
                    return
                lk = look_st["look"]
                if lk["type"] == "char" and (not lk.get("image") or look_picture(ROOT, lk, chars())[0] is None):
                    messagebox.showerror("Schedule", "Choose a picture of the library (add one in the Characters tab).", parent=win)
                    return
                if lk["type"] == "pose" and not lk.get("pose"):
                    messagebox.showerror("Schedule", "Choose an activity picture.", parent=win)
                    return
                ent.update(place=pair[0], room=pair[1], look=dict(lk))
                if at_state["at"]:
                    ent["at"] = {"x": int(at_state["at"]["x"]), "y": int(at_state["at"]["y"]),
                                 "scale": round(float(sv.get()), 3), "flip": bool(fv.get())}
            out["v"] = ent
            win.destroy()

        brow = ttk.Frame(right)
        brow.pack(fill="x", pady=(4, 0))
        ttk.Button(brow, text="Save entry", command=ok).pack(side="right", padx=4)
        ttk.Button(brow, text="Cancel", command=win.destroy).pack(side="right", padx=4)
        win.bind("<Escape>", lambda ev: win.destroy())
        win.bind("<Return>", lambda ev: ok())
        pick_look(look_st["look"])
        redraw(reset=True)
        win.update_idletasks()
        win.geometry("+%d+%d" % (max(0, (sw - win.winfo_reqwidth()) // 2), max(0, (sh - win.winfo_reqheight()) // 3)))
        root.wait_window(win)
        return out["v"]

    # ------------------------------------------------------------------ actions
    def add_entry():
        ent = studio(None, title="New schedule entry: %s %s" % (DAYS[st["cell"][0]], PARTS[st["cell"][1]].lower()))
        if ent:
            snap()
            entries(data, st["who"]).append(ent)
            mark("schedule")
            refresh()

    def edit_entry():
        e = sel_entry()
        if not e:
            messagebox.showinfo("Schedule", "Select an entry in the list first (or click + New entry).")
            return
        ent = studio(e, title="Edit schedule entry")
        if ent:
            snap()
            lst_ = entries(data, st["who"])
            lst_[lst_.index(e)] = ent
            mark("schedule")
            refresh()

    def dup_entry():
        e = sel_entry()
        if not e:
            messagebox.showinfo("Schedule", "Select an entry in the list first.")
            return
        ent = studio(copy.deepcopy(e), new=True, title="Duplicate: change what you want, then save")
        if ent:
            snap()
            entries(data, st["who"]).append(ent)
            mark("schedule")
            refresh()

    def delete_entry():
        e = sel_entry()
        if not e:
            return
        span = "%d day(s) x %d slot(s)" % (len(e["days"]), len(e["parts"]))
        if messagebox.askyesno("Schedule", "Delete this entry? It covers %s, not only the selected slot." % span):
            snap()
            entries(data, st["who"]).remove(e)
            mark("schedule")
            refresh()

    def copy_slot():
        """Copy everything that happens in the selected slot to other days / time slots."""
        wd, part = st["cell"]
        src = cell_entries(data, st["who"], wd, part)
        if not src:
            messagebox.showinfo("Schedule", "This slot is empty: nothing to copy.")
            return
        win = tk.Toplevel(root)
        win.title("Copy this slot to...")
        win.transient(root)
        win.grab_set()
        dv = [tk.BooleanVar(value=False) for _ in range(7)]
        pv = [tk.BooleanVar(value=False) for _ in range(4)]
        ttk.Label(win, text="Copy the %d entr%s of %s %s to:" % (len(src), "y" if len(src) == 1 else "ies", DAYS[wd], PARTS[part].lower())).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        fr = ttk.Frame(win)
        fr.grid(row=1, column=0, padx=10)
        for i, d in enumerate(DAYS):
            ttk.Checkbutton(fr, text=d, variable=dv[i]).pack(side="left", padx=1)
        fq = ttk.Frame(win)
        fq.grid(row=2, column=0, padx=10, pady=2, sticky="w")

        def setd(vals):
            for i, v in enumerate(dv):
                v.set(i in vals)

        for txt, vals in (("Every day", range(7)), ("Weekdays", range(5)), ("Weekend", [5, 6])):
            ttk.Button(fq, text=txt, command=lambda vals=vals: setd(vals)).pack(side="left", padx=2)
        fp = ttk.Frame(win)
        fp.grid(row=3, column=0, padx=10, pady=6, sticky="w")
        for i, pn in enumerate(PARTS):
            ttk.Checkbutton(fp, text=pn, variable=pv[i]).pack(side="left", padx=1)

        def go():
            days = [i for i, v in enumerate(dv) if v.get()]
            parts = [i for i, v in enumerate(pv) if v.get()]
            if not days or not parts:
                messagebox.showerror("Schedule", "Tick at least one day and one time slot.", parent=win)
                return
            snap()
            for e in src:
                c = copy.deepcopy(e)
                c["id"] = new_id(data, st["who"])
                c["days"], c["parts"] = days, parts
                entries(data, st["who"]).append(c)
            mark("schedule")
            win.destroy()
            refresh()

        b = ttk.Frame(win)
        b.grid(row=4, column=0, pady=8)
        ttk.Button(b, text="Copy", command=go).pack(side="left", padx=6)
        ttk.Button(b, text="Cancel", command=win.destroy).pack(side="left", padx=6)
        win.bind("<Escape>", lambda ev: win.destroy())
        root.wait_window(win)

    lst.bind("<Double-Button-1>", lambda ev: edit_entry())
    lst.bind("<Return>", lambda ev: edit_entry())
    lst.bind("<Delete>", lambda ev: delete_entry())

    def on_key(fn):
        """Keyboard shortcuts work only while the Schedule tab is open."""
        def h(ev):
            try:
                if nb.select() == str(tab):
                    fn()
            except Exception:                                # noqa: BLE001
                pass
        return h

    root.bind("<Control-z>", on_key(undo), add="+")
    root.bind("<Control-d>", on_key(dup_entry), add="+")

    def change_who(*_):
        st["who"] = who_v.get() or "ana"
        entries(data, st["who"])
        refresh()

    def refresh_who():
        ids = ["ana"] + [c for c in chars() if c != "ana"]
        who_cb["values"] = ids

    who_cb.bind("<<ComboboxSelected>>", change_who)
    refresh_who()
    refresh()
    return dict(data=data, refresh=refresh, select=select_cell, state=st, add_dialog=studio, place_dialog=studio,
                cells=cells, lst=lst, undo=undo, snapshot=snap, copy_slot=copy_slot, studio=studio, entry_warnings=entry_warnings,
                validate=lambda chars_: validate(ROOT, data, room_label, rooms, chars_))
