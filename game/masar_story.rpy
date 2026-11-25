# Masar story: Ana's love, the day ledger and the end-of-day report.
# Logic: masar_story.py (pure Python).  Numbers and rules: game/data/story.json.  Test without the game: python tools/masar_sim.py

init python:
    import masar_story as mst

default story = mst.Story()

init 10 python:
    def story_end_of_day(old_day):
        """The clock just passed from Night to the next Morning: review the day that finished."""
        try:
            store.story.end_of_day(old_day, store.phone)
        except Exception:
            import traceback
            traceback.print_exc()
            renpy.notify("Story engine error: see traceback.txt")

    # Every place in the game moves time with mc.advance_time(day, part): wrap it once, so the end of the
    # day is noticed in one place (the guard avoids wrapping twice when the scripts are reloaded).
    if not getattr(mc.advance_time, "_story_hook", False):
        _story_adv_orig = mc.advance_time

        def _story_adv(day, part):
            nd, np = _story_adv_orig(day, part)
            if nd != day:
                story_end_of_day(day)
            return nd, np

        _story_adv._story_hook = True
        _story_adv._orig = _story_adv_orig
        mc.advance_time = _story_adv

    def story_dev_next_day():
        """Developer shortcut (F9 menu): jump to the last slot of today; the button then passes the final slot."""
        d, p = store.day, store.day_part
        orig = getattr(mc.advance_time, "_orig", mc.advance_time)
        while p < 3:
            d, p = orig(d, p)
        store.day, store.day_part = d, p
        store.time_name = mc.TIME_NAMES[p]

    def story_dev_pay_rent():
        ok, text = store.story.pay_rent(store.phone, store.day, store.day_part)
        renpy.notify(text)

    def story_dev_gate():
        g = store.story.next_gate()
        if g is None:
            renpy.notify("No gate left.")
        else:
            store.story.cross_gate(g, store.day, store.day_part)
            renpy.notify("Gate %d crossed (love = %d)." % (g, store.story.love))

    def story_dev_log(event):
        store.story.log(event, store.day, store.day_part)
        renpy.notify("Logged: %s (day %d)" % (event, store.day))

    def story_actions(pid, rid):
        """Extra actions the story adds to a room (shown under 'Pass time'): (label, title) pairs."""
        out = []
        if pid == "home" and rid == "kitchen" and not store.story.count("dishes_done", store.day):
            out.append(("act_dishes", "Wash the dishes"))
        return out

    config.overlay_screens.append("story_dev_keys")

# Washing the dishes: costs the time slot (script.rpy passes it), written into the day ledger.
# At the end of the day love +1 (if love < 20); skipping it costs -1 while Ana has fewer than 500 followers.
label act_dishes:
    $ story.log("dishes_done", day, day_part)
    if ana_here:
        if room_w > 1920:
            scene expression room_view_bg()
        show ana smile at ana_pos
        with dissolve
        ana "Oh, you don't have to... but thank you, dear."
    "You wash the dishes while the kitchen fills with warm light. It takes a while, but the sink is empty at last."
    hide ana
    return

# The end-of-day report (shown when the player is back in a room or on the map).
screen day_report(rep):
    modal True
    zorder 200
    add Solid("#000000b8")
    frame:
        align (0.5, 0.5)
        xsize 780
        padding (40, 30)
        background Solid("#10172af0")
        vbox:
            spacing 12
            text ("Day %d is over" % rep["day"]) size 36 color "#ffffff"
            null height 4
            if not rep["lines"]:
                text "Nothing special happened between you and Ana." size 24 color "#aab4cc"
            for label, v in rep["lines"]:
                if rep["show_numbers"] and v:
                    text ("%s   %+d" % (label, v)) size 24 color ("#9be28f" if v > 0 else "#ff8f8f")
                else:
                    text label size 24 color "#d6dcec"
            if rep["show_numbers"]:
                text ("Ana's love: %d  >  %d" % (rep["love_before"], rep["love_after"])) size 26 color "#ffd36b"
            if rep["capped"]:
                text "Her feelings cannot grow further until something changes between you." size 20 color "#8a93a8"
            for sender, txt in rep["messages"]:
                text ("New message from %s" % sender) size 20 color "#8ec5ff"
            if rep["ended"]:
                null height 6
                text rep["end_message"] size 24 color "#ffd36b"
            null height 10
            textbutton "Continue" action [Function(story.dismiss), Return()] text_size 28 xalign 1.0

# Developer menu: press F9 anywhere (turn it off with "dev_tools": false in game/data/story.json).
screen story_dev_keys():
    if mst.rules().get("dev_tools"):
        key "K_F9" action ToggleScreen("story_dev")

screen story_dev():
    zorder 190
    frame:
        xalign 0.01
        yalign 0.12
        padding (16, 12)
        background Solid("#0a0f1ccc")
        vbox:
            spacing 6
            text "STORY DEV   (F9 closes)" size 20 color "#ffd36b"
            text ("Day %d  %s   love %d   cap %d" % (day, time_name, story.love, story.cap())) size 18
            text ("Money $%d   rent due today: $%d" % (phone.money, story.rent_due(day))) size 18
            text ("Gates crossed: %s   next: %s" % (sorted(story.gates_crossed), story.next_gate())) size 18
            textbutton "Log: played the talk game" action Function(story_dev_log, "talk_game") text_size 18
            textbutton "Log: washed the dishes" action Function(story_dev_log, "dishes_done") text_size 18
            textbutton "Pay the rent" action Function(story_dev_pay_rent) text_size 18
            textbutton "+ $100" action Function(phone.pay, 100, "Developer money", day, day_part) text_size 18
            textbutton "Story quest: cross the next gate" action Function(story_dev_gate) text_size 18
            textbutton "Finish today (see the report)" action [Function(story_dev_next_day), Return("__wait__")] text_size 18
