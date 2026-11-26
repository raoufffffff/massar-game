# The phone: messages, bank, tasks, contacts, gallery, Supernova (empty for now) and Snapjob (photo gigs).
# Rules and data live in masar_phone.py - this file is only the screens.
# The phone is free to use (no time passes). Open it with the phone button (bottom left) or the P key.

init -1 python:
    import masar_phone as mph

default phone = mph.Phone()
default ph_app = "home"          # home / messages / gallery / snapjob / supernova / bank / tasks / contacts
default ph_view = "list"         # list / detail / confirm / pick / result
default ph_filter = "all"        # gallery filter
default ph_ana_filter = "any"    # gallery sub-filter for Ana (shot type)
default ph_photo_id = None       # the photo being looked at
default ph_gig_id = None         # the gig being looked at
default ph_quest_id = None       # the quest being looked at
default ph_result = None         # result of the last upload
default photo_subject = "view"   # what the player chose to photograph
default photo_gig_hint_done = False

init python:
    # every room that offers subjects to photograph (ROOM_SUBJECTS in masar_phone.py) is a photo spot
    for _spot in mph.ROOM_SUBJECTS:
        if _spot not in mc.PHOTO_SPOTS:
            mc.PHOTO_SPOTS.append(_spot)

    # ------------------------------------------------------------ navigation
    def ph_reset():
        store.ph_app = "home"
        store.ph_view = "list"
        store.ph_photo_id = None
        store.ph_gig_id = None
        store.ph_quest_id = None
        store.ph_result = None

    def ph_open(app):
        store.ph_app = app
        store.ph_view = "list"
        store.ph_photo_id = None
        store.ph_gig_id = None
        store.ph_quest_id = None
        store.ph_result = None

    def ph_quest_open(qid):
        store.ph_quest_id = qid
        store.ph_view = "detail"

    def ph_home():
        if store.ph_app == "messages":
            store.phone.mark_read()
        ph_reset()

    def ph_close():
        ph_home()
        return True            # a value ends the screen: the phone closes

    def ph_back():
        """One step back; from the first page of an app, to the home screen."""
        v = store.ph_view
        if v in ("confirm", "pick"):
            store.ph_view = "detail"
        elif v in ("detail", "result"):
            store.ph_view = "list"
            store.ph_photo_id = None
            store.ph_quest_id = None
            store.ph_result = None
        else:
            ph_home()

    def ph_esc():
        if store.ph_app == "home":
            return ph_close()
        ph_back()

    # ------------------------------------------------------------ actions of the apps
    def ph_submit(gig_id, photo_id):
        store.ph_result = store.phone.submit(gig_id, photo_id, store.day, store.day_part, mph.level_for(store.followers))
        store.ph_photo_id = photo_id
        store.ph_view = "result"
        flush_notes()

    def ph_delete(pid):
        store.phone.delete_photo(pid)
        store.ph_photo_id = None
        store.ph_view = "list"

    # ------------------------------------------------------------ pictures
    def ph_photo(p, w, h):
        """A gallery photo fitted into a w x h box. New photos show exactly what the lens framed (room, Ana's
        pictures, blur from shaking); older ones are a crop of the room picture (dull when the match is low)."""
        img = p["img"]
        if isinstance(img, str) and not renpy.loadable(img):
            return Solid("#222a36", xysize=(w, h))
        if p.get("view"):
            vx, vy, vw, vh = p["view"]
            s = min(w / float(vw), h / float(vh))
            ww = p.get("ww", 1920)                  # world width (wider than 1920 = panoramic room)
            bgd = img if ww <= 1920 else im.Scale(img, ww, mp.WORLD_H)
            if p.get("bgblur", 0.0) > 0.05:
                bgd = Transform(img, blur=p["bgblur"])
            parts = [bgd]
            lay = [Transform(path, alpha=al, zoom=mp.IMG_ZOOM, pos=(x, y)) for path, x, y, al in p.get("layers", [])]
            if lay:
                grp = Fixed(*lay, xysize=(ww, mp.WORLD_H))
                if p.get("anablur", 0.0) > 0.05:
                    grp = Transform(grp, blur=p["anablur"])
                parts.append(grp)
            world = Fixed(*parts, xysize=(ww, mp.WORLD_H))
            inner = Fixed(Transform(world, zoom=s, subpixel=True, pos=(int(-vx * s), int(-vy * s))),
                          xysize=(max(1, int(vw * s)), max(1, int(vh * s))), clipping=True)
            return Fixed(Solid("#0a0c10", xysize=(w, h)), Transform(inner, align=(0.5, 0.5)), xysize=(w, h))
        cx, cy, cw, ch = p["crop"]
        s = min(w / float(cw), h / float(ch))
        pic = im.Scale(im.Crop(img, (cx, cy, cw, ch)), max(1, int(cw * s)), max(1, int(ch * s)))
        if p["kind"] == "room":
            b, sat = mph.tint(p["score"])
            pic = Transform(pic, matrixcolor=BrightnessMatrix(b) * SaturationMatrix(sat))
        return Fixed(Solid("#0a0c10", xysize=(w, h)), Transform(pic, align=(0.5, 0.5)), xysize=(w, h))

    def ph_short(text, n=22):
        return text if len(text) <= n else text[:n - 2] + ".."

    def ph_lines(p):
        """The properties shown in the photo detail: ['Taken: Day 3, Morning', ...]."""
        out = ["Taken: " + mph.when_text(p["day"], p["part"])]
        try:
            out.append("Place: " + mc.BY_ID[p["place"]].name + " - " + mc.room_name(p["place"], p["room"]))
        except Exception:
            pass
        props = p.get("props") or []
        for k, v in props:
            out.append("%s: %s" % (k, v))
        if not props:
            out.append("Match: %d%%" % p["score"])
        elif p["kind"] == "ana" and not p.get("rating"):
            out.append("Quality: %d%%" % p["score"])
        out.append("Sold to a Snapjob client" if p["sold"] else "Not sold")
        return out

    def ph_subject_thumb(sid, place, room, w, h):
        """Where the subject is in the room picture (for the 'what do you want to photograph' list)."""
        part = mph.subject_ref_part(sid)         # a night-only subject is shown on the NIGHT picture
        img = mc.bg_path(place, room, part)
        try:
            iw, ih = renpy.image_size(img)
            ww = max(1920, int(round(iw * 1080.0 / max(1, ih)))) if iw * 9 > ih * 16 * 1.01 else 1920
        except Exception:
            ww = room_world_w(place, room)
        if ww > 1920:                       # panoramic room: boxes are fractions of the whole panorama
            img = im.Scale(img, ww, mp.WORLD_H)
        return ph_photo({"img": img, "crop": mph.crop_px(sid, ww, mp.WORLD_H), "kind": "plain", "score": 100}, w, h)

    def ph_where(subject):
        """'Gym - Pool': where a gig subject can be photographed."""
        spots = mph.rooms_for(subject)
        if not spots:
            return "anywhere"
        pl, rm = spots[0]
        return mc.BY_ID[pl].name + " - " + mc.room_name(pl, rm)

    # ------------------------------------------------------------ saving photos into the gallery
    def ph_save_room_photo(subject, score):
        pl, rm = store.location, store.room
        return store.phone.add_photo(subject, "room", pl, rm, score, store.day, store.day_part,
                                     mc.bg_path(pl, rm), mph.crop_px(subject))

    def ph_save_ana_photos():
        """Every shot of a photo session with Ana goes to the gallery (the camera pictures are 1600x2160)."""
        for idx, total in store.cam_done.items():
            shot = store.cam_shots[idx]
            r = mp.PARTS[shot["part"]]["roi"]
            store.phone.add_photo("ana", "ana", shot["place"], shot["room"], total, store.day, store.day_part,
                                  shot["still"], (r[0] * 2, r[1] * 2, r[2] * 2, r[3] * 2), label=shot["brief"])


