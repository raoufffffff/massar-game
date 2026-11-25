# Talk game (version 1): press 6 arrows in order before the time runs out.  Success or failure, no points.
# Rules: masar_talk.py.  Numbers and lines: game/data/talk.json.  The result goes into the story ledger (masar_story.py).
# Pictures: Ana's normal sprite (image ana ...) over the room; the arrows are the yoga arrow pictures.
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

default talk_s = None
default talk_t0 = 0.0
default talk_left = 10.0
default talk_name = "Ana"

screen talk_hud():
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        pos (20, 20)
        padding (24, 12)
        vbox:
            spacing 2
            text "Talking with [talk_name]" font NAV_FONT size 30 color "#ffffff"
            text "Keep the conversation going: press the arrows in order." size 22 color "#d0d4e0"

screen talk_arrows():
    frame:
        background Solid("#101218cc")
        xpos 1180
        ypos 330
        xsize 680
        padding (30, 24)
        vbox:
            spacing 14
            xalign 0.5
            text "Press the arrows in order" size 30 color "#ffffff" xalign 0.5 outlines [(2, "#000000", 0, 1)]
            hbox:
                spacing 6
                xalign 0.5
                for talk_i, talk_a in enumerate(talk_s.seq):
                    $ talk_k = "d" if talk_i < talk_s.pos else ("c" if talk_i == talk_s.pos else "n")
                    add ("images/gym/yoga_arrow_%s_%s.png" % (talk_a, talk_k)) zoom 0.75

screen talk_timer():
    $ talk_frac = talk_left / talk_s.seconds
    $ talk_col = "#4cd964" if talk_frac > 0.5 else ("#ffb13b" if talk_frac > 0.25 else "#ff5a4a")
    $ talk_secs = int(talk_left + 0.99)
    fixed:
        xpos 1180
        ypos 650
        xsize 680
        ysize 50
        add Solid("#101218cc") xysize (680, 50)
        add Solid(talk_col) xysize (int(660 * talk_frac), 30) pos (10, 10)
        text "[talk_secs]" size 30 color "#ffffff" xalign 0.5 yalign 0.5 outlines [(2, "#000000", 0, 1)]

screen talk_buttons():
    # on-screen arrows (mouse / touch); the keyboard arrows work too
    for talk_d, talk_dx, talk_dy in (("up", 0, -110), ("left", -110, 0), ("down", 0, 0), ("right", 110, 0)):
        imagebutton:
            idle ("images/gym/yoga_arrow_%s_n.png" % talk_d)
            hover ("images/gym/yoga_arrow_%s_c.png" % talk_d)
            xpos 1370 + talk_dx
            ypos 740 + talk_dy + 110
            at transform:
                zoom 0.7
            action Function(talk_press, talk_d)

screen talk_play():
    use talk_hud
    use talk_arrows
    use talk_timer
    use talk_buttons
    timer 0.05 repeat True action Function(talk_tick)
    key "K_UP" action Function(talk_press, "up")
    key "K_DOWN" action Function(talk_press, "down")
    key "K_LEFT" action Function(talk_press, "left")
    key "K_RIGHT" action Function(talk_press, "right")

screen talk_intro():
    modal True
    add Solid("#000000a0")
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        align (0.5, 0.5)
        padding (60, 40)
        vbox:
            spacing 18
            xalign 0.5
            text "TALK" font NAV_FONT size 56 color "#ffffff" xalign 0.5
            text "Press the [talk_s.length] arrows in the order shown (arrow keys or the on-screen buttons).\nA wrong key, or more than [talk_s.seconds:.0f] seconds, and the moment is lost. You can try once a day." size 28 color "#d0d4e0" xalign 0.5 text_align 0.5
            textbutton "Start (SPACE)" xalign 0.5 text_size 40 action Return()
    key "K_SPACE" action Return()

screen talk_feedback(res):
    if res == "win":
        text "She smiles!" size 64 color "#7dffa0" font NAV_FONT outlines [(3, "#000000", 0, 2)] xpos 1300 ypos 400
    elif res == "timeout":
        text "Too slow..." size 64 color "#ff9b8b" font NAV_FONT outlines [(3, "#000000", 0, 2)] xpos 1290 ypos 400
    else:
        text "Awkward..." size 64 color "#ff9b8b" font NAV_FONT outlines [(3, "#000000", 0, 2)] xpos 1300 ypos 400
    timer 1.2 action Return()

label talk_game(who="ana"):
    $ talk_s = talk.TalkSession()
    $ talk_name = talk.name_of(who)
    if room_w > 1920:
        scene expression room_view_bg()
    else:
        scene expression room_bg(location, room)
    show ana smile at ana_pos_x(0.2)
    with dissolve
    call screen talk_intro
    $ talk_t0 = time.time()
    $ talk_left = talk_s.seconds
    call screen talk_play
    $ talk_res = _return
    if talk_s.success:
        show ana smile
    else:
        show ana sad
    call screen talk_feedback(talk_res)
    # the day ledger remembers it: one try a day; a win gives love at the end of the day (rules in story.json)
    $ story.talk_result(who, talk_s.success, day, day_part)
    $ talk_line = talk.pick_line(who, talk_s.success, day)
    if talk_line:
        ana "[talk_line]"
    hide ana
    return
