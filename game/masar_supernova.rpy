# Supernova: the in-game photo platform (a phone app, purple).  Rules and numbers: masar_supernova.py + data/supernova.json.
# Two accounts: "me" (the player, any photo) and "ana" (opens after gate 15, only photos of Ana).
# Tabs (bottom bar): Feed, Post, Inbox, Profile.  Inbox and the other people's feed are not built yet.

init python:
    import masar_supernova as msn

    def sn_enter(aid):
        store.sn_account = aid
        store.sn_tab = "feed"
        store.sn_pick = None
        store.sn_msg = ""

    def sn_leave():
        store.sn_account = None
        store.sn_pick = None
        store.sn_msg = ""

    def sn_tab_set(tab):
        store.sn_tab = tab
        store.sn_pick = None
        store.sn_msg = ""

    def sn_followers(aid):
        return store.followers if aid == "me" else store.story.ana_followers

    def sn_post(aid, pid):
        p = store.phone.photo(pid)
        r = store.sn.post(aid, p, store.day, store.day_part, sn_followers(aid), store.story.gates_crossed)
        if r["ok"]:
            if aid == "me":
                store.followers = store.followers + r["gain"]
            else:
                store.story.ana_followers = store.story.ana_followers + r["gain"]
                store.story.log("sn_post", store.day, store.day_part, account=aid)
        store.sn_msg = r["text"]
        store.sn_pick = None
        flush_notes()

default sn = msn.Supernova()
default sn_account = None        # None = the account chooser; "me" / "ana"
default sn_tab = "feed"          # feed / add / inbox / profile
default sn_pick = None           # gallery photo chosen to post
default sn_msg = ""


screen phone_supernova():
    add Solid("#150d24")
    if sn_account is None:
        use sn_chooser
    else:
        use sn_header
        use sn_body
        use sn_tabbar


screen sn_chooser():
    add Solid("#4b1d8a") xysize (584, 112)
    textbutton "< Back":
        pos (16, 46)
        text_size 26
        text_color "#ffd54a"
        text_hover_color "#ffffff"
        action Function(ph_back)
    text "Supernova" font NAV_FONT size 36 color "#ffffff" xalign 0.5 ypos 50
    vbox:
        pos (24, 150)
        spacing 18
        xsize 536
        text "Whose account do you want to open?" size 26 color "#d9c2ff"
        for sn_aid in msn.account_ids():
            $ sn_a = msn.account(sn_aid)
            $ sn_open = sn.unlocked(sn_aid, story.gates_crossed)
            $ sn_fol = sn_followers(sn_aid)
            button:
                xfill True
                padding (22, 20)
                background Solid("#2a1747" if sn_open else "#1b1230")
                hover_background Solid("#4b2a80")
                sensitive sn_open
                action Function(sn_enter, sn_aid)
                vbox:
                    spacing 4
                    text sn_a["title"] size 34 bold True color ("#ffffff" if sn_open else "#7b6a99")
                    text sn_a["handle"] size 22 color ("#b57bff" if sn_open else "#5d4e78")
                    if sn_open:
                        text ("%d followers   -   %d posts" % (sn_fol, len(sn.posts.get(sn_aid, [])))) size 22 color "#d9c2ff"
                    else:
                        text sn_a.get("locked_text", "Not open yet.") size 22 color "#7b6a99"


screen sn_header():
    $ sn_a = msn.account(sn_account)
    add Solid("#4b1d8a") xysize (584, 112)
    textbutton "< Back":
        pos (16, 46)
        text_size 26
        text_color "#ffd54a"
        text_hover_color "#ffffff"
        action Function(ph_back)
    text sn_a["name"] font NAV_FONT size 36 color "#ffffff" xalign 0.5 ypos 50


screen sn_tabbar():
    add Solid("#2a1747") xysize (584, 88) ypos 896
    hbox:
        ypos 896
        for sn_t, sn_label in [("feed", "Feed"), ("add", "Post"), ("inbox", "Inbox"), ("profile", "Profile")]:
            textbutton sn_label:
                xysize (146, 88)
                text_size (40 if sn_t == "add" else 26)
                text_bold (sn_t == "add")
                text_xalign 0.5
                text_yalign 0.5
                text_color ("#ffffff" if sn_tab == sn_t else "#b9a3de")
                text_hover_color "#ffffff"
                background Solid("#6a2fc0" if sn_tab == sn_t else "#2a1747")
                hover_background Solid("#5a28a6")
                action Function(sn_tab_set, sn_t)


