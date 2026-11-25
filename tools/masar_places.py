# -*- coding: utf-8 -*-
"""Editor tab "Places": which places are unlocked, and when each place / room is open.

Data: game/data/places.json
  {"version": 1, "unlocked": ["home", ...],
   "places": {"library": {"open": [0, 1, 2], "message": "The library closes at night."}},
   "rooms":  {"gym/combat": {"open": [0, 1, 2], "message": "..."}}}
open = time slots 0 Morning, 1 Afternoon, 2 Evening, 3 Night (no 'open' = always open).
"""
TIMES = ("Morning", "Afternoon", "Evening", "Night")


def load(masar_data, default_unlocked):
    try:
        d = masar_data.load("places")
    except Exception:
        d = {}
    d.setdefault("version", 1)
    d.setdefault("unlocked", list(default_unlocked))
    d.setdefault("places", {})
    d.setdefault("rooms", {})
    return d


def hours_text(entry):
    hrs = (entry or {}).get("open")
    if hrs is None:
        return "all day"
    if not hrs:
        return "never"
    return ", ".join(TIMES[i] for i in sorted(hrs))


def is_open(data, pid, rid, part):
    """Same rule as game/masar_core.py room_open (rid None = the place only)."""
    def ok(e):
        h = (e or {}).get("open")
        return True if h is None else part in h
    if not ok(data["places"].get(pid)):
        return False
    return rid is None or ok(data["rooms"].get("%s/%s" % (pid, rid)))


def validate(data, sched):
    """[(kind, text)] - Ana scheduled in a closed room, rooms that can never open, etc."""
    out = []
    for pid, e in data["places"].items():
        if e.get("open") == []:
            out.append(("warn", "Places: '%s' is never open." % pid))
    for who, c in (sched or {}).get("characters", {}).items():
        for e in c.get("entries", []):
            if e.get("away") or not e.get("place"):
                continue
            for part in e.get("parts", []):
                if not is_open(data, e["place"], e.get("room"), part):
                    out.append(("warn", "Schedule: '%s' is in %s/%s at %s, but it is closed then (she will not appear there)."
                                % (who, e["place"], e.get("room"), TIMES[part].lower())))
    return out


def build_tab(ctx):
    tk, ttk, nb = ctx["tk"], ctx["ttk"], ctx["nb"]
    mc, mark, data = ctx["mc"], ctx["mark"], ctx["data"]
    tab = ttk.Frame(nb)
    nb.add(tab, text="Places")
    left = ttk.Frame(tab)
    left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
    right = ttk.LabelFrame(tab, text="Selected", width=360)
    right.pack(side="right", fill="y", padx=8, pady=8)

    tree = ttk.Treeview(left, columns=("unlocked", "hours", "msg"), height=26)
    tree.heading("#0", text="Place / room")
    tree.heading("unlocked", text="Unlocked at start")
    tree.heading("hours", text="Open")
    tree.heading("msg", text="Closed message")
    tree.column("#0", width=260)
    tree.column("unlocked", width=110, anchor="center")
    tree.column("hours", width=210)
    tree.column("msg", width=330)
    tree.pack(fill="both", expand=True)
    ttk.Label(left, wraplength=800, foreground="#555",
              text="Locked = the place shows the lock picture on the map until the story unlocks it. Open hours = the time slots when the "
                   "place (or one room of it) can be entered; outside them the player gets the message, and if he is inside when it "
                   "closes he is sent out. Ana is never placed in a closed place.").pack(anchor="w", pady=6)

    st = {"sel": None, "lock": False}
    unlocked_v = tk.BooleanVar()
    time_v = [tk.BooleanVar(value=True) for _ in range(4)]
    msg_v = tk.StringVar()
    title_v = tk.StringVar(value="(select a place or a room)")
    ttk.Label(right, textvariable=title_v, font=("Arial", 11, "bold")).pack(anchor="w", padx=8, pady=6)
    chk_unlocked = ttk.Checkbutton(right, text="Unlocked at the start of Part 1", variable=unlocked_v)
    chk_unlocked.pack(anchor="w", padx=8, pady=4)
    ttk.Label(right, text="Open at (tick none = never; all four = all day):").pack(anchor="w", padx=8, pady=(10, 2))
    row = ttk.Frame(right)
    row.pack(anchor="w", padx=8)
    for i, t in enumerate(TIMES):
        ttk.Checkbutton(row, text=t, variable=time_v[i]).grid(row=i // 2, column=i % 2, sticky="w", padx=6, pady=2)
    ttk.Label(right, text="Message when closed (leave empty for the default):").pack(anchor="w", padx=8, pady=(12, 2))
    ttk.Entry(right, textvariable=msg_v, width=44).pack(padx=8)
    ttk.Label(right, text="e.g.  The library closes at night.", foreground="#777").pack(anchor="w", padx=8)

    def key_of(iid):
        return tuple(iid.split("/")) if "/" in iid else (iid, None)

    def entry_of(iid, create=False):
        pid, rid = key_of(iid)
        bucket = data["rooms"] if rid else data["places"]
        k = iid
        if create:
            return bucket.setdefault(k, {})
        return bucket.get(k, {})

    def refresh_rows():
        for iid in tree.get_children(""):
            pid = iid
            e = data["places"].get(pid, {})
            tree.item(iid, values=("yes" if pid in data["unlocked"] else "LOCKED", hours_text(e), e.get("message", "")))
            for rid_iid in tree.get_children(iid):
                re_ = data["rooms"].get(rid_iid, {})
                tree.item(rid_iid, values=("", hours_text(re_) if "open" in re_ else "(as the place)", re_.get("message", "")))

    for p in mc.PLACES:
        tree.insert("", "end", iid=p.id, text=p.name, open=False)
        for rid, rname in mc.rooms_of(p.id):
            tree.insert(p.id, "end", iid="%s/%s" % (p.id, rid), text="   " + rname)
    refresh_rows()

    def select(*_):
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        st["sel"] = iid
        st["lock"] = True
        pid, rid = key_of(iid)
        e = entry_of(iid)
        title_v.set(("%s  /  %s" % (mc.BY_ID[pid].name, mc.room_name(pid, rid))) if rid else mc.BY_ID[pid].name)
        hrs = e.get("open")
        for i in range(4):
            time_v[i].set(True if hrs is None else i in hrs)
        msg_v.set(e.get("message", ""))
        unlocked_v.set(pid in data["unlocked"])
        chk_unlocked.state(["disabled"] if rid else ["!disabled"])
        st["lock"] = False

    def apply(*_):
        if st["lock"] or not st["sel"]:
            return
        iid = st["sel"]
        pid, rid = key_of(iid)
        e = entry_of(iid, create=True)
        chosen = [i for i in range(4) if time_v[i].get()]
        if len(chosen) == 4:
            e.pop("open", None)
        else:
            e["open"] = chosen
        m = msg_v.get().strip()
        if m:
            e["message"] = m
        else:
            e.pop("message", None)
        if not e:
            (data["rooms"] if rid else data["places"]).pop(iid, None)
        if not rid:
            order = [p.id for p in mc.PLACES]
            cur = set(data["unlocked"])
            (cur.add if unlocked_v.get() else cur.discard)(pid)
            data["unlocked"] = [x for x in order if x in cur]
        refresh_rows()
        mark("places")

    tree.bind("<<TreeviewSelect>>", select)
    for v in time_v:
        v.trace_add("write", apply)
    unlocked_v.trace_add("write", apply)
    msg_v.trace_add("write", apply)
    return dict(tab=tab, data=data, validate=lambda sched: validate(data, sched), tree=tree, select=select, refresh=refresh_rows)
