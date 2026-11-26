# -*- coding: utf-8 -*-
"""Masar editor: add and change game content without touching code.

Run from the project root (the folder that contains game/ and tools/):
    python tools/masar_editor.py

Tabs
  Overview         what exists in the game, and a list of problems (missing pictures, wrong numbers ...)
  Subjects         things that can be photographed in a room: draw a rectangle around them on the room picture
  Gigs             Snapjob photo gigs: title, client, reward, level, which subject they ask for
  Levels           Snapjob levels (followers needed to unlock) and subject categories
  Ana boxes        the rectangles around Ana's body parts for each photo scene (face, torso, legs, feet, hands, objects)

Nothing is written until you press  Save  (Ctrl+S).  Every save first copies the old file to game/data/_backup.
The data files are game/data/snapjob.json and game/data/ana_regions.json (plain JSON, you can also open them in a text editor).
"""
import os
import re
import sys

ROOT = os.getcwd()
GAME = os.path.join(ROOT, "game")
if not os.path.isdir(GAME):                      # started from the tools folder
    ROOT = os.path.dirname(ROOT)
    GAME = os.path.join(ROOT, "game")
sys.path.insert(0, GAME)

import masar_data                                # noqa: E402
import masar_core as mc                          # noqa: E402
import masar_rooms
import masar_places                               # noqa: E402  (room pictures: panoramas, start view, size checks)

try:
    import poses_data                            # noqa: E402
except Exception:                                # the scenes list is only needed for the "Ana boxes" tab
    poses_data = None

PART_KEYS = ["face", "torso", "legs", "feet", "hands"]
PART_COLORS = {"figure": "#9a9a9a", "face": "#ff3b3b", "torso": "#ffd54a", "legs": "#3bd16f", "feet": "#3b8cff",
               "hands": "#ff3bd5", "object": "#ffffff"}
MAX_REWARD_NOTE = 200                             # rewards above this get a warning (your rule: keep gigs <= 200 for now)


# =====================================================================================================
#  Pure logic (no windows): easy to test
# =====================================================================================================
def room_ids_of(place):
    try:
        return [r for r, _n in mc.rooms_of(place)]
    except Exception:
        return []


def bg_file(place, room, part=None):
    """The room picture (.jpg, or .png/.jpeg/.webp when only that exists); the .jpg path if none exists.
    part = a time slot 0..3 (that time's picture, with the same fallbacks as the game)."""
    return masar_rooms.find_bg(GAME, place, room, part, room_ids_of(place)) or os.path.join(GAME, "images", "bg", "%s_%s.jpg" % (place, room))


def place_name(pid):
    p = mc.BY_ID.get(pid)
    return p.name if p else pid


def all_rooms():
    """[(place id, room id, 'Gym - Pool')] for every room of the game."""
    out = []
    for p in mc.PLACES:
        for rid, rname in mc.rooms_of(p.id):
            out.append((p.id, rid, "%s - %s" % (p.name, rname)))
    return out


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s or "item"


def room_entry(snap, place, room, create=False):
    for r in snap["rooms"]:
        if r["place"] == place and r["room"] == room:
            return r
    if create:
        r = {"place": place, "room": room, "subjects": []}
        snap["rooms"].append(r)
        return r
    return None


def room_of_subject(snap, sid):
    for r in snap["rooms"]:
        if sid in r["subjects"]:
            return (r["place"], r["room"])
    return None


def gigs_using(snap, sid):
    return [g for g in snap["gigs"] if g["subject"] == sid]


def box_ok(b, w, h):
    return (len(b) == 4 and all(isinstance(v, (int, float)) for v in b) and b[2] > 0 and b[3] > 0
            and b[0] >= -1e-6 and b[1] >= -1e-6 and b[0] + b[2] <= w + 1e-6 and b[1] + b[3] <= h + 1e-6)


def validate(snap, regions):
    """List of (kind, text): kind is 'error' (the game may break) or 'warn' (works, but look at it)."""
    out = []
    cats = [c[0] for c in snap.get("categories", [])]
    levels = [int(k) for k in snap.get("levels", {})]
    if 1 not in levels:
        out.append(("error", "Level 1 is missing (Levels tab)."))
    last = -1
    for lv in sorted(levels):
        f = snap["levels"][str(lv)]["followers"]
        if f < last:
            out.append(("warn", "Level %d needs fewer followers than the level before it." % lv))
        last = f
    for r in snap["rooms"]:
        label = "%s - %s" % (place_name(r["place"]), mc.room_name(r["place"], r["room"]))
        if r["place"] not in mc.BY_ID:
            out.append(("error", "Rooms list: unknown place '%s'." % r["place"]))
            continue
        if not os.path.exists(bg_file(r["place"], r["room"])):
            out.append(("error", "%s: the room picture is missing (game/images/bg/%s_%s.jpg)." % (label, r["place"], r["room"])))
        rinfo = masar_rooms.info(GAME, r["place"], r["room"], None, room_ids_of(r["place"]))
        for note2 in (masar_rooms.size_problems(GAME, r["place"], r["room"], room_ids_of(r["place"])),
                      masar_rooms.name_clash(r["place"], r["room"], room_ids_of(r["place"]))):
            if note2:
                out.append(("error" if "different sizes" in note2 else "warn", "%s: %s" % (label, note2)))
        note = masar_rooms.width_note(rinfo)
        if note:
            out.append(("warn", "%s: %s" % (label, note)))
        for sid in r["subjects"]:
            if sid not in snap["subjects"]:
                out.append(("error", "%s lists the subject '%s', which does not exist." % (label, sid)))
            else:
                for kind, text in masar_rooms.box_problems(snap["subjects"][sid]["label"], snap["subjects"][sid]["box"], rinfo["W"]):
                    out.append((kind, "%s: %s" % (label, text)))
    for sid, s in snap["subjects"].items():
        if not box_ok(s["box"], 1.0, 1.0):
            out.append(("error", "Subject '%s': its rectangle is not inside the picture." % sid))
        if s["category"] not in cats:
            out.append(("warn", "Subject '%s': unknown category '%s' (Levels tab)." % (sid, s["category"])))
        if room_of_subject(snap, sid) is None:
            out.append(("warn", "Subject '%s' is not in any room, so nobody can photograph it." % sid))
    seen = set()
    for g in snap["gigs"]:
        gid = g["id"]
        if gid in seen:
            out.append(("error", "Two gigs have the id '%s'." % gid))
        seen.add(gid)
        if g["subject"] not in snap["subjects"]:
            out.append(("error", "Gig '%s' asks for the subject '%s', which does not exist." % (gid, g["subject"])))
        elif room_of_subject(snap, g["subject"]) is None:
            out.append(("warn", "Gig '%s': its subject is not in any room, so it cannot be done." % gid))
        if g.get("level", 1) not in levels:
            out.append(("error", "Gig '%s' is in level %s, which does not exist." % (gid, g.get("level"))))
        if g["reward"] <= 0:
            out.append(("error", "Gig '%s' has no reward." % gid))
        elif g["reward"] > MAX_REWARD_NOTE:
            out.append(("warn", "Gig '%s' pays $%d (more than $%d)." % (gid, g["reward"], MAX_REWARD_NOTE)))
    for lv in levels:
        n = len([g for g in snap["gigs"] if g.get("level", 1) == lv])
        if n == 0:
            out.append(("warn", "Level %d has no gigs yet." % lv))
    if poses_data:
        for sid, sc in poses_data.SCENES.items():
            if sid not in regions:
                out.append(("warn", "Scene '%s' has no Ana boxes yet (not an error): the camera uses rough default boxes until you draw them in the Ana boxes tab." % sid))
            for kind, path in sc["images"].items():
                if not os.path.exists(os.path.join(GAME, path)):
                    out.append(("error", "Scene '%s': picture missing: %s" % (sid, path)))
    for sid, r in regions.items():
        if not box_ok(r["figure"], 800, 1080):
            out.append(("error", "Scene '%s': the figure box is outside the 800x1080 picture." % sid))
        for key in PART_KEYS:
            for b in r.get(key, []):
                if not box_ok(b, 800, 1080):
                    out.append(("error", "Scene '%s': a %s box is outside the picture." % (sid, key)))
        for o in r.get("objects", []):
            if not box_ok(o["box"], 800, 1080):
                out.append(("error", "Scene '%s': object '%s' is outside the picture." % (sid, o["name"])))
    return out


