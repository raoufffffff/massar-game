# Photographing Ana through a camera: lens window, real zoom and pan, steadiness, portrait focus.
# The player gets five challenges and chooses which to take. Rules live in masar_photo.py.

# Ana in the lens is built live from still pictures (see SCENES in masar_photo.py): the game blends
# her expressions on a timeline generated from her mood, so no video file is needed.

default cam_cx = 960.0
default cam_cy = 540.0
default cam_z = 1.0
default cam_zt = 1.0
default cam_steady = 1.0
default cam_bgb = 0.0
default cam_held = False
default cam_zmax = 2.6                    # how far the lens may zoom (the free camera sets it, see masar_shot.py)
default cam_last = 0.0
default cam_keys = {"l": False, "r": False, "u": False, "d": False}
default cam_res = {"expr": 0, "framing": 0, "sharp": 0, "bg": 0, "total": 0, "tip": ""}
default cam_shot_t = 0.0
default cam_done = {}
default cam_title = "Cooking"
default photo_ana_tutorial_done = False

transform cam_view(px, py, s):
    subpixel True
    xanchor 0
    yanchor 0
    xpos absolute(px)
    ypos absolute(py)
    zoom s

transform cam_blur(b):
    blur b

init python:
    def cam_reset():
        # the lens opens on what the player was looking at (in a panoramic room the view may be scrolled)
        store.cam_cx = 960.0 + (store.room_vx if mp.WORLD_W > 1920 else 0)
        store.cam_cy = 540.0
        store.cam_cx, store.cam_cy = mp.clamp_view(store.cam_cx, store.cam_cy, 1.0)
        store.cam_z = store.cam_zt = 1.0
        store.cam_steady = 1.0
        store.cam_bgb = 0.0
        store.cam_held = False
        store.cam_last = renpy.get_game_runtime()
        for k in store.cam_keys:
            store.cam_keys[k] = False

    def cam_key(direction, down):
        store.cam_keys[direction] = down

    def cam_zoom(dz):
        store.cam_zt = mp.clamp_zoom(store.cam_zt + dz, store.cam_zmax)

    def cam_nudge(dx, dy):
        """Move the view by dx, dy window pixels (on-screen arrow buttons)."""
        s = mp.BASE * store.cam_z
        store.cam_cx, store.cam_cy = mp.clamp_view(store.cam_cx + dx / s, store.cam_cy + dy / s, store.cam_z)
        store.cam_steady = max(0.0, store.cam_steady - 0.5)

    def cam_tick():
        now = renpy.get_game_runtime()
        dt = min(0.1, max(0.0, now - store.cam_last))
        store.cam_last = now
        old_z = store.cam_z
        store.cam_z += (store.cam_zt - store.cam_z) * min(1.0, dt * 9.0)
        s = mp.BASE * store.cam_z
        k = store.cam_keys
        vx = (1.0 if k["r"] else 0.0) - (1.0 if k["l"] else 0.0)
        vy = (1.0 if k["d"] else 0.0) - (1.0 if k["u"] else 0.0)
        try:
            mx, my = renpy.get_mouse_pos()
            ex, ey = mp.edge_push(mx, my)
        except Exception:
            ex = ey = 0.0
        vx = max(-1.0, min(1.0, vx + ex))
        vy = max(-1.0, min(1.0, vy + ey))
        speed = 560.0   # window pixels per second, whatever the zoom
        boost = max(1.0, mp.WORLD_W / 1920.0) ** 0.6      # a panoramic room: pan faster (steadiness is not affected)
        store.cam_cx, store.cam_cy = mp.clamp_view(store.cam_cx + vx * speed * boost * dt / s,
                                                   store.cam_cy + vy * speed * dt / s, store.cam_z)
        moved = (vx * vx + vy * vy) ** 0.5 * speed * dt
        store.cam_steady = mp.update_steady(store.cam_steady, dt, moved, store.cam_z - old_z)
        store.cam_bgb = mp.update_bg_blur(store.cam_bgb, store.cam_held, dt)

    def cam_shoot(shot, t0):
        """Score the photo with exactly what the lens shows at this instant."""
        now = renpy.get_game_runtime()
        t = (now - t0) % mp.LOOP_LENGTH
        swx, swy = mp.sway(now, store.cam_z, store.cam_steady)
        vcx, vcy = mp.clamp_view(store.cam_cx + swx, store.cam_cy + swy, store.cam_z)
        res = mp.score_shot(shot, t, vcx, vcy, store.cam_z, store.cam_steady, store.cam_bgb)
        res["tip"] = mp.shot_tip(res, shot["style"])
        store.cam_res = res
        store.cam_shot_t = t
        store.shot_q = res["total"]

    def shot_place(shot):
        return mc.BY_ID[shot["place"]].name + " - " + mc.room_name(shot["place"], shot["room"])