label phone_app:
    call screen phone
    return


# ------------------------------------------------------------------------------------ the phone button
screen phone_button():
    $ ph_unread = phone.unread()
    fixed:
        pos (30, 905)
        xysize (84, 138)
        imagebutton:
            idle "images/ui/phone_btn.png"
            hover "images/ui/phone_btn_hover.png"
            action [Function(ph_reset), Function(renpy.call_in_new_context, "phone_app")]
        if ph_unread > 0:
            frame:
                background Solid("#e8334a")
                padding (9, 2)
                pos (62, -8)
                text "[ph_unread]" size 20 color "#ffffff"
    key "K_p" action [Function(ph_reset), Function(renpy.call_in_new_context, "phone_app")]


# ------------------------------------------------------------------------------------ the phone itself
screen phone():
    modal True
    zorder 100
    key "game_menu" action Function(ph_esc)
    add Solid("#06070a")

    # the screen of the phone (584 x 984)
    fixed:
        pos (668, 48)
        xysize (584, 984)
        if ph_app == "home":
            use phone_home
        else:
            add Solid("#10131b")
            if ph_app == "messages":
                use phone_header("Messages")
                use phone_messages
            elif ph_app == "gallery":
                use phone_header("Gallery")
                use phone_gallery
            elif ph_app == "snapjob":
                use phone_header("Snapjob")
                use phone_snapjob
            elif ph_app == "supernova":
                use phone_header("Supernova")
                use phone_supernova
            elif ph_app == "bank":
                use phone_header("Bank")
                use phone_bank
            elif ph_app == "tasks":
                use phone_header("Quests")
                use phone_quests
            elif ph_app == "me":
                use phone_header("Me")
                use phone_me
            elif ph_app == "contacts":
                use phone_header("Contacts")
                use phone_contacts
        # status bar
        text "Day [day]  -  [time_name]" size 20 color "#c9cfdd" pos (34, 10)
        text "$[phone.money]" size 20 color "#7dffa0" xalign 1.0 xoffset -34 ypos 10
        # home bar: tap to go to the home screen
        if ph_app != "home":
            button:
                xalign 0.5
                ypos 958
                xysize (200, 22)
                background None
                action Function(ph_home)
                add Solid("#aab2c8") xysize (150, 6) align (0.5, 0.5)

    add "images/ui/phone_body.png" pos (640, 20)

    textbutton "Close  (Esc)":
        pos (1320, 40)
        text_size 28
        action Function(ph_close)


