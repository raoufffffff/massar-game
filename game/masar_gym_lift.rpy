# Gym mini-game 1: bench press (the player). Rules and numbers live in masar_gym.py.
#
# POV scene: the player lies on the bench and looks up at the bar. A bar at the bottom of the screen has a
# marker sweeping over red / orange / green zones. SPACE (or a click) stops it:
#   green = smooth lift (+2), orange = hard lift (+1), red = failed lift (0).
# Pictures: images/gym/gym_bg.jpg and gym_pov_1..5 / gym_pov_fail / gym_pov_shake (made by tools/make_bench_images.py
# from the green-screen files in raw_gym/).  Call it from any script with:  call gym_bench(1)
# When it ends, the points of the session are in  bench_points  (0..10).

init python:
    import time
    import masar_gym as gym

    METER_X = 460          # the meter on screen
    METER_Y = 930
    METER_W = 1000
    METER_H = 44

    def lift_press():
        # ends the interaction with the zone the marker is in right now
        return gym.zone_at(gym.marker_pos(time.time() - lift_t0))

    def lift_marker_fn(trans, st, at):
        # the marker follows the clock itself, the same one lift_press() reads
        trans.xoffset = int(gym.marker_pos(time.time() - lift_t0) * METER_W) - 6
        return 0.0

default lift_t0 = 0.0
default lift_session = None
default lift_best = 0

default bench_points = 0

image gymbg = "images/gym/gym_bg.jpg"
image pov 1 = "images/gym/gym_pov_1.png"
image pov 2 = "images/gym/gym_pov_2.png"
image pov 3 = "images/gym/gym_pov_3.png"
image pov 4 = "images/gym/gym_pov_4.png"
image pov 5 = "images/gym/gym_pov_5.png"
image pov fail = "images/gym/gym_pov_fail.png"
image pov shake = "images/gym/gym_pov_shake.png"

transform lift_tremble:       # small shaking of the whole picture
    block:
        linear 0.04 xoffset 6
        linear 0.04 xoffset -6
        repeat
transform lift_still:
    xoffset 0

init python:
    def lift_frame(name, hold, fade=0.12, shaky=False):
        # shows one frame of the bar going up/down, dissolving from the previous one
        if not renpy.has_image("pov " + name):
            return
        renpy.show("pov " + name, at_list=[lift_tremble] if shaky else [lift_still])
        renpy.with_statement(Dissolve(fade / gym.ANIM_SPEED))
        renpy.pause(hold / gym.ANIM_SPEED, hard=True)

    def lift_animate(zone):
        if zone == "green":          # smooth: all the way up and back down
            for f in ("2", "3", "4", "5"):
                lift_frame(f, 0.10)
            lift_frame("5", 0.30)
            for f in ("4", "3", "2", "1"):
                lift_frame(f, 0.08)
        elif zone == "orange":       # hard: slow, shaking, still gets there
            for f in ("2", "3"):
                lift_frame(f, 0.30, 0.25)
            lift_frame("shake" if renpy.has_image("pov shake") else "4", 0.45, 0.2, True)
            lift_frame("4", 0.35, 0.25, True)
            lift_frame("5", 0.30, 0.25)
            for f in ("4", "3", "2", "1"):
                lift_frame(f, 0.14, 0.14)
        else:                        # red: stalls halfway, trembles and drops
            lift_frame("2", 0.12)
            lift_frame("3", 0.15)
            lift_frame("fail", 0.55, 0.15, True)
            lift_frame("2", 0.08, 0.1)
            lift_frame("1", 0.2, 0.1)

screen lift_hud():
    $ lift_cur = lift_session.done + (0 if lift_session.finished else 1)
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        pos (20, 20)
        padding (24, 12)
        vbox:
            spacing 2
            text "Bench press" font NAV_FONT size 30 color "#ffffff"
            text "Lift [lift_cur] / [gym.LIFT_ATTEMPTS]      Points [lift_session.score]      Fails [lift_session.fails] / [gym.LIFT_FAIL_LIMIT]" size 22 color "#d0d4e0"

