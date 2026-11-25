# Interactive city map - relies on masar_core.py

init -1 python:
    import masar_core as mc
    import map_shapes as ms

define MAP_W = 1920
define MAP_H = 1072
define MAP_TOP = 4

init python:
    def map_image():
        """Map image by time of day; falls back to the day map if no night map exists."""
        if mc.is_night(store.day_part) and renpy.loadable("images/map_night.jpg"):
            return "images/map_night.jpg"
        return "images/map_day.jpg"

screen city_map():
    modal True

    add map_image() xysize (MAP_W, MAP_H) ypos MAP_TOP fit "fill"

    # Place buttons: each place is its own shape. Hover = glow around the building itself.
    for p in mc.PLACES:
        $ ok = mc.can_enter(unlocked, p.id, day_part)
        $ closed_msg = "" if ok else mc.closed_text(p.id, None, day_part, unlocked)
        $ px = int(p.fx * MAP_W)
        $ py = int(p.fy * MAP_H) + MAP_TOP
        $ shp = ms.SHAPES.get(p.id)

        if shp:
            imagebutton:
                xpos shp[0]
                ypos shp[1] + MAP_TOP
                idle ("images/map/%s_%s.png" % (mc.map_art(p.id), "idle" if ok else "lock"))
                hover ("images/map/%s_%s.png" % (mc.map_art(p.id), "hover" if ok else "lock"))
                focus_mask True
                action (Return(p.id) if ok else Notify(closed_msg))
                tooltip p.name
        else:
            button:
                xpos px
                ypos py
                anchor (0.5, 0.5)
                xysize (150, 110)
                background (None if ok else Solid("#00000066"))
                hover_background (Solid("#ffffff44") if ok else Solid("#00000066"))
                action (Return(p.id) if ok else Notify(closed_msg))
                tooltip p.name

        if ok:
            text "{size=22}{color=#ffd54a}*{/color}{/size}" xpos px ypos py anchor (0.5, 0.5)

    # Back to where I was (no time passes)
    textbutton "Back":
        xpos 20
        ypos 14
        text_size 32
        action Return("__back__")
    key "K_m" action Return("__back__")
    key "K_ESCAPE" action Return("__back__")

    # Top bar: day and time
    frame:
        xalign 0.5
        ypos 14
        padding (24, 8)
        text "Day [day] - [time_name]      $[phone.money]" size 30

    # Phone (bottom left, P)
    use phone_button

    # Pass time from anywhere (T)
    textbutton "Pass time (T)":
        xalign 0.98
        ypos 130
        text_size 28
        action Return("__wait__")
    key "K_t" action Return("__wait__")

    # Place name on hover
    $ tip = GetTooltip()
    if tip:
        frame:
            xalign 0.5
            yalign 0.97
            padding (28, 10)
            text tip size 34
