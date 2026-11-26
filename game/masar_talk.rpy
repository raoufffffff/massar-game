# Talk game (version 1.1): a sitting conversation.  Ana sits in front of the player (a picture per mood), says something, the
# player answers with a few arrows; 3 moments, 2 good ones win.  Success or failure, no points.
# Rules: masar_talk.py.  Numbers, conversations, closing lines: game/data/talk.json.  Scenes (pictures per place): game/data/talk_scenes.json
# (neutral / smile / annoyed pictures, 2560x1440, in game/images/talk/).  The result goes into the story ledger (masar_story.py).
# The picture moves a little: it breathes, creeps closer while the time runs, pulses on success and leans away on failure.
#
# Call it with:   call talk_game("ana")      (ana_click does it; the caller makes the time slot pass)

init python:
    import time
    import masar_talk as talk

    def talk_tick():
        left = store.talk_s.seconds - (time.time() - store.talk_t0)
        store.talk_left = max(0.0, left)
        if left <= 0:
            return store.talk_s.timeout()

    def talk_press(direction):
        r = store.talk_s.press(direction)
        if r:
            return r

    def talk_pic(key):
        """Picture of the current talk scene for a mood (neutral / smile / annoyed); a plain colour when the scene has none."""
        sc = store.talk_scene
        if sc:
            return sc["images"][key]
        return Solid("#2a2d36")

default talk_s = None
default talk_t0 = 0.0
default talk_left = 7.0
default talk_name = "Ana"
default talk_scene = None
default talk_ana_text = ""
default talk_you_text = ""
default talk_verdict = ""

# ---- camera motion of the scene picture (anchored at the bottom centre; base zoom 0.80 leaves a margin so no edge shows)
transform talk_cam_enter:
    subpixel True
    anchor (0.5, 1.0)
    pos (0.5, 1.0)
    zoom 0.80
    alpha 0.0
    yoffset 70
    parallel:
        ease 1.0 alpha 1.0 yoffset 0
    parallel:
        block:
            ease 2.6 yzoom 1.012
            ease 2.6 yzoom 1.0
            repeat

transform talk_cam_to(z=0.80, t=0.5):
    subpixel True
    anchor (0.5, 1.0)
    pos (0.5, 1.0)
    parallel:
        ease t zoom z
    parallel:
        block:
            ease 2.6 yzoom 1.012
            ease 2.6 yzoom 1.0
            repeat

transform talk_cam_pulse:
    subpixel True
    anchor (0.5, 1.0)
    pos (0.5, 1.0)
    parallel:
        ease 0.2 zoom 0.83
        ease 1.4 zoom 0.80
    parallel:
        block:
            ease 2.6 yzoom 1.012
            ease 2.6 yzoom 1.0
            repeat

transform talk_cam_away:
    subpixel True
    anchor (0.5, 1.0)
    pos (0.5, 1.0)
    parallel:
        ease 0.6 zoom 0.775
    parallel:
        block:
            ease 2.6 yzoom 1.012
            ease 2.6 yzoom 1.0
            repeat

# ---- screens (everything sits in the bottom band, so her face is never covered)
screen talk_hud():
    add "images/ui/talk_shade.png"
    frame:
        background Solid("#0a0c12a0")
        pos (24, 24)
        padding (18, 10)
        vbox:
            spacing 6
            text "Talking with [talk_name]" size 26 color "#ffffff" outlines [(2, "#000000", 0, 1)]
            hbox:
                spacing 8
                for talk_i in range(talk_s.rounds):
                    $ talk_dot = ("#4cd964" if talk_s.history[talk_i] == "win" else "#ff5a4a") if talk_i < len(talk_s.history) else "#ffffff55"
                    add Solid(talk_dot) xysize (22, 22)

screen talk_words(show_reply=True):
    vbox:
        xalign 0.5
        ypos 790
        xsize 1500
        spacing 8
        text "{color=#e8b4a0}[talk_name]:{/color} [talk_ana_text]" size 38 color "#ffffff" xalign 0.5 text_align 0.5 outlines [(2, "#000000", 0, 1)]
        if show_reply:
            text "You: [talk_you_text]" size 30 color "#cfe3ff" italic True xalign 0.5 text_align 0.5 outlines [(2, "#000000", 0, 1)]

screen talk_intro():
    modal True
    use talk_hud
    vbox:
        xalign 0.5
        ypos 780
        spacing 10
        text "A quiet talk" font NAV_FONT size 52 color "#ffffff" xalign 0.5 outlines [(2, "#000000", 0, 1)]
        text "[talk_s.rounds] moments. Answer with the arrows in order before the time runs out. Win [talk_s.need] and she warms up.\nOne talk a day.   (SPACE)" size 28 color "#e6e9f2" xalign 0.5 text_align 0.5 outlines [(2, "#000000", 0, 1)]
    key "dismiss" action Return()