# A still picture of a challenge: the place, Ana in the requested pose and expression, at the
# ideal framing (blurred background for portrait shots). k = size relative to the lens window.
screen target_view(shot, k):
    $ tcx, tcy, tz = mp.ideal_view(shot["part"], shot["ax"])
    $ tsc = mp.BASE * tz
    $ tpx = (mp.WIN_W / 2.0 - tcx * tsc) * k
    $ tpy = (mp.WIN_H / 2.0 - tcy * tsc) * k
    $ tbl = (9.0 / tsc) if shot["style"] == "portrait" else 0.0
    fixed:
        xysize (int(mp.WIN_W * k), int(mp.WIN_H * k))
        clipping True
        fixed:
            at cam_view(tpx, tpy, tsc * k)
            xysize (mp.WORLD_W, mp.WORLD_H)
            add room_bg(shot["place"], shot["room"]) at cam_blur(tbl)
            add shot["still"] pos (int(mp.ana_left(shot["ax"])), mp.ANA_TOP) zoom mp.IMG_ZOOM

screen photo_target_big(shot):
    modal True
    zorder 200
    $ pl = shot_place(shot)
    $ sty = mp.STYLE_NAMES[shot["style"]]
    add Solid("#000000d8")
    button:
        xysize (1920, 1080)
        background None
        action Hide("photo_target_big")
    vbox:
        align (0.5, 0.5)
        spacing 14
        text "TARGET  -  [shot['brief']]" size 34 color "#ffd54a" xalign 0.5
        frame:
            padding (4, 4)
            background Solid("#ffffff")
            use target_view(shot, 0.9)
        text "[pl]   |   [sty]" size 26 xalign 0.5
        text "Click anywhere to close" size 20 color "#9aa0b4" xalign 0.5
    key "K_ESCAPE" action Hide("photo_target_big")
    key "K_t" action Hide("photo_target_big")

