# Photography mini-game: screen + session flow. Logic lives in masar_photo.py

init -1 python:
    import masar_photo as mp

define photo_flash = Fade(0.05, 0.0, 0.35, color="#ffffff")

default shot_q = 0
default followers = 0
default total_views = 0
default donations = 0
default photo_tutorial_done = False
default photo_spot = False

init python:
    def mp_capture(wave, start):
        """Freeze the light level at the exact moment the player presses capture."""
        store.shot_q = int(round(wave.value(renpy.get_game_runtime() - start)))

screen photo_shoot(wave, shot, total, bg):
    default start = renpy.get_game_runtime()
    $ t = renpy.get_game_runtime() - start
    $ q = wave.value(t)

    # The scene itself gets brighter/duller and more/less colourful with the light
    add Transform(bg, matrixcolor=BrightnessMatrix(-0.40 + 0.55 * q / 100.0) * SaturationMatrix(0.55 + 0.45 * q / 100.0))

    # Viewfinder frame
    frame:
        background None
        xysize (1700, 900)
        align (0.5, 0.45)
        add Solid("#ffffffcc") xysize (120, 4) align (0.0, 0.0)
        add Solid("#ffffffcc") xysize (4, 120) align (0.0, 0.0)
        add Solid("#ffffffcc") xysize (120, 4) align (1.0, 0.0)
        add Solid("#ffffffcc") xysize (4, 120) align (1.0, 0.0)
        add Solid("#ffffffcc") xysize (120, 4) align (0.0, 1.0)
        add Solid("#ffffffcc") xysize (4, 120) align (0.0, 1.0)
        add Solid("#ffffffcc") xysize (120, 4) align (1.0, 1.0)
        add Solid("#ffffffcc") xysize (4, 120) align (1.0, 1.0)

    # Light meter (right side)
    frame:
        align (0.96, 0.45)
        padding (14, 14)
        vbox:
            spacing 8
            text "LIGHT" size 22 xalign 0.5
            vbar value StaticValue(q, 100):
                xysize (36, 520)
                xalign 0.5
            text "[q:.0f]%" size 26 xalign 0.5

    frame:
        xalign 0.5
        ypos 14
        padding (24, 8)
        text "Shot [shot] / [total]" size 30

    textbutton "CAPTURE  (Space)":
        xalign 0.5
        yalign 0.97
        text_size 40
        padding (50, 18)
        action [Function(mp_capture, wave, start), Return(True)]
    key "K_SPACE" action [Function(mp_capture, wave, start), Return(True)]

    # Redraw continuously so the light keeps moving
    timer 0.03 repeat True action Function(renpy.restart_interaction)

# Every photo session now uses the free camera (masar_photo_free.rpy).
label photo_session(shots=3, difficulty=1.0):
    call photo_free_session(None)
    return _return

# The older light-wave mode (kept for reference, not used): several shots, the best one counts.
label photo_session_light(shots=3, difficulty=1.0):
    $ photo_bg = room_bg(location, room)
    $ scores = []
    $ photo_subject = "view"
    $ subj_list = mph.subjects_here(location, room)
    if subj_list:
        # rooms with named subjects (see ROOM_SUBJECTS in masar_phone.py): choose what to photograph
        call screen photo_subject(subj_list, location, room)
        if _return == "__cancel__":
            return "cancelled"
        $ photo_subject = _return

    if not photo_tutorial_done:
        scene expression photo_bg
        "Photography: the light keeps changing. Press CAPTURE (or Space) when it is at its best."
        "The match percentage is the light level at the moment you shoot. Above 50%% the photo helps your page. Below 50%% it hurts."
        $ photo_tutorial_done = True

    $ shot_no = 0
    while shot_no < shots:
        $ shot_no += 1
        $ wave = mp.LightWave(seed=renpy.random.randint(0, 1000000), speed=difficulty)
        call screen photo_shoot(wave, shot_no, shots, photo_bg)
        $ scores.append(shot_q)
        scene expression photo_bg with photo_flash
        "Shot [shot_no] of [shots]: [shot_q]%% match."

    if subj_list:
        # the photo goes to the phone gallery; clients pay for it in Snapjob
        call photo_save_result
    else:
        # an ordinary scenery photo: it goes to the gallery and also counts for the page numbers
        $ ph_save_room_photo("view", mp.session_result(scores))
        call photo_apply_result
    return "done"
