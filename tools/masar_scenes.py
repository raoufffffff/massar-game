# -*- coding: utf-8 -*-
"""Photo scenes wizard (editor tab "Photo scenes").

A photo scene = one pose of a character in a room, with up to 4 pictures on a green background
(neutral / smile / shy / eyes closed).  The wizard fills poses/<pose>.json, copies the pictures to
raw_blink/ and runs tools/add_pose.py (the existing pipeline: cut-out, camera pictures, eye/mouth
face layers, game/poses_data.py).  Afterwards the scene appears in the "Ana boxes" tab.

Pure logic first (testable without a window), the tab at the bottom.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time

from PIL import Image, ImageChops, ImageFilter

EXPRS = (("neutral", "Normal (required)"), ("smile", "Smiling"), ("shy", "Shy"), ("blink", "Eyes closed"))
DEFAULT_EYES = [700, 300, 1000, 430]
DEFAULT_MOUTH = [800, 460, 960, 550]
AX = {4: 1274, "right": 1520}


def slug(text):
    import re
    s = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return s or "scene"


# ----------------------------------------------------------------------------------------------- data
def poses_dir(root):
    return os.path.join(root, "poses")


def load_all(root):
    out = {}
    for p in sorted(glob.glob(os.path.join(poses_dir(root), "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                out[os.path.splitext(os.path.basename(p))[0]] = json.load(f)
        except ValueError:
            pass
    return out


def raw_path(root, raw, expr):
    return os.path.join(root, "raw_blink", "%s_%s.jpg" % (raw, expr))


def camera_path(root, key, expr):
    return os.path.join(root, "game", "images", "camera", "%s_%s.png" % (key, "closed" if expr == "blink" else expr))


def present_raw(root, cfg):
    return [e for e, _ in EXPRS if os.path.exists(raw_path(root, cfg["raw"], e))]


def present_built(root, cfg):
    return [e for e, _ in EXPRS if os.path.exists(camera_path(root, cfg["key"], e))]


def make_cfg(pose, title, place, room, right=False, despill=False, eyes=None, mouth=None, boxes_set=False, old=None):
    xoff = "right" if right else 4
    cfg = dict(old or {})
    cfg.update({"key": pose, "raw": "pose_" + pose, "pose": pose, "scene": "%s_%s" % (room, pose), "title": title,
                "place": place, "room": room, "xoff": xoff, "ax": AX[xoff], "despill": bool(despill),
                "eyes_box": list(eyes or DEFAULT_EYES), "mouth_box": list(mouth or DEFAULT_MOUTH), "boxes_set": bool(boxes_set)})
    cfg.setdefault("parts", {})
    cfg.setdefault("shots", [])
    return cfg


def check_cfg(root, cfgs, name, cfg, files):
    """Problems that stop a build (list of text).  files = {expr: path} the user just chose."""
    errs = []
    if not cfg["title"].strip():
        errs.append("Give the scene a name (shown to the player).")
    for other, c in cfgs.items():
        if other != name and c.get("scene") == cfg["scene"]:
            errs.append("The scene id '%s' is already used by poses/%s.json - choose another pose id." % (cfg["scene"], other))
    if "neutral" not in files and not os.path.exists(raw_path(root, cfg["raw"], "neutral")) \
            and not os.path.exists(camera_path(root, cfg["key"], "neutral")):
        errs.append("The normal (neutral) picture is required.")
    return errs


def write_cfg(root, cfg):
    d = poses_dir(root)
    if not os.path.isdir(d):
        os.makedirs(d)
    with open(os.path.join(d, cfg["pose"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def store_pictures(root, raw, files):
    """Copy the chosen pictures to raw_blink/<raw>_<expr>.jpg (converted to JPEG)."""
    d = os.path.join(root, "raw_blink")
    if not os.path.isdir(d):
        os.makedirs(d)
    for expr, path in files.items():
        Image.open(path).convert("RGB").save(raw_path(root, raw, expr), quality=95)


def build_command(root, pose, python=None):
    return [python or os.environ.get("MASAR_PYTHON") or sys.executable, os.path.join("tools", "add_pose.py"), pose]


def trash_scene(root, pose):
    """Move poses/<pose>.json and its raw pictures to poses_trash/ (nothing is erased)."""
    cfg = load_all(root).get(pose)
    t = os.path.join(root, "poses_trash", time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(t)
    jp = os.path.join(poses_dir(root), pose + ".json")
    if os.path.exists(jp):
        shutil.move(jp, os.path.join(t, pose + ".json"))
    if cfg:
        for e, _ in EXPRS:
            p = raw_path(root, cfg["raw"], e)
            if os.path.exists(p):
                shutil.move(p, os.path.join(t, os.path.basename(p)))


def regenerate_data_command(python=None):
    """Rewrites game/poses_data.py from the remaining poses/*.json (after a delete)."""
    code = "import sys; sys.path.insert(0, 'tools'); import add_pose; add_pose.write_data(add_pose.load_all(), None)"
    return [python or os.environ.get("MASAR_PYTHON") or sys.executable, "-c", code]


# ----------------------------------------------------------------------------------------------- face box suggestion
def _flat(path, k):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
    bg.alpha_composite(im)
    return bg.convert("L").resize((max(1, im.width // k), max(1, im.height // k)), Image.BILINEAR), im.size


def _diff_mask(a, b, k, rel):
    A, size = _flat(a, k)
    B, _ = _flat(b, k)
    d = ImageChops.difference(A, B).filter(ImageFilter.GaussianBlur(2))
    mx = max(d.tobytes()) if d.size[0] else 0
    if mx < 12:
        return None, size
    return d.point(lambda v: 255 if v > mx * rel else 0), size


def suggest_boxes(root, cfg, pad=30):
    """A starting point for the eye and mouth boxes, from where the pictures differ.  Returns (eyes, mouth) or None."""
    k = 4
    eyes = mouth = None
    key = cfg["key"]
    neutral = camera_path(root, key, "neutral")
    if not os.path.exists(neutral):
        return None
    m, size = (None, None)
    for e in ("blink", "smile", "shy"):
        p = camera_path(root, key, e)
        if os.path.exists(p):
            m, size = _diff_mask(neutral, p, k, 0.45)
            if m and m.getbbox():
                bb = [v * k for v in m.getbbox()]
                eyes = [max(0, bb[0] - pad), max(0, bb[1] - pad), min(size[0], bb[2] + pad), min(size[1], bb[3] + pad)]
                break
    if eyes is None:
        return None
    for e in ("smile", "shy"):
        p = camera_path(root, key, e)
        if os.path.exists(p):
            m, size = _diff_mask(neutral, p, k, 0.4)
            if not m:
                continue
            y0 = (eyes[3] - pad // 2) // k
            low = m.crop((0, max(0, y0), m.width, m.height)).getbbox()
            if low:
                bb = [v * k for v in low]
                top = eyes[3] - pad // 2
                mouth = [max(0, bb[0] - pad // 2), max(eyes[3], top + bb[1] - pad // 2), min(size[0], bb[2] + pad // 2),
                         min(size[1], top + bb[3] + pad // 2)]
                break
    return eyes, mouth


# ----------------------------------------------------------------------------------------------- the tab
def build_tab(ctx):
    tk, ttk = ctx["tk"], ctx["ttk"]
    messagebox, filedialog = ctx["messagebox"], ctx["filedialog"]
    ImageTk = ctx["ImageTk"]
    root, nb, status, ROOT = ctx["root"], ctx["nb"], ctx["status"], ctx["ROOT"]
    rooms = ctx["rooms"]                                  # [(place_id, room_id, label)]
    on_built = ctx["on_built"]

    tab = ttk.Frame(nb)
    nb.add(tab, text="Photo scenes")
    st = {"name": None, "files": {}, "cfg": None, "box": {"eyes": list(DEFAULT_EYES), "mouth": list(DEFAULT_MOUTH)},
          "set": False, "keep": [], "busy": False, "drag": None}
    SC = 0.26

    colL = ttk.Frame(tab)
    colL.pack(side="left", fill="y", padx=8, pady=8)
    ttk.Label(colL, text="Photo scenes").pack(anchor="w")
    slist = tk.Listbox(colL, height=22, width=26, exportselection=False)
    slist.pack(fill="y", pady=4)

    colM = ttk.Frame(tab)
    colM.pack(side="left", fill="y", padx=8, pady=8)
    colR = ttk.Frame(tab)
    colR.pack(side="left", fill="both", expand=True, padx=8, pady=8)

    # ---- form
    title_v, pose_v, room_v = tk.StringVar(), tk.StringVar(), tk.StringVar(value=rooms[0][2])
    right_v, despill_v = tk.BooleanVar(), tk.BooleanVar()
    ttk.Label(colM, text="Name shown to the player (e.g. Cooking in the kitchen):").pack(anchor="w")
    ttk.Entry(colM, textvariable=title_v, width=40).pack(anchor="w", pady=(0, 4))
    ttk.Label(colM, text="Short id of the pose (letters, e.g. cooking) - cannot change later:").pack(anchor="w")
    pose_entry = ttk.Entry(colM, textvariable=pose_v, width=24)
    pose_entry.pack(anchor="w", pady=(0, 4))
    ttk.Label(colM, text="Where can it happen?").pack(anchor="w")
    ttk.Combobox(colM, textvariable=room_v, values=[r[2] for r in rooms], state="readonly", width=34).pack(anchor="w", pady=(0, 6))

    pf = ttk.LabelFrame(colM, text="Pictures (on a green background, same pose; only 'Normal' is required)")
    pf.pack(fill="x", pady=4)
    file_lbl = {}
    for i, (e, text) in enumerate(EXPRS):
        ttk.Label(pf, text=text, width=16).grid(row=i, column=0, sticky="w", padx=4, pady=2)
        file_lbl[e] = tk.StringVar(value="-")
        ttk.Label(pf, textvariable=file_lbl[e], width=18).grid(row=i, column=1, sticky="w")
        ttk.Button(pf, text="Choose...", width=9, command=lambda e=e: choose(e)).grid(row=i, column=2, padx=2)
        ttk.Button(pf, text="Clear", width=6, command=lambda e=e: clear(e)).grid(row=i, column=3, padx=2)
    ttk.Checkbutton(colM, text="Her picture is cut by the right edge (she stands flush right)", variable=right_v).pack(anchor="w")
    ttk.Checkbutton(colM, text="Remove a green fringe around the hair", variable=despill_v).pack(anchor="w")
    bar = ttk.Frame(colM)
    bar.pack(anchor="w", pady=8)
    build_btn = ttk.Button(bar, text="Build / rebuild", command=lambda: do_build())
    build_btn.pack(side="left", padx=4)
    ttk.Button(bar, text="New scene", command=lambda: new_form()).pack(side="left", padx=4)
    ttk.Button(bar, text="Delete scene", command=lambda: del_scene()).pack(side="left", padx=4)
    log = tk.Text(colM, height=10, width=52, state="disabled", wrap="word", background="#f4f4f4")
    log.pack(fill="x", pady=4)
    ttk.Label(colM, foreground="#666", wraplength=440,
              text="Steps: 1) fill the form and press Build. 2) If you have smile / shy / eyes-closed pictures, look at "
                   "the picture on the right: draw the EYES and MOUTH rectangles (or press Auto-suggest) and press Build again. "
                   "3) Open the 'Ana boxes' tab and draw her body boxes for the new scene.").pack(anchor="w")

    # ---- boxes canvas
    ttk.Label(colR, text="Check her face boxes on the built picture").pack(anchor="w")
    cv = tk.Canvas(colR, width=int(1600 * SC), height=int(2160 * SC), bg="#444", highlightthickness=0)
    cv.pack(anchor="w")
    part_v = tk.StringVar(value="eyes")
    show_v = tk.StringVar(value="neutral")
    rf = ttk.Frame(colR)
    rf.pack(anchor="w", pady=4)
    ttk.Radiobutton(rf, text="Eyes box (blue)", value="eyes", variable=part_v).pack(side="left", padx=4)
    ttk.Radiobutton(rf, text="Mouth box (green)", value="mouth", variable=part_v).pack(side="left", padx=4)
    ttk.Button(rf, text="Auto-suggest", command=lambda: auto()).pack(side="left", padx=8)
    sf = ttk.Frame(colR)
    sf.pack(anchor="w")
    ttk.Label(sf, text="Show:").pack(side="left")
    for e, text in EXPRS:
        ttk.Radiobutton(sf, text=text.split(" (")[0], value=e, variable=show_v, command=lambda: draw()).pack(side="left", padx=3)

    def say(text, clear_first=False):
        log.config(state="normal")
        if clear_first:
            log.delete("1.0", "end")
        log.insert("end", text + "\n")
        log.see("end")
        log.config(state="disabled")

    def choose(e):
        p = filedialog.askopenfilename(title="Picture on a green background",
                                       filetypes=[("Pictures", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")])
        if p:
            st["files"][e] = p
            file_lbl[e].set(os.path.basename(p))

    def clear(e):
        st["files"].pop(e, None)
        file_lbl[e].set("-")

    def refresh_list(select=None):
        slist.delete(0, "end")
        cfgs = load_all(ROOT)
        st["names"] = list(cfgs)
        for n, c in cfgs.items():
            have = present_built(ROOT, c) or present_raw(ROOT, c)
            slist.insert("end", "%s  [%s]  %d pict." % (c.get("title", n), c.get("scene", n), len(have)))
        if select in st["names"]:
            slist.selection_set(st["names"].index(select))

    def new_form():
        slist.selection_clear(0, "end")
        st.update(name=None, files={}, cfg=None, set=False)
        st["box"] = {"eyes": list(DEFAULT_EYES), "mouth": list(DEFAULT_MOUTH)}
        title_v.set("")
        pose_v.set("")
        pose_entry.config(state="normal")
        right_v.set(False)
        despill_v.set(False)
        for e, _ in EXPRS:
            file_lbl[e].set("-")
        draw()

    def load_scene(*_):
        sel = slist.curselection()
        if not sel:
            return
        name = st["names"][sel[0]]
        cfg = load_all(ROOT)[name]
        st.update(name=name, files={}, cfg=cfg, set=bool(cfg.get("boxes_set", True)))
        st["box"] = {"eyes": list(cfg.get("eyes_box", DEFAULT_EYES)), "mouth": list(cfg.get("mouth_box", DEFAULT_MOUTH))}
        title_v.set(cfg.get("title", ""))
        pose_v.set(cfg["pose"])
        pose_entry.config(state="disabled")
        for pid, rid, lab in rooms:
            if pid == cfg["place"] and rid == cfg["room"]:
                room_v.set(lab)
        right_v.set(cfg.get("xoff") == "right")
        despill_v.set(bool(cfg.get("despill")))
        raw = present_raw(ROOT, cfg)
        built = present_built(ROOT, cfg)
        for e, _ in EXPRS:
            file_lbl[e].set("(already there)" if (e in raw or e in built) else "-")
        draw()

    def draw():
        cv.delete("all")
        cfg = st["cfg"]
        if not cfg:
            cv.create_text(int(1600 * SC) // 2, 100, fill="#ddd", justify="center",
                           text="Build the scene once:\nher built picture appears here.")
            return
        p = camera_path(ROOT, cfg["key"], show_v.get())
        if not os.path.exists(p):
            p = camera_path(ROOT, cfg["key"], "neutral")
        if os.path.exists(p):
            im = Image.open(p).convert("RGBA")
            bg = Image.new("RGBA", im.size, (225, 220, 210, 255))
            bg.alpha_composite(im)
            bg = bg.resize((int(1600 * SC), int(2160 * SC)), Image.LANCZOS)
            ph = ImageTk.PhotoImage(bg)
            st["keep"] = [ph]
            cv.create_image(0, 0, image=ph, anchor="nw")
        else:
            cv.create_text(int(1600 * SC) // 2, 100, fill="#ddd", text="Not built yet.")
        for part, col in (("eyes", "#2a7fff"), ("mouth", "#1fb34a")):
            x0, y0, x1, y1 = [v * SC for v in st["box"][part]]
            cv.create_rectangle(x0, y0, x1, y1, outline=col, width=2)
            cv.create_text(x0 + 3, y0 - 8, text=part, fill=col, anchor="w")

    def press(ev):
        st["drag"] = (ev.x, ev.y)

    def move(ev):
        if not st["drag"]:
            return
        x0, y0 = st["drag"]
        st["box"][part_v.get()] = [int(min(x0, ev.x) / SC), int(min(y0, ev.y) / SC), int(max(x0, ev.x) / SC), int(max(y0, ev.y) / SC)]
        st["set"] = True
        draw()

    def release(ev):
        st["drag"] = None

    cv.bind("<ButtonPress-1>", press)
    cv.bind("<B1-Motion>", move)
    cv.bind("<ButtonRelease-1>", release)

    def auto():
        cfg = st["cfg"]
        if not cfg:
            messagebox.showinfo("Auto-suggest", "Build the scene once first (with at least one extra picture).")
            return
        r = suggest_boxes(ROOT, cfg)
        if not r:
            messagebox.showinfo("Auto-suggest", "Not enough different pictures to guess. Draw the two boxes by hand.")
            return
        st["box"]["eyes"] = r[0]
        if r[1]:
            st["box"]["mouth"] = r[1]
        st["set"] = True
        draw()
        say("Boxes suggested: check them on the picture and adjust by drawing again.")

    def run(cmd, then):
        """Run a command, show its output in the log, call then(ok) at the end."""
        import threading
        out = []
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"

        def worker():
            try:
                pr = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
                for line in pr.stdout:
                    out.append(line.decode("utf-8", "replace").rstrip())
                pr.wait()
                out.append("EXIT %d" % pr.returncode)
            except Exception as ex:
                out.append("ERROR %s" % ex)
                out.append("EXIT 1")

        threading.Thread(target=worker, daemon=True).start()
        shown = [0]

        def poll():
            while shown[0] < len(out):
                say(out[shown[0]])
                shown[0] += 1
            if out and out[-1].startswith("EXIT"):
                then(out[-1] == "EXIT 0", "\n".join(out))
            else:
                root.after(300, poll)

        poll()

    def do_build():
        if st["busy"]:
            return
        label = room_v.get()
        place, room = [(p, r) for p, r, lab in rooms if lab == label][0]
        old = st["cfg"]
        pose = st["name"] or slug(pose_v.get() or title_v.get())
        cfgs = load_all(ROOT)
        cfg = make_cfg(pose, title_v.get().strip(), place, room, right_v.get(), despill_v.get(),
                       st["box"]["eyes"], st["box"]["mouth"], st["set"], old if st["name"] else None)
        errs = check_cfg(ROOT, cfgs, st["name"], cfg, st["files"])
        if errs:
            messagebox.showerror("Photo scene", "\n".join(errs))
            return
        try:
            write_cfg(ROOT, cfg)
            store_pictures(ROOT, cfg["raw"], st["files"])
        except Exception as ex:
            messagebox.showerror("Photo scene", str(ex))
            return
        st["name"] = pose
        pose_entry.config(state="disabled")
        pose_v.set(pose)
        st["busy"] = True
        build_btn.config(state="disabled")
        status.set("Building the scene... (can take a minute)")
        say("--- building %s ---" % pose, clear_first=True)

        def done(ok, text):
            st["busy"] = False
            build_btn.config(state="normal")
            st["files"] = {}
            if not ok:
                hint = ""
                if "No module named" in text:
                    hint = "\n\nA Python package is missing. Run once:  pip install pillow numpy opencv-python"
                status.set("The build failed (see the log).")
                messagebox.showerror("Photo scene", "The build failed. See the log below the form." + hint)
                return
            st["cfg"] = load_all(ROOT).get(pose, cfg)
            refresh_list(pose)
            for e, _ in EXPRS:
                file_lbl[e].set("(already there)" if e in present_built(ROOT, st["cfg"]) else "-")
            draw()
            status.set("Scene built.")
            multi = len(present_built(ROOT, st["cfg"])) > 1
            on_built(st["cfg"]["scene"])
            if multi and not st["set"]:
                say("Built with rough face boxes. Check them on the picture (or press Auto-suggest), then Build again.")
            else:
                say("Done. Next: open the 'Ana boxes' tab, pick the scene '%s' and draw her body boxes." % st["cfg"]["scene"])

        run(build_command(ROOT, pose), done)

    def del_scene():
        if not st["name"]:
            return
        if not messagebox.askyesno("Delete scene", "Remove the scene '%s' from the game?\n(Its settings and original pictures move to poses_trash/.)" % title_v.get()):
            return
        trash_scene(ROOT, st["name"])
        name = st["name"]
        new_form()
        refresh_list()

        def after(ok, _t):
            on_built(None)
            status.set("Scene removed." if ok else "Scene removed, but game/poses_data.py could not be rewritten (see log).")

        run(regenerate_data_command(), after)

    slist.bind("<<ListboxSelect>>", load_scene)
    refresh_list()
    draw()
    return dict(tab=tab, st=st, build=do_build, load=load_scene, slist=slist, vars=dict(title=title_v, pose=pose_v, room=room_v, right=right_v, despill=despill_v),
                refresh=refresh_list, new=new_form, auto=auto, draw=draw, files=st["files"], log=log, file_lbl=file_lbl)
