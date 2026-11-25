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
import glob
import os
import re

import masar_rooms

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PARTS = ["Morning", "Afternoon", "Evening", "Night"]
POSE_SUFFIX = ("_glow", "_blink", "_shy", "_smile", "_closed")


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

    try:
        data = masar_data.load("schedule")
    except IOError:
        data = empty()
    entries(data, "ana")

    def room_label(pid, rid):
        for p, r, lab in rooms:
            if (p, r) == (pid, rid):
                return lab
        return "%s / %s" % (pid, rid)

    tab = ttk.Frame(nb)
    nb.add(tab, text="Schedule")
    st = {"who": "ana", "cell": (0, 0), "keep": [], "ids": []}

    top = ttk.Frame(tab)
    top.pack(fill="x", padx=8, pady=6)
    ttk.Label(top, text="Character:").pack(side="left")
    who_v = tk.StringVar(value="ana")
    who_cb = ttk.Combobox(top, textvariable=who_v, state="readonly", width=18)
    who_cb.pack(side="left", padx=6)
    ttk.Label(top, foreground="#666", text="  Click a time slot, then add what she does there. "
              "If several things are set for one slot, the game picks one at random.").pack(side="left")

    grid = ttk.Frame(tab)
    grid.pack(anchor="w", padx=8)
    cells = {}
    ttk.Label(grid, text="").grid(row=0, column=0)
    for wd, d in enumerate(DAYS):
        ttk.Label(grid, text=d, anchor="center", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=wd + 1, sticky="we")
    for part, pn in enumerate(PARTS):
        ttk.Label(grid, text=pn, width=10).grid(row=part + 1, column=0, sticky="w")
        for wd in range(7):
            b = tk.Button(grid, width=16, height=5, wraplength=118, justify="left", anchor="nw", relief="groove",
                          command=lambda wd=wd, part=part: select_cell(wd, part))
            b.grid(row=part + 1, column=wd + 1, padx=1, pady=1)
            cells[(wd, part)] = b

    bot = ttk.LabelFrame(tab, text="This slot")
    bot.pack(fill="both", expand=True, padx=8, pady=8)
    lst = tk.Listbox(bot, height=6, width=90, exportselection=False)
    lst.pack(side="left", fill="both", expand=True, padx=6, pady=6)
    bb = ttk.Frame(bot)
    bb.pack(side="left", padx=6)

    def chars():
        return get_chars()

    def refresh_who():
        ids = ["ana"] + [c for c in chars() if c != "ana"]
        who_cb["values"] = ids

    def refresh():
        who = st["who"]
        for (wd, part), b in cells.items():
            ents = cell_entries(data, who, wd, part)
            if not ents:
                b.config(text="nobody", bg="#e6e6e6", fg="#888")
            else:
                lines = [entry_text(e, room_label, chars()) for e in ents[:3]]
                if len(ents) > 3:
                    lines.append("+%d more" % (len(ents) - 3))
                b.config(text="\n".join(lines), bg="#dff0d8" if len(ents) == 1 else "#fff2cc", fg="#000")
            b.config(highlightthickness=3 if (wd, part) == st["cell"] else 0, highlightbackground="#2a7fff", highlightcolor="#2a7fff")
        refresh_list()

    def refresh_list():
        lst.delete(0, "end")
        wd, part = st["cell"]
        ents = cell_entries(data, st["who"], wd, part)
        st["ids"] = [e["id"] for e in ents]
        bot.config(text="%s %s: %s" % (DAYS[wd], PARTS[part].lower(),
                                       "nobody (she is away)" if not ents else "%d option%s (one is picked at random)" % (len(ents), "" if len(ents) == 1 else "s")))
        for e in ents:
            span = "%s / %s" % (", ".join(DAYS[d] for d in e["days"]) if len(e["days"]) < 7 else "every day",
                                ", ".join(PARTS[p] for p in e["parts"]))
            lst.insert("end", "%s     [%s]%s" % (entry_text(e, room_label, chars()), span, "   (placed)" if e.get("at") else ""))

    def select_cell(wd, part):
        st["cell"] = (wd, part)
        refresh()

    def sel_entry():
        s = lst.curselection()
        if not s:
            return None
        for e in entries(data, st["who"]):
            if e["id"] == st["ids"][s[0]]:
                return e
        return None

    # ---- placement dialog
    def dialog_place(look, rid_pair, at, part=None):
        """Drag her in the room; returns {"x","y","scale","flip"} or None."""
        win = tk.Toplevel(root)
        win.title("Place her in the room")
        win.grab_set()
        SC = 0.5
        pid, rid = rid_pair
        GAMEDIR = os.path.join(ROOT, "game")
        try:
            import masar_core as _mc
            room_ids = [r for r, _n in _mc.rooms_of(pid)]
        except Exception:
            room_ids = []
        ri = masar_rooms.info(GAMEDIR, pid, rid, part, room_ids)
        W = ri["W"]                                        # world width: 1920, or wider in a panoramic room
        cw = int(W * SC)
        cv = tk.Canvas(win, width=960, height=540, bg="#222", highlightthickness=0, xscrollincrement=20,
                       scrollregion=(0, 0, cw, 540))
        cv.pack(padx=8, pady=(8, 0))
        hbar = ttk.Scrollbar(win, orient="horizontal", command=cv.xview)
        hbar.pack(fill="x", padx=8)
        cv.configure(xscrollcommand=hbar.set)
        home = masar_rooms.start_px(W, room_start(pid, rid))
        bgh = {"img": None}

        def load_bg(p_):
            """The room picture of a time slot (p_ None = the plain picture)."""
            r2 = masar_rooms.info(GAMEDIR, pid, rid, p_, room_ids)
            bgh["img"] = ImageTk.PhotoImage(Image.open(r2["path"]).convert("RGB").resize((cw, 540), Image.LANCZOS)) if r2["path"] else None
        load_bg(part)
        trow = ttk.Frame(win)
        trow.pack(anchor="w", padx=8)
        ttk.Label(trow, text="Show the picture of:").pack(side="left")
        tv = tk.StringVar(value=masar_rooms.TIME_LABELS[part] if part is not None else "Plain picture")
        tb = ttk.Combobox(trow, textvariable=tv, values=["Plain picture"] + list(masar_rooms.TIME_LABELS), state="readonly", width=16)
        tb.pack(side="left", padx=6)
        path, mb = look_picture(ROOT, look, chars())
        src = Image.open(path).convert("RGBA") if path else None
        if at:
            cur = dict(at)
        else:                                              # the game's own default spot (relative to the start view)
            cur = dict(default_at(look))
            cur["x"] = int(cur["x"] + home)
        sv = tk.DoubleVar(value=cur.get("scale", 1.0))
        fv = tk.BooleanVar(value=bool(cur.get("flip", False)))
        keep = {}

        def draw(*_):
            cv.delete("all")
            if bgh["img"]:
                cv.create_image(0, 0, image=bgh["img"], anchor="nw")
            if W > 1920:                                    # the screen the player sees when entering the room
                cv.create_rectangle(home * SC, 1, home * SC + 960, 539, outline="#00e5ff", dash=(6, 4), width=2)
            s = sv.get()
            cur["scale"] = round(s, 3)
            cur["flip"] = fv.get()
            if src is not None:
                w, h = max(1, int(src.width * s * SC)), max(1, int(src.height * s * SC))
                im = src.resize((w, h), Image.LANCZOS)
                if fv.get():
                    im = im.transpose(Image.FLIP_LEFT_RIGHT)
                keep["im"] = ImageTk.PhotoImage(im)
                bottom = cur["y"] * SC + mb * s * SC
                cv.create_image(cur["x"] * SC, bottom, image=keep["im"], anchor="s")
            else:
                cv.create_rectangle(cur["x"] * SC - 40, cur["y"] * SC - 120, cur["x"] * SC + 40, cur["y"] * SC, fill="#888")
            cv.create_oval(cur["x"] * SC - 4, cur["y"] * SC - 4, cur["x"] * SC + 4, cur["y"] * SC + 4, fill="#ff3b6b", outline="")

        def drag(ev):
            if ev.x > 940:                                  # dragging near the edge scrolls the picture
                cv.xview_scroll(1, "units")
            elif ev.x < 20:
                cv.xview_scroll(-1, "units")
            cur["x"] = int(max(0, min(W, cv.canvasx(ev.x) / SC)))
            cur["y"] = int(max(0, min(1500, ev.y / SC)))
            draw()

        def wheel(ev):
            d = 0.02 if (getattr(ev, "delta", 0) > 0 or getattr(ev, "num", 0) == 4) else -0.02
            sv.set(max(0.05, min(1.6, sv.get() + d)))
            draw()

        cv.bind("<Button-1>", drag)
        cv.bind("<B1-Motion>", drag)
        cv.bind("<MouseWheel>", wheel)
        cv.bind("<Button-4>", wheel)
        cv.bind("<Button-5>", wheel)
        row = ttk.Frame(win)
        row.pack(fill="x", padx=8)
        ttk.Label(row, text="Size").pack(side="left")
        ttk.Scale(row, from_=0.05, to=1.6, variable=sv, orient="horizontal", length=320, command=draw).pack(side="left", padx=6)
        ttk.Checkbutton(row, text="Mirror", variable=fv, command=draw).pack(side="left", padx=10)
        ttk.Label(win, foreground="#666", wraplength=900,
                  text="Click or drag to put her FEET (red dot) on the floor. Mouse wheel or the slider changes her size. "
                       "The picture is the room as the player sees it (half size here). In a panoramic room use the bar "
                       "under the picture (or drag to the edge) to scroll; the dashed frame is what the player sees when entering."
                  ).pack(anchor="w", padx=8, pady=4)
        out = {"v": None}

        def ok():
            out["v"] = {"x": int(cur["x"]), "y": int(cur["y"]), "scale": round(sv.get(), 3), "flip": bool(fv.get())}
            win.destroy()

        brow = ttk.Frame(win)
        brow.pack(pady=8)
        ttk.Button(brow, text="OK", command=ok).pack(side="left", padx=6)
        ttk.Button(brow, text="Cancel", command=win.destroy).pack(side="left", padx=6)
        tb.bind("<<ComboboxSelected>>", lambda e: (load_bg(masar_rooms.TIME_LABELS.index(tv.get()) if tv.get() in masar_rooms.TIME_LABELS else None), draw()))
        draw()
        cv.xview_moveto(min(1.0, home * SC / float(cw)) if cw else 0.0)
        root.wait_window(win)
        return out["v"]

    # ---- entry dialog
    def dialog_entry(e=None):
        """Create (e is None) or edit an entry. Returns the entry dict or None."""
        win = tk.Toplevel(root)
        win.title("Schedule entry")
        win.grab_set()
        wd0, part0 = st["cell"]
        days_v = [tk.BooleanVar(value=(d in e["days"]) if e else d == wd0) for d in range(7)]
        parts_v = [tk.BooleanVar(value=(p in e["parts"]) if e else p == part0) for p in range(4)]
        away_v = tk.BooleanVar(value=bool(e and e.get("away")))
        labels = [r[2] for r in rooms]
        cur_room = room_label(e["place"], e["room"]) if e and not e.get("away") else (labels[0] if labels else "")
        room_v = tk.StringVar(value=cur_room)
        look = dict(e["look"]) if e else {"type": "pose", "pose": ""}
        type_v = tk.StringVar(value=look.get("type", "stand"))
        poses = pose_names(ROOT)
        pose_v = tk.StringVar(value=look.get("pose") or (poses[0] if poses else ""))
        ch = chars()
        char_ids = list(ch)
        char_v = tk.StringVar(value=look.get("char") or (char_ids[0] if char_ids else ""))
        img_v = tk.StringVar()
        at_state = {"at": dict(e["at"]) if e and e.get("at") else None}

        def img_choices():
            c = ch.get(char_v.get(), {}).get("images", {})
            return ["%s  [%s]" % (v["label"], k) for k, v in c.items()], list(c)

        def f_days(vals):
            for i, v in enumerate(days_v):
                v.set(i in vals)

        r = 0
        fr = ttk.LabelFrame(win, text="When")
        fr.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        for i, d in enumerate(DAYS):
            ttk.Checkbutton(fr, text=d, variable=days_v[i]).grid(row=0, column=i, padx=3)
        q = ttk.Frame(fr)
        q.grid(row=1, column=0, columnspan=7, sticky="w", pady=2)
        ttk.Button(q, text="Every day", width=10, command=lambda: f_days(range(7))).pack(side="left", padx=2)
        ttk.Button(q, text="Weekdays", width=10, command=lambda: f_days(range(5))).pack(side="left", padx=2)
        ttk.Button(q, text="Weekend", width=10, command=lambda: f_days([5, 6])).pack(side="left", padx=2)
        pr = ttk.Frame(fr)
        pr.grid(row=2, column=0, columnspan=7, sticky="w", pady=2)
        for i, pn in enumerate(PARTS):
            ttk.Checkbutton(pr, text=pn, variable=parts_v[i]).pack(side="left", padx=6)

        fw = ttk.LabelFrame(win, text="Where")
        fw.grid(row=1, column=0, sticky="we", padx=8, pady=6)
        ttk.Checkbutton(fw, text="She is away (not found anywhere)", variable=away_v).grid(row=0, column=0, sticky="w", padx=4)
        ttk.Combobox(fw, textvariable=room_v, values=labels, state="readonly", width=34).grid(row=1, column=0, sticky="w", padx=4, pady=3)

        fl = ttk.LabelFrame(win, text="How she looks")
        fl.grid(row=2, column=0, sticky="we", padx=8, pady=6)
        ttk.Radiobutton(fl, text="Activity picture (a photo scene pose):", variable=type_v, value="pose").grid(row=0, column=0, sticky="w")
        ttk.Combobox(fl, textvariable=pose_v, values=poses, state="readonly", width=20).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(fl, text="Standing (her normal picture)", variable=type_v, value="stand").grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(fl, text="A picture of the library:", variable=type_v, value="char").grid(row=2, column=0, sticky="w")
        lib = ttk.Frame(fl)
        lib.grid(row=2, column=1, sticky="w")
        char_cb = ttk.Combobox(lib, textvariable=char_v, values=char_ids, state="readonly", width=12)
        char_cb.pack(side="left")
        img_cb = ttk.Combobox(lib, textvariable=img_v, state="readonly", width=30)
        img_cb.pack(side="left", padx=4)

        def fill_imgs(*_):
            labs, ids = img_choices()
            img_cb["values"] = labs
            want = look.get("image")
            if want in ids and not img_v.get():
                img_v.set(labs[ids.index(want)])
            elif labs and img_v.get() not in labs:
                img_v.set(labs[0])

        char_cb.bind("<<ComboboxSelected>>", lambda ev: (img_v.set(""), fill_imgs()))
        fill_imgs()

        fp = ttk.LabelFrame(win, text="Where she stands in the room")
        fp.grid(row=3, column=0, sticky="we", padx=8, pady=6)
        at_txt = tk.StringVar()

        def upd_at():
            a = at_state["at"]
            at_txt.set("custom: x=%d y=%d size=%.2f%s" % (a["x"], a["y"], a["scale"], " mirrored" if a.get("flip") else "") if a
                       else "default (the game's usual place for this picture)")

        def cur_look():
            t = type_v.get()
            if t == "pose":
                return {"type": "pose", "pose": pose_v.get()}
            if t == "char":
                labs, ids = img_choices()
                return {"type": "char", "char": char_v.get(), "image": ids[labs.index(img_v.get())] if img_v.get() in labs else ""}
            return {"type": "stand"}

        def place():
            lab = room_v.get()
            pair = [(p, rr) for p, rr, l in rooms if l == lab]
            if not pair:
                return
            chosen_parts = [i for i, v in enumerate(parts_v) if v.get()]
            res = dialog_place(cur_look(), pair[0], at_state["at"], chosen_parts[0] if chosen_parts else None)
            if res:
                at_state["at"] = res
                upd_at()

        ttk.Label(fp, textvariable=at_txt).grid(row=0, column=0, columnspan=2, sticky="w", padx=4)
        ttk.Button(fp, text="Place her in the room...", command=place).grid(row=1, column=0, padx=4, pady=3)
        ttk.Button(fp, text="Use the default place", command=lambda: (at_state.update(at=None), upd_at())).grid(row=1, column=1, padx=4)
        upd_at()

        out = {"v": None}

        def ok():
            days = [i for i, v in enumerate(days_v) if v.get()]
            parts = [i for i, v in enumerate(parts_v) if v.get()]
            if not days or not parts:
                messagebox.showerror("Schedule", "Tick at least one day and one time slot.", parent=win)
                return
            ent = {"id": e["id"] if e else new_id(data, st["who"]), "days": days, "parts": parts, "away": bool(away_v.get())}
            if away_v.get():
                ent.update(place=None, room=None, look={"type": "stand"})
            else:
                lab = room_v.get()
                pair = [(p, rr) for p, rr, l in rooms if l == lab]
                if not pair:
                    messagebox.showerror("Schedule", "Choose where she is.", parent=win)
                    return
                lk = cur_look()
                if lk["type"] == "char" and not lk["image"]:
                    messagebox.showerror("Schedule", "Choose a picture of the library (add one in the Characters tab).", parent=win)
                    return
                if lk["type"] == "pose" and not lk["pose"]:
                    messagebox.showerror("Schedule", "Choose an activity picture.", parent=win)
                    return
                ent.update(place=pair[0][0], room=pair[0][1], look=lk)
                if at_state["at"]:
                    ent["at"] = at_state["at"]
            out["v"] = ent
            win.destroy()

        brow = ttk.Frame(win)
        brow.grid(row=4, column=0, pady=8)
        ttk.Button(brow, text="OK", command=ok).pack(side="left", padx=6)
        ttk.Button(brow, text="Cancel", command=win.destroy).pack(side="left", padx=6)
        root.wait_window(win)
        return out["v"]

    def add_entry():
        ent = dialog_entry(None)
        if ent:
            entries(data, st["who"]).append(ent)
            mark("schedule")
            refresh()

    def edit_entry():
        e = sel_entry()
        if not e:
            messagebox.showinfo("Schedule", "Select an entry in the list first.")
            return
        ent = dialog_entry(e)
        if ent:
            lst_ = entries(data, st["who"])
            lst_[lst_.index(e)] = ent
            mark("schedule")
            refresh()

    def delete_entry():
        e = sel_entry()
        if not e:
            return
        span = "%d day(s) x %d slot(s)" % (len(e["days"]), len(e["parts"]))
        if messagebox.askyesno("Schedule", "Delete this entry? It covers %s, not only the selected slot." % span):
            entries(data, st["who"]).remove(e)
            mark("schedule")
            refresh()

    ttk.Button(bb, text="Add...", width=14, command=add_entry).pack(pady=2)
    ttk.Button(bb, text="Edit...", width=14, command=edit_entry).pack(pady=2)
    ttk.Button(bb, text="Delete", width=14, command=delete_entry).pack(pady=2)
    lst.bind("<Double-Button-1>", lambda ev: edit_entry())

    def change_who(*_):
        st["who"] = who_v.get() or "ana"
        entries(data, st["who"])
        refresh()

    who_cb.bind("<<ComboboxSelected>>", change_who)
    refresh_who()
    refresh()
    return dict(data=data, refresh=refresh, select=select_cell, state=st, add_dialog=dialog_entry, place_dialog=dialog_place,
                cells=cells, lst=lst, validate=lambda chars_: validate(ROOT, data, room_label, rooms, chars_))
