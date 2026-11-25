# Gym mini-game: running (Chrome-Dino style).  Rules and numbers live in masar_run.py.
#
# The runner stays in place, the world scrolls, SPACE (or a click) jumps over the obstacles.
# Pictures: images/gym/run_<who>_run1/run2/jump/hit.png, run_bg.jpg, run_obs_1..3.png
# (made by tools/make_run_images.py from the green-screen files in raw_run/).
#
# Call it from any script with:   call gym_run("ana", 1)       ("ana" or later "player", level)
# When it ends, the points of the session (0..10) are in  run_points.

init python:
    import time
    import masar_run as run

    def run_tick():
        # called every frame by the screen; moves the game on by the real time that passed
        now = time.time()
        dt = now - store.run_last
        store.run_last = now
        store.run_s.step(dt)
        if store.run_s.finished:
            return "done"

    def run_jump():
        store.run_s.jump()

default run_s = None
default run_last = 0.0
default run_who = "ana"
default run_points = 0
default run_best = 0

screen run_hud():
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        pos (20, 20)
        padding (24, 12)
        vbox:
            spacing 2
            text "Running" font NAV_FONT size 30 color "#ffffff"
            text "Cleared [run_s.cleared] / [run_s.total]      Hits [run_s.hits] / [run.RUN_HIT_LIMIT]" size 22 color "#d0d4e0"

screen run_world():
    # scrolling background (the picture is 3840 wide and repeats because its right half is a mirror image)
    $ run_bgx = int(run_s.dist * 0.5) % 3840
    add "images/gym/run_bg.jpg" xpos -run_bgx
    add "images/gym/run_bg.jpg" xpos 3840 - run_bgx
    for run_o in run_s.obstacles:
        $ run_opic = "images/gym/run_obs_%d.png" % run_o.kind
        add run_opic:
            xanchor 0.5
            yanchor 1.0
            xpos int(run_o.x)
            ypos run.GROUND_Y + 12
    # the runner: shown at half size of the file; blinks while protected after a hit
    $ run_fr = run_s.frame()
    if not renpy.loadable("images/gym/run_%s_%s.png" % (run_who, run_fr)):
        $ run_fr = "run1"
    $ run_pic = "images/gym/run_%s_%s.png" % (run_who, run_fr)
    $ run_lift, run_tilt, run_squash = run_s.bob()
    $ run_alpha = 0.45 if (run_s.protect > 0 and int(run_s.t * 12) % 2 == 0) else 1.0
    add run_pic:
        transform_anchor True
        xzoom 0.5
        yzoom 0.5 * run_squash
        rotate run_tilt
        xanchor 0.5
        yanchor 1.0
        xpos run.PLAYER_X
        ypos run.GROUND_Y - int(run_s.y + run_lift) + 8
        alpha run_alpha

screen run_play():
    use run_world
    use run_hud
    timer 0.016 repeat True action Function(run_tick)
    key "K_SPACE" action Function(run_jump)
    key "K_UP" action Function(run_jump)
    button:
        xysize (1920, 1080)
        background None
        action Function(run_jump)
    textbutton "JUMP":
        xalign 0.5
        ypos 985
        text_size 44
        text_font NAV_FONT
        padding (60, 8)
        action Function(run_jump)

screen run_intro():
    use run_world
    modal True
    add Solid("#000000b0")
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        align (0.5, 0.5)
        padding (60, 40)
        vbox:
            spacing 18
            xalign 0.5
            text "RUNNING" font NAV_FONT size 56 color "#ffffff" xalign 0.5
            text "Press SPACE (or click / tap JUMP) to jump over the obstacles." size 30 color "#d0d4e0" xalign 0.5 text_align 0.5
            text "Clear them all. [run.RUN_HIT_LIMIT] hits end the run." size 26 color "#d0d4e0" xalign 0.5
            textbutton "Start (SPACE)" xalign 0.5 text_size 40 action Return()
    key "K_SPACE" action Return()

screen run_summary():
    $ run_verdict = run_s.rating()
    use run_world
    modal True
    add Solid("#000000b0")
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        align (0.5, 0.5)
        padding (70, 44)
        vbox:
            spacing 16
            xalign 0.5
            text "RUN OVER" font NAV_FONT size 56 color "#ffffff" xalign 0.5
            text "[run_verdict]" size 34 color "#ffd54a" xalign 0.5
            text "Points: [run_s.points] / 10      Cleared: [run_s.cleared] / [run_s.total]      Hits: [run_s.hits]" size 30 color "#d0d4e0" xalign 0.5
            text "Best so far: [run_best]" size 26 color "#d0d4e0" xalign 0.5
            textbutton "Leave (SPACE)" xalign 0.5 text_size 40 action Return()
    key "K_SPACE" action Return()

label gym_run_ana:
    # the hook used by the gym room button (ROOM_ACTIONS in masar_gym.py)
    call gym_run("ana", 1)
    return

label gym_run_player:
    call gym_run("player", 1)
    return

label gym_run(who="ana", level=1):
    $ run_who = who
    $ run_s = run.RunSession(level)
    scene black
    with fade
    call screen run_intro
    $ run_last = time.time()
    call screen run_play
    $ run_points = run_s.points
    if run_points > run_best:
        $ run_best = run_points
    call screen run_summary
    scene black with fade
    return
