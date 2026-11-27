# Masar - entry point (map + rooms)

default day = 1
default day_part = 0
default time_name = "Morning"
default location = "home"
default room = "outside"
default unlocked = list(mc.PART1_UNLOCKED)
default bg_last = (None, -1)

label start:
    scene black
    "Masar - map and rooms prototype."
    "Click the minimap (top right) or press M to open the city map. Move between rooms with the numbered tags or the number keys. Click Ana to talk to her."
    jump city_loop

label city_loop:
    scene black
    # the end-of-day report (Ana's love, rent...) is shown once, as soon as the player is back at the map or in a room
    if story.pending:
        call screen day_report(story.pending)
    $ flush_notes()
    call screen city_map
    if _return == "__back__":
        # Closed the map without travelling: no time passes
        jump place_loop
    if _return == "__wait__":
        $ day, day_part = mc.advance_time(day, day_part)
        $ time_name = mc.TIME_NAMES[day_part]
        jump city_loop
    # Travelling does not cost time: only the "Pass time" button, photo sessions and similar actions do
    $ location = _return
    $ room = mc.first_room(location)
    jump place_loop

label place_loop:
    if story.pending:
        call screen day_report(story.pending)
    $ flush_notes()
    # Opening hours: when time passes and this place (or room) closes, the player is sent out with a message
    if not mc.place_open(location, day_part):
        $ closed_note = mc.closed_text(location, None, day_part)
        $ room_view_key = None
        "[closed_note]"
        jump city_loop
    if not mc.room_open(location, room, day_part):
        $ closed_note = mc.closed_text(location, room, day_part)
        $ room = mc.first_open_room(location, day_part)
        $ room_view_key = None
        "[closed_note]"
        if room is None:
            jump city_loop
    $ place_title = mc.BY_ID[location].name
    $ room_title = mc.room_name(location, room)
    $ room_prepare()
    # the picture changes with the time of day: a soft dissolve when time passed while staying in the same room
    $ bg_fade = dissolve if (bg_last[0] == (location, room) and bg_last[1] != day_part) else None
    $ bg_last = ((location, room), day_part)
    if room_w > 1920:
        scene expression room_view_bg() with bg_fade     # the screen room_pano draws the scrolling picture over it
    else:
        scene expression room_bg(location, room) with bg_fade
    $ ana_here = mc.ana_is_here(day, day_part, location, room)
    $ photo_spot = mc.is_photo_spot(location, room)
    $ ana_pose_name = mc.ana_pose(day, day_part, location, room, ana_available_poses()) if ana_here else None
    $ ana_look_entry = mc.ana_entry(day, day_part) if ana_here else None
    # Room events if defined: a label named  room_<place>_<room>
    if renpy.has_label("room_" + location + "_" + room):
        call expression ("room_" + location + "_" + room)
    call screen room_nav(location, room)
    if _return == "__map__":
        jump city_loop
    if _return == "__wait__":
        $ day, day_part = mc.advance_time(day, day_part)
        $ time_name = mc.TIME_NAMES[day_part]
        jump place_loop
    if _return == "__ana__":
        call ana_click
        if _return == "photo":
            call photo_session_ana
            # A session costs one time slot, unless the player left without shooting
            if _return != "cancelled":
                $ day, day_part = mc.advance_time(day, day_part)
                $ time_name = mc.TIME_NAMES[day_part]
        elif _return == "talkgame":
            # the talk game takes one time slot (win or lose)
            $ day, day_part = mc.advance_time(day, day_part)
            $ time_name = mc.TIME_NAMES[day_part]
        elif _return == "talkgame_photo":
            # a won talk game, then she agreed to a photo: the talk takes a slot, the session another
            $ day, day_part = mc.advance_time(day, day_part)
            $ time_name = mc.TIME_NAMES[day_part]
            call photo_session_ana
            if _return != "cancelled":
                $ day, day_part = mc.advance_time(day, day_part)
                $ time_name = mc.TIME_NAMES[day_part]
        jump place_loop
    if _return == "__rent__":
        # the player pays Ana's rent (only offered on a Monday, see story.rent_due)
        $ rent_ok, rent_text = story.pay_rent(phone, day, day_part)
        $ renpy.notify(rent_text)
        $ flush_notes()
        jump place_loop
    if _return.startswith("__act__quest:"):
        # an action of a quest step (see game/data/quests.json); costs a slot unless it returns "cancelled"
        $ quest_ids = _return[13:].split(":")
        call quest_action(quest_ids[0], int(quest_ids[1]))
        if _return != "cancelled":
            $ day, day_part = mc.advance_time(day, day_part)
            $ time_name = mc.TIME_NAMES[day_part]
        jump place_loop
    if _return.startswith("__act__"):
        # An activity of the room (mini-game): costs one time slot unless it returns "cancelled"
        $ act_label = _return[7:]
        call expression act_label
        $ player_after_act(act_label)
        $ flush_notes()
        if _return != "cancelled":
            $ day, day_part = mc.advance_time(day, day_part)
            $ time_name = mc.TIME_NAMES[day_part]
        jump place_loop
    if _return == "__photo__":
        call photo_session
        # A photo session costs one time slot, unless the player cancelled before shooting
        if _return != "cancelled":
            $ day, day_part = mc.advance_time(day, day_part)
            $ time_name = mc.TIME_NAMES[day_part]
        jump place_loop
    $ room = _return
    jump place_loop