screen photo_cam(shot, idx, total, t0, bg):
    modal True
    $ now = renpy.get_game_runtime()
    $ t = (now - t0) % mp.LOOP_LENGTH
    $ draws = mp.layer_draws(shot, t)
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
    $ pl = shot_place(shot)
    $ fx = mp.WIN_X + mp.WIN_W // 2
    $ fy = mp.WIN_Y + mp.WIN_H // 2

    add Solid("#0b0c10")

    # What the lens sees: the scene, scaled and moved. Ana is part of the scene.
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
        action [Function(cam_shoot, shot, t0), Return(True)]

    add "images/camera/lens.png"

    # Steadiness frame (red: shaking, yellow: settling, green: steady)
    add Solid(fcol) pos (fx - 62, fy - 62) xysize (124, 3)
    add Solid(fcol) pos (fx - 62, fy + 59) xysize (124, 3)
    add Solid(fcol) pos (fx - 62, fy - 62) xysize (3, 124)
    add Solid(fcol) pos (fx + 59, fy - 62) xysize (3, 124)

    # Left bar: the target picture (click to enlarge)
    vbox:
        pos (20, 100)
        xsize 290
        spacing 10
        text "SHOT [idx] / [total]" size 30 color "#ffffff"
        text "TARGET  (click to enlarge)" size 22 color "#9aa0b4"
        button:
            padding (3, 3)
            background Solid("#ffffff")
            action Show("photo_target_big", shot=shot)
            use target_view(shot, 0.225)
        text "[shot['brief']]" size 28 color "#ffd54a"
        text "[pl]" size 22 color "#ffffff"
        if shot["style"] == "portrait":
            text "PORTRAIT: hold SPACE so the background blurs" size 22 color "#ffd54a"
        else:
            text "STANDARD: keep SPACE released" size 22 color "#9aa0b4"

    # Right bar: zoom, arrows, steadiness, portrait
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
        text "PORTRAIT" size 26 color "#ffffff"
        bar value StaticValue(cam_bgb, 1.0) xsize 270 ysize 20
        text "Hold SPACE: portrait focus" size 20 color "#9aa0b4"
        text "T: enlarge target" size 20 color "#9aa0b4"

    # Shutter button
    button:
        pos (1610, 770)
        xysize (290, 110)
        background Solid("#e8e8ee")
        hover_background Solid("#ffffff")
        action [Function(cam_shoot, shot, t0), Return(True)]
        text "SHOOT" size 44 color "#16181f" align (0.5, 0.4)
        text "or click the lens / ENTER" size 18 color "#555a6b" align (0.5, 0.88)

    # Bottom bar: her loop clock
    vbox:
        xalign 0.5
        ypos 930
        spacing 6
        text "TIME  [t:.1f] s" size 24 xalign 0.5 color "#ffffff"
        bar value StaticValue(t, mp.LOOP_LENGTH) xsize 1100 ysize 16
        text "Arrows / WASD or the mouse at the edge: move   |   Wheel, Q/E or buttons: zoom   |   Hold SPACE: portrait   |   SHOOT button, click or ENTER: take the photo" size 20 xalign 0.5 color "#9aa0b4"

    # Keys
    key "keydown_K_SPACE" action SetVariable("cam_held", True)
    key "keyup_K_SPACE" action SetVariable("cam_held", False)
    key "K_t" action Show("photo_target_big", shot=shot)
    key "K_RETURN" action [Function(cam_shoot, shot, t0), Return(True)]
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

# The shoot list: five challenges, the player picks which ones to take
screen photo_board(shots, done):
    modal True
    add Solid("#0b0c10")
    vbox:
        xalign 0.5
        ypos 40
        spacing 6
        text "PHOTO SHOOT  -  [cam_title]" size 44 xalign 0.5 color "#ffffff"
        text "Pick the shots you want to take. Each one can be tried once. Click a picture to see it large." size 24 xalign 0.5 color "#9aa0b4"
    hbox:
        xalign 0.5
        ypos 190
        spacing 20
        for i, sh in enumerate(shots):
            $ dn = done.get(i)
            $ pl = shot_place(sh)
            vbox:
                xsize 350
                spacing 8
                button:
                    padding (3, 3)
                    background Solid("#ffffff")
                    action Show("photo_target_big", shot=sh)
                    use target_view(sh, 0.26)
                text "[sh['brief']]" size 26 color "#ffd54a"
                text "[pl]" size 22 color "#ffffff"
                if sh["style"] == "portrait":
                    text "Portrait (blurred background)" size 20 color "#9ad0ff"
                else:
                    text "Standard" size 20 color "#9aa0b4"
                if dn is not None:
                    text "Done: [dn]%" size 28 color "#5dff7a"
                else:
                    textbutton "Take this shot" action Return(i) text_size 28
    textbutton ("Finish session" if done else "Leave without shooting") action Return(-1) text_size 32 xalign 0.5 ypos 900

