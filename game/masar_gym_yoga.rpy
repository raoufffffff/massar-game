# Gym mini-game: yoga (Ana).  Rules and numbers live in masar_yoga.py.
#
# Arrows appear on the right.  Press them in the same order (arrow keys, or the buttons on the screen).
# Right = Ana moves to the next pose.  Wrong = she loses her balance and the round is repeated.
# Pictures: images/gym/yoga_start.png, yoga_p1..p5.png, optional yoga_f0..f4.png (confused faces),
# yoga_bg.jpg, yoga_arrow_*  (made by tools/make_yoga_images.py from the green-screen files in raw_yoga/).
#
# Call it from any script with:   call gym_yoga
# When it ends, the points (0..10) are in  yoga_points  and the pose reached in  yoga_pose.

init python:
    import time
    import masar_yoga as yoga

    def yoga_tick():
        # called many times a second by the play screen: updates the countdown, ends the round when it hits zero
        left = yoga.ROUND_SECONDS - (time.time() - store.yoga_t0)
        store.yoga_left = max(0.0, left)
        if left <= 0:
            return store.yoga_s.timeout()

    def yoga_press(direction):
        r = store.yoga_s.press(direction)
        if r:
            return r

    def yoga_pic(fail=False):
        # the picture of Ana for the current state; the confused one when a round was just lost
        st = store.yoga_s.state
        base = "images/gym/yoga_start.png" if st == 0 else "images/gym/yoga_p%d.png" % st
        if fail:
            f = "images/gym/yoga_f%d.png" % st
            if renpy.loadable(f):
                return f
        return base if renpy.loadable(base) else "images/gym/yoga_start.png"

default yoga_s = None
default yoga_t0 = 0.0
default yoga_left = 20.0
default yoga_points = 0
default yoga_pose = 0
default yoga_best = 0

transform yoga_wobble:
    block:
        linear 0.05 xoffset 10
        linear 0.05 xoffset -10
        repeat 6
    xoffset 0

screen yoga_hud(yoga_round_no=1):
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        pos (20, 20)
        padding (24, 12)
        vbox:
            spacing 2
            text "Yoga" font NAV_FONT size 30 color "#ffffff"
            text "Round [yoga_round_no] / [yoga.ROUNDS]      Pose [yoga_s.state] / [yoga.POSES]      Lost [yoga_s.fails] / [yoga.FAIL_LIMIT]" size 22 color "#d0d4e0"

screen yoga_arrows(show_progress=True):
    # the sequence, on the right of the screen
    $ yoga_n = len(yoga_s.seq)
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
                for yoga_i, yoga_a in enumerate(yoga_s.seq):
                    $ yoga_k = "d" if (show_progress and yoga_i < yoga_s.pos) else ("c" if (show_progress and yoga_i == yoga_s.pos) else "n")
                    $ yoga_arrow_pic = "images/gym/yoga_arrow_%s_%s.png" % (yoga_a, yoga_k)
                    add yoga_arrow_pic zoom 0.75

screen yoga_buttons():
    # on-screen arrows (for the mouse / touch); the keyboard arrows work too
    $ yoga_bx = 1370
    $ yoga_by = 740
    for yoga_d, yoga_dx, yoga_dy in (("up", 0, -110), ("left", -110, 0), ("down", 0, 0), ("right", 110, 0)):
        $ yoga_bpic = "images/gym/yoga_arrow_%s_n.png" % yoga_d
        $ yoga_bhov = "images/gym/yoga_arrow_%s_c.png" % yoga_d
        imagebutton:
            idle yoga_bpic
            hover yoga_bhov
            xpos yoga_bx + yoga_dx
            ypos yoga_by + yoga_dy + 110
            at transform:
                zoom 0.7
            action Function(yoga_press, yoga_d)

screen yoga_world(pic, wobble=False):
    add "images/gym/yoga_bg.jpg"
    if wobble:
        add pic xpos -80 yalign 1.0 at yoga_wobble
    else:
        add pic xpos -80 yalign 1.0