screen phone_home():
    add "images/ui/phone_wall.png"
    text "Day [day]" font NAV_FONT size 84 color "#ffffff" xalign 0.5 ypos 66
    text "[time_name]" size 32 color "#d7dcff" xalign 0.5 ypos 168
    $ ph_unread = phone.unread()
    $ ph_apps = [("messages", "Messages"), ("gallery", "Gallery"), ("snapjob", "Snapjob"), ("supernova", "Supernova"), ("bank", "Bank"), ("tasks", "Quests"), ("me", "Me"), ("contacts", "Contacts")]
    for i, a in enumerate(ph_apps):
        $ ph_icon = "images/ui/phone_app_%s.png" % a[0]
        fixed:
            pos (56 + (i % 3) * 174, 290 + (i // 3) * 190)
            xysize (124, 170)
            imagebutton:
                idle ph_icon
                hover Transform(ph_icon, matrixcolor=BrightnessMatrix(0.15))
                action Function(ph_open, a[0])
            text a[1] size 22 color "#ffffff" xalign 0.5 ypos 132 outlines [(2, "#000000", 0, 1)]
            if a[0] == "messages" and ph_unread > 0:
                frame:
                    background Solid("#e8334a")
                    padding (9, 2)
                    pos (96, -8)
                    text "[ph_unread]" size 20 color "#ffffff"


screen phone_header(title):
    add Solid("#171b27") xysize (584, 112)
    textbutton "< Back":
        pos (16, 46)
        text_size 26
        text_color "#ffd54a"
        text_hover_color "#ffffff"
        action Function(ph_back)
    text title font NAV_FONT size 36 color "#ffffff" xalign 0.5 ypos 50


# ------------------------------------------------------------------------------------ Messages
screen phone_messages():
    viewport:
        pos (18, 124)
        xysize (548, 820)
        mousewheel True
        draggable True
        scrollbars "vertical"
        vbox:
            spacing 12
            xfill True
            if not phone.messages:
                text "No messages yet." size 24 color "#8a93a8"
            for m in reversed(phone.messages):
                frame:
                    background Solid("#1d2333")
                    xfill True
                    padding (16, 12)
                    vbox:
                        spacing 4
                        hbox:
                            spacing 12
                            text m["sender"] size 24 bold True color "#ffd54a"
                            if not m["read"]:
                                text "NEW" size 18 color "#7dffa0" yalign 0.5
                        text m["text"] size 22 color "#e6e9f2" xsize 480
                        text mph.when_text(m["day"], m["part"]) size 18 color "#8a93a8"


# ------------------------------------------------------------------------------------ Bank
screen phone_bank():
    frame:
        pos (18, 128)
        xysize (548, 190)
        background Solid("#1f56b8")
        vbox:
            align (0.5, 0.5)
            spacing 4
            text "Balance" size 24 color "#cfe0ff" xalign 0.5
            text "$[phone.money]" font NAV_FONT size 84 color "#ffffff" xalign 0.5
    text "Recent activity" size 24 color "#aab2c8" pos (24, 336)
    viewport:
        pos (18, 376)
        xysize (548, 570)
        mousewheel True
        draggable True
        scrollbars "vertical"
        vbox:
            spacing 8
            xfill True
            for t in reversed(phone.transactions):
                $ ph_amt = ("+$%d" % t["amount"]) if t["amount"] >= 0 else ("-$%d" % (-t["amount"]))
                frame:
                    background Solid("#1d2333")
                    xfill True
                    padding (14, 10)
                    hbox:
                        spacing 10
                        vbox:
                            xsize 350
                            text t["title"] size 22 color "#e6e9f2"
                            text mph.when_text(t["day"], t["part"]) size 17 color "#8a93a8"
                        text ph_amt size 26 color ("#7dffa0" if t["amount"] >= 0 else "#ff8a8a") yalign 0.5


# ------------------------------------------------------------------------------------ Tasks
screen phone_tasks():
    $ ph_open_tasks = phone.open_tasks()
    if not ph_open_tasks:
        vbox:
            align (0.5, 0.4)
            spacing 10
            text "No tasks yet." size 30 color "#aab2c8" xalign 0.5
            text "Story tasks and their deadlines will appear here." size 22 color "#8a93a8" xalign 0.5 text_align 0.5 xsize 440
    else:
        viewport:
            pos (18, 124)
            xysize (548, 820)
            mousewheel True
            draggable True
            scrollbars "vertical"
            vbox:
                spacing 12
                xfill True
                for t in ph_open_tasks:
                    frame:
                        background Solid("#1d2333")
                        xfill True
                        padding (16, 12)
                        vbox:
                            spacing 4
                            text t["title"] size 26 bold True color "#ffffff"
                            text t["text"] size 22 color "#e6e9f2" xsize 480
                            if t["due"]:
                                text ("Due: day %d" % t["due"]) size 20 color "#ffb347"


# ------------------------------------------------------------------------------------ Quests
screen quest_bar(cur, tgt, w=470):
    $ qb_frac = max(0.0, min(1.0, float(cur) / tgt)) if tgt else 0.0
    fixed:
        xysize (w, 22)
        add Solid("#2b3347") xysize (w, 22)
        add Solid("#4cd964") xysize (int(w * qb_frac), 22)
        text ("%g / %g" % (cur, tgt)) size 16 color "#ffffff" align (0.5, 0.5)

screen phone_quests():
    $ q_ctx = quests_ctx()
    if ph_view == "detail" and ph_quest_id:
        use phone_quest_detail(ph_quest_id, q_ctx)
    else:
        $ q_active = quests.active()
        $ q_done = [mq.quest(i) for i in quests.done if mq.quest(i)]
        $ q_tasks = phone.open_tasks()
        if not q_active and not q_done and not q_tasks:
            vbox:
                align (0.5, 0.4)
                spacing 10
                text "No quests yet." size 30 color "#aab2c8" xalign 0.5
        else:
            viewport:
                pos (18, 124)
                xysize (548, 820)
                mousewheel True
                draggable True
                scrollbars "vertical"
                vbox:
                    spacing 10
                    xfill True
                    for q_dom, q_dname in mq.data()["domains"].items():
                        $ q_here = [q for q in q_active if q["domain"] == q_dom]
                        if q_here:
                            text q_dname size 22 color "#ffd36b"
                            for q in q_here:
                                $ q_step = quests.current_step(q, q_ctx)
                                button:
                                    background Solid("#1d2333")
                                    hover_background Solid("#283049")
                                    xfill True
                                    padding (16, 12)
                                    action Function(ph_quest_open, q["id"])
                                    vbox:
                                        spacing 4
                                        text q["title"] size 26 bold True color "#ffffff"
                                        if q_step:
                                            text q_step["text"] size 20 color "#c9cfdd" xsize 480
                                            if q_step["target"]:
                                                use quest_bar(q_step["current"], q_step["target"])
                    if q_tasks:
                        text "Reminders" size 22 color "#ffd36b"
                        for t in q_tasks:
                            frame:
                                background Solid("#1d2333")
                                xfill True
                                padding (16, 12)
                                vbox:
                                    spacing 4
                                    text t["title"] size 24 bold True color "#ffffff"
                                    text t["text"] size 20 color "#e6e9f2" xsize 480
                                    if t["due"]:
                                        text ("Due: day %d" % t["due"]) size 18 color "#ffb347"
                    if q_done:
                        text "Completed" size 22 color "#8a93a8"
                        for q in q_done:
                            text ("- " + q["title"]) size 22 color "#8a93a8"

screen phone_quest_detail(qid, q_ctx):
    $ qd = mq.quest(qid)
    $ qd_steps = quests.steps(qd, q_ctx) if qd else []
    $ qd_cur = quests.current_step(qd, q_ctx) if qd else None
    viewport:
        pos (18, 124)
        xysize (548, 820)
        mousewheel True
        draggable True
        scrollbars "vertical"
        vbox:
            spacing 12
            xfill True
            text qd["title"] size 32 bold True color "#ffffff" xsize 500
            if qd.get("summary"):
                text qd["summary"] size 21 color "#c9cfdd" xsize 500
            null height 4
            for st in qd_steps:
                hbox:
                    spacing 10
                    text ("[[x]" if st["done"] else "[[ ]") size 22 color ("#7dffa0" if st["done"] else "#ffd36b")
                    text st["text"] size 22 color ("#8a93a8" if st["done"] else "#ffffff") xsize 440
            if qd_cur:
                null height 6
                frame:
                    background Solid("#1d2333")
                    xfill True
                    padding (16, 12)
                    vbox:
                        spacing 6
                        text "What to do" size 20 color "#ffd36b"
                        text qd_cur["hint"] size 21 color "#e6e9f2" xsize 480
                        if qd_cur["target"]:
                            use quest_bar(qd_cur["current"], qd_cur["target"])
            if qd.get("reward", {}).get("money"):
                text ("Reward: $%d" % qd["reward"]["money"]) size 22 color "#7dffa0"


# ------------------------------------------------------------------------------------ Me (numbers and bag)
screen phone_me():
    viewport:
        pos (18, 124)
        xysize (548, 820)
        mousewheel True
        draggable True
        scrollbars "vertical"
        vbox:
            spacing 12
            xfill True
            text "Your numbers" size 24 color "#ffd36b"
            for me_key in ("fitness", "charisma", "intelligence"):
                frame:
                    background Solid("#1d2333")
                    xfill True
                    padding (16, 10)
                    vbox:
                        spacing 4
                        text player.label(me_key) size 24 color "#ffffff"
                        use quest_bar(player.get(me_key), 100)
            null height 6
            text "Bag" size 24 color "#ffd36b"
            if not player.bag:
                text "Nothing yet." size 22 color "#8a93a8"
            for me_item, me_n in player.bag.items():
                frame:
                    background Solid("#1d2333")
                    xfill True
                    padding (16, 10)
                    vbox:
                        spacing 2
                        text ("%s%s" % (msh.item(me_item)["name"], (" x%d" % me_n) if me_n > 1 else "")) size 24 color "#ffffff"
                        text msh.item(me_item).get("text", "") size 18 color "#aab2c8" xsize 480


# ------------------------------------------------------------------------------------ Contacts
screen phone_contacts():
    vbox:
        pos (18, 128)
        spacing 10
        xsize 548
        for cid in phone.contacts:
            $ ph_ci = mph.CONTACT_INFO[cid]
            frame:
                background Solid("#1d2333")
                xfill True
                padding (16, 14)
                vbox:
                    spacing 2
                    text ph_ci[0] size 28 bold True color "#ffffff"
                    text ph_ci[1] size 20 color "#8a93a8"
        text "More contacts will appear as you meet people." size 20 color "#6f7890" xsize 520


# ------------------------------------------------------------------------------------ Supernova (empty for now)
screen phone_supernova():
    vbox:
        align (0.5, 0.4)
        spacing 14
        add "images/ui/phone_app_supernova.png" xalign 0.5
        text "Supernova" font NAV_FONT size 44 color "#ffffff" xalign 0.5
        text "Your page is not set up yet." size 24 color "#aab2c8" xalign 0.5
        text "Coming soon." size 22 color "#8a93a8" xalign 0.5


# ------------------------------------------------------------------------------------ Gallery
screen phone_gallery():
    if ph_view == "list":
        hbox:
            pos (18, 124)
            spacing 6
            for fid, fname in mph.FILTERS:
                textbutton fname:
                    text_size 20
                    padding (12, 6)
                    background Solid("#34406a" if fid == ph_filter else "#171b27")
                    hover_background Solid("#2a3350")
                    text_color ("#ffffff" if fid == ph_filter else "#aab2c8")
                    action SetVariable("ph_filter", fid)
        $ ph_top = 176
        if ph_filter == "ana":
            $ ph_top = 222
            hbox:
                pos (18, 168)
                spacing 4
                for fid, fname in mph.FILTERS_ANA:
                    textbutton fname:
                        text_size 17
                        padding (8, 4)
                        background Solid("#5a3a6a" if fid == ph_ana_filter else "#171b27")
                        hover_background Solid("#2a3350")
                        text_color ("#ffffff" if fid == ph_ana_filter else "#aab2c8")
                        action SetVariable("ph_ana_filter", fid)
        $ ph_shots = phone.photos_in(ph_filter, ph_ana_filter)
        if not ph_shots:
            text "No photos here yet.\nTake photos with the camera icon at a photo spot." size 22 color "#8a93a8" xalign 0.5 ypos 340 text_align 0.5 xsize 440
        else:
            vpgrid:
                pos (18, ph_top)
                xysize (548, 958 - ph_top)
                cols 3
                spacing 10
                mousewheel True
                draggable True
                scrollbars "vertical"
                for p in ph_shots:
                    button:
                        xysize (164, 122)
                        padding (0, 0)
                        background None
                        hover_foreground Solid("#ffffff22")
                        action [SetVariable("ph_photo_id", p["id"]), SetVariable("ph_view", "detail")]
                        fixed:
                            xysize (164, 122)
                            add ph_photo(p, 164, 100)
                            text (("%d/10" % p["rating"]) if p.get("rating") else ("%d%%" % p["score"])) size 17 color "#ffffff" outlines [(2, "#000000", 0, 1)] xpos 6 ypos 76
                            if p["sold"]:
                                text "SOLD" size 16 color "#ffd54a" outlines [(2, "#000000", 0, 1)] xalign 0.97 ypos 4
                            text ph_short(p["label"]) size 14 color "#c9cfdd" xpos 2 ypos 103
    else:
        $ ph_p = phone.photo(ph_photo_id)
        if ph_p is None:
            text "This photo is gone." size 24 color "#8a93a8" align (0.5, 0.4)
        else:
            $ ph_pl = ph_lines(ph_p)
            add ph_photo(ph_p, 548, 356) pos (18, 126)
            text ph_p["label"] size 30 bold True color "#ffffff" pos (24, 492)
            vbox:
                pos (24, 536)
                spacing 2
                for ln in ph_pl:
                    text ln size 20 color "#c9cfdd" xsize 530
            if ph_view == "detail":
                textbutton "Delete photo":
                    pos (24, 856)
                    text_size 24
                    padding (20, 8)
                    background Solid("#3a2230")
                    hover_background Solid("#5a2a3c")
                    text_color "#ff9b9b"
                    action SetVariable("ph_view", "confirm")
            else:
                text "Delete this photo for good?" size 24 color "#ffffff" pos (24, 836)
                hbox:
                    pos (24, 880)
                    spacing 16
                    textbutton "Delete":
                        text_size 24
                        padding (24, 8)
                        background Solid("#7a2a3c")
                        hover_background Solid("#a53a52")
                        text_color "#ffffff"
                        action Function(ph_delete, ph_p["id"])
                    textbutton "Keep it":
                        text_size 24
                        padding (24, 8)
                        background Solid("#283048")
                        hover_background Solid("#34406a")
                        text_color "#ffffff"
                        action SetVariable("ph_view", "detail")


# ------------------------------------------------------------------------------------ Snapjob
screen phone_snapjob():
    if ph_view == "list":
        $ ph_lvl = mph.level_for(followers)
        $ ph_next = mph.next_level_info(ph_lvl, followers)
        text ("Level %d - %s   |   five new gigs every day" % (ph_lvl, mph.level_name(ph_lvl))) size 21 color "#ffd54a" pos (24, 124)
        if ph_next:
            text ("Next level: %d more followers on Supernova" % ph_next[1]) size 18 color "#8a93a8" pos (24, 146)
        $ ph_board = phone.board(day, ph_lvl)
        vbox:
            pos (18, 166)
            spacing 12
            for g in ph_board:
                button:
                    xysize (548, 126)
                    padding (16, 10)
                    background Solid("#1d2333")
                    hover_background Solid("#2a3350")
                    action [SetVariable("ph_gig_id", g["id"]), SetVariable("ph_view", "detail")]
                    fixed:
                        xysize (516, 106)
                        vbox:
                            spacing 2
                            text g["title"] size 28 bold True color ("#6f7890" if g["done"] else "#ffffff")
                            text g["client"] size 20 color "#8a93a8"
                            text ("Where: " + ph_where(g["subject"])) size 20 color "#aab2c8"
                        if g["done"]:
                            text "DONE" size 26 bold True color "#7dffa0" xalign 1.0 yalign 0.5
                        else:
                            text ("$%d" % g["reward"]) font NAV_FONT size 38 color "#7dffa0" xalign 1.0 yalign 0.5
    elif ph_view == "detail":
        $ ph_g = mph.GIG_BY_ID[ph_gig_id]
        $ ph_done = (day, ph_gig_id) in phone.gig_done
        $ ph_spots = mph.rooms_for(ph_g["subject"])
        if ph_spots:
            add ph_subject_thumb(ph_g["subject"], ph_spots[0][0], ph_spots[0][1], 548, 308) pos (18, 126)
            text "REFERENCE" size 16 color "#ffffff" outlines [(2, "#000000", 0, 1)] pos (28, 134)
        vbox:
            pos (24, 444)
            spacing 4
            xsize 536
            text ph_g["title"] font NAV_FONT size 38 color "#ffffff"
            text ("Client: " + ph_g["client"]) size 21 color "#ffd54a"
            text ph_g["brief"] size 23 color "#e6e9f2" xsize 520
            text ("Where to shoot: " + ph_where(ph_g["subject"])) size 20 color "#aab2c8"
            text ("Required match: %d%% or more" % mph.MATCH_REQUIRED) size 20 color "#aab2c8"
            text ("Reward: $%d" % ph_g["reward"]) size 32 bold True color "#7dffa0"
        if ph_done:
            text "Completed - payment received." size 26 color "#7dffa0" pos (24, 800)
        else:
            textbutton "Upload photo":
                pos (24, 780)
                text_size 30
                padding (34, 12)
                background Solid("#ffc233")
                hover_background Solid("#ffd666")
                text_color "#2b2112"
                action SetVariable("ph_view", "pick")
            text "Tip: shoot it with the camera icon in that room, framing the subject like the reference. Hold the camera steady! A photo session uses part of the day." size 19 color "#6f7890" pos (24, 862) xsize 520
    elif ph_view == "pick":
        $ ph_want = mph.GIG_BY_ID[ph_gig_id]["subject"]
        $ ph_cands = phone.pick_list(ph_gig_id)
        text "Choose a photo from your gallery" size 24 color "#ffffff" pos (24, 126)
        if not ph_cands:
            text "You have no unsold photos.\nGo and take one first!" size 24 color "#8a93a8" xalign 0.5 ypos 300 text_align 0.5 xsize 440
        else:
            vpgrid:
                pos (18, 170)
                xysize (548, 786)
                cols 3
                spacing 10
                mousewheel True
                draggable True
                scrollbars "vertical"
                for p in ph_cands:
                    button:
                        xysize (164, 122)
                        padding (0, 0)
                        background None
                        hover_foreground Solid("#ffffff22")
                        action Function(ph_submit, ph_gig_id, p["id"])
                        fixed:
                            xysize (164, 122)
                            add ph_photo(p, 164, 100)
                            $ ph_m = phone.match_for(p, ph_want)
                            if ph_m <= 0:
                                add Solid("#000000a0") xysize (164, 100)
                                text "-" size 17 color "#ffffff" outlines [(2, "#000000", 0, 1)] xpos 6 ypos 76
                            else:
                                add Solid("#7dffa0" if ph_m >= mph.MATCH_REQUIRED else "#ffb347") xysize (164, 4) yalign 0.0
                                text ("%d%%" % ph_m) size 17 color "#ffffff" outlines [(2, "#000000", 0, 1)] xpos 6 ypos 76
                            text ph_short(p["label"]) size 14 color "#c9cfdd" xpos 2 ypos 103
    elif ph_view == "result":
        $ ph_r = ph_result
        $ ph_p = phone.photo(ph_photo_id)
        if ph_p:
            add ph_photo(ph_p, 548, 308) pos (18, 128)
        text ("ACCEPTED" if ph_r["ok"] else "REJECTED") font NAV_FONT size 60 color ("#7dffa0" if ph_r["ok"] else "#ff8a8a") pos (24, 452)
        text ph_r["text"] size 24 color "#e6e9f2" pos (24, 536) xsize 520
        if ph_r["ok"]:
            text ("+$%d" % ph_r["reward"]) font NAV_FONT size 72 color "#7dffa0" pos (24, 650)
        textbutton "OK":
            pos (24, 800)
            text_size 30
            padding (40, 12)
            background Solid("#283048")
            hover_background Solid("#34406a")
            text_color "#ffffff"
            action Function(ph_back)


# ------------------------------------------------------------------------------------ what to photograph (before a photo session)
screen photo_subject(subs, place, room):
    modal True
    zorder 90
    add Solid("#000000c8")
    frame:
        align (0.5, 0.5)
        background Frame("images/ui/panel.png", 24, 24)
        padding (44, 32)
        vbox:
            spacing 12
            text "What do you want to photograph?" font NAV_FONT size 44 color "#ffffff" xalign 0.5
            text "A photo session uses part of the day. Your best shot of the session is kept in the phone gallery." size 22 color "#d0d4e0" xalign 0.5
            null height 4
            for sid in subs:
                button:
                    xsize 900
                    padding (12, 8)
                    background Solid("#1d2333")
                    hover_background Solid("#34406a")
                    action Return(sid)
                    hbox:
                        spacing 24
                        add ph_subject_thumb(sid, place, room, 160, 90)
                        text mph.subject_label(sid) size 34 color "#ffffff" yalign 0.5
            null height 4
            textbutton "Cancel":
                text_size 30
                xalign 0.5
                action Return("__cancel__")


# ------------------------------------------------------------------------------------ after a subject photo session
label photo_save_result:
    $ best = mp.session_result(scores)
    $ ph_new = ph_save_room_photo(photo_subject, best)
    $ ph_name = mph.subject_label(photo_subject)
    if best >= mph.MATCH_REQUIRED:
        "Best shot: [best]%% match. \"[ph_name]\" was saved to your phone gallery."
    else:
        "Best shot: [best]%% match. \"[ph_name]\" was saved to your phone gallery, but it is a bit dull."
    if not photo_gig_hint_done:
        $ photo_gig_hint_done = True
        $ ph_req = mph.MATCH_REQUIRED
        "Open your phone (the button at the bottom left, or the P key) and look at Snapjob: clients pay for photos that match their request by [ph_req]%% or more."
    return
