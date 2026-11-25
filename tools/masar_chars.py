# -*- coding: utf-8 -*-
"""Character library: import a green-screen picture -> transparent PNG + hover glow.

Used by tools/masar_editor.py (tab "Characters").  Pure Pillow (no numpy / OpenCV needed).

Files written, for a picture with id "stand_hips" of character "ana":
    game/chars/ana/stand_hips.png        the cut-out picture (cropped to the body + a small margin)
    game/chars/ana/stand_hips_glow.png   same size: the picture with a soft warm outline around the body
    chars_src/ana/stand_hips.png         your original (kept OUTSIDE game/ so it is not packed into the build;
                                         lets you re-process later with other settings)
Data: game/data/characters.json  (paths are relative to the game/ folder, like "chars/ana/stand_hips.png").

In Ren'Py, the click area of an imagebutton follows the visible body when you add focus_mask True:
    imagebutton idle "chars/ana/stand_hips.png" hover "chars/ana/stand_hips_glow.png" focus_mask True action ...
"""
import os
import re
import shutil
import time

from PIL import Image, ImageChops, ImageFilter

DEFAULTS = {"tol": 50, "shrink": 1, "feather": 1, "spill": 4, "glow_size": 7, "glow_power": 110,
            "glow_color": "#ffeec8", "margin": 48}


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return s or "item"


