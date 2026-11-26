# Quests, the player's numbers, the bag and shops: the Ren'Py side.
# Logic (pure Python, tested without the game): masar_quests.py, masar_player.py, masar_shops.py.
# Data you can edit: game/data/quests.json, player.json, shops.json.  Check them with: python tools/test_quests.py

init python:
    import masar_quests as mq
    import masar_player as mpl
    import masar_shops as mshop

default player = mpl.Player()
default quests = mq.Quests()
default note_queue = []

define you = Character("You", color="#9ec5ff")

init 10 python:
    def quests_ctx():
        return mq.make_ctx(store.story, store.player, store.phone)

    def quests_check():
        """Finish quests whose steps are all done, announce new ones.  Returns texts to show."""
        try:
            return store.quests.check(quests_ctx, store.story, store.phone, store.day, store.day_part)
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    def note(text):
        """Queue a short text (like 'Charisma +1') for the next flush_notes()."""
        if text:
            store.note_queue.append(text)

    def flush_notes():
        """Show everything that just changed as one notification: love, stats, quests."""
        out = list(store.story.pop_notes())
        out += store.note_queue
        store.note_queue = []
        out += quests_check()
        out += store.story.pop_notes()
        if out:
            renpy.notify("\n".join(out))

    # gym games that train the player: label -> variable holding their points (0..10)
    GYM_TRAINING = {"gym_bench_press": "bench_points", "gym_run_player": "run_points"}

    def player_after_act(act_label):
        var = GYM_TRAINING.get(act_label)
        if var:
            note(store.player.training(getattr(store, var, 0)))

    def quest_actions_here(pid, rid, who):
        return store.quests.actions(quests_ctx(), pid, rid, who)

    def quest_ana_option():
        """The quest choice shown when clicking Ana here: (quest id, step index, title) or None."""
        acts = quest_actions_here(store.location, store.room, "ana")
        if not acts:
            return None
        parts = acts[0][0].split(":")
        return parts[1], int(parts[2]), acts[0][1]

# Runs the action of a quest step.  Returns "cancelled" when no time should pass (failed, or the step costs no time).
label quest_action(qid, idx):
    $ qa = mq.Quests.action_of(qid, int(idx)) or {}
    $ qa_ok, qa_text = store.quests.action_check(qa, quests_ctx())
    if not qa_ok:
        "[qa_text]"
        return "cancelled"
    if qa.get("label") and renpy.has_label(qa["label"]):
        call expression qa["label"]
    if qa.get("flag"):
        $ quests.set_flag(qa["flag"])
    $ flush_notes()
    if qa.get("time", 1) == 0:
        return "cancelled"
    return "done"

# --- the Plumber (quest ana_plumber)
label quest_plumber_ask:
    show ana neutral at ana_pos
    you "Is something wrong? You look worried."
    show ana sad
    ana "Oh... it is nothing, dear. The pipes under the kitchen sink are broken. Water everywhere."
    ana "A plumber would cost a fortune, and with the divorce... well. I will manage."
    show ana neutral
    you "(Maybe I can fix it myself. I just need the right tools.)"
    return

label quest_plumber_fix:
    scene black with dissolve
    "You lie under the sink with your new toolkit. It is harder than you thought, but slowly the leak stops."
    if room_w > 1920:
        scene expression room_view_bg() with dissolve
    else:
        scene expression room_bg(location, room) with dissolve
    show ana surprised at ana_pos
    ana "It... it does not leak anymore? You fixed it yourself?"
    show ana smile
    ana "Thank you. Really. Nobody has done something like this for me in a long time."
    hide ana
    return

# --- shops: a room with an entry in game/data/shops.json shows the action "Shop"
label act_shop:
    $ shop_def = mshop.shop_at(location, room)
    if not shop_def:
        return "cancelled"
    $ shop_greeting = shop_def["greeting"]
    "[shop_greeting]"

label .loop:
    call screen shop_screen(shop_def)
    if _return == "leave":
        return "cancelled"
    $ shop_iid, shop_price = _return
    $ shop_ok, shop_text = mshop.buy(player, phone, shop_iid, shop_price, day, day_part)
    $ renpy.notify(shop_text)
    $ flush_notes()
    jump .loop

screen shop_screen(shop_def):
    modal True
    zorder 150
    add Solid("#000000b0")
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        align (0.5, 0.5)
        padding (50, 36)
        xsize 900
        vbox:
            spacing 14
            text shop_def["title"] font NAV_FONT size 52 color "#ffffff" xalign 0.5
            text ("Your money: $%d" % phone.money) size 28 color "#7dffa0" xalign 0.5
            null height 6
            for shop_row in shop_def["items"]:
                $ shop_it = mshop.item(shop_row["id"])
                $ shop_owned = shop_it.get("unique") and player.has(shop_row["id"])
                frame:
                    background Solid("#1d2333")
                    xfill True
                    padding (20, 14)
                    hbox:
                        spacing 20
                        vbox:
                            xsize 560
                            text shop_it["name"] size 30 color "#ffffff"
                            text shop_it.get("text", "") size 20 color "#aab2c8" xsize 540
                        if shop_owned:
                            text "Owned" size 28 color "#8a93a8" yalign 0.5
                        else:
                            textbutton ("Buy  $%d" % shop_row["price"]):
                                yalign 0.5
                                text_size 30
                                sensitive phone.money >= shop_row["price"]
                                action Return((shop_row["id"], shop_row["price"]))
            null height 8
            textbutton "Leave" xalign 0.5 text_size 34 action Return("leave")
    key "game_menu" action Return("leave")