screen photo_result(shot, res, idx, total):
    modal True
    $ pl = shot_place(shot)
    add Solid("#000000d0")
    frame:
        align (0.5, 0.5)
        padding (40, 30)
        hbox:
            spacing 40
            vbox:
                spacing 8
                text "Target" size 22 color "#9aa0b4"
                frame:
                    padding (3, 3)
                    background Solid("#ffffff")
                    use target_view(shot, 0.26)
                text "[shot['brief']]" size 26 color "#ffd54a"
                text "[pl]" size 20
            vbox:
                spacing 12
                xsize 560
                text "Match [res['total']]%" size 42
                text "Expression  [res['expr']]%" size 26
                bar value StaticValue(res["expr"], 100) xsize 520 ysize 16
                text "Framing  [res['framing']]%" size 26
                bar value StaticValue(res["framing"], 100) xsize 520 ysize 16
                text "Sharpness (steadiness)  [res['sharp']]%" size 26
                bar value StaticValue(res["sharp"], 100) xsize 520 ysize 16
                text "Background  [res['bg']]%" size 26
                bar value StaticValue(res["bg"], 100) xsize 520 ysize 16
                text "[res['tip']]" size 24 color "#ffd54a"
                null height 6
                textbutton "Back to the list" action Return(True) text_size 32 xalign 1.0
    key "K_RETURN" action Return(True)
    key "K_SPACE" action Return(True)

# The camera session with Ana is the free camera (masar_photo_free.rpy). Without a photo scene here she is not in the lens.
label photo_session_ana:
    $ ana_scene_here = mp.scene_for(ana_pose_name, location, room)
    call photo_free_session(ana_scene_here)
    return _return

# The older challenge mode (five target pictures to choose from). Not used any more; kept for reference.
label photo_session_ana_challenges:
    $ cam_zmax = mp.ZOOM_MAX
    scene black
    if not photo_ana_tutorial_done:
        "You are holding a camera, and Ana is a living subject: she breathes, smiles, turns shy and blinks, and her mood changes how often."
        "You get photo challenges. Each shows a target picture: which part of her, which expression. Choose the ones you want to take."
        "In the lens, move and zoom until your frame matches the target, then wait for her expression. Stop moving for a moment, or the picture shakes and blurs. Do not shoot while she blinks."
        "Portrait challenges need the focus mode: hold SPACE until the background blurs, then click. For standard challenges, keep SPACE released. Click inside the lens to shoot."
        $ photo_ana_tutorial_done = True

    $ cam_scene = mp.scene_for(ana_pose_name, location, room)
    if cam_scene is None:
        return "cancelled"
    $ cam_shots = mp.make_shots(cam_scene, mood=ana_idle)
    $ cam_title = mp.SCENES[cam_scene]["title"]
    $ cam_preload = mp.scene_files(cam_scene)
    $ renpy.start_predict(*cam_preload)
    $ cam_done = {}
    $ photo_choice = 0
    while photo_choice != -1 and len(cam_done) < len(cam_shots):
        call screen photo_board(cam_shots, cam_done)
        $ photo_choice = _return
        if photo_choice != -1:
            $ cam_shot = cam_shots[photo_choice]
            $ cam_reset()
            $ cam_t0 = renpy.get_game_runtime()
            call screen photo_cam(cam_shot, len(cam_done) + 1, len(cam_shots), cam_t0, room_bg(cam_shot["place"], cam_shot["room"]))
            $ cam_done[photo_choice] = cam_res["total"]
            scene black with photo_flash
            call screen photo_result(cam_shot, cam_res, len(cam_done), len(cam_shots))

    $ renpy.stop_predict(*cam_preload)
    if not cam_done:
        return "cancelled"

    $ scores = list(cam_done.values())
    $ ph_save_ana_photos()
    call photo_apply_result
    return "done"

# Applies the best shot of a session to the page's numbers (shared by both photo modes)
label photo_apply_result:
    $ best = mp.session_result(scores)
    $ res = mp.outcome(best)
    $ res_label = res["label"]
    $ res_views = res["views"]
    $ res_subs = res["subs"]
    $ res_don = res["donations"]
    $ followers = max(0, followers + res_subs)
    $ total_views += res_views
    $ donations += res_don

    "Best shot: [best]%% - [res_label]."
    if res["positive"]:
        "The photo got [res_views] views, [res_subs] new subscribers and [res_don] in donations."
    else:
        "The photo flopped: [res_views] views and you lost [res_subs] subscribers."
    "Followers: [followers]   Total views: [total_views]   Donations: [donations]"
    return