screen talk_ask():
    modal True
    use talk_hud
    use talk_words(False)
    text "SPACE / click to answer" size 22 color "#ffffffaa" xalign 0.5 ypos 1020
    key "dismiss" action Return()

screen talk_play():
    use talk_hud
    use talk_words
    # the arrows to press (centre), a thin timer bar above them, and mouse buttons on the right
    $ talk_frac = talk_left / talk_s.seconds
    $ talk_col = "#4cd964" if talk_frac > 0.5 else ("#ffb13b" if talk_frac > 0.25 else "#ff5a4a")
    add Solid("#ffffff30") xysize (700, 8) xalign 0.5 ypos 925
    add Solid(talk_col) xysize (int(700 * talk_frac), 8) xpos 610 ypos 925
    hbox:
        spacing 10
        xalign 0.5
        ypos 945
        for talk_i, talk_a in enumerate(talk_s.seq):
            $ talk_k = "d" if talk_i < talk_s.pos else ("c" if talk_i == talk_s.pos else "n")
            add ("images/gym/yoga_arrow_%s_%s.png" % (talk_a, talk_k)) zoom 0.6
    for talk_d, talk_dx, talk_dy in (("up", 0, -66), ("left", -66, 0), ("down", 0, 0), ("right", 66, 0)):
        imagebutton:
            idle ("images/gym/yoga_arrow_%s_n.png" % talk_d)
            hover ("images/gym/yoga_arrow_%s_c.png" % talk_d)
            xpos 1690 + talk_dx
            ypos 960 + talk_dy
            at transform:
                zoom 0.4
                alpha 0.75
            action Function(talk_press, talk_d)
    timer 0.05 repeat True action Function(talk_tick)
    key "K_UP" action Function(talk_press, "up")
    key "K_DOWN" action Function(talk_press, "down")
    key "K_LEFT" action Function(talk_press, "left")
    key "K_RIGHT" action Function(talk_press, "right")

screen talk_react():
    modal True
    use talk_hud
    vbox:
        xalign 0.5
        ypos 790
        xsize 1500
        spacing 8
        text "[talk_verdict]" size 24 color ("#7dffa0" if talk_s.round_res == "win" else "#ff9b8b") xalign 0.5 outlines [(2, "#000000", 0, 1)]
        text "{color=#e8b4a0}[talk_name]:{/color} [talk_ana_text]" size 38 color "#ffffff" xalign 0.5 text_align 0.5 outlines [(2, "#000000", 0, 1)]
    text "SPACE / click" size 22 color "#ffffffaa" xalign 0.5 ypos 1020
    key "dismiss" action Return()

label talk_game(who="ana"):
    $ talk_s = talk.TalkSession(who, day)
    $ talk_name = talk.name_of(who)
    $ talk_scene = talk.scene_for(location, room, renpy.loadable)
    scene black
    show expression talk_pic("neutral") as talkbg at talk_cam_enter
    with Dissolve(0.5)
    call screen talk_intro
    while not talk_s.finished:
        $ talk_ana_text = talk_s.conv["ana"]
        $ talk_you_text = talk_s.conv["you"]
        call screen talk_ask
        $ talk_t0 = time.time()
        $ talk_left = talk_s.seconds
        show expression talk_pic("neutral") as talkbg at talk_cam_to(0.835, talk_s.seconds)
        call screen talk_play
        $ talk_res = _return
        if talk_s.round_res == "win":
            $ talk_ana_text = talk_s.conv["win"]
            $ talk_verdict = "She likes that."
            show expression talk_pic("smile") as talkbg at talk_cam_pulse
        else:
            $ talk_ana_text = talk_s.conv["fail"]
            $ talk_verdict = "Too slow..." if talk_s.round_res == "timeout" else "That came out wrong."
            show expression talk_pic("annoyed") as talkbg at talk_cam_away
        with Dissolve(0.15)
        call screen talk_react
        if not talk_s.finished:
            show expression talk_pic("neutral") as talkbg at talk_cam_to(0.80, 0.8)
            with Dissolve(0.3)
        $ talk_s.next_round()
    # the day ledger remembers it: one try a day; a win gives love at the end of the day (rules in story.json)
    $ story.talk_result(who, talk_s.success, day, day_part)
    $ note(player.talk(talk_s.success))
    $ flush_notes()
    $ talk_line = talk.pick_line(who, talk_s.success, day)
    if talk_line:
        ana "[talk_line]"
    scene black
    with Dissolve(0.5)
    return
