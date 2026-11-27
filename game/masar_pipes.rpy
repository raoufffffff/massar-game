# Pipe repair mini-game (first barrier challenge: the kitchen pipes).  Rules: masar_pipes.py.  Pictures and layout: game/data/pipes.json,
# made by  python tools/make_pipe_scene.py  (pieces cut from raw_pipes/pieces_sheet.jpg, wall from raw_pipes/kitchen_bg_src.jpg).
#
# The player clicks a piece in the tray, then the shadow where it fits.  A wrong shadow does not take it.  No timer: he plays at ease and may
# leave and come back (the placed pieces are kept in pipe_state).
#
# Call it with:   call minigame_pipes("kitchen")      -> returns "done" (repaired) or "abort" (the player left; nothing is lost)

init python:
    import masar_pipes as mpipe

    def pipe_pick(pid):
        store.pipe_game.select(pid)

    def pipe_slot(sid):
        g = store.pipe_game
        r = g.click_slot(sid)
        if g.done:
            return "done"

default pipe_game = None
default pipe_spec = None
default pipe_state = {}

transform pipe_pulse:
    alpha 0.5
    linear 0.6 alpha 1.0
    linear 0.6 alpha 0.5
    repeat

screen pipes_play():
    modal True
    $ g = pipe_game
    $ tray = pipe_spec["tray"]
    $ hint = g.hint_slot()
    add pipe_spec["bg"]

    # what is already in place
    for p in pipe_spec["pieces"]:
        if p["id"] in g.placed:
            add p["image"] xpos p["x"] ypos p["y"]

    # the shadows (only where nothing is placed): click one with a piece in hand
    for p in pipe_spec["pieces"]:
        if p["id"] not in g.placed:
            $ pipe_hot = (g.flash == p["id"])
            imagebutton:
                xpos p["x"]
                ypos p["y"]
                focus_mask True
                idle (Transform(p["shadow"], matrixcolor=TintMatrix("#ff6a5a")) if pipe_hot else Transform(p["shadow"], alpha=0.9))
                hover Transform(p["shadow"], matrixcolor=BrightnessMatrix(0.3))
                action Function(pipe_slot, p["id"])
            if hint == p["id"]:
                add Transform(p["shadow"], matrixcolor=TintMatrix("#7fe0ff")) xpos p["x"] ypos p["y"] at pipe_pulse

    # the tray with the pieces that are still loose
    frame:
        xpos tray["x"] - 24
        ypos tray["y"] - 24
        xysize (tray["w"] + 48, tray["h"] + 48)
        background Solid("#ffffff30")
    for p in pipe_spec["pieces"]:
        if p["id"] not in g.placed:
            $ pipe_on = (g.selected == p["id"])
            if pipe_on:
                add Solid("#ffffff55") xpos p["tray"][0] - 8 ypos p["tray"][1] - 8 xysize (int(p["w"] * tray["zoom"]) + 16, int(p["h"] * tray["zoom"]) + 16)
            imagebutton:
                xpos p["tray"][0]
                ypos p["tray"][1]
                focus_mask True
                idle Transform(p["image"], zoom=tray["zoom"], matrixcolor=BrightnessMatrix(0.25 if pipe_on else 0.0))
                hover Transform(p["image"], zoom=tray["zoom"], matrixcolor=BrightnessMatrix(0.15))
                action Function(pipe_pick, p["id"])

    # words
    $ pipe_done_n, pipe_all_n = g.progress()
    text pipe_spec["title"] font NAV_FONT size 46 color "#2b2f3a" xalign 0.5 ypos 22
    text (g.message or "Pick a piece from the tray, then click the shadow where it fits.") size 30 color "#2b2f3a" xalign 0.5 ypos 84
    text "Pieces in place: [pipe_done_n] / [pipe_all_n]" size 26 color "#2b2f3a" xpos tray["x"] ypos tray["y"] - 62
    textbutton "Leave it for now" xpos 40 ypos 40 text_size 28 action Return("leave")
    key "game_menu" action Return("leave")

screen pipes_win():
    modal True
    add pipe_spec["bg"]
    for p in pipe_spec["pieces"]:
        add p["image"] xpos p["x"] ypos p["y"]
    text "The leak stops." font NAV_FONT size 56 color "#2b2f3a" xalign 0.5 ypos 40
    text "Water runs through the pipe again.   (click)" size 28 color "#2b2f3a" xalign 0.5 ypos 112
    key "dismiss" action Return()

label minigame_pipes(name="kitchen"):
    $ pipe_spec = mpipe.load_game(name)
    if not pipe_spec:
        "There is nothing to fix here."
        return "done"
    $ pipe_game = mpipe.PipeGame(name, list(pipe_state.get(name, [])))
    scene black
    with Dissolve(0.3)
    call screen pipes_play
    $ pipe_res = _return
    $ pipe_state[name] = list(pipe_game.placed)
    if pipe_res == "done":
        call screen pipes_win
        $ pipe_state.pop(name, None)
        return "done"
    return "abort"