screen sn_body():
    $ sn_a = msn.account(sn_account)
    if sn_tab == "feed":
        $ sn_mine = sn.posts_of(sn_account)
        if not sn_mine:
            text "Nothing here yet.\nPost a photo and it will show up here.\n\nOther people's posts will appear in this feed soon." size 24 color "#b9a3de" xalign 0.5 ypos 300 text_align 0.5 xsize 460
        else:
            viewport:
                pos (18, 124)
                xysize (548, 764)
                mousewheel True
                draggable True
                scrollbars "vertical"
                vbox:
                    spacing 22
                    for sn_p in sn_mine:
                        vbox:
                            spacing 6
                            text (sn_a["handle"] + "   -   " + mph.when_text(sn_p["day"], sn_p["part"])) size 20 color "#b57bff"
                            add ph_photo(sn_p["photo"], 520, 360)
                            text ("%d likes   -   +%d followers" % (sn_p["likes"], sn_p["gain"])) size 22 color "#ffffff"
    elif sn_tab == "add":
        $ sn_today = sn.posted_today(sn_account, day)
        text ("Posts today: %d / %d" % (sn_today, sn_a.get("per_day", 1))) size 22 color "#b9a3de" pos (24, 128)
        if sn_msg:
            text sn_msg size 22 color "#ffd54a" pos (24, 160) xsize 520
        if sn_pick is not None:
            $ sn_ph = phone.photo(sn_pick)
            if sn_ph is None:
                text "This photo is gone." size 24 color "#b9a3de" align (0.5, 0.4)
            else:
                add ph_photo(sn_ph, 548, 356) pos (18, 200)
                text sn_ph["label"] size 28 bold True color "#ffffff" pos (24, 570)
                text ("Quality: %d%%" % msn.quality(sn_ph)) size 22 color "#d9c2ff" pos (24, 612)
                hbox:
                    pos (24, 680)
                    spacing 16
                    textbutton "Post it":
                        text_size 28
                        padding (28, 10)
                        background Solid("#6a2fc0")
                        hover_background Solid("#8a4fe0")
                        text_color "#ffffff"
                        action Function(sn_post, sn_account, sn_ph["id"])
                    textbutton "Cancel":
                        text_size 28
                        padding (28, 10)
                        background Solid("#2a1747")
                        hover_background Solid("#4b2a80")
                        text_color "#ffffff"
                        action SetVariable("sn_pick", None)
        else:
            $ sn_list = sn.eligible(sn_account, phone.photos)
            if not sn_list:
                if sn_a.get("accepts") == "ana":
                    text "No photos of Ana to post.\nWhen she is in a good mood after a talk, ask to take her picture." size 22 color "#b9a3de" xalign 0.5 ypos 330 text_align 0.5 xsize 460
                else:
                    text "No photos to post.\nTake photos with the camera icon at a photo spot." size 22 color "#b9a3de" xalign 0.5 ypos 330 text_align 0.5 xsize 460
            else:
                text "Choose a photo:" size 24 color "#ffffff" pos (24, 196)
                vpgrid:
                    pos (18, 236)
                    xysize (548, 650)
                    cols 3
                    spacing 10
                    mousewheel True
                    draggable True
                    scrollbars "vertical"
                    for sn_p in sn_list:
                        button:
                            xysize (164, 122)
                            padding (0, 0)
                            background None
                            hover_foreground Solid("#ffffff22")
                            action SetVariable("sn_pick", sn_p["id"])
                            fixed:
                                xysize (164, 122)
                                add ph_photo(sn_p, 164, 100)
                                text ("%d%%" % msn.quality(sn_p)) size 17 color "#ffffff" outlines [(2, "#000000", 0, 1)] xpos 6 ypos 76
                                text ph_short(sn_p["label"]) size 14 color "#d9c2ff" xpos 2 ypos 103
    elif sn_tab == "inbox":
        text "No messages yet." size 26 color "#b9a3de" xalign 0.5 ypos 330
        if sn_account == "ana":
            text "Sponsors and offers will write to her here." size 20 color "#7b6a99" xalign 0.5 ypos 376
        else:
            text "Clients and photography offers will write to you here." size 20 color "#7b6a99" xalign 0.5 ypos 376
    else:
        $ sn_mine = sn.posts_of(sn_account)
        text sn_a["name"] font NAV_FONT size 44 color "#ffffff" pos (24, 128)
        text sn_a["handle"] size 22 color "#b57bff" pos (24, 182)
        text sn_a.get("bio", "") size 22 color "#d9c2ff" pos (24, 214) xsize 520
        hbox:
            pos (24, 262)
            spacing 40
            vbox:
                text ("%d" % len(sn_mine)) size 34 bold True color "#ffffff"
                text "posts" size 20 color "#b9a3de"
            vbox:
                text ("%d" % sn_followers(sn_account)) size 34 bold True color "#ffffff"
                text "followers" size 20 color "#b9a3de"
            if sn_account == "ana":
                vbox:
                    text "soon" size 34 bold True color "#7b6a99"
                    text "earnings" size 20 color "#b9a3de"
        if not sn_mine:
            text "No posts yet." size 22 color "#7b6a99" pos (24, 380)
        else:
            vpgrid:
                pos (18, 350)
                xysize (548, 536)
                cols 3
                spacing 10
                mousewheel True
                draggable True
                scrollbars "vertical"
                for sn_p in sn_mine:
                    fixed:
                        xysize (164, 122)
                        add ph_photo(sn_p["photo"], 164, 122)
                        text ("%d" % sn_p["likes"]) size 17 color "#ffffff" outlines [(2, "#000000", 0, 1)] xpos 6 ypos 98