screen lift_meter_bar(running=True):
    # coloured zones
    $ gx0 = int(gym.CUR["orange"][0] * METER_W)
    $ gx1 = int(gym.CUR["green"][0] * METER_W)
    $ gx2 = int(gym.CUR["green"][1] * METER_W)
    $ gx3 = int(gym.CUR["orange"][1] * METER_W)
    frame:
        background Solid("#101218cc")
        pos (METER_X - 14, METER_Y - 30)
        xysize (METER_W + 28, METER_H + 60)
    fixed:
        pos (METER_X, METER_Y)
        xysize (METER_W, METER_H)
        add Solid("#c0392b") xysize (METER_W, METER_H)
        add Solid("#e8912d") pos (gx0, 0) xysize (gx3 - gx0, METER_H)
        add Solid("#33c25a") pos (gx1, 0) xysize (gx2 - gx1, METER_H)
    if running:
        add Solid("#ffffff", xsize=12, ysize=METER_H + 26) pos (METER_X, METER_Y - 13) at lift_marker_move

transform lift_marker_move:
    function lift_marker_fn

screen lift_meter():
    use lift_hud
    use lift_meter_bar(True)
    text "Press SPACE when the marker is in the green zone" size 30 color "#ffffff" outlines [(2, "#000000", 0, 1)] xalign 0.5 ypos 860
    key "K_SPACE" action Function(lift_press)
    key "K_RETURN" action Function(lift_press)
    button:
        xysize (1920, 1080)
        background None
        action Function(lift_press)
    textbutton "LIFT":
        xalign 0.5
        ypos 985
        text_size 44
        text_font NAV_FONT
        padding (60, 8)
        action Function(lift_press)

screen lift_result(zone):
    # shown while the lift animation plays, then hidden by the label (about 0.9 s of text is enough to read)
    use lift_hud
    $ label_text = {"green": "Smooth lift!   +2", "orange": "Hard lift...   +1", "red": "Failed!   +0"}[zone]
    $ label_col = {"green": "#7dffa0", "orange": "#ffc46b", "red": "#ff7b6b"}[zone]
    text label_text size 64 color label_col font NAV_FONT outlines [(3, "#000000", 0, 2)] xalign 0.5 ypos 140

screen lift_intro():
    modal True
    add Solid("#000000b0")
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        align (0.5, 0.5)
        padding (60, 40)
        vbox:
            spacing 18
            xalign 0.5
            text "BENCH PRESS" font NAV_FONT size 56 color "#ffffff" xalign 0.5
            text "A marker sweeps over the bar at the bottom of the screen.\nPress SPACE (or click) to stop it." size 30 color "#d0d4e0" xalign 0.5 text_align 0.5
            hbox:
                spacing 20
                xalign 0.5
                text "GREEN  +2 points" size 30 color "#7dffa0"
                text "ORANGE  +1" size 30 color "#ffc46b"
                text "RED  fail" size 30 color "#ff7b6b"
            text "[gym.LIFT_ATTEMPTS] lifts.  [gym.LIFT_FAIL_LIMIT] failed lifts end the session." size 26 color "#d0d4e0" xalign 0.5
            textbutton "Start (SPACE)" xalign 0.5 text_size 40 action Return()
    key "K_SPACE" action Return()

screen lift_summary():
    $ lift_verdict = lift_session.rating()
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
            text "[lift_verdict]" size 34 color "#ffd54a" xalign 0.5
            text "Points: [lift_session.score] / [lift_session.max_score]      Failed lifts: [lift_session.fails]" size 30 color "#d0d4e0" xalign 0.5
            text "Best so far: [lift_best]" size 26 color "#d0d4e0" xalign 0.5
            textbutton "Leave (SPACE)" xalign 0.5 text_size 40 action Return()
    key "K_SPACE" action Return()

label gym_bench_press:
    # the hook used by the gym room button (ROOM_ACTIONS in masar_gym.py)
    call gym_bench(1)
    return

label gym_bench(level=1):
    $ gym.set_level(level)
    $ lift_session = gym.LiftSession()
    scene gymbg
    show pov 1 at lift_still
    with fade
    call screen lift_intro
    while not lift_session.finished:
        $ lift_t0 = time.time()
        call screen lift_meter
        $ lift_zone = _return
        $ lift_session.press(lift_zone)
        show screen lift_result(lift_zone)
        $ lift_animate(lift_zone)
        hide screen lift_result
        show pov 1 at lift_still
        with Dissolve(0.15)
    $ bench_points = lift_session.score
    if lift_session.score > lift_best:
        $ lift_best = lift_session.score
    call screen lift_summary
    scene black with fade
    return
