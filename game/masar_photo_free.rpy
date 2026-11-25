# The free camera: used for EVERY photo, in every photo spot and with Ana.
# Nothing is asked of the player: aim the lens, zoom, hold steady, press SHOOT. The game then works out what is in
# the photo (rules in masar_shot.py) and saves it in the phone gallery:
#   * a room: every named subject in the frame is counted (the match comes from framing and steadiness);
#     a photo with no known subject is a "Random shot N"
#   * Ana in the room: which part of her, her expression at that instant, her activity
# A session = up to 5 shots and costs one time slot (script.rpy).  The lens engine is shared with masar_photo_ana.rpy.

init -1 python:
    import masar_shot as msh

default ff = {}                           # the running session (see ff_setup)
default photo_free_tutorial_done = False
default photo_free_hint_done = False

init python:
    def cam_bar(st, at):
        """Panoramic room: a thin strip under the lens that shows which part of the whole room the lens sees."""
        if mp.WORLD_W <= 1920:
            return Null(), 0.5
        total = 1260
        vw = mp.WIN_W / float(mp.BASE * store.cam_z)
        w = max(12, int(total * min(1.0, vw / mp.WORLD_W)))
        x = int(total * max(0.0, store.cam_cx - vw / 2.0) / mp.WORLD_W)
        return Fixed(Solid("#ffffff38", xysize=(total, 7)), Solid("#ffd54a", xysize=(w, 7), xpos=min(x, total - w)),
                     xysize=(total, 7)), 0.05

    import random

    FREE_SHOTS = 5                        # shots per session

    def ff_setup(scene_id):
        """Start a session. scene_id = Ana's photo scene here (mp.SCENES), or None when she is not in the room."""
        d = {"n": 0, "max": FREE_SHOTS, "place": store.location, "room": store.room, "ana": None,
             "t0": renpy.get_game_runtime(), "photo_id": None}
        mp.set_world(room_world_w(store.location, store.room))      # a panoramic room gives a wider camera world
        if scene_id:
            sc = mp.SCENES[scene_id]
            keys, blinks = mp.make_timeline(random.Random(), store.ana_idle)
            ax = ana_world_ax(sc["ax"])                              # where she stands in this room's world
            d["ana"] = {"scene": scene_id, "ax": ax,
                        "shot": {"scene": scene_id, "ax": ax, "tl": keys, "bl": blinks}}
        store.ff = d
        store.cam_zmax = msh.ZMAX_ANA if scene_id else msh.ZMAX_ROOM

    def ff_draws(t):
        """Ana's pictures at time t of her loop (empty when she is not here)."""
        a = store.ff.get("ana")
        return mp.layer_draws(a["shot"], t) if a else []

    def ff_shoot():
        """Take the photo with exactly what the lens shows at this instant, and keep it in the gallery."""
        d = store.ff
        now = renpy.get_game_runtime()
        t = (now - d["t0"]) % mp.LOOP_LENGTH
        swx, swy = mp.sway(now, store.cam_z, store.cam_steady)
        vcx, vcy = mp.clamp_view(store.cam_cx + swx, store.cam_cy + swy, store.cam_z)
        res = msh.analyze(d["place"], d["room"], d["ana"], t, vcx, vcy, store.cam_z, store.cam_steady, store.cam_bgb)
        sc = mp.BASE * store.cam_z
        res["anablur"] = mp.blur_amount(1.0 - store.cam_steady) / sc
        res["bgblur"] = mp.blur_amount(max(1.0 - store.cam_steady, store.cam_bgb)) / sc
        p = ph_save_free(res)
        p["ww"] = mp.WORLD_W                          # width of the world this photo was taken in (panoramic rooms)
        d["n"] += 1
        d["photo_id"] = p["id"]

    def ph_save_free(res):
        pl, rm = res["place"], res["room"]
        if res["kind"] == "ana":
            label = "Ana - " + res["type_label"]
        elif res["subject"] == "random":
            label = None                              # the phone numbers it: "Random shot N"
        else:
            label = mph.subject_label(res["subject"])
        return store.phone.add_photo(res["subject"], res["kind"], pl, rm, res["score"], store.day, store.day_part,
                                     mc.bg_path(pl, rm), (0, 0, 1920, 1080), label=label,
                                     matches=res["matches"], layers=res["layers"], view=res["view"],
                                     props=res["props"], shot_type=res["shot_type"],
                                     expression=res.get("expression", ""),
                                     bgblur=res["bgblur"], anablur=res["anablur"], rating=res.get("rating"))


