# Ana: sprites, character definition, placement, and a test conversation

define ana = Character("Ana", color="#e8b4a0")

# Casual (housewife) outfit. Add new outfits the same way: image ana <outfit> <expression>
# Each expression blinks by itself when a closed-eyes picture exists:
#   images/ana/ana_casual_<expression>_blink.png   (optional; without it she simply does not blink)
init python:
    ANA_BLINK_GAPS = [3.4, 2.6, 4.8, 3.1, 5.2, 2.9]    # seconds between blinks (cycled)
    ANA_BLINK_LEN = 0.12                                # how long the eyes stay closed

    def ana_outfit(expr):
        """Apron (casual) only in the kitchen; the apron-less set (plain) everywhere else.
        Falls back to casual when a plain picture of that expression does not exist."""
        if not (store.location == "home" and store.room == "kitchen"):
            if renpy.loadable("images/ana/ana_plain_%s.png" % expr):
                return "plain"
        return "casual"

    def ana_blink(st, at, expr):
        o = ana_outfit(expr)
        open_ = "images/ana/ana_%s_%s.png" % (o, expr)
        closed = "images/ana/ana_%s_%s_blink.png" % (o, expr)
        if not renpy.loadable(closed):
            return renpy.displayable(open_), None
        total = sum(ANA_BLINK_GAPS) + ANA_BLINK_LEN * len(ANA_BLINK_GAPS)
        t = st % total
        acc = 0.0
        for gap in ANA_BLINK_GAPS:
            if t < acc + gap:
                return renpy.displayable(open_), max(0.02, acc + gap - t)
            acc += gap
            if t < acc + ANA_BLINK_LEN:
                return renpy.displayable(closed), max(0.02, acc + ANA_BLINK_LEN - t)
            acc += ANA_BLINK_LEN
        return renpy.displayable(open_), 0.05

image ana neutral   = DynamicDisplayable(ana_blink, expr="neutral")
image ana smile     = DynamicDisplayable(ana_blink, expr="smile")
image ana sad       = DynamicDisplayable(ana_blink, expr="sad")
image ana angry     = DynamicDisplayable(ana_blink, expr="angry")
image ana shy       = DynamicDisplayable(ana_blink, expr="shy")
image ana surprised = DynamicDisplayable(ana_blink, expr="surprised")

# Right of centre so the bottom room bar does not hide her face.
# She breathes: a slow, tiny stretch from her feet (chest rising and falling).
transform ana_pos:
    subpixel True
    xalign 0.78
    yalign 1.0
    block:
        ease 2.0 yzoom 1.012
        ease 2.0 yzoom 1.0
        repeat

transform ana_pos_x(xa=0.78):
    subpixel True
    xalign xa
    yalign 1.0
    block:
        ease 2.0 yzoom 1.012
        ease 2.0 yzoom 1.0
        repeat

# Ana placed INTO the scene (room view only): feet at screen (px, py), shrunk by 's', optional colour tint
# so she blends with the place. The photo mode is not affected.
# Same, placed from the schedule editor: feet at (px, py), scale s, optional mirror, mb = transparent margin under the feet
transform ana_place_at(px=960, py=1080, s=1.0, flip=False, mb=0):
    subpixel True
    anchor (0.5, 1.0)
    pos (px, int(py + mb * s))
    zoom s
    xzoom (-1.0 if flip else 1.0)
    block:
        ease 2.0 yzoom 1.012
        ease 2.0 yzoom 1.0
        repeat

transform ana_place(px=960, py=1080, s=1.0, tint="#ffffff"):
    subpixel True
    anchor (0.5, 1.0)
    pos (px, py)
    zoom s
    matrixcolor TintMatrix(tint)
    block:
        ease 2.0 yzoom 1.012
        ease 2.0 yzoom 1.0
        repeat

default ana_here = False
default ana_pose_name = None     # activity picture she is doing in this room (cooking, phone ...), or None
default ana_look_entry = None    # her schedule entry right now (look + placement), see game/data/schedule.json
default ana_idle = "neutral"      # expression she shows when idle in a room (a mood system will set it later)
default ana_clicks = 0

# Placeholder conversation that tests every expression
label ana_talk:
    show ana neutral at ana_pos
    ana "Oh! It's you. Good morning."
    show ana smile
    ana "I was just testing a new recipe. Do you want to taste it?"
    show ana shy
    ana "Sorry, I must look a mess today..."
    show ana surprised
    ana "Wait. You want to take photos of my cooking?"
    show ana sad
    ana "Nobody has ever offered to do that for me."
    show ana angry
    ana "And if you call me 'aunty' again, I'm raising your rent."
    show ana smile
    ana "(Placeholder dialogue to test the six expressions.)"
    show ana neutral
    return


# The player clicked on Ana: a light greeting, then what to do.
# Returns "talk", "photo" or "none".
label ana_click:
    $ ana_clicks += 1
    if room_w > 1920:
        # panoramic room: the dialogue background is the part of the picture the player was looking at
        scene expression room_view_bg()
    show ana smile at ana_pos
    with dissolve
    $ ana_greet = mc.ana_greeting(day, day_part, location, room, ana_clicks)
    ana "[ana_greet]"
    # (the photo choice is offered after a won talk game once gate 15 is crossed: ana_photo_offer)
    $ pose_opts = mp.poses_here(location, room, ana_available_poses())
    # a quest may add one choice here (e.g. "Is something wrong?")
    $ qa_choice = quest_ana_option()
    $ qa_opt = qa_choice is not None
    $ qa_qid, qa_idx, qa_title = qa_choice if qa_opt else ("", 0, "")
    menu:
        "Let's talk":
            call ana_talk
            return "talk"
        "[qa_title]" if qa_opt:
            call quest_action(qa_qid, qa_idx)
            return "talk"
        "Have a real conversation (talk game)" if not story.talked_today("ana", day):
            call talk_game("ana")
            # after gate 15, a WON talk game puts her in a good mood: she may allow a photo
            if talk_s.success and story.photo_unlocked():
                call ana_photo_offer(pose_opts)
                if _return == "photo":
                    return "talkgame_photo"
            return "talkgame"
        "Never mind.":
            ana "Okay. See you around."
            return "none"


# After a won talk game (gate 15 crossed): Ana is in a good mood and may allow a photo.  Returns "photo" or "none".
label ana_photo_offer(opts):
    if not opts:
        return "none"
    if room_w > 1920:
        scene expression room_view_bg()
    else:
        scene expression room_bg(location, room)
    show ana smile at ana_pos
    with dissolve
    ana "That was a lovely talk. I am in a good mood today."
    menu:
        "Ana, can I take your photo?":
            show ana shy
            ana "Sure... but please don't make me look silly."
            if len(opts) > 1:
                ana "What do you have in mind?"
                $ pose_pick = renpy.display_menu([(t, p) for p, t in opts] + [("Never mind.", None)])
                if pose_pick is None:
                    show ana neutral
                    ana "Okay. Another time."
                    return "none"
            else:
                $ pose_pick = opts[0][0]
            if pose_pick != ana_pose_name:
                ana "Give me a second to get ready."
            $ ana_pose_name = pose_pick
            return "photo"
        "Not now.":
            show ana neutral
            ana "Okay. Another time."
            return "none"
