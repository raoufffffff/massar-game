# Inside a place: room background, numbered room tags at the bottom, minimap and Ana as a button.

init python:
    import face_layers
    import poses_data
    POSE_FACE = poses_data.POSE_FACE     # pose name -> key in face_layers.LAYERS
    POSE_RIGHT = poses_data.POSE_RIGHT
    POSE_AX = getattr(poses_data, "POSE_AX", {})
    POSE_ROOM = getattr(poses_data, "POSE_ROOM", {})
    def pose_xalign(pose):
        """Horizontal placement of her picture: from the pose's 'ax' in poses/*.json (centre x on the 1920 screen)."""
        if pose in POSE_AX:
            return max(0.0, min(1.0, (POSE_AX[pose] - 400) / 1120.0))
        return 1.0 if pose in POSE_RIGHT else 0.78
    mc.bg_exists = renpy.loadable           # lets mc.bg_path accept .png / .webp room pictures too
    mc.part_now = lambda: store.day_part     # room pictures change with the time of day (park_lake_night.jpg ...)
    import masar_phone as _mph_time
    _mph_time.part_now = mc.part_now               # subjects can exist at some times only

    ROOM_BASE_W = 1920
    _room_w_cache = {}
    def room_world_w(pid, rid):
        """Width of the room world in pixels (height is always 1080). 1920 for an ordinary room; a picture wider
        than 16:9 is a panoramic room: its height is fitted to 1080 and the rest of the width can be scrolled."""
        path = mc.bg_path(pid, rid)
        if path not in _room_w_cache:
            w = ROOM_BASE_W
            if renpy.loadable(path):
                try:
                    iw, ih = renpy.image_size(path)
                    ww = int(round(iw * 1080.0 / max(1, ih)))
                    if ww > ROOM_BASE_W + 20:
                        w = ww
                except Exception:
                    w = ROOM_BASE_W
            _room_w_cache[path] = w
        return _room_w_cache[path]

    def room_bg(pid, rid):
        """Room background (the whole panorama in a panoramic room); a black screen if the image does not exist."""
        path = mc.bg_path(pid, rid)
        if renpy.loadable(path):
            # scale to the room world so any source resolution fits
            return im.Scale(path, room_world_w(pid, rid), config.screen_height)
        return "#000000"

    def room_view_bg():
        """What the player sees of a panoramic room right now (the 1920 wide part of the picture the view is on).
        It is the scene behind dialogues: the scrolling screen itself is hidden while Ana talks."""
        return Fixed(Transform(room_bg(store.location, store.room), xpos=-int(store.room_vx)), xysize=(1920, 1080))

    def room_prepare():
        """Called every time a room is shown: its world width, and where the view starts when the player ENTERS it
        (moving around inside the same room keeps the view)."""
        store.room_w = room_world_w(store.location, store.room)
        key = (store.location, store.room)
        if store.room_view_key != key:
            store.room_view_key = key
            span = max(0, store.room_w - ROOM_BASE_W)
            store.room_home_x = int(span * mc.room_start(store.location, store.room)) if span else 0
            store.room_vx = store.room_home_x

    ROOM_ADJ = ui.adjustment()           # the horizontal scroll of a panoramic room (shared, not saved)
    ROOM_EDGE = 70.0                     # mouse within this many pixels of the left/right edge scrolls the view
    ROOM_EDGE_SPEED = 1000.0             # pixels per second at the very edge

    def room_tick():
        """Edge scrolling + remembering the view. Dragging and its inertia are done by the viewport itself."""
        now = renpy.get_game_runtime()
        dt = min(0.1, max(0.0, now - store.room_tick_t))
        store.room_tick_t = now
        try:
            dragging = renpy.display.focus.get_grab() is not None
        except Exception:
            dragging = False
        if not dragging and dt > 0:
            try:
                import pygame_sdl2
                inside = pygame_sdl2.mouse.get_focused()
            except Exception:
                inside = True
            mx, my = renpy.get_mouse_pos()
            # the screen edges next to the buttons (top and bottom corners) do not scroll
            if inside and 430 <= my <= 880 and 0 <= mx <= 1920:
                v = 0.0
                if mx < ROOM_EDGE:
                    v = -(ROOM_EDGE - mx) / ROOM_EDGE
                elif mx > 1920 - ROOM_EDGE:
                    v = (mx - (1920 - ROOM_EDGE)) / ROOM_EDGE
                if v:
                    ROOM_ADJ.change(ROOM_ADJ.value + v * ROOM_EDGE_SPEED * dt)
        if int(ROOM_ADJ.value) != store.room_vx:
            store.room_vx = int(ROOM_ADJ.value)

    def room_nudge(dx):
        """Arrow keys / A and D."""
        ROOM_ADJ.change(ROOM_ADJ.value + dx)
        store.room_vx = int(ROOM_ADJ.value)

    def room_arrow(st, at, side):
        """A soft arrow at the edge where the room can still be scrolled."""
        v, r = ROOM_ADJ.value, ROOM_ADJ.range
        if (side == "l" and v > 4) or (side == "r" and v < r - 4):
            return Text("<" if side == "l" else ">", size=96, color="#ffffffd0", font="fonts/Anton-Regular.ttf",
                        outlines=[(3, "#000000a0", 0, 2)]), 0.1
        return Null(), 0.1

    def room_bar(st, at):
        """Thin strip at the top: where the view is inside the whole width of a panoramic room."""
        if store.room_w <= ROOM_BASE_W:
            return Null(), 0.5
        total = 420
        w = max(12, int(total * ROOM_BASE_W / float(store.room_w)))
        x = int(total * max(0.0, ROOM_ADJ.value) / float(store.room_w))
        return Fixed(Solid("#ffffff38", xysize=(total, 7)), Solid("#ffd54a", xysize=(w, 7), xpos=min(x, total - w)),
                     xysize=(total, 7)), 0.05

    def ana_world_ax(ax):
        """Where Ana's centre is in the camera world. Ordinary room: the scene's own ax. Panoramic room: her
        schedule placement if she has one, else the scene's ax relative to where the view started."""
        if store.room_w <= ROOM_BASE_W:
            return ax
        ent = store.ana_look_entry
        at = (ent or {}).get("at")
        if at:
            return at["x"]
        return ax + store.room_home_x

    def ana_available_poses():
        """Names of the activity pictures that exist in the project."""
        return [n for n in mc.ALL_POSES if renpy.loadable("images/ana/pose_%s.png" % n)]

    def ana_room_images(pose, expr):
        """(idle picture, hover picture) of Ana in a room: her activity, or the standing sprite."""
        if pose and renpy.loadable("images/ana/pose_%s.png" % pose):
            idle = "images/ana/pose_%s.png" % pose
            glow = "images/ana/pose_%s_glow.png" % pose
            if pose in POSE_FACE:
                # she blinks while busy (needs the face layers of the pose, see tools/make_face_layers.py)
                idle = DynamicDisplayable(pose_blink, pose=pose)
            if renpy.loadable(glow):
                return idle, glow
            return idle, Transform(idle, matrixcolor=BrightnessMatrix(0.12))
        o = ana_outfit(expr)
        return "images/ana/ana_%s_%s.png" % (o, expr), "images/ana/ana_%s_%s_glow.png" % (o, expr)

    def pose_blink(st, at, pose):
        """Idle picture of a busy pose with natural blinking: the closed-eyes patch is laid over the open picture."""
        open_ = "images/ana/pose_%s.png" % pose
        total = sum(ANA_BLINK_GAPS) + ANA_BLINK_LEN * len(ANA_BLINK_GAPS)
        t = st % total
        acc = 0.0
        closed = False
        wait = 0.05
        for gap in ANA_BLINK_GAPS:
            if t < acc + gap:
                wait = max(0.02, acc + gap - t)
                break
            acc += gap
            if t < acc + ANA_BLINK_LEN:
                closed = True
                wait = max(0.02, acc + ANA_BLINK_LEN - t)
                break
            acc += ANA_BLINK_LEN
        if not closed:
            return renpy.displayable(open_), wait
        key = POSE_FACE.get(pose)
        patch = face_layers.LAYERS.get(key, {}).get("eyes", {}).get("closed") if key else None
        if patch is None:
            return renpy.displayable(open_), wait
        x, y, path = patch
        # patches are cut from the 1600x2160 picture; the room picture is 800x1080
        return Fixed(open_, Transform(path, zoom=0.5, xpos=int(x * 0.5), ypos=int(y * 0.5)),
                     xysize=(800, 1080)), wait

    import masar_data
    try:
        CHARS = masar_data.load("characters")["characters"]
    except Exception:
        CHARS = {}

    def ana_look():
        """(idle, hover, at-transform) for Ana in the room from her schedule entry (look + placement)."""
        ent = store.ana_look_entry
        look = (ent or {}).get("look", {})
        at = (ent or {}).get("at")
        mb = 0
        if look.get("type") == "char":
            e = CHARS.get(look.get("char"), {}).get("images", {}).get(look.get("image"))
            if e and renpy.loadable(e["file"]):
                idle, hover = e["file"], (e["glow"] if renpy.loadable(e["glow"]) else e["file"])
                mb = e.get("params", {}).get("margin", 48)
                at = at or {"x": 960 + store.room_home_x, "y": 1080, "scale": 950.0 / max(1, e["size"][1]), "flip": False}
                return idle, hover, ana_place_at(at["x"], at["y"], at.get("scale", 1.0), at.get("flip", False), mb)
        idle, hover = ana_room_images(store.ana_pose_name, store.ana_idle)
        if at:
            return idle, hover, ana_place_at(at["x"], at["y"], at.get("scale", 1.0), at.get("flip", False), 0)
        rv = POSE_ROOM.get(store.ana_pose_name)
        if rv:
            return idle, hover, ana_place(rv.get("x", 960) + store.room_home_x, rv.get("y", 1080), rv.get("scale", 1.0), rv.get("tint", "#ffffff"))
        if store.room_w > ROOM_BASE_W:
            # panoramic room: the same spot as in an ordinary room, relative to where the view starts
            cx = 400 + pose_xalign(store.ana_pose_name) * 1120 + store.room_home_x
            return idle, hover, ana_place_at(int(cx), 1080, 1.0, False, 0)
        return idle, hover, ana_pos_x(pose_xalign(store.ana_pose_name))

    def nav_font_size(name):
        n = len(name)
        return 30 if n <= 11 else (26 if n <= 14 else 22)