screen yoga_timer():
    # the countdown bar under the arrows: green, then orange, then red as the time runs out
    $ yoga_frac = yoga_left / yoga.ROUND_SECONDS
    $ yoga_col = "#4cd964" if yoga_frac > 0.5 else ("#ffb13b" if yoga_frac > 0.25 else "#ff5a4a")
    $ yoga_secs = int(yoga_left + 0.99)
    fixed:
        xpos 1180
        ypos 650
        xsize 680
        ysize 50
        add Solid("#101218cc") xysize (680, 50)
        add Solid(yoga_col) xysize (int(660 * yoga_frac), 30) pos (10, 10)
        text "[yoga_secs]" size 30 color "#ffffff" xalign 0.5 yalign 0.5 outlines [(2, "#000000", 0, 1)]

screen yoga_play():
    $ yoga_round_no = min(yoga.ROUNDS, yoga_s.rounds + 1)
    use yoga_world(yoga_pic())
    use yoga_hud(yoga_round_no)
    use yoga_arrows
    use yoga_timer
    use yoga_buttons
    timer 0.05 repeat True action Function(yoga_tick)
    key "K_UP" action Function(yoga_press, "up")
    key "K_DOWN" action Function(yoga_press, "down")
    key "K_LEFT" action Function(yoga_press, "left")
    key "K_RIGHT" action Function(yoga_press, "right")

screen yoga_feedback(res):
    $ yoga_round_no = min(yoga.ROUNDS, yoga_s.rounds)
    use yoga_world(yoga_pic(res != "win"), res != "win")
    use yoga_hud(yoga_round_no)
    if res == "win":
        text "Well done!" size 64 color "#7dffa0" font NAV_FONT outlines [(3, "#000000", 0, 2)] xpos 1230 ypos 400
    elif res == "timeout":
        text "Too slow!" size 64 color "#ff9b8b" font NAV_FONT outlines [(3, "#000000", 0, 2)] xpos 1250 ypos 400
    else:
        text "Lost her balance..." size 56 color "#ff9b8b" font NAV_FONT outlines [(3, "#000000", 0, 2)] xpos 1130 ypos 400
    timer 1.1 action Return()

screen yoga_intro():
    $ yoga_round_no = 1
    $ yoga_secs_txt = int(yoga.ROUND_SECONDS)
    use yoga_world(yoga_pic())
    modal True
    add Solid("#000000b0")
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        align (0.5, 0.5)
        padding (60, 40)
        vbox:
            spacing 18
            xalign 0.5
            text "YOGA" font NAV_FONT size 56 color "#ffffff" xalign 0.5
            text "Press the arrows in the order shown (arrow keys or the on-screen buttons).\nRight: Ana moves to the next pose. Wrong key or more than [yoga_secs_txt] seconds: she loses her balance and you try again." size 28 color "#d0d4e0" xalign 0.5 text_align 0.5
            text "[yoga.ROUNDS] rounds.  [yoga.FAIL_LIMIT] lost rounds end the session." size 26 color "#d0d4e0" xalign 0.5
            textbutton "Start (SPACE)" xalign 0.5 text_size 40 action Return()
    key "K_SPACE" action Return()

screen yoga_summary():
    $ yoga_verdict = yoga_s.rating()
    use yoga_world(yoga_pic())
    modal True
    add Solid("#000000b0")
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        align (0.5, 0.5)
        padding (70, 44)
        vbox:
            spacing 16
            xalign 0.5
            text "SESSION OVER" font NAV_FONT size 56 color "#ffffff" xalign 0.5
            text "[yoga_verdict]" size 34 color "#ffd54a" xalign 0.5
            text "Points: [yoga_s.points] / 10      Pose reached: [yoga_s.state] / [yoga.POSES]      Lost rounds: [yoga_s.fails]" size 30 color "#d0d4e0" xalign 0.5
            text "Best so far: [yoga_best]" size 26 color "#d0d4e0" xalign 0.5
            textbutton "Leave (SPACE)" xalign 0.5 text_size 40 action Return()
    key "K_SPACE" action Return()

label gym_yoga:
    $ yoga_s = yoga.YogaSession()
    scene black
    with fade
    call screen yoga_intro
    while not yoga_s.finished:
        $ yoga_t0 = time.time()
        $ yoga_left = yoga.ROUND_SECONDS
        call screen yoga_play
        $ yoga_res = _return
        $ renpy.transition(Dissolve(0.25))
        call screen yoga_feedback(yoga_res)
        if not yoga_s.finished:
            $ yoga_s.new_round()
    $ yoga_points = yoga_s.points
    $ yoga_pose = yoga_s.state
    if yoga_points > yoga_best:
        $ yoga_best = yoga_points
    call screen yoga_summary
    scene black with fade
    return