# ----------------------------------------------------------------------------------------------- keying
def detect_key(im):
    """Return 'dominance' of the background green, measured from the picture's corners/edges."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    pts = []
    n = max(4, min(w, h) // 40)
    for x0, y0 in ((0, 0), (w - n, 0), (0, h - n), (w - n, h - n)):
        c = rgb.crop((x0, y0, x0 + n, y0 + n)).resize((1, 1), Image.BOX).getpixel((0, 0))
        pts.append(c)
    r = sum(p[0] for p in pts) / 4.0
    g = sum(p[1] for p in pts) / 4.0
    b = sum(p[2] for p in pts) / 4.0
    return (r, g, b), g - max(r, b)


def key_image(im, tol=50, shrink=1, feather=1, spill=4):
    """Green screen -> RGBA.  tol 0..100: higher removes more green (and more of the fringe)."""
    rgb = im.convert("RGB")
    r, g, b = rgb.split()
    _col, dk = detect_key(rgb)
    if dk < 25:                                        # corners are not green: assume the classic key
        dk = 150.0
    t = max(0, min(100, tol)) / 100.0
    lo = dk * (0.60 - 0.50 * t)                        # below lo: fully kept
    hi = dk * (0.90 - 0.50 * t)                        # above hi: fully removed
    span = max(1.0, hi - lo)
    # dominance of green over the other channels (0..255), then a soft ramp to alpha
    dom = ImageChops.subtract(g, ImageChops.lighter(r, b))
    lut = [255 - int(max(0.0, min(1.0, (v - lo) / span)) * 255) for v in range(256)]
    alpha = dom.point(lut)
    if shrink > 0:                                     # eat the last light fringe
        alpha = alpha.filter(ImageFilter.MinFilter(2 * int(shrink) + 1))
    if feather > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
    # remove green spill near the silhouette only (so green clothes elsewhere stay green)
    if spill > 0:
        near = alpha.filter(ImageFilter.MinFilter(2 * int(spill) + 1)).point(lambda v: 255 if v < 250 else 0)
        near = near.filter(ImageFilter.GaussianBlur(1))
        g2 = ImageChops.darker(g, ImageChops.lighter(r, b))
        g = Image.composite(g2, g, near)
    out = Image.merge("RGBA", (r, g, b, alpha))
    return out


def drop_specks(rgba, min_share=0.02):
    """Delete small stray islands (JPEG noise, bits of floor/shadow) - keeps the big shapes (body, loose arms)."""
    a = rgba.getchannel("A")
    k = 4
    small = a.resize((max(1, a.width // k), max(1, a.height // k)), Image.BILINEAR).point(lambda v: 255 if v > 24 else 0)
    w, h = small.size
    px = list(small.getdata())
    lab = [0] * (w * h)
    sizes = {}
    n = 0
    for start in range(w * h):
        if px[start] and not lab[start]:
            n += 1
            stack = [start]
            lab[start] = n
            cnt = 0
            while stack:
                i = stack.pop()
                cnt += 1
                x = i % w
                for j in ((i - 1) if x > 0 else -1, (i + 1) if x < w - 1 else -1, i - w, i + w):
                    if 0 <= j < w * h and px[j] and not lab[j]:
                        lab[j] = n
                        stack.append(j)
            sizes[n] = cnt
    if n == 0:
        return rgba
    biggest = max(sizes.values())
    keep = set(i for i, c in sizes.items() if c >= max(4, biggest * min_share))
    mask = Image.new("L", (w, h), 0)
    mask.putdata([255 if lab[i] in keep else 0 for i in range(w * h)])
    mask = mask.resize(a.size, Image.NEAREST).filter(ImageFilter.MaxFilter(2 * k + 1))
    out = rgba.copy()
    out.putalpha(ImageChops.multiply(a, mask))
    return out


def trim_margin(rgba, margin=48):
    """Crop to the visible body, then add a transparent margin (room for the glow)."""
    box = rgba.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    if not box:
        return rgba
    body = rgba.crop(box)
    out = Image.new("RGBA", (body.width + 2 * margin, body.height + 2 * margin), (0, 0, 0, 0))
    out.paste(body, (margin, margin))
    return out


def hex_rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def make_glow(rgba, size=7, power=110, color="#ffeec8"):
    """The picture with a soft outline around the body only (same convention as the Ana pictures)."""
    a = rgba.getchannel("A")
    # work at quarter size: the filters are much faster and the glow is soft anyway
    k = 4
    small = a.resize((max(1, a.width // k), max(1, a.height // k)), Image.BILINEAR)
    grown = small.filter(ImageFilter.MaxFilter(2 * max(1, int(size) // 2) + 1)).filter(
        ImageFilter.GaussianBlur(max(1, size) / 2.0))
    big = grown.resize(a.size, Image.BILINEAR)
    k_pow = max(0, power) / 100.0
    big = big.point(lambda v: min(255, int(v * k_pow)))
    layer = Image.new("RGBA", rgba.size, hex_rgb(color) + (0,))
    layer.putalpha(big)
    layer.alpha_composite(rgba)
    return layer


def process(src_im, params):
    p = dict(DEFAULTS)
    p.update(params or {})
    k = key_image(src_im, p["tol"], p["shrink"], p["feather"], p["spill"])
    k = drop_specks(k)
    k = trim_margin(k, p["margin"])
    glow = make_glow(k, p["glow_size"], p["glow_power"], p["glow_color"])
    return k, glow


# ----------------------------------------------------------------------------------------------- data + files
def empty_data():
    return {"version": 1, "characters": {}}


def new_character(data, cid, name):
    cid = slug(cid)
    if cid in data["characters"]:
        raise ValueError("A character with id '%s' already exists." % cid)
    data["characters"][cid] = {"name": name.strip() or cid, "images": {}}
    return cid


def unique_image_id(data, cid, base):
    base = slug(base)
    used = data["characters"][cid]["images"]
    n, cand = 2, base
    while cand in used:
        cand = "%s_%d" % (base, n)
        n += 1
    return cand


def paths_for(root, cid, iid):
    game = os.path.join(root, "game")
    return {"png": os.path.join(game, "chars", cid, iid + ".png"),
            "glow": os.path.join(game, "chars", cid, iid + "_glow.png"),
            "src": os.path.join(root, "chars_src", cid, iid + ".png"),
            "rel_png": "chars/%s/%s.png" % (cid, iid), "rel_glow": "chars/%s/%s_glow.png" % (cid, iid)}


def write_image(root, data, cid, iid, label, src_im, params):
    """Process src_im and write the three files; create/update the data entry."""
    p = paths_for(root, cid, iid)
    for key in ("png", "src"):
        d = os.path.dirname(p[key])
        if not os.path.isdir(d):
            os.makedirs(d)
    k, glow = process(src_im, params)
    k.save(p["png"], optimize=True)
    glow.save(p["glow"], optimize=True)
    if not os.path.exists(p["src"]):
        src_im.convert("RGB").save(p["src"])
    prm = dict(DEFAULTS)
    prm.update(params or {})
    data["characters"][cid]["images"][iid] = {"label": label, "file": p["rel_png"], "glow": p["rel_glow"],
                                              "size": list(k.size), "params": prm}
    return k, glow


def import_file(root, data, cid, path, label=None, params=None):
    """Import one picture file for character cid.  Returns the new image id."""
    im = Image.open(path)
    im.load()
    iid = unique_image_id(data, cid, label or os.path.splitext(os.path.basename(path))[0])
    write_image(root, data, cid, iid, label or iid.replace("_", " ").capitalize(), im, params)
    return iid


def reprocess(root, data, cid, iid, params):
    p = paths_for(root, cid, iid)
    if not os.path.exists(p["src"]):
        raise IOError("The original of this picture is missing (%s)." % p["src"])
    im = Image.open(p["src"])
    im.load()
    entry = data["characters"][cid]["images"][iid]
    write_image(root, data, cid, iid, entry["label"], im, params)


def _trash_dir(root):
    d = os.path.join(root, "chars_trash", time.strftime("%Y%m%d_%H%M%S"))
    if not os.path.isdir(d):
        os.makedirs(d)
    return d


def delete_image(root, data, cid, iid):
    """Remove the entry and MOVE its files to chars_trash/ (nothing is erased)."""
    p = paths_for(root, cid, iid)
    t = _trash_dir(root)
    for key in ("png", "glow", "src"):
        if os.path.exists(p[key]):
            shutil.move(p[key], os.path.join(t, "%s_%s_%s" % (cid, iid, os.path.basename(p[key]))))
    data["characters"][cid]["images"].pop(iid, None)


def delete_character(root, data, cid):
    for iid in list(data["characters"][cid]["images"]):
        delete_image(root, data, cid, iid)
    data["characters"].pop(cid, None)


def rename_image(data, cid, iid, label):
    data["characters"][cid]["images"][iid]["label"] = label.strip() or iid


def inventory(data):
    n = sum(len(c["images"]) for c in data["characters"].values())
    return "%d characters, %d pictures" % (len(data["characters"]), n)


def validate(root, data):
    out = []
    for cid, c in data["characters"].items():
        for iid, e in c["images"].items():
            for k in ("file", "glow"):
                if not os.path.exists(os.path.join(root, "game", e[k])):
                    out.append(("error", "Character '%s', picture '%s': file %s is missing." % (cid, iid, e[k])))
    return out


# ----------------------------------------------------------------------------------------------- GUI tab
def build_tab(ctx):
    """Adds the 'Characters' tab to the editor's notebook.  ctx: dict from masar_editor.run_gui()."""
    tk, ttk = ctx["tk"], ctx["ttk"]
    messagebox, simpledialog, filedialog = ctx["messagebox"], ctx["simpledialog"], ctx["filedialog"]
    ImageTk = ctx["ImageTk"]
    root, nb, status, ROOT = ctx["root"], ctx["nb"], ctx["status"], ctx["ROOT"]
    masar_data = ctx["masar_data"]

    try:
        data = masar_data.load("characters")
    except IOError:
        data = empty_data()
    data.setdefault("characters", {})

    def save_now():
        masar_data.save("characters", data, backup=False)

    tab = ttk.Frame(nb)
    nb.add(tab, text="Characters")
    st = {"cid": None, "iid": None, "src_small": None, "scale": 1.0, "job": None, "keep": []}

    # ---- left: characters
    colL = ttk.Frame(tab)
    colL.pack(side="left", fill="y", padx=8, pady=8)
    ttk.Label(colL, text="Characters").pack(anchor="w")
    clist = tk.Listbox(colL, height=18, width=24, exportselection=False)
    clist.pack(fill="y", pady=4)
    # ---- middle: pictures
    colM = ttk.Frame(tab)
    colM.pack(side="left", fill="y", padx=8, pady=8)
    ttk.Label(colM, text="Pictures of the selected character").pack(anchor="w")
    ptree = ttk.Treeview(colM, columns=("size",), height=16)
    ptree.heading("#0", text="Name")
    ptree.heading("size", text="Size")
    ptree.column("#0", width=230)
    ptree.column("size", width=90, anchor="center")
    ptree.pack(pady=4)
    # ---- right: preview + settings
    colR = ttk.Frame(tab)
    colR.pack(side="left", fill="both", expand=True, padx=8, pady=8)
    PW, PH = 340, 440
    cv = tk.Canvas(colR, width=PW, height=PH, bg="#555", highlightthickness=0)
    cv.pack(anchor="w")
    view = tk.StringVar(value="result")
    vf = ttk.Frame(colR)
    vf.pack(anchor="w", pady=4)
    for val, txt in (("result", "Result"), ("glow", "Hover glow"), ("orig", "Original")):
        ttk.Radiobutton(vf, text=txt, value=val, variable=view, command=lambda: draw()).pack(side="left", padx=6)

    bf = ttk.Frame(colR)
    bf.pack(anchor="w", pady=4)
    ttk.Button(bf, text="Glow colour...", command=lambda: pick_color()).pack(side="left", padx=4)
    apply_btn = ttk.Button(bf, text="Apply to this picture", command=lambda: apply_params())
    apply_btn.pack(side="left", padx=4)

    sv = {"tol": tk.IntVar(value=DEFAULTS["tol"]), "shrink": tk.IntVar(value=DEFAULTS["shrink"]),
          "feather": tk.IntVar(value=DEFAULTS["feather"]), "spill": tk.IntVar(value=DEFAULTS["spill"]),
          "glow_size": tk.IntVar(value=DEFAULTS["glow_size"]), "glow_power": tk.IntVar(value=DEFAULTS["glow_power"])}
    color = tk.StringVar(value=DEFAULTS["glow_color"])
    sf = ttk.LabelFrame(colR, text="Cut-out and glow settings")
    sf.pack(fill="x", pady=4)
    rows = (("tol", "Green removal (higher = removes more)", 0, 100), ("shrink", "Shrink edge (px)", 0, 6),
            ("feather", "Soften edge (px)", 0, 6), ("spill", "Remove green tint on edge (px)", 0, 10),
            ("glow_size", "Glow size", 1, 20), ("glow_power", "Glow strength", 0, 200))
    for i, (key, text, lo, hi) in enumerate(rows):
        ttk.Label(sf, text=text, width=34).grid(row=i, column=0, sticky="w", padx=6)
        ttk.Scale(sf, from_=lo, to=hi, orient="horizontal", length=200,
                  command=lambda v, k=key: on_scale(k, v)).grid(row=i, column=1, pady=2)
        ttk.Label(sf, textvariable=sv[key], width=4).grid(row=i, column=2)
    scales = [w for w in sf.winfo_children() if isinstance(w, ttk.Scale)]

    def on_scale(k, v):
        if st.get("lock"):
            return
        sv[k].set(int(float(v)))
        schedule()

    st["lock"] = True
    for sc, (key, *_r) in zip(scales, rows):
        sc.set(sv[key].get())
    st["lock"] = False

    def pick_color():
        from tkinter import colorchooser
        c = colorchooser.askcolor(color.get(), title="Glow colour")[1]
        if c:
            color.set(c)
            schedule()

    ttk.Label(colR, foreground="#666", wraplength=420,
              text="Tip: send the picture on a plain green background. The preview is quick and approximate; "
                   "'Apply' redraws the real files. New imports use the settings shown here.").pack(anchor="w")

    # ---- helpers
    def params():
        p = {k: v.get() for k, v in sv.items()}
        p["glow_color"] = color.get()
        return p

    def set_params(p):
        st["lock"] = True
        for k in sv:
            sv[k].set(p.get(k, DEFAULTS[k]))
        color.set(p.get("glow_color", DEFAULTS["glow_color"]))
        for sc, (key, *_r) in zip(scales, rows):
            sc.set(sv[key].get())
        st["lock"] = False

    def cur_entry():
        if st["cid"] and st["iid"]:
            return data["characters"][st["cid"]]["images"].get(st["iid"])
        return None

    def refresh_chars(select=None):
        clist.delete(0, "end")
        ids = list(data["characters"])
        for cid in ids:
            clist.insert("end", "%s  [%s]" % (data["characters"][cid]["name"], cid))
        st["ids"] = ids
        if select in ids:
            clist.selection_set(ids.index(select))
        refresh_pics()

    def sel_cid():
        s = clist.curselection()
        return st["ids"][s[0]] if s else None

    def refresh_pics(select=None):
        for i in ptree.get_children():
            ptree.delete(i)
        cid = sel_cid()
        st["cid"] = cid
        if cid:
            for iid, e in data["characters"][cid]["images"].items():
                ptree.insert("", "end", iid=iid, text="%s  [%s]" % (e["label"], iid), values=("%dx%d" % tuple(e["size"]),))
            if select and ptree.exists(select):
                ptree.selection_set(select)
        on_pick()

    def on_pick(*_):
        sel = ptree.selection()
        st["iid"] = sel[0] if sel else None
        st["src_small"] = None
        e = cur_entry()
        if e:
            set_params(e.get("params", {}))
            sp = paths_for(ROOT, st["cid"], st["iid"])["src"]
            if os.path.exists(sp):
                im = Image.open(sp)
                im.load()
                s = min(1.0, 1100.0 / im.height)
                st["scale"] = s
                st["src_small"] = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS) if s < 1 else im
        draw()

    def scaled_params():
        p = params()
        s = st["scale"]
        for k in ("shrink", "feather", "spill"):
            p[k] = 0 if p[k] == 0 else max(1, int(round(p[k] * s)))
        p["margin"] = int(DEFAULTS["margin"] * s)
        return p

    def checker(size):
        w, h = size
        bg = Image.new("RGBA", size, (235, 235, 235, 255))
        from PIL import ImageDraw
        d = ImageDraw.Draw(bg)
        for y in range(0, h, 16):
            for x in range(0, w, 16):
                if (x // 16 + y // 16) % 2:
                    d.rectangle((x, y, x + 15, y + 15), fill=(205, 205, 205, 255))
        return bg

    def draw():
        cv.delete("all")
        e = cur_entry()
        if not e:
            cv.create_text(PW // 2, PH // 2, fill="#ddd", justify="center",
                           text="Select a picture on the left,\nor press 'Import pictures...'")
            return
        mode = view.get()
        if st["src_small"] is None:
            im = Image.open(os.path.join(ROOT, "game", e["glow" if mode == "glow" else "file"])).convert("RGBA")
        elif mode == "orig":
            im = st["src_small"].convert("RGBA")
        else:
            k, g = process(st["src_small"], scaled_params())
            im = g if mode == "glow" else k
        s = min(PW / float(im.width), PH / float(im.height))
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        bg = checker(im.size)
        bg.alpha_composite(im)
        ph = ImageTk.PhotoImage(bg)
        st["keep"] = [ph]
        cv.create_image(PW // 2, PH // 2, image=ph)

    def schedule():
        if st["job"]:
            root.after_cancel(st["job"])
        st["job"] = root.after(250, draw)

    # ---- actions
    def new_char():
        name = simpledialog.askstring("New character", "Character name (e.g. Ana, Sara, Coach Omar):", parent=root)
        if not name:
            return
        try:
            cid = new_character(data, slug(name), name)
        except ValueError as ex:
            messagebox.showerror("New character", str(ex))
            return
        save_now()
        refresh_chars(cid)
        status.set("Character '%s' created (id: %s)." % (name, cid))

    def del_char():
        cid = sel_cid()
        if not cid:
            return
        n = len(data["characters"][cid]["images"])
        if not messagebox.askyesno("Delete character", "Delete '%s' and its %d pictures?\n(The files are moved to the chars_trash folder, not erased.)"
                                   % (data["characters"][cid]["name"], n)):
            return
        delete_character(ROOT, data, cid)
        save_now()
        refresh_chars()

    def import_pics(paths=None, labels=None):
        cid = sel_cid()
        if not cid:
            messagebox.showinfo("Import", "Create or select a character first.")
            return
        if paths is None:
            paths = filedialog.askopenfilenames(title="Pictures on a green background",
                                                filetypes=[("Pictures", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")])
        last = None
        for i, path in enumerate(paths):
            stem = os.path.splitext(os.path.basename(path))[0].replace("_", " ")
            label = labels[i] if labels else simpledialog.askstring("Name this picture", "Name for %s\n(e.g. Standing, hands on hips):" % os.path.basename(path),
                                                                    initialvalue=stem, parent=root)
            if not label:
                continue
            try:
                last = import_file(ROOT, data, cid, path, label, params())
            except Exception as ex:
                messagebox.showerror("Import", "%s\n\n%s" % (os.path.basename(path), ex))
        if last:
            save_now()
            refresh_pics(last)
            status.set("Imported. Check the cut-out edge; adjust the sliders and press 'Apply' if needed.")

    def apply_params():
        e = cur_entry()
        if not e:
            return
        try:
            reprocess(ROOT, data, st["cid"], st["iid"], params())
        except Exception as ex:
            messagebox.showerror("Apply", str(ex))
            return
        save_now()
        refresh_pics(st["iid"])
        status.set("Picture re-processed.")

    def rename_pic():
        e = cur_entry()
        if not e:
            return
        label = simpledialog.askstring("Rename", "New name:", initialvalue=e["label"], parent=root)
        if label:
            rename_image(data, st["cid"], st["iid"], label)
            save_now()
            refresh_pics(st["iid"])

    def del_pic():
        e = cur_entry()
        if not e:
            return
        if not messagebox.askyesno("Delete picture", "Delete '%s'?\n(The files are moved to the chars_trash folder.)" % e["label"]):
            return
        delete_image(ROOT, data, st["cid"], st["iid"])
        save_now()
        refresh_pics()

    ttk.Button(colL, text="New character...", command=new_char).pack(fill="x", pady=2)
    ttk.Button(colL, text="Delete character", command=del_char).pack(fill="x", pady=2)
    ttk.Button(colM, text="Import pictures...", command=import_pics).pack(fill="x", pady=2)
    ttk.Button(colM, text="Rename", command=rename_pic).pack(fill="x", pady=2)
    ttk.Button(colM, text="Delete picture", command=del_pic).pack(fill="x", pady=2)
    clist.bind("<<ListboxSelect>>", lambda e: refresh_pics())
    ptree.bind("<<TreeviewSelect>>", on_pick)
    refresh_chars(next(iter(data["characters"]), None))
    return dict(data=data, import_pics=import_pics, new_char=new_char, clist=clist, ptree=ptree, refresh=refresh_chars,
                apply=apply_params, sv=sv, draw=draw, cv=cv, state=st)