define NAV_FONT = "fonts/Anton-Regular.ttf"

default room_w = 1920                 # width of the room world (wider than 1920 = panoramic room)
default room_vx = 0                   # horizontal scroll of the view (panoramic rooms)
default room_home_x = 0               # where the view started when the player entered the room
default room_view_key = None
default room_tick_t = 0.0

# A panoramic room: the picture (and Ana) sit in a viewport. Drag with the mouse, push the mouse to the left/right edge,
# or use the arrow keys / A and D. The buttons and bars are drawn above it by room_nav and never move.
screen room_pano():
    viewport:
        xysize (1920, 1080)
        child_size (room_w, 1080)
        xadjustment ROOM_ADJ
        xinitial int(room_vx)
        draggable True
        mousewheel False
        fixed:
            xysize (room_w, 1080)
            add room_bg(location, room)
            if ana_here:
                $ ana_idle_img, ana_hover_img, ana_at = ana_look()
                imagebutton:
                    idle ana_idle_img
                    hover ana_hover_img
                    focus_mask True
                    at ana_at
                    action Return("__ana__")
    add DynamicDisplayable(room_bar) xalign 0.5 ypos 14
    add DynamicDisplayable(room_arrow, side="l") pos (26, 440)
    add DynamicDisplayable(room_arrow, side="r") xalign 1.0 xoffset -26 ypos 440
    timer 0.03 repeat True action Function(room_tick)
    key "K_LEFT" action Function(room_nudge, -260)
    key "K_RIGHT" action Function(room_nudge, 260)
    key "K_a" action Function(room_nudge, -260)
    key "K_d" action Function(room_nudge, 260)

