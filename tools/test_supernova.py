"""Checks for the Supernova rules.  Run from the project root:  python tools/test_supernova.py"""
import os, sys
ROOT = os.getcwd()
if os.path.basename(ROOT) == "tools":
    ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "game"))
import masar_supernova as sn
import masar_phone as mph
fails = []
def check(label, ok):
    print(("ok    " if ok else "FAIL  ") + label)
    if not ok:
        fails.append(label)

ph = mph.Phone()
room = ph.add_photo("view", "room", "park", "lake", 60, 1, 0, "x.jpg", (0, 0, 10, 10))
ana = ph.add_photo("ana", "ana", "home", "kitchen", 80, 1, 0, "y.png", (0, 0, 10, 10), rating=8)
s = sn.Supernova()
check("two accounts in the data", sn.account_ids() == ["me", "ana"])
check("his account is open from the start, Ana's is not", s.unlocked("me", []) and not s.unlocked("ana", []) and s.unlocked("ana", [5, 15]))
check("quality: rating x10 for Ana, match for the rest", sn.quality(ana) == 80 and sn.quality(room) == 60)
r = s.post("ana", ana, 2, 0, 0, [5])
check("Ana's account refuses before gate 15", not r["ok"] and "no Supernova" in r["text"])
r = s.post("ana", room, 2, 0, 0, [5, 15])
check("Ana's account refuses other photos", not r["ok"] and "Only photos of Ana" in r["text"])
r = s.post("ana", ana, 2, 0, 0, [5, 15])
check("Ana's post gives followers (80 x 0.8 = 64)", r["ok"] and r["gain"] == 64 and r["likes"] >= 0)
check("same photo twice refused", not s.can_post("ana", ana, 3, [15])[0])
ana2 = ph.add_photo("ana", "ana", "home", "kitchen", 50, 1, 0, "z.png", (0, 0, 10, 10), rating=5)
check("one post a day on Ana's account", not s.post("ana", ana2, 2, 1, 64, [15])["ok"])
check("... a new day is fine", s.post("ana", ana2, 3, 0, 64, [15])["ok"])
check("player: any photo, 3 a day", all(s.post("me", p, 2, 0, 0, [])["ok"] for p in (room, ana)))
extra = ph.add_photo("view", "room", "park", "lake", 90, 1, 0, "w.jpg", (0, 0, 10, 10))
check("the 3rd is fine", s.post("me", extra, 2, 1, 0, [])["ok"])
extra2 = ph.add_photo("view", "room", "park", "lake", 70, 1, 0, "v.jpg", (0, 0, 10, 10))
check("the 4th post of the day is refused", not s.post("me", extra2, 2, 2, 0, [])["ok"])
check("eligible list for Ana = only unposted Ana photos", s.eligible("ana", ph.photos) == [])
check("posts newest first and keep the photo", s.posts_of("me")[0]["photo"]["id"] == extra["id"])
import pickle
check("state pickles", len(pickle.loads(pickle.dumps(s)).posts["me"]) == 3)
print("\n%d failure(s)" % len(fails))
sys.exit(1 if fails else 0)
