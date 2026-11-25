"""Add or rebuild Ana poses WITHOUT touching any code.

  python tools/add_pose.py                 rebuild every pose in poses/*.json
  python tools/add_pose.py eating          rebuild one pose
  python tools/add_pose.py eating --preview   only draw poses/_preview_eating.png (boxes check), build nothing

For each pose you provide:
  raw_blink/<raw>_neutral.jpg   (required, green screen)
  raw_blink/<raw>_smile.jpg     (optional)  raw_blink/<raw>_shy.jpg (optional)  raw_blink/<raw>_blink.jpg (optional)
  poses/<name>.json             (copy an existing one and edit it - see poses/README.txt)
The script cuts the green screen, writes the room picture, the camera pictures, the glow, the eyes/mouth
face layers, and game/poses_data.py (scenes, challenges, where she appears). The game reads that file.
"""
import glob, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import make_pose_camera as cam
import make_face_layers as fl
from PIL import Image, ImageDraw

RAW = "raw_blink"


def load_all():
    out = {}
    for p in sorted(glob.glob("poses/*.json")):
        out[os.path.splitext(os.path.basename(p))[0]] = json.load(open(p, encoding="utf-8"))
    return out


def present(cfg):
    return [e for e in ("neutral", "smile", "shy", "blink") if os.path.exists("%s/%s_%s.jpg" % (RAW, cfg["raw"], e))]


def check(name, cfg):
    errs = []
    if "neutral" not in present(cfg):
        errs.append("missing %s/%s_neutral.jpg" % (RAW, cfg["raw"]))
    for part, v in cfg["parts"].items():
        x, y, w, h = v["roi"]
        if x < 0 or y < 0 or x + w > 800 or y + h > 1080:
            errs.append("part %s: roi leaves the 800x1080 picture" % part)
    for shot in cfg["shots"]:
        if shot[0] not in cfg["parts"]:
            errs.append("shot uses unknown part %s" % shot[0])
        if shot[1] not in present(cfg) or shot[1] == "blink":
            errs.append("shot %s wants expression '%s' but there is no such picture" % (shot[0], shot[1]))
    return errs


def preview(name, cfg):
    img = "game/images/ana/pose_%s.png" % cfg["pose"]
    if not os.path.exists(img):
        sys.exit("build the pose once first (python tools/add_pose.py %s)" % name)
    base = Image.new("RGBA", (800, 1080), (225, 220, 210, 255))
    base.alpha_composite(Image.open(img).convert("RGBA"))
    d = ImageDraw.Draw(base)
    for part, v in cfg["parts"].items():
        x, y, w, h = v["roi"]
        d.rectangle([x, y, x + w, y + h], outline=(255, 0, 0, 255), width=3)
        d.text((x + 4, y + 4), part, fill=(255, 0, 0, 255))
    for k, col in (("eyes_box", (0, 120, 255, 255)), ("mouth_box", (0, 170, 0, 255))):
        if k not in cfg:
            continue
        x0, y0, x1, y1 = [v / 2 for v in cfg[k]]
        d.rectangle([x0, y0, x1, y1], outline=col, width=2)
    out = "poses/_preview_%s.png" % name
    base.save(out)
    print("wrote", out, "- red = challenge frames, blue = eyes box, green = mouth box")


def build(name, cfg):
    errs = check(name, cfg)
    if errs:
        sys.exit("poses/%s.json: \n  - " % name + "\n  - ".join(errs))
    key, have = cfg["key"], present(cfg)
    cam.POSES[key] = {"raw": cfg["raw"], "xoff": cfg["xoff"], "room": "pose_" + cfg["pose"]}
    cam.run(key)
    exprs = {"eyes": [e for e in ("blink", "smile", "shy") if e in have], "mouth": [e for e in ("smile", "shy") if e in have]}
    exprs["eyes"] = ["closed" if e == "blink" else e for e in exprs["eyes"]]
    layers = None
    if len(have) > 1:
        fl.POSES[key] = {"regions": {"eyes": tuple(cfg["eyes_box"]), "mouth": tuple(cfg["mouth_box"])}, "exprs": exprs}
        layers = fl.run(key)
    return layers