screen room_nav(pid, current):
    $ rooms = mc.rooms_of(pid)
    $ n = len(rooms)
    $ tw = int(min(230, (1800 - 24 * (n - 1)) / n))
    $ here = mc.BY_ID[pid]

    # Ana is a button: click her to chat. A soft glow follows the outline of her body on hover.
    # (In a panoramic room she lives inside the scrolling view instead.)
    if room_w > 1920:
        use room_pano
    elif ana_here:
        $ ana_idle_img, ana_hover_img, ana_at = ana_look()
        imagebutton:
            idle ana_idle_img
            hover ana_hover_img
            focus_mask True
            at ana_at
            action Return("__ana__")

    # Developer notice: the room picture is missing (the room is black), with the exact name the game looks for
    $ bg_file_name = mc.bg_path(pid, current)
    if not renpy.loadable(bg_file_name):
        text "Missing room picture: [bg_file_name]" size 22 color "#ff6a6a" xalign 0.5 ypos 20

    # Where am I, and when
    frame:
        background Frame("images/ui/panel.png", 24, 24)
        pos (20, 20)
        padding (24, 12)
        vbox:
            spacing 2
            text "[place_title]  /  [room_title]" font NAV_FONT size 30 color "#ffffff"
            text "Day [day]  -  [time_name]      $[phone.money]      Followers [followers]" size 22 color "#d0d4e0"

    # Phone (bottom left, P)
    use phone_button

    # Pass time without moving (T)
    textbutton "Pass time (T)":
        pos (20, 120)
        text_size 26
        action Return("__wait__")
    key "K_t" action Return("__wait__")

    # Activities of this room (see ROOM_ACTIONS in masar_gym.py), under "Pass time"
    $ acts = gym.actions_here(pid, current)
    if acts:
        vbox:
            pos (20, 180)
            spacing 6
            for act_label, act_title in acts:
                textbutton act_title:
                    text_size 26
                    action Return("__act__" + act_label)

    # Minimap (top right): click to open the city map
    button:
        pos (1600, 20)
        padding (4, 4)
        background Solid("#ffffff")
        hover_background Solid("#ffd54a")
        action Return("__map__")
        fixed:
            xysize (300, 167)
            add im.Scale(map_image(), 300, 167)
            add Solid("#ff3b6b") pos (int(here.fx * 300) - 6, int(here.fy * 167) - 6) xysize (12, 12)
            text "MAP  (M)" font NAV_FONT size 22 color "#ffffff" outlines [(2, "#000000", 0, 1)] xpos 8 yalign 1.0 yoffset -6

    # Photo spot: camera icon under the minimap
    if photo_spot:
        vbox:
            pos (1816, 210)
            spacing 2
            imagebutton:
                idle "images/ui/cam_icon.png"
                hover "images/ui/cam_icon_hover.png"
                action Return("__photo__")
            text "PHOTOS" font NAV_FONT size 20 color "#ffffff" outlines [(2, "#000000", 0, 1)] xalign 0.5

    # Room tags, numbered like the keyboard shortcuts
    hbox:
        xalign 0.5
        ypos 905
        spacing 24
        for i, room in enumerate(rooms):
            $ rid = room[0]
            $ rname = room[1].upper()
            fixed:
                xysize (tw, 150)
                button:
                    xalign 0.5
                    ypos 46
                    xysize (tw, 92)
                    background Frame("images/ui/nav_tag.png", 28, 22, 28, 28)
                    hover_background Frame("images/ui/nav_tag_hover.png", 28, 22, 28, 28)
                    insensitive_background Frame("images/ui/nav_tag_current.png", 28, 22, 28, 28)
                    sensitive (rid != current)
                    action (Return(rid) if mc.room_open(pid, rid, day_part) else Notify(mc.closed_text(pid, rid, day_part)))
                    text rname:
                        font NAV_FONT
                        size nav_font_size(rname)
                        color (("#ffffff" if mc.room_open(pid, rid, day_part) else "#8a8a9a") if rid != current else "#3a2200")
                        outlines ([(3, "#3a0a18", 0, 2)] if rid != current else [])
                        align (0.5, 0.62)
                add "images/ui/nav_num.png" xalign 0.5 ypos 0
                text str(i + 1) font NAV_FONT size 36 color "#111111" xalign 0.5 ypos 10

    for i, room in enumerate(rooms):
        if room[0] != current:
            key ("K_%d" % (i + 1)) action (Return(room[0]) if mc.room_open(pid, room[0], day_part) else Notify(mc.closed_text(pid, room[0], day_part)))
    key "K_m" action Return("__map__")
