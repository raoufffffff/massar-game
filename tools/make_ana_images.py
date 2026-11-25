"""Ana's pictures from green-screen originals.  Run from the project root.

  python tools/make_ana_images.py outfit plain raw_plain
      raw_plain/ana_plain_<expression>.jpg  and  ana_plain_<expression>_blink.jpg (optional)
      -> game/images/ana/ana_plain_<expression>[_blink].png (800x1080) + hover glows.
      Every picture is registered onto the neutral one so swapping expressions / blinking does not jitter.
      The game picks an outfit by room (see ana_outfit() in game/ana.rpy).

  python tools/make_ana_images.py poses raw_poses_plain
      raw_poses_plain/pose_<name>.jpg -> game/images/ana/pose_<name>.png (800x1080) + glow
      (room pictures of an activity without a photo scene, e.g. sweeping, phone, coffee).
Requires: pip install pillow numpy opencv-python
"""
import glob, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from key_sprites import key
from make_pose_camera import edge_despill, fit_34
import make_face_layers as fl

OUT = "game/images/ana"


def prep(path):
    im = fit_34(Image.open(path))                      # 3:4, as every other picture
    k = edge_despill(key(im))
    s = 1080 / k.height
    k = k.resize((round(k.width * s), 1080), Image.LANCZOS)
    c = Image.new("RGBA", (800, 1080), (0, 0, 0, 0))
    c.paste(k, ((800 - k.width) // 2, 0), k)
    return c


def outfit(name, src):
    files = sorted(glob.glob(os.path.join(src, "ana_%s_*.jpg" % name)))
    pics = {os.path.splitext(os.path.basename(f))[0]: prep(f) for f in files}
    ref = pics["ana_%s_neutral" % name]
    base = np.asarray(ref)
    for n, p in pics.items():
        if n != "ana_%s_neutral" % name:
            a = fl.global_align(base, np.asarray(p))
            p = Image.fromarray(np.asarray(a))
        p.save(os.path.join(OUT, n + ".png"), optimize=True)
        print(n)


def poses(src):
    for f in sorted(glob.glob(os.path.join(src, "pose_*.jpg"))):
        n = os.path.splitext(os.path.basename(f))[0]
        prep(f).save(os.path.join(OUT, n + ".png"), optimize=True)
        print(n)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if sys.argv[1] == "outfit":
        outfit(sys.argv[2], sys.argv[3])
    else:
        poses(sys.argv[2])
    subprocess.run([sys.executable, "tools/make_ui_assets.py", "game"], check=True, stdout=subprocess.DEVNULL)