# ------------------------------------------------------------------------------------ the camera screen
screen photo_free(d, bg):
    modal True
    $ now = renpy.get_game_runtime()
    $ t = (now - d["t0"]) % mp.LOOP_LENGTH
    $ draws = ff_draws(t)
    $ has_ana = d["ana"] is not None
    $ swx, swy = mp.sway(now, cam_z, cam_steady)
    $ vcx, vcy = mp.clamp_view(cam_cx + swx, cam_cy + swy, cam_z)
    $ sc = mp.BASE * cam_z
    $ px = mp.WIN_W / 2.0 - vcx * sc
    $ py = mp.WIN_H / 2.0 - vcy * sc
    $ ana_lv = 1.0 - cam_steady
    $ bg_lv = max(ana_lv, cam_bgb)
    $ ana_b = mp.blur_amount(ana_lv) / sc
    $ bg_b = mp.blur_amount(bg_lv) / sc
    $ fcol = "#ff5a4a" if cam_steady < 0.5 else ("#ffd54a" if cam_steady < 0.9 else "#5dff7a")
    $ ffn = d["n"] + 1
    $ ffmax = d["max"]
    $ fx = mp.WIN_X + mp.WIN_W // 2
    $ fy = mp.WIN_Y + mp.WIN_H // 2

    add Solid("#0b0c10")

    # What the lens sees: the room (and Ana, if she is here), scaled and moved
    fixed:
        pos (mp.WIN_X, mp.WIN_Y)
        xysize (mp.WIN_W, mp.WIN_H)
        clipping True
        fixed:
            at cam_view(px, py, sc)
            xysize (mp.WORLD_W, mp.WORLD_H)
            add bg at cam_blur(bg_b)
            fixed:
                at cam_blur(ana_b)
                xysize (mp.WORLD_W, mp.WORLD_H)
                for dpath, dx, dy, dalpha in draws:
                    add Transform(dpath, alpha=dalpha) pos (int(dx), int(dy)) zoom mp.IMG_ZOOM

    # Click inside the lens = shutter
    button:
        pos (mp.WIN_X, mp.WIN_Y)
        xysize (mp.WIN_W, mp.WIN_H)
        background None
        action [Function(ff_shoot), Return("shot")]

    add "images/camera/lens.png"

    # Steadiness frame (red: shaking, yellow: settling, green: steady)
    add Solid(fcol) pos (fx - 62, fy - 62) xysize (124, 3)
    add Solid(fcol) pos (fx - 62, fy + 59) xysize (124, 3)
    add Solid(fcol) pos (fx - 62, fy - 62) xysize (3, 124)
    add Solid(fcol) pos (fx + 59, fy - 62) xysize (3, 124)

    # Left bar
    vbox:
        pos (20, 100)
        xsize 290
        spacing 12
        text "CAMERA" size 34 color "#ffffff"
        text "Shot [ffn] / [ffmax]" size 30 color "#ffd54a"
        text "Frame what you like and shoot. Every photo goes to your phone gallery." size 22 color "#9aa0b4"
        if has_ana:
            text "Ana is in the room. Her expression changes: choose the moment." size 22 color "#9aa0b4"
        null height 20
        textbutton "Finish session":
            text_size 28
            padding (20, 10)
            background Solid("#283048")
            hover_background Solid("#34406a")
            text_color "#ffffff"
            action Return("finish")
        text "(Esc)" size 18 color "#6f7890"

    # Right bar: zoom, arrows, steadiness
    vbox:
        pos (1610, 100)
        xsize 290
        spacing 12
        text "ZOOM  x[cam_z:.1f]" size 28 color "#ffffff"
        hbox:
            spacing 14
            textbutton "-" action Function(cam_zoom, -0.3) text_size 44 xsize 100 ysize 70 text_xalign 0.5 text_yalign 0.5
            textbutton "+" action Function(cam_zoom, 0.3) text_size 44 xsize 100 ysize 70 text_xalign 0.5 text_yalign 0.5
        text "MOVE" size 22 color "#9aa0b4"
        hbox:
            xsize 214
            textbutton "^" action Function(cam_nudge, 0, -140) text_size 34 xsize 64 xalign 0.5 text_xalign 0.5
        hbox:
            spacing 6
            textbutton "<" action Function(cam_nudge, -140, 0) text_size 34 xsize 64 text_xalign 0.5
            textbutton "v" action Function(cam_nudge, 0, 140) text_size 34 xsize 64 text_xalign 0.5
            textbutton ">" action Function(cam_nudge, 140, 0) text_size 34 xsize 64 text_xalign 0.5
        null height 10
        text "STEADY" size 26 color "#ffffff"
        bar value StaticValue(cam_steady, 1.0) xsize 270 ysize 20
        if has_ana:
            text "PORTRAIT" size 26 color "#ffffff"
            bar value StaticValue(cam_bgb, 1.0) xsize 270 ysize 20
            text "Hold SPACE: portrait focus (blurs the background)" size 20 color "#9aa0b4"

    # Shutter button
    button:
        pos (1610, 770)
        xysize (290, 110)
        background Solid("#e8e8ee")
        hover_background Solid("#ffffff")
        action [Function(ff_shoot), Return("shot")]
        text "SHOOT" size 44 color "#16181f" align (0.5, 0.4)
        text "or click the lens / ENTER" size 18 color "#555a6b" align (0.5, 0.88)

    add DynamicDisplayable(cam_bar) pos (330, 912)

    # Bottom bar
    text "Arrows / WASD or the mouse at the edge: move   |   Wheel, Q/E or buttons: zoom   |   SHOOT button, click or ENTER: take the photo" size 20 xalign 0.5 ypos 960 color "#9aa0b4"

    # Keys
    if has_ana:
        key "keydown_K_SPACE" action SetVariable("cam_held", True)
        key "keyup_K_SPACE" action SetVariable("cam_held", False)
    key "K_RETURN" action [Function(ff_shoot), Return("shot")]
    key "game_menu" action Return("finish")
    key "mousedown_4" action Function(cam_zoom, 0.2)
    key "mousedown_5" action Function(cam_zoom, -0.2)
    for kn in ("K_EQUALS", "K_PLUS", "K_KP_PLUS", "K_e"):
        key kn action Function(cam_zoom, 0.3)
    for kn in ("K_MINUS", "K_KP_MINUS", "K_q"):
        key kn action Function(cam_zoom, -0.3)
    for kn, dn in (("K_LEFT", "l"), ("K_a", "l"), ("K_RIGHT", "r"), ("K_d", "r"),
                   ("K_UP", "u"), ("K_w", "u"), ("K_DOWN", "d"), ("K_s", "d")):
        key ("keydown_" + kn) action Function(cam_key, dn, True)
        key ("keyup_" + kn) action Function(cam_key, dn, False)

    timer 0.03 repeat True action [Function(cam_tick), Function(renpy.restart_interaction)]