def inventory(snap, regions):
    """Rows for the overview tree: (label, bg status, size, subjects, Ana poses, gigs)."""
    rows = []
    poses = {}
    if poses_data:
        for k, v in poses_data.ANA_POSES.items():
            poses[k] = v
    for pid, rid, label in all_rooms():
        e = room_entry(snap, pid, rid)
        subs = e["subjects"] if e else []
        gigs = [g for g in snap["gigs"] if g["subject"] in subs]
        ri = masar_rooms.info(GAME, pid, rid)
        size = "-" if ri["path"] is None else ("%dx%d  (%d%% visible)" % (ri["W"], masar_rooms.WORLD_H, ri["visible"]) if ri["pano"] else "normal")
        n_own = len(masar_rooms.time_files(GAME, pid, rid, room_ids_of(pid)))
        rows.append((label, ("yes" + (", %d/4 times" % n_own if n_own else "")) if ri["path"] else "MISSING", size, len(subs),
                     ", ".join(poses.get((pid, rid), [])), len(gigs)))
    return rows


# =====================================================================================================
#  The window
# =====================================================================================================
def run_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
    from PIL import Image, ImageTk

    root = tk.Tk()
    root.title("Masar editor")
    root.geometry("%dx%d" % (min(1360, root.winfo_screenwidth() - 30), min(880, root.winfo_screenheight() - 90)))

    try:
        rooms_data = masar_data.load("rooms")
    except Exception:
        rooms_data = {"version": 1, "rooms": {}}
    state = {"snap": masar_data.load("snapjob"), "regions": masar_data.load("ana_regions")["scenes"],
             "dirty": set(), "images": {}, "rooms": rooms_data}
    snap = state["snap"]
    regions = state["regions"]
    snap.setdefault("categories", [])

    status = tk.StringVar(value="Loaded. Nothing changed yet.")

    def mark(name):
        state["dirty"].add(name)
        status.set("Unsaved changes (press Save or Ctrl+S).")
        refresh_overview()

    def save_all():
        problems = [p for p in validate(snap, regions) if p[0] == "error"]
        if problems and not messagebox.askyesno("Problems found", "There are %d errors (see Overview). Save anyway?" % len(problems)):
            return
        if "snapjob" in state["dirty"]:
            masar_data.save("snapjob", snap)
        if "ana_regions" in state["dirty"]:
            masar_data.save("ana_regions", {"version": 1, "scenes": regions})
        if "schedule" in state["dirty"]:
            masar_data.save("schedule", schedule_ui["data"])
        if "rooms" in state["dirty"]:
            masar_data.save("rooms", rooms_data)
        if "places" in state["dirty"]:
            masar_data.save("places", places_ui["data"])
        state["dirty"].clear()
        status.set("Saved. A backup of the old files is in game/data/_backup.")
        refresh_overview()

    def on_close():
        if state["dirty"] and not messagebox.askyesno("Unsaved changes", "Close without saving?"):
            return
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.bind("<Control-s>", lambda e: save_all())

    top = ttk.Frame(root)
    top.pack(fill="x", padx=8, pady=6)
    ttk.Button(top, text="Save  (Ctrl+S)", command=save_all).pack(side="left")
    ttk.Label(top, textvariable=status).pack(side="left", padx=14)

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def load_image(path, size=None):
        if not os.path.exists(path):
            return None
        im = Image.open(path).convert("RGBA")
        if size:
            im = im.resize(size, Image.LANCZOS)
        return im

    def photo(im):
        ph = ImageTk.PhotoImage(im)
        state["images"][id(ph)] = ph          # keep a reference alive
        return ph

    # ------------------------------------------------------------------------------- Overview
    tab_o = ttk.Frame(nb)
    nb.add(tab_o, text="Overview")
    tree_fr = ttk.Frame(tab_o)
    tree_fr.pack(fill="x", padx=8, pady=8)
    tree = ttk.Treeview(tree_fr, columns=("bg", "size", "subs", "poses", "gigs"), height=18)
    tree.heading("#0", text="Room")
    tree.heading("bg", text="Room picture")
    tree.heading("size", text="Size (what the player sees)")
    tree.heading("subs", text="Subjects")
    tree.heading("poses", text="Ana poses")
    tree.heading("gigs", text="Gigs")
    tree.column("#0", width=260)
    tree.column("bg", width=100, anchor="center")
    tree.column("size", width=170, anchor="center")
    tree.column("subs", width=80, anchor="center")
    tree.column("poses", width=240)
    tree.column("gigs", width=60, anchor="center")
    tree.pack(side="left", fill="x", expand=True)
    sb = ttk.Scrollbar(tree_fr, orient="vertical", command=tree.yview)
    sb.pack(side="right", fill="y")
    tree.configure(yscrollcommand=sb.set)
    ttk.Label(tab_o, text="Problems").pack(anchor="w", padx=8)
    problems_box = tk.Text(tab_o, height=14, wrap="word")
    problems_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    problems_box.tag_config("error", foreground="#c0392b")
    problems_box.tag_config("warn", foreground="#b9770e")
    problems_box.tag_config("ok", foreground="#1e8449")

    def refresh_overview():
        for i in tree.get_children():
            tree.delete(i)
        for label, bg, size, subs, poses, gigs in inventory(snap, regions):
            tree.insert("", "end", text=label, values=(bg, size, subs, poses, gigs))
        problems_box.config(state="normal")
        problems_box.delete("1.0", "end")
        probs = validate(snap, regions)
        try:
            probs = probs + masar_chars.validate(ROOT, chars_ui["data"])
            probs = probs + schedule_ui["validate"](chars_ui["data"]["characters"])
            probs = probs + places_ui["validate"](schedule_ui["data"])
        except NameError:
            pass
        if not probs:
            problems_box.insert("end", "No problems found.\n", "ok")
        for kind, text in probs:
            problems_box.insert("end", ("ERROR: " if kind == "error" else "Note: ") + text + "\n", kind)
        problems_box.config(state="disabled")

    # ------------------------------------------------------------------------------- Subjects
    tab_s = ttk.Frame(nb)
    nb.add(tab_s, text="Subjects")
    rooms_list = all_rooms()
    room_var = tk.StringVar(value=rooms_list[0][2])
    left = ttk.Frame(tab_s)
    left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
    right = ttk.Frame(tab_s, width=300)
    right.pack(side="right", fill="y", padx=8, pady=8)

    ttk.Label(left, text="Room:").pack(anchor="w")
    room_box = ttk.Combobox(left, textvariable=room_var, values=[r[2] for r in rooms_list], state="readonly", width=40)
    room_box.pack(anchor="w", pady=(0, 6))
    time_v = tk.StringVar(value="Plain picture")
    trow = ttk.Frame(left)
    trow.pack(anchor="w", pady=(0, 6))
    ttk.Label(trow, text="Show the picture of:").pack(side="left")
    time_box = ttk.Combobox(trow, textvariable=time_v, values=["Plain picture"] + list(masar_rooms.TIME_LABELS), state="readonly", width=16)
    time_box.pack(side="left", padx=6)
    time_note_v = tk.StringVar()
    ttk.Label(trow, textvariable=time_note_v, foreground="#555").pack(side="left")

    def view_part():
        v = time_v.get()
        return list(masar_rooms.TIME_LABELS).index(v) if v in masar_rooms.TIME_LABELS else None
    SCALE_S = 0.5
    canvas_s = tk.Canvas(left, width=960, height=540, bg="#222", highlightthickness=0, xscrollincrement=20)
    canvas_s.pack()
    hbar_s = ttk.Scrollbar(left, orient="horizontal", command=canvas_s.xview)
    hbar_s.pack(fill="x")
    canvas_s.configure(xscrollcommand=hbar_s.set)
    hint_s = tk.StringVar(value="Pick a subject on the right, or press 'New subject' and drag a rectangle on the picture.")
    ttk.Label(left, textvariable=hint_s, wraplength=900).pack(anchor="w", pady=6)

    ttk.Label(right, text="Subjects in this room").pack(anchor="w")
    subj_list = tk.Listbox(right, height=12, width=36, exportselection=False)
    subj_list.pack(fill="x", pady=4)
    s_state = {"mode": None, "drag": None, "ids": [], "bg": None, "W": 1920, "lock": False, "undo": None}
    room_info_v = tk.StringVar()
    start_v = tk.DoubleVar(value=50.0)

    def cur_room():
        label = room_var.get()
        for pid, rid, lab in rooms_list:
            if lab == label:
                return pid, rid
        return rooms_list[0][:2]

    def sbox_px(box):
        """A subject rectangle (fractions of the whole picture) -> canvas coordinates."""
        W = s_state["W"]
        return box[0] * W * SCALE_S, box[1] * 1080 * SCALE_S, (box[0] + box[2]) * W * SCALE_S, (box[1] + box[3]) * 1080 * SCALE_S

    def draw_subjects():
        canvas_s.delete("all")
        pid, rid = cur_room()
        ri = masar_rooms.info(GAME, pid, rid, view_part(), room_ids_of(pid))
        W = ri["W"]
        s_state["W"] = W
        own = masar_rooms.time_files(GAME, pid, rid, room_ids_of(pid))
        miss = masar_rooms.missing_times(GAME, pid, rid, room_ids_of(pid))
        time_note_v.set("own pictures: %s" % (", ".join(masar_rooms.TIME_LABELS[i] for i in sorted(own)) or "none (plain picture used all day)")
                        + ("" if not miss or len(miss) == 4 else "   |   falls back for: " + ", ".join(miss)))
        cw = int(W * SCALE_S)
        canvas_s.configure(scrollregion=(0, 0, cw, 540))
        if ri["path"] is None:
            canvas_s.create_text(480, 270, text="Room picture missing:\ngame/images/bg/%s_%s.jpg" % (pid, rid), fill="white")
        else:
            im = load_image(ri["path"], (cw, 540))
            s_state["bg"] = photo(im)
            canvas_s.create_image(0, 0, image=s_state["bg"], anchor="nw")
        # where the view starts when the player enters (panoramic rooms)
        s_state["lock"] = True
        if ri["pano"]:
            st = masar_rooms.get_start(rooms_data, pid, rid)
            sx = masar_rooms.start_px(W, st) * SCALE_S
            canvas_s.create_rectangle(sx, 1, sx + 1920 * SCALE_S, 539, outline="#00e5ff", width=2, dash=(6, 4))
            canvas_s.create_text(sx + 6, 520, text="view when the player enters", fill="#00e5ff", anchor="sw", font=("Arial", 10, "bold"))
            if abs(start_v.get() - st * 100) > 0.6:
                start_v.set(round(st * 100))
            room_info_v.set("Panorama: picture %dx%d -> room %dx1080. The player sees %d%% of it at a time (dashed frame = the start view)."
                            % (ri["size"][0], ri["size"][1], W, ri["visible"]))
            start_scale.state(["!disabled"])
        else:
            room_info_v.set("Normal room (the picture fits one screen)." if ri["path"] else "")
            start_scale.state(["disabled"])
        s_state["lock"] = False
        e = room_entry(snap, pid, rid)
        s_state["ids"] = list(e["subjects"]) if e else []
        subj_list.delete(0, "end")
        for sid in s_state["ids"]:
            tm = snap["subjects"][sid].get("times")
            subj_list.insert("end", "%s %s  [%s]%s" % ("[gig]" if gigs_using(snap, sid) else "[ - ]",
                                                       snap["subjects"][sid]["label"], sid,
                                                       ("  @" + ",".join(t[:3] for t in tm)) if tm else ""))
        for i, sid in enumerate(s_state["ids"]):
            x, y, x2, y2 = sbox_px(snap["subjects"][sid]["box"])
            col = "#ffd54a"
            tm = snap["subjects"][sid].get("times")
            vp = view_part()
            if tm and vp is not None and masar_rooms.TIME_KEYS[vp] not in tm:
                col = "#777777"                              # not there at the time shown
            canvas_s.create_rectangle(x, y, x2, y2, outline=col, width=2, dash=(3, 3) if col == "#777777" else None)
            canvas_s.create_text(x + 4, y + 2, text=snap["subjects"][sid]["label"], fill=col, anchor="nw", font=("Arial", 10, "bold"))

    def selected_sid():
        sel = subj_list.curselection()
        return s_state["ids"][sel[0]] if sel else None

    def highlight(*_):
        draw_subjects_keep()

    def draw_subjects_keep():
        sel = subj_list.curselection()
        draw_subjects()
        if sel:
            subj_list.selection_set(sel[0])
            sid = s_state["ids"][sel[0]]
            x, y, x2, y2 = sbox_px(snap["subjects"][sid]["box"])
            canvas_s.create_rectangle(x, y, x2, y2, outline="#00ff88", width=4)

    def scroll_to(px_world):
        """Scroll the picture so that world x = px_world is at the left of the window."""
        cw = max(1, s_state["W"] * SCALE_S)
        canvas_s.xview_moveto(max(0.0, min(1.0, px_world * SCALE_S / cw)))

    def pick_room(*_):
        draw_subjects()
        canvas_s.xview_moveto(0.0)
        pid, rid = cur_room()
        ri = masar_rooms.info(GAME, pid, rid)
        if ri["pano"]:
            scroll_to(masar_rooms.start_px(ri["W"], masar_rooms.get_start(rooms_data, pid, rid)))

    room_box.bind("<<ComboboxSelected>>", pick_room)
    time_box.bind("<<ComboboxSelected>>", lambda e: draw_subjects())
    subj_list.bind("<<ListboxSelect>>", lambda e: draw_subjects_keep())

    def wheel_s(ev):
        if s_state["W"] > 1920:
            up = getattr(ev, "delta", 0) > 0 or getattr(ev, "num", 0) == 4
            canvas_s.xview_scroll(-3 if up else 3, "units")

    canvas_s.bind("<MouseWheel>", wheel_s)
    canvas_s.bind("<Button-4>", wheel_s)
    canvas_s.bind("<Button-5>", wheel_s)

    def canvas_press(ev):
        if s_state["mode"]:
            cx = canvas_s.canvasx(ev.x)
            s_state["drag"] = [cx, ev.y, cx, ev.y]

    def canvas_move(ev):
        d = s_state["drag"]
        if d:
            if ev.x > 940:                                   # dragging near the edge scrolls the picture
                canvas_s.xview_scroll(1, "units")
            elif ev.x < 20:
                canvas_s.xview_scroll(-1, "units")
            d[2], d[3] = canvas_s.canvasx(ev.x), ev.y
            canvas_s.delete("rubber")
            canvas_s.create_rectangle(d[0], d[1], d[2], d[3], outline="#00ffff", width=3, dash=(4, 3), tags="rubber")

    def canvas_release(ev):
        d = s_state["drag"]
        mode = s_state["mode"]
        s_state["drag"] = None
        if not d or not mode:
            return
        cw = s_state["W"] * SCALE_S
        x0, x1 = sorted((max(0, min(cw, d[0])), max(0, min(cw, d[2]))))
        y0, y1 = sorted((max(0, min(540, d[1])), max(0, min(540, d[3]))))
        if x1 - x0 < 6 or y1 - y0 < 6:
            canvas_s.delete("rubber")
            return
        box = [round(x0 / cw, 4), round(y0 / 540.0, 4), round((x1 - x0) / cw, 4), round((y1 - y0) / 540.0, 4)]
        pid, rid = cur_room()
        if mode == "new":
            dialog_subject(box, pid, rid)
        elif mode == "redraw":
            snap["subjects"][mode_sid[0]]["box"] = box
            mark("snapjob")
        s_state["mode"] = None
        hint_s.set("Done. Pick another subject, or press 'New subject'.")
        draw_subjects_keep()

    mode_sid = [None]
    canvas_s.bind("<ButtonPress-1>", canvas_press)
    canvas_s.bind("<B1-Motion>", canvas_move)
    canvas_s.bind("<ButtonRelease-1>", canvas_release)

    def dialog_subject(box, pid, rid, sid=None):
        """Ask for the id / label / category of a subject. Returns after saving."""
        win = tk.Toplevel(root)
        win.title("Subject")
        win.grab_set()
        cur = snap["subjects"].get(sid) if sid else None
        label_v = tk.StringVar(value=cur["label"] if cur else "")
        id_v = tk.StringVar(value=sid or "")
        cats = [c[0] for c in snap["categories"]]
        cat_v = tk.StringVar(value=cur["category"] if cur else (cats[0] if cats else "places"))
        ttk.Label(win, text="Name shown to the player (e.g. Crocodile on the bank):").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(win, textvariable=label_v, width=44).grid(row=1, column=0, padx=8)
        ttk.Label(win, text="Short id (letters and underscores, e.g. crocodile) - cannot change later:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        id_e = ttk.Entry(win, textvariable=id_v, width=44, state="normal" if not sid else "disabled")
        id_e.grid(row=3, column=0, padx=8)
        ttk.Label(win, text="Category (the gallery filter it appears under):").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        ttk.Combobox(win, textvariable=cat_v, values=cats, state="readonly").grid(row=5, column=0, sticky="w", padx=8)
        tbox = ttk.LabelFrame(win, text="Only at these times (tick none = all day)")
        tbox.grid(row=7, column=0, sticky="we", padx=8, pady=4)
        cur_times = (cur or {}).get("times") or []
        time_vars = []
        for i, k in enumerate(masar_rooms.TIME_KEYS):
            v = tk.BooleanVar(value=k in cur_times)
            time_vars.append(v)
            ttk.Checkbutton(tbox, text=masar_rooms.TIME_LABELS[i], variable=v).grid(row=0, column=i, padx=6, pady=3)
        gig_v = tk.BooleanVar(value=False)
        reward_v = tk.StringVar(value="100")
        level_v = tk.StringVar(value="1")
        if not sid:
            box_g = ttk.LabelFrame(win, text="Snapjob")
            box_g.grid(row=6, column=0, sticky="we", padx=8, pady=8)
            ttk.Checkbutton(box_g, text="Also make a gig for it now (leave unticked to decide later)", variable=gig_v).grid(
                row=0, column=0, columnspan=4, sticky="w", padx=6, pady=3)
            ttk.Label(box_g, text="Reward $").grid(row=1, column=0, padx=6, sticky="w")
            ttk.Spinbox(box_g, from_=10, to=1000, increment=10, textvariable=reward_v, width=7).grid(row=1, column=1, sticky="w")
            ttk.Label(box_g, text="Level").grid(row=1, column=2, padx=6, sticky="w")
            ttk.Combobox(box_g, textvariable=level_v, values=sorted(int(k) for k in snap["levels"]), state="readonly", width=5).grid(row=1, column=3, sticky="w")

        def ok():
            lab = label_v.get().strip()
            if not lab:
                messagebox.showerror("Subject", "Give it a name.", parent=win)
                return
            new_id = sid or (id_v.get().strip() or slug(lab))
            new_id = slug(new_id)
            if not sid and new_id in snap["subjects"]:
                messagebox.showerror("Subject", "The id '%s' already exists. Choose another." % new_id, parent=win)
                return
            snap["subjects"][new_id] = {"label": lab, "category": cat_v.get(), "box": box if box else cur["box"]}
            chosen = [k for k, v in zip(masar_rooms.TIME_KEYS, time_vars) if v.get()]
            if chosen and len(chosen) < 4:
                snap["subjects"][new_id]["times"] = chosen
            for extra in (cur or {}):
                if extra not in snap["subjects"][new_id] and extra != "times":
                    snap["subjects"][new_id][extra] = cur[extra]
            if not sid:
                room_entry(snap, pid, rid, create=True)["subjects"].append(new_id)
                if gig_v.get():
                    try:
                        rw, lv = int(reward_v.get()), int(level_v.get())
                    except ValueError:
                        rw, lv = 100, 1
                    gid = new_id
                    n = 2
                    while any(g["id"] == gid for g in snap["gigs"]):
                        gid = "%s_%d" % (new_id, n)
                        n += 1
                    snap["gigs"].append({"id": gid, "subject": new_id, "title": lab, "client": "Client",
                                         "brief": "Photograph: %s." % lab.lower(), "reward": rw, "level": lv})
                    refresh_gigs()
                    refresh_levels()
            mark("snapjob")
            win.destroy()
            draw_subjects_keep()

        ttk.Button(win, text="OK", command=ok).grid(row=7, column=0, pady=10)
        win.wait_window()

    def new_subject():
        s_state["mode"] = "new"
        hint_s.set("Drag a rectangle around the subject on the picture.")

    def redraw_subject():
        sid = selected_sid()
        if not sid:
            messagebox.showinfo("Subjects", "Select a subject in the list first.")
            return
        mode_sid[0] = sid
        s_state["mode"] = "redraw"
        hint_s.set("Drag a new rectangle for '%s'." % snap["subjects"][sid]["label"])

    def edit_subject():
        sid = selected_sid()
        if not sid:
            messagebox.showinfo("Subjects", "Select a subject in the list first.")
            return
        pid, rid = cur_room()
        dialog_subject(None, pid, rid, sid)

    def delete_subject():
        sid = selected_sid()
        if not sid:
            return
        used = gigs_using(snap, sid)
        if used:
            messagebox.showerror("Subjects", "Gigs use this subject: %s.\nDelete or change those gigs first (Gigs tab)." %
                                 ", ".join(g["id"] for g in used))
            return
        if not messagebox.askyesno("Delete", "Delete the subject '%s' completely?" % snap["subjects"][sid]["label"]):
            return
        for r in snap["rooms"]:
            if sid in r["subjects"]:
                r["subjects"].remove(sid)
        del snap["subjects"][sid]
        mark("snapjob")
        draw_subjects()

    ttk.Button(right, text="New subject (draw box)", command=new_subject).pack(fill="x", pady=2)
    ttk.Button(right, text="Redraw its rectangle", command=redraw_subject).pack(fill="x", pady=2)
    ttk.Button(right, text="Edit name / category", command=edit_subject).pack(fill="x", pady=2)
    ttk.Button(right, text="Delete subject", command=delete_subject).pack(fill="x", pady=2)

    def make_gig_for_subject():
        sid = selected_sid()
        if not sid:
            messagebox.showinfo("Subjects", "Select a subject in the list first.")
            return
        gstate["sel"] = None
        gtree.selection_remove(*gtree.selection())
        gv["id"].set(sid if not any(g["id"] == sid for g in snap["gigs"]) else sid + "_2")
        gv["title"].set(snap["subjects"][sid]["label"])
        gv["client"].set("Client")
        gv["brief"].set("Photograph: %s." % snap["subjects"][sid]["label"].lower())
        gv["reward"].set("100")
        gv["level"].set("1")
        gv["subject"].set(subj_label_for(sid))
        show_ref()
        nb.select(tab_g)
        status.set("Fill in the gig and press 'Add as new gig'.")

    ttk.Button(right, text="Make a gig from it...", command=make_gig_for_subject).pack(fill="x", pady=(10, 2))

    # ---- the room itself: panorama info, where the view starts, shifting rectangles
    rv_frame = ttk.LabelFrame(right, text="This room's picture")
    rv_frame.pack(fill="x", pady=(12, 0))
    ttk.Label(rv_frame, textvariable=room_info_v, wraplength=270, foreground="#444").pack(anchor="w", padx=6, pady=4)
    ttk.Label(rv_frame, text="Start view (0 = left ... 100 = right):").pack(anchor="w", padx=6)

    def start_changed(*_):
        if s_state["lock"]:
            return
        pid, rid = cur_room()
        masar_rooms.set_start(rooms_data, pid, rid, start_v.get() / 100.0)
        mark("rooms")
        draw_subjects_keep()

    start_scale = ttk.Scale(rv_frame, from_=0, to=100, variable=start_v, orient="horizontal", length=250, command=start_changed)
    start_scale.pack(padx=6, pady=2)

    def dialog_shift():
        pid, rid = cur_room()
        W = s_state["W"]
        if W <= 1920 and not messagebox.askyesno("Shift rectangles", "This room is not a panorama (yet). Continue anyway?"):
            return
        win = tk.Toplevel(root)
        win.title("Shift rectangles")
        win.grab_set()
        old_v = tk.StringVar(value="1920")
        dx_v = tk.StringVar(value="0")
        sch_v = tk.BooleanVar(value=True)
        ttk.Label(win, wraplength=420, justify="left",
                  text="Use this after you REPLACED the picture of this room by a wider one that CONTAINS the old picture "
                       "(for example you extended it to the left and right). The rectangles of this room are moved so that "
                       "they stay on the same things. If the new picture is a different drawing, redraw the rectangles instead."
                  ).grid(row=0, column=0, columnspan=2, padx=10, pady=8)
        ttk.Label(win, text="Width of the OLD picture in the room (pixels, 1920 for a normal room):").grid(row=1, column=0, sticky="w", padx=10)
        ttk.Entry(win, textvariable=old_v, width=8).grid(row=1, column=1, padx=10)
        ttk.Label(win, text="Where its left edge now is, in the NEW room (pixels, from the left):").grid(row=2, column=0, sticky="w", padx=10, pady=4)
        ttk.Entry(win, textvariable=dx_v, width=8).grid(row=2, column=1, padx=10)
        ttk.Checkbutton(win, text="Also move Ana's own placements in this room (Schedule tab)", variable=sch_v).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=4)

        def ok():
            try:
                old_w = float(old_v.get())
                dx = float(dx_v.get())
            except ValueError:
                messagebox.showerror("Shift rectangles", "Please type numbers.")
                return
            if old_w < 100 or old_w > 20000:
                messagebox.showerror("Shift rectangles", "The old width looks wrong.")
                return
            undo = masar_rooms.shift_subjects(snap, pid, rid, dx, old_w, W)
            moved_sched = masar_rooms.shift_schedule(schedule_ui["data"], pid, rid, dx) if sch_v.get() else 0
            s_state["undo"] = {"room": (pid, rid), "boxes": undo, "dx": dx, "sched": bool(sch_v.get())}
            if undo:
                mark("snapjob")
            if moved_sched:
                mark("schedule")
            win.destroy()
            hint_s.set("Moved %d rectangle(s) and %d placement(s). If it is not right, press 'Undo last shift'." % (len(undo), moved_sched))
            draw_subjects_keep()

        brow = ttk.Frame(win)
        brow.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(brow, text="Shift", command=ok).pack(side="left", padx=6)
        ttk.Button(brow, text="Cancel", command=win.destroy).pack(side="left", padx=6)

    def undo_shift():
        u = s_state["undo"]
        if not u:
            messagebox.showinfo("Shift rectangles", "Nothing to undo.")
            return
        for sid, b in u["boxes"].items():
            if sid in snap["subjects"]:
                snap["subjects"][sid]["box"] = b
        if u["sched"]:
            masar_rooms.shift_schedule(schedule_ui["data"], u["room"][0], u["room"][1], -u["dx"])
            mark("schedule")
        mark("snapjob")
        s_state["undo"] = None
        hint_s.set("Shift undone.")
        draw_subjects_keep()

    ttk.Button(rv_frame, text="Shift rectangles...", command=dialog_shift).pack(fill="x", padx=6, pady=(6, 2))
    ttk.Button(rv_frame, text="Undo last shift", command=undo_shift).pack(fill="x", padx=6, pady=(0, 6))
    ttk.Label(right, wraplength=280, foreground="#666",
              text="The rectangle is where the subject is on the room picture. The camera counts a subject as photographed "
                   "when enough of that rectangle is in the frame.").pack(anchor="w", pady=12)

    # ------------------------------------------------------------------------------- Gigs
    tab_g = ttk.Frame(nb)
    nb.add(tab_g, text="Gigs")
    gtree = ttk.Treeview(tab_g, columns=("title", "subject", "level", "reward", "client"), height=12)
    for c, t, w in (("#0", "Id", 120), ("title", "Title", 200), ("subject", "Subject", 200), ("level", "Level", 60),
                    ("reward", "Reward $", 80), ("client", "Client", 200)):
        gtree.heading(c, text=t)
        gtree.column(c, width=w, anchor="w" if c in ("#0", "title", "subject", "client") else "center")
    gtree.pack(fill="x", padx=8, pady=8)
    form = ttk.LabelFrame(tab_g, text="Gig details")
    form.pack(fill="x", padx=8, pady=4)
    gv = {k: tk.StringVar() for k in ("id", "title", "client", "brief", "reward", "level", "subject")}
    row = 0
    for key, lab in (("id", "Id (unique)"), ("title", "Title"), ("client", "Client"), ("brief", "What the client wants")):
        ttk.Label(form, text=lab).grid(row=row, column=0, sticky="w", padx=6, pady=3)
        ttk.Entry(form, textvariable=gv[key], width=70).grid(row=row, column=1, sticky="w", pady=3)
        row += 1
    ttk.Label(form, text="Subject").grid(row=row, column=0, sticky="w", padx=6)
    subj_combo = ttk.Combobox(form, textvariable=gv["subject"], state="readonly", width=50)
    subj_combo.grid(row=row, column=1, sticky="w")
    row += 1
    ttk.Label(form, text="Reward $").grid(row=row, column=0, sticky="w", padx=6, pady=3)
    ttk.Spinbox(form, from_=10, to=1000, increment=10, textvariable=gv["reward"], width=8).grid(row=row, column=1, sticky="w")
    row += 1
    ttk.Label(form, text="Level").grid(row=row, column=0, sticky="w", padx=6, pady=3)
    level_combo = ttk.Combobox(form, textvariable=gv["level"], state="readonly", width=8)
    level_combo.grid(row=row, column=1, sticky="w")
    ref_canvas = tk.Canvas(form, width=320, height=180, bg="#222", highlightthickness=0)
    ref_canvas.grid(row=0, column=2, rowspan=7, padx=16, pady=4)
    gstate = {"sel": None, "ref": None}

    def subj_label_for(sid):
        return "%s  [%s]" % (snap["subjects"][sid]["label"], sid) if sid in snap["subjects"] else sid

    def sid_from_label(lab):
        m = re.search(r"\[([^\]]+)\]\s*$", lab)
        return m.group(1) if m else lab

    def refresh_gigs():
        gtree.delete(*gtree.get_children())
        for g in snap["gigs"]:
            gtree.insert("", "end", iid=g["id"], text=g["id"],
                         values=(g["title"], subj_label_for(g["subject"]), g.get("level", 1), g["reward"], g["client"]))
        subj_combo["values"] = [subj_label_for(s) for s in snap["subjects"]]
        level_combo["values"] = sorted(int(k) for k in snap["levels"])

    def show_ref(*_):
        sid = sid_from_label(gv["subject"].get())
        ref_canvas.delete("all")
        if sid not in snap["subjects"]:
            return
        r = room_of_subject(snap, sid)
        if not r:
            ref_canvas.create_text(160, 90, text="(this subject is in no room)", fill="white")
            return
        im = load_image(bg_file(*r))
        if im is None:
            return
        fx, fy, fw, fh = snap["subjects"][sid]["box"]
        W, H = im.size
        crop = im.crop((int(fx * W), int(fy * H), int((fx + fw) * W), int((fy + fh) * H)))
        k = min(320.0 / crop.width, 180.0 / crop.height)
        crop = crop.resize((max(1, int(crop.width * k)), max(1, int(crop.height * k))), Image.LANCZOS)
        gstate["ref"] = photo(crop)
        ref_canvas.create_image(160, 90, image=gstate["ref"])

    subj_combo.bind("<<ComboboxSelected>>", show_ref)

    def gig_select(*_):
        sel = gtree.selection()
        if not sel:
            return
        g = next(x for x in snap["gigs"] if x["id"] == sel[0])
        gstate["sel"] = g["id"]
        gv["id"].set(g["id"])
        gv["title"].set(g["title"])
        gv["client"].set(g["client"])
        gv["brief"].set(g["brief"])
        gv["reward"].set(str(g["reward"]))
        gv["level"].set(str(g.get("level", 1)))
        gv["subject"].set(subj_label_for(g["subject"]))
        show_ref()

    gtree.bind("<<TreeviewSelect>>", gig_select)

    def read_gig():
        try:
            reward = int(gv["reward"].get())
            level = int(gv["level"].get())
        except ValueError:
            messagebox.showerror("Gig", "Reward and level must be numbers.")
            return None
        sid = sid_from_label(gv["subject"].get())
        if sid not in snap["subjects"]:
            messagebox.showerror("Gig", "Choose the subject this gig asks for.")
            return None
        if not gv["title"].get().strip():
            messagebox.showerror("Gig", "Give the gig a title.")
            return None
        if reward > MAX_REWARD_NOTE and not messagebox.askyesno("Reward", "$%d is more than $%d. Keep it?" % (reward, MAX_REWARD_NOTE)):
            return None
        return {"subject": sid, "title": gv["title"].get().strip(), "client": gv["client"].get().strip() or "Client",
                "brief": gv["brief"].get().strip(), "reward": reward, "level": level}

    def gig_new():
        data = read_gig()
        if not data:
            return
        gid = slug(gv["id"].get() or data["title"])
        if any(g["id"] == gid for g in snap["gigs"]):
            messagebox.showerror("Gig", "The id '%s' is already used. Change the id field." % gid)
            return
        data["id"] = gid
        snap["gigs"].append(data)
        mark("snapjob")
        refresh_gigs()
        gtree.selection_set(gid)

    def gig_update():
        if not gstate["sel"]:
            messagebox.showinfo("Gig", "Select a gig in the list first (or use 'Add as new gig').")
            return
        data = read_gig()
        if not data:
            return
        for g in snap["gigs"]:
            if g["id"] == gstate["sel"]:
                g.update(data)
        mark("snapjob")
        refresh_gigs()
        gtree.selection_set(gstate["sel"])

    def gig_delete():
        if not gstate["sel"]:
            return
        if not messagebox.askyesno("Delete", "Delete the gig '%s'?" % gstate["sel"]):
            return
        snap["gigs"] = [g for g in snap["gigs"] if g["id"] != gstate["sel"]]
        gstate["sel"] = None
        mark("snapjob")
        refresh_gigs()

    btns = ttk.Frame(tab_g)
    btns.pack(fill="x", padx=8, pady=6)
    ttk.Button(btns, text="Add as new gig", command=gig_new).pack(side="left", padx=4)
    ttk.Button(btns, text="Save changes to selected", command=gig_update).pack(side="left", padx=4)
    ttk.Button(btns, text="Delete selected", command=gig_delete).pack(side="left", padx=4)
    gset = ttk.LabelFrame(tab_g, text="Snapjob settings")
    gset.pack(fill="x", padx=8, pady=4)
    match_v = tk.StringVar(value=str(snap.get("match_required", 80)))
    board_v = tk.StringVar(value=str(snap.get("board_size", 5)))
    ttk.Label(gset, text="Match needed to accept a photo (%)").grid(row=0, column=0, padx=6, pady=4, sticky="w")
    ttk.Spinbox(gset, from_=50, to=100, textvariable=match_v, width=6).grid(row=0, column=1)
    ttk.Label(gset, text="Gigs on the board each day").grid(row=0, column=2, padx=16, sticky="w")
    ttk.Spinbox(gset, from_=1, to=12, textvariable=board_v, width=6).grid(row=0, column=3)

    def apply_settings():
        try:
            snap["match_required"] = int(match_v.get())
            snap["board_size"] = int(board_v.get())
        except ValueError:
            return
        mark("snapjob")

    ttk.Button(gset, text="Apply", command=apply_settings).grid(row=0, column=4, padx=10)

    # ------------------------------------------------------------------------------- Levels and categories
    tab_l = ttk.Frame(nb)
    nb.add(tab_l, text="Levels")
    ltree = ttk.Treeview(tab_l, columns=("name", "followers", "gigs"), height=8)
    ltree.heading("#0", text="Level")
    ltree.heading("name", text="Name")
    ltree.heading("followers", text="Followers needed")
    ltree.heading("gigs", text="Gigs")
    ltree.column("#0", width=80)
    ltree.pack(fill="x", padx=8, pady=8)
    lf = ttk.Frame(tab_l)
    lf.pack(fill="x", padx=8)
    lname = tk.StringVar()
    lfol = tk.StringVar(value="0")
    ttk.Label(lf, text="Name").pack(side="left")
    ttk.Entry(lf, textvariable=lname, width=20).pack(side="left", padx=6)
    ttk.Label(lf, text="Followers needed").pack(side="left")
    ttk.Spinbox(lf, from_=0, to=1000000, increment=50, textvariable=lfol, width=10).pack(side="left", padx=6)

    def refresh_levels():
        ltree.delete(*ltree.get_children())
        for k in sorted(int(x) for x in snap["levels"]):
            v = snap["levels"][str(k)]
            n = len([g for g in snap["gigs"] if g.get("level", 1) == k])
            ltree.insert("", "end", iid=str(k), text=str(k), values=(v["name"], v["followers"], n))

    def level_add():
        try:
            fol = int(lfol.get())
        except ValueError:
            return
        nxt = max(int(k) for k in snap["levels"]) + 1
        snap["levels"][str(nxt)] = {"name": lname.get().strip() or "Level %d" % nxt, "followers": fol}
        mark("snapjob")
        refresh_levels()
        refresh_gigs()

    def level_update():
        sel = ltree.selection()
        if not sel:
            return
        try:
            fol = int(lfol.get())
        except ValueError:
            return
        snap["levels"][sel[0]] = {"name": lname.get().strip() or "Level %s" % sel[0], "followers": fol}
        mark("snapjob")
        refresh_levels()

    def level_delete():
        sel = ltree.selection()
        if not sel:
            return
        if sel[0] == "1":
            messagebox.showerror("Levels", "Level 1 cannot be deleted.")
            return
        if any(g.get("level", 1) == int(sel[0]) for g in snap["gigs"]):
            messagebox.showerror("Levels", "Gigs are in this level. Move or delete them first (Gigs tab).")
            return
        del snap["levels"][sel[0]]
        mark("snapjob")
        refresh_levels()
        refresh_gigs()

    def level_pick(*_):
        sel = ltree.selection()
        if sel:
            v = snap["levels"][sel[0]]
            lname.set(v["name"])
            lfol.set(str(v["followers"]))

    ltree.bind("<<TreeviewSelect>>", level_pick)
    ttk.Button(lf, text="Add as new level", command=level_add).pack(side="left", padx=8)
    ttk.Button(lf, text="Save changes to selected", command=level_update).pack(side="left", padx=4)
    ttk.Button(lf, text="Delete selected", command=level_delete).pack(side="left", padx=4)

    ttk.Label(tab_l, text="Subject categories (the gallery filters of the phone)").pack(anchor="w", padx=8, pady=(20, 4))
    ctree = ttk.Treeview(tab_l, columns=("label",), height=6)
    ctree.heading("#0", text="Id")
    ctree.heading("label", text="Name shown")
    ctree.pack(fill="x", padx=8)
    cf = ttk.Frame(tab_l)
    cf.pack(fill="x", padx=8, pady=6)
    cname = tk.StringVar()
    ttk.Label(cf, text="New category name").pack(side="left")
    ttk.Entry(cf, textvariable=cname, width=24).pack(side="left", padx=6)

    def refresh_cats():
        ctree.delete(*ctree.get_children())
        for cid, lab in snap["categories"]:
            ctree.insert("", "end", iid=cid, text=cid, values=(lab,))

    def cat_add():
        lab = cname.get().strip()
        if not lab:
            return
        cid = slug(lab)
        if any(c[0] == cid for c in snap["categories"]):
            messagebox.showerror("Categories", "That category already exists.")
            return
        snap["categories"].append([cid, lab])
        cname.set("")
        mark("snapjob")
        refresh_cats()

    def cat_delete():
        sel = ctree.selection()
        if not sel:
            return
        if any(s["category"] == sel[0] for s in snap["subjects"].values()):
            messagebox.showerror("Categories", "Subjects use this category. Change them first.")
            return
        snap["categories"] = [c for c in snap["categories"] if c[0] != sel[0]]
        mark("snapjob")
        refresh_cats()

    ttk.Button(cf, text="Add category", command=cat_add).pack(side="left", padx=6)
    ttk.Button(cf, text="Delete selected", command=cat_delete).pack(side="left", padx=4)
    ttk.Label(tab_l, foreground="#666", wraplength=900,
              text="A level opens when the player reaches its follower count on Supernova. The Snapjob board shows gigs of the player's "
                   "level first and fills up with easier ones if the level has too few gigs.").pack(anchor="w", padx=8, pady=14)

    # ------------------------------------------------------------------------------- Ana boxes
    tab_a = ttk.Frame(nb)
    nb.add(tab_a, text="Ana boxes")
    SCALE_A = 0.6
    scene_ids = sorted(set(list(regions.keys()) + (list(poses_data.SCENES.keys()) if poses_data else [])))
    scene_var = tk.StringVar(value=scene_ids[0] if scene_ids else "")
    part_var = tk.StringVar(value="face")
    lf_a = ttk.Frame(tab_a)
    lf_a.pack(side="left", padx=8, pady=8)
    rf_a = ttk.Frame(tab_a)
    rf_a.pack(side="left", fill="y", padx=8, pady=8)
    ttk.Label(lf_a, text="Scene:").pack(anchor="w")
    scene_cb = ttk.Combobox(lf_a, textvariable=scene_var, values=scene_ids, state="readonly", width=30)
    scene_cb.pack(anchor="w", pady=4)
    canvas_a = tk.Canvas(lf_a, width=int(800 * SCALE_A), height=int(1080 * SCALE_A), bg="#333", highlightthickness=0)
    canvas_a.pack()
    a_state = {"drag": None, "img": None}
    ttk.Label(rf_a, text="Part to draw:").pack(anchor="w")
    for key in ["figure"] + PART_KEYS + ["object"]:
        ttk.Radiobutton(rf_a, text=key + ("  (the whole of her)" if key == "figure" else ""), variable=part_var, value=key).pack(anchor="w")
    ttk.Label(rf_a, wraplength=300, foreground="#666",
              text="Choose a part, then drag a rectangle on her picture. 'figure' replaces the old one; the others add a box "
                   "(a part can have several, like two hands). 'object' asks for a name (the pot, the mug...).").pack(anchor="w", pady=8)
    ttk.Label(rf_a, text="Boxes of this scene (click one to delete it):").pack(anchor="w")
    box_list = tk.Listbox(rf_a, height=16, width=44, exportselection=False)
    box_list.pack(anchor="w", pady=4)
    a_items = []

    def scene_regions(create=False):
        sid = scene_var.get()
        if sid not in regions and create:
            regions[sid] = {"figure": [0, 0, 800, 1080], "face": [[250, 40, 300, 250]], "torso": [[100, 250, 600, 350]],
                            "legs": [[100, 600, 600, 350]], "feet": [[100, 950, 600, 130]], "hands": [], "objects": []}
        return regions.get(sid)

    def draw_ana():
        canvas_a.delete("all")
        sid = scene_var.get()
        path = None
        if poses_data and sid in poses_data.SCENES:
            path = os.path.join(GAME, poses_data.SCENES[sid]["images"]["neutral"])
        W, H = int(800 * SCALE_A), int(1080 * SCALE_A)
        im = load_image(path, (int(1600 * 0.5 * SCALE_A), int(2160 * 0.5 * SCALE_A))) if path else None
        if im is not None:
            base = Image.new("RGBA", (W, H), (225, 220, 210, 255))
            base.alpha_composite(im)
            a_state["img"] = photo(base)
            canvas_a.create_image(0, 0, image=a_state["img"], anchor="nw")
        else:
            canvas_a.create_text(W // 2, H // 2, text="(picture not found)", fill="white")
        r = regions.get(sid)
        a_items.clear()
        box_list.delete(0, "end")
        if r is None:
            import masar_shot
            d = masar_shot.DEFAULT_REGIONS
            canvas_a.create_text(W // 2, 14, text="No boxes yet. Dashed = rough defaults the camera uses now.\nPress 'Start from the defaults' or just draw.", fill="#c00")
            for key in PART_KEYS:
                for b in d.get(key, []):
                    x, y, bw, bh = [v * SCALE_A for v in b]
                    canvas_a.create_rectangle(x, y, x + bw, y + bh, outline=PART_COLORS[key], dash=(4, 3), width=2)
            return

        def rect(b, color, text, w=2):
            x, y, bw, bh = [v * SCALE_A for v in b]
            canvas_a.create_rectangle(x, y, x + bw, y + bh, outline=color, width=w)
            if text:
                canvas_a.create_text(x + 3, y + 2, text=text, fill=color, anchor="nw", font=("Arial", 9, "bold"))

        rect(r["figure"], PART_COLORS["figure"], "figure")
        a_items.append(("figure", None))
        box_list.insert("end", "figure  %s" % (tuple(r["figure"]),))
        for key in PART_KEYS:
            for i, b in enumerate(r.get(key, [])):
                rect(b, PART_COLORS[key], key)
                a_items.append((key, i))
                box_list.insert("end", "%s  %s" % (key, tuple(b)))
        for i, o in enumerate(r.get("objects", [])):
            rect(o["box"], PART_COLORS["object"], o["name"], 3)
            a_items.append(("object", i))
            box_list.insert("end", "object '%s'  %s" % (o["name"], tuple(o["box"])))

    def ana_press(ev):
        a_state["drag"] = [ev.x, ev.y, ev.x, ev.y]

    def ana_move(ev):
        d = a_state["drag"]
        if d:
            d[2], d[3] = ev.x, ev.y
            canvas_a.delete("rubber")
            canvas_a.create_rectangle(d[0], d[1], d[2], d[3], outline="#00ffff", width=3, dash=(4, 3), tags="rubber")

    def ana_release(ev):
        d = a_state["drag"]
        a_state["drag"] = None
        if not d:
            return
        W, H = 800 * SCALE_A, 1080 * SCALE_A
        x0, x1 = sorted((max(0, min(W, d[0])), max(0, min(W, d[2]))))
        y0, y1 = sorted((max(0, min(H, d[1])), max(0, min(H, d[3]))))
        if x1 - x0 < 5 or y1 - y0 < 5:
            canvas_a.delete("rubber")
            return
        box = [int(round(x0 / SCALE_A)), int(round(y0 / SCALE_A)), int(round((x1 - x0) / SCALE_A)), int(round((y1 - y0) / SCALE_A))]
        r = scene_regions(create=True)
        part = part_var.get()
        if part == "figure":
            r["figure"] = box
        elif part == "object":
            name = simpledialog.askstring("Object", "Name of this object (e.g. The pot):", parent=root)
            if not name:
                draw_ana()
                return
            r.setdefault("objects", []).append({"name": name.strip(), "box": box})
        else:
            r.setdefault(part, []).append(box)
        mark("ana_regions")
        draw_ana()

    def ana_delete(*_):
        sel = box_list.curselection()
        r = regions.get(scene_var.get())
        if not sel or r is None:
            return
        key, i = a_items[sel[0]]
        if key == "figure":
            messagebox.showinfo("Ana boxes", "The figure box cannot be deleted; draw a new one to replace it.")
            return
        if key == "object":
            del r["objects"][i]
        else:
            del r[key][i]
        mark("ana_regions")
        draw_ana()

    canvas_a.bind("<ButtonPress-1>", ana_press)
    canvas_a.bind("<B1-Motion>", ana_move)
    canvas_a.bind("<ButtonRelease-1>", ana_release)
    ttk.Button(rf_a, text="Delete selected box", command=ana_delete).pack(anchor="w", pady=4)

    def ana_defaults():
        if scene_var.get() in regions:
            messagebox.showinfo("Ana boxes", "This scene already has boxes.")
            return
        scene_regions(create=True)
        mark("ana_regions")
        draw_ana()

    ttk.Button(rf_a, text="Start from the defaults", command=ana_defaults).pack(anchor="w", pady=4)
    scene_cb.bind("<<ComboboxSelected>>", lambda e: draw_ana())

    # ------------------------------------------------------------------------------- Characters (library)
    import masar_chars
    from tkinter import filedialog
    chars_ui = masar_chars.build_tab(dict(tk=tk, ttk=ttk, messagebox=messagebox, simpledialog=simpledialog,
                                          filedialog=filedialog, ImageTk=ImageTk, root=root, nb=nb, status=status,
                                          ROOT=ROOT, masar_data=masar_data))

    # ------------------------------------------------------------------------------- Photo scenes (wizard)
    import importlib
    import masar_scenes

    def scenes_changed(sid):
        """A scene was built or removed: reload game/poses_data.py and refresh the Ana boxes tab."""
        global poses_data
        try:
            if poses_data is None:
                import poses_data as _pd
                poses_data = _pd
            else:
                poses_data = importlib.reload(poses_data)
        except Exception as ex:                      # noqa: BLE001
            status.set("Scene saved, but game/poses_data.py could not be reloaded: %s" % ex)
            return
        ids = sorted(set(list(regions.keys()) + list(poses_data.SCENES.keys())))
        scene_cb.configure(values=ids)
        if sid and sid in ids:
            scene_var.set(sid)
        elif scene_var.get() not in ids and ids:
            scene_var.set(ids[0])
        draw_ana()
        refresh_overview()

    scenes_ui = masar_scenes.build_tab(dict(tk=tk, ttk=ttk, messagebox=messagebox, filedialog=filedialog, ImageTk=ImageTk,
                                            root=root, nb=nb, status=status, ROOT=ROOT, rooms=all_rooms(),
                                            on_built=scenes_changed))

    # ------------------------------------------------------------------------------- Schedule (who is where, when)
    import masar_schedule

    def default_at(look):
        """Where the game puts her when an entry has no custom place (same rules as game/rooms.rpy)."""
        if look.get("type") == "pose" and poses_data:
            rv = getattr(poses_data, "POSE_ROOM", {}).get(look.get("pose"))
            if rv:
                return {"x": rv.get("x", 960), "y": rv.get("y", 1080), "scale": rv.get("scale", 1.0), "flip": False}
            return {"x": getattr(poses_data, "POSE_AX", {}).get(look.get("pose"), 1274), "y": 1080, "scale": 1.0, "flip": False}
        if look.get("type") == "char":
            e = chars_ui["data"]["characters"].get(look.get("char"), {}).get("images", {}).get(look.get("image"))
            return {"x": 960, "y": 1080, "scale": round(950.0 / max(1, e["size"][1]), 3) if e else 0.4, "flip": False}
        return {"x": 1274, "y": 1080, "scale": 1.0, "flip": False}

    places_late = {}                                       # filled once the Places tab exists (it is built after the Schedule tab)
    schedule_ui = masar_schedule.build_tab(dict(tk=tk, ttk=ttk, messagebox=messagebox, ImageTk=ImageTk, root=root, nb=nb,
                                                status=status, ROOT=ROOT, rooms=all_rooms(), mark=mark, masar_data=masar_data,
                                                get_chars=lambda: chars_ui["data"]["characters"], default_at=default_at,
                                                room_start=lambda pid, rid: masar_rooms.get_start(rooms_data, pid, rid),
                                                hours=lambda pid, rid, part: (masar_places.is_open(places_late["ui"]["data"], pid, rid, part) if places_late else True)))

    places_ui = masar_places.build_tab(dict(tk=tk, ttk=ttk, nb=nb, mc=mc, mark=mark,
                                            data=masar_places.load(masar_data, mc.PART1_UNLOCKED)))
    places_late["ui"] = places_ui
    schedule_ui["refresh"]()

    # ------------------------------------------------------------------------------- start
    refresh_gigs()
    refresh_levels()
    refresh_cats()
    pick_room()
    draw_ana()
    refresh_overview()
    status.set("Loaded. Nothing changed yet.")
    state["refs"] = dict(room_var=room_var, time_v=time_v, draw_subjects=draw_subjects, root=root, nb=nb, snap=snap, regions=regions, state=state, subj_list=subj_list,
                         dialog=dialog_subject, save=save_all, canvas_s=canvas_s, canvas_a=canvas_a, chars=chars_ui, scenes=scenes_ui, scene_cb=scene_cb, tab_a=tab_a, schedule=schedule_ui, places=places_ui)
    return root, state["refs"]


if __name__ == "__main__":
    if not os.path.exists(os.path.join(GAME, "data", "snapjob.json")):
        sys.exit("Run this from the project folder (the one that contains game/ and tools/).")
    window, _refs = run_gui()
    window.mainloop()