def write_data(cfgs, layers):
    data = {"SCENES": {}, "PARTS": {}, "ANA_POSES": {}, "POSE_FACE": {}, "POSE_RIGHT": [], "POSE_AX": {}, "POSE_ROOM": {}}
    for name, cfg in cfgs.items():
        # what exists = the camera pictures already built (the raw pictures may not be on disk any more)
        have = [e for e in ("neutral", "smile", "shy", "blink")
                if e in present(cfg) or os.path.exists("game/images/camera/%s_%s.png" % (cfg["key"], "closed" if e == "blink" else e))]
        images = {e: "images/camera/%s_%s.png" % (cfg["key"], e) for e in ("neutral", "smile", "shy") if e in have}
        if "neutral" not in images:
            print("WARNING: poses/%s.json has no neutral picture (raw_blink/%s_neutral.jpg or game/images/camera/%s_neutral.png) - skipped" % (name, cfg["raw"], cfg["key"]))
            continue
        sc = {"title": cfg["title"], "place": cfg["place"], "room": cfg["room"], "pose": cfg["pose"],
              "ax": cfg["ax"], "images": images, "shots": [tuple(s) for s in cfg["shots"]]}
        if len(have) > 1:
            sc["face"] = cfg["key"]
            data["POSE_FACE"][cfg["pose"]] = cfg["key"]
        data["SCENES"][cfg["scene"]] = sc
        data["PARTS"].update({k: {"name": v["name"], "roi": tuple(v["roi"]), "zoom": v["zoom"], "expr_w": v["expr_w"]}
                              for k, v in cfg["parts"].items()})
        data["ANA_POSES"].setdefault("%s|%s" % (cfg["place"], cfg["room"]), []).append(cfg["pose"])
        data["POSE_AX"][cfg["pose"]] = cfg["ax"]
        if cfg.get("room_view"):
            data["POSE_ROOM"][cfg["pose"]] = cfg["room_view"]
        if cfg["xoff"] == "right":
            data["POSE_RIGHT"].append(cfg["pose"])
    with open("game/poses_data.py", "w", encoding="utf-8") as f:
        f.write("# Generated by tools/add_pose.py from poses/*.json - do not edit by hand.\n")
        f.write("SCENES = %r\nPARTS = %r\nPOSE_FACE = %r\nPOSE_RIGHT = %r\nPOSE_AX = %r   # pose -> centre x of her picture on the 1920 screen (from \"ax\" in poses/*.json)\nPOSE_ROOM = %r   # pose -> placement in the ROOM view only (\"room_view\" in poses/*.json)\n" % (data["SCENES"], data["PARTS"], data["POSE_FACE"], data["POSE_RIGHT"], data["POSE_AX"], data["POSE_ROOM"]))
        f.write("ANA_POSES = %r   # (place, room) -> poses\n" % {tuple(k.split("|")): v for k, v in data["ANA_POSES"].items()})


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cfgs = load_all()
    names = args or list(cfgs)
    for n in names:
        if n not in cfgs:
            sys.exit("no poses/%s.json" % n)
    if "--preview" in sys.argv:
        for n in names:
            preview(n, cfgs[n])
        sys.exit()
    allv = {}
    if os.path.exists("game/face_layers.py"):
        ns = {}
        exec(open("game/face_layers.py", encoding="utf-8").read(), ns)
        allv = ns.get("LAYERS", {})
    for n in names:
        cfgs[n]["despill"] = cfgs[n].get("despill", False)
        if not args and "neutral" not in present(cfgs[n]) and os.path.exists("game/images/camera/%s_neutral.png" % cfgs[n]["key"]):
            print("kept as it is (raw pictures not in %s/, already built): %s" % (RAW, n))
            continue
        lay = build(n, cfgs[n])
        if lay:
            allv[cfgs[n]["key"]] = lay
    with open("game/face_layers.py", "w", encoding="utf-8") as f:
        f.write("# Generated by tools/add_pose.py - do not edit.\n"
                "# LAYERS[pose][eyes|mouth][expression] = (x, y, path) in the 1600x2160 pose picture.\n")
        f.write("LAYERS = " + json.dumps(allv, indent=1, sort_keys=True).replace("[", "(").replace("]", ")") + "\n")
    # face layers file: keep entries of other poses
    subprocess.run([sys.executable, "tools/make_ui_assets.py", "game"], check=True, stdout=subprocess.DEVNULL)
    write_data(cfgs, None)
    print("done: game/poses_data.py written for", ", ".join(cfgs))