# ------------------------------------------------------------------------------------ what the photo turned out to be
screen photo_free_result(p, n, nmax):
    modal True
    $ pr_lines = ph_lines(p)
    add Solid("#000000d8")
    frame:
        align (0.5, 0.5)
        padding (36, 28)
        hbox:
            spacing 36
            vbox:
                spacing 10
                frame:
                    padding (3, 3)
                    background Solid("#ffffff")
                    add ph_photo(p, 760, 495)
                text "Photo [n] / [nmax]  saved to your gallery" size 22 color "#9aa0b4"
            vbox:
                spacing 6
                xsize 520
                text p["label"] size 40 bold True color "#ffffff"
                if p.get("rating"):
                    text ("Influencer rating: %d / 10" % p["rating"]) size 34 bold True color ("#7dffa0" if p["rating"] >= 7 else ("#ffd54a" if p["rating"] >= 4 else "#ff8a8a"))
                null height 6
                for ln in pr_lines:
                    text ln size 24 color "#e6e9f2"
                null height 12
                if p["subject"] != "random" and p["kind"] == "room":
                    text "A client might pay for this: check Snapjob on your phone." size 22 color "#ffd54a" xsize 520
                null height 10
                hbox:
                    spacing 20
                    if n < nmax:
                        textbutton "Next shot" action Return("next") text_size 32
                    textbutton "Finish" action Return("finish") text_size 32
    key "K_RETURN" action Return("next" if n < nmax else "finish")
    key "K_SPACE" action Return("next" if n < nmax else "finish")


# ------------------------------------------------------------------------------------ the session
# scene_id: Ana's photo scene in this room (mp.scene_for), or None
label photo_free_session(scene_id=None):
    scene black
    if not photo_free_tutorial_done:
        "You hold your camera. There is nothing to pick: aim it at anything and shoot."
        "Move the lens with the arrows, WASD or the mouse at the screen edge. Zoom with the wheel, Q and E. Stay still for a moment, or the picture shakes and blurs."
        "The game recognises what you photographed. People, places and animals can be worth money to Snapjob clients: open the Snapjob app on your phone to see what they want, then shoot it yourself."
        "If Ana is in the room you can photograph her face, her hands, her feet, anything. The gallery remembers what part of her it was and what her face was doing."
        "A session is up to five photos and takes part of the day."
        $ photo_free_tutorial_done = True

    $ ff_setup(scene_id)
    $ ff_bg = room_bg(location, room)
    $ ff_preload = mp.scene_files(scene_id) if scene_id else []
    $ renpy.start_predict(*ff_preload)
    $ cam_reset()
    $ ff_go = True
    while ff_go:
        call screen photo_free(ff, ff_bg)
        if _return == "shot":
            scene black with photo_flash
            call screen photo_free_result(phone.photo(ff["photo_id"]), ff["n"], ff["max"])
            if _return == "finish" or ff["n"] >= ff["max"]:
                $ ff_go = False
        else:
            $ ff_go = False
    $ renpy.stop_predict(*ff_preload)
    $ mp.set_world(1920)

    if ff["n"] == 0:
        return "cancelled"
    if not photo_free_hint_done:
        $ photo_free_hint_done = True
        "Your photos are in the Gallery app. Open your phone (the button at the bottom left, or the P key) and look at Snapjob for photo gigs."
    return "done"
