MASAR EDITOR
============
Run from the project folder (the one with game/ and tools/):

    python tools/masar_editor.py

Nothing is written until you press Save (Ctrl+S). Every save copies the old file to game/data/_backup/.
The content lives in two plain JSON files you can also open in a text editor:
    game/data/snapjob.json       subjects, rooms, Snapjob gigs, levels, categories
    game/data/ana_regions.json   the boxes around Ana's body parts for each photo scene

ADD A THING TO PHOTOGRAPH (e.g. a crocodile at the lake)
  1. Subjects tab -> pick the room -> "New subject" -> drag a rectangle around it on the picture -> name + category.
  2. Gigs tab -> fill the form (subject, title, client, reward, level) -> "Add as new gig".
  3. Save. Start the game.

ADD A LEVEL: Levels tab -> name + followers needed -> "Add as new level", then give gigs that level in the Gigs tab.
ADD A CATEGORY (e.g. Animals): Levels tab -> New category name.
FIX ANA'S BOXES: "Ana boxes" tab -> choose the scene, choose the part, drag a rectangle (face, torso, legs, feet, hands, objects).
CHECK EVERYTHING: the Overview tab lists missing pictures and wrong numbers.


CHARACTERS TAB (character library)
----------------------------------
1. Press "New character..." and type a name (Ana, Sara, Coach Omar...).
2. Select it, press "Import pictures..." and choose pictures on a plain GREEN background (like the ones Gemini makes).
   You can pick several at once; the editor asks a name for each ("Standing, hands on hips").
3. The editor removes the green, trims the picture to the body and makes a hover glow.
   Look at the Result / Hover glow / Original views. If the edge is not clean, move the sliders and press
   "Apply to this picture". (Higher "Green removal" removes more of the green fringe; "Shrink edge" eats the last light border.)
4. Files are written to game/chars/<character>/<picture>.png and ..._glow.png, your originals are kept in
   chars_src/ (outside game/, not packed in the build). Deleted pictures move to chars_trash/, nothing is erased.
   game/data/characters.json is saved automatically after each action.
5. The pictures will be offered in the pickers of the next tabs (weekly schedule, placing her in a room, photo scenes).

Use in Ren'Py (for reference): the click area follows the body when focus_mask is on:
    imagebutton idle "chars/ana/standing_neutral.png" hover "chars/ana/standing_neutral_glow.png" focus_mask True action ...


PHOTO SCENES TAB (add a photo scene without touching code)
----------------------------------------------------------
A photo scene is one pose of Ana (or any character) in a room: 1 to 4 pictures on a green background, all with the SAME
pose and framing: Normal (required), Smiling, Shy, Eyes closed (the last three are optional).
1. "New scene": type the name the player sees, a short id (letters, e.g. cooking), pick where it can happen.
2. "Choose..." a picture for each expression you have. If the picture is cut by the right edge of the image, tick that box.
3. "Build / rebuild" (about 20 seconds). It cuts the green, makes the camera pictures, the room picture, the glow and the
   eyes/mouth layers, and writes game/poses_data.py + game/face_layers.py + poses/<id>.json. The log shows what happened.
4. With more than one expression: the first build uses rough face boxes. Look at the picture on the right, press
   "Auto-suggest" (or drag the blue EYES and green MOUTH rectangles yourself), switch "Show" between the expressions to
   check, and press Build again. The boxes only need to contain the eyes / the mouth with a little room around them.
5. Open the "Ana boxes" tab, pick the new scene in the list and draw her body boxes (face, torso, legs...).
The scene then shows in the photo menu in that room. "Delete scene" moves its settings and original pictures to poses_trash/.
Needs once:  pip install pillow numpy opencv-python   (the same packages as tools/add_pose.py)


SCHEDULE TAB (where she is, when, and how she looks)
----------------------------------------------------
The grid is the week: 7 days x 4 time slots (Morning / Afternoon / Evening / Night). Green = one option, yellow = several
options (the game picks ONE at random, the same all slot long), grey = nobody (she is away).
1. Click a slot, then "Add...".
2. "When": tick the days and slots the entry covers (buttons: Every day / Weekdays / Weekend). One entry can cover many slots.
3. "Where": a room, or tick "She is away".
4. "How she looks": an activity picture (a photo-scene pose such as cooking), her standing picture, or a picture of the
   Characters library (the one you cut from the green background; it glows when the mouse is over her).
5. "Place her in the room...": drag her feet to the spot on the floor, wheel or slider = size, Mirror = flip.
   If you do not place her, the game uses its usual place for that picture.
Press Save (Ctrl+S): the data goes to game/data/schedule.json.
When the player clicks her, the option "Can I take your photo?" appears only if a photo scene exists in that room.
(Old rules from masar_core.py were moved into this data: same behaviour until you change it.)


PANORAMIC ROOMS (a room wider than the screen)
----------------------------------------------
Put a WIDE picture at game/images/bg/<place>_<room>.jpg (.png and .webp work too). Nothing else to switch on:
a picture wider than 16:9 becomes a panorama. The game fits its HEIGHT to 1080, so the room is
    width = picture width x 1080 / picture height      (e.g. 2576x720 -> 3864x1080).
The player sees 1920 of it at a time and moves the view by dragging with the mouse, pushing the mouse to the left/right
edge, or with the arrow keys / A / D. A thin strip at the top (and under the camera lens) shows where the view is.
Comfortable widths: 1920 (normal), 2880, 3840, 4800 (player sees 100 / 67 / 50 / 40 %). Any width works; avoid > 6000.
Make every picture of the same room (later: morning / evening / night versions) EXACTLY the same size.
What to do in the editor:
 1. Subjects tab: pick the room. The picture is wide: scroll with the bar under it, the mouse wheel, or drag a
    rectangle to the edge. Draw rectangles exactly as in a normal room (they are stored as fractions of the whole picture).
 2. "This room's picture" (right side): shows the size, and the START VIEW slider = where the player looks when entering
    (the dashed frame on the picture). It is saved in game/data/rooms.json.
 3. If you REPLACED a room picture by a wider one that contains the old picture (you extended it left/right), press
    "Shift rectangles...": type the old width (1920 for a normal room) and where the old picture's left edge now is in
    the new picture; all rectangles of the room (and Ana's own placements in the Schedule, optional) move with it.
    "Undo last shift" reverts. If the new picture is a different drawing, just redraw the rectangles.
 4. Schedule tab -> "Place her in the room...": the picture scrolls too; the dashed frame is the start view.
 5. Overview tab: "Size" column, and notes/ERRORS about rectangles that cannot be photographed:
    - too big: the lens (even zoomed out) covers less than 55% of it, so no photo can ever match;
    - tiny (< 24 px): hard to frame (small things like a squirrel are fine: the camera accepts them when zoomed in).


PICTURES BY TIME OF DAY (morning / afternoon / evening / night)
---------------------------------------------------------------
Name a room's pictures  <place>_<room>_<time>.<ext>  in game/images/bg/ :
    gym_combat_night_morning.jpg   gym_combat_night_afternoon.jpg   gym_combat_night_evening.jpg   gym_combat_night_night.jpg
(also accepted for the afternoon: _noon / _midday / _day;  for the evening: _dusk / _sunset;  .png / .webp work too.)
The plain picture  gym_combat_night.jpg  is optional: it is used for any time that has no picture of its own.
No picture for a time? The game uses the plain picture, else the NEAREST time that has one. So you can add times one by one.
When time passes while you stay in the room, the picture changes with a soft fade.
RULES: every picture of one room must have EXACTLY the same size (the editor reports an ERROR otherwise), and the
scenery (trees, benches, ring...) must stay in the same place, or rectangles and Ana's places will not line up.
A room id that ends with a time word (e.g. combat_night) is fine, but do not ALSO create a room called 'combat':
its night picture would be the same file name (the editor warns).
In the editor:
 - Subjects tab: "Show the picture of:" chooses which time's picture you draw on. The line next to it shows which times
   have their own picture. Overview shows "yes, 3/4 times" per room.
 - Subject dialog: "Only at these times": tick e.g. Morning for a fisherman, Night for a crocodile (tick none = all day).
   Such a subject is only offered and only detected by the camera at those times; in the list it shows @mor / @eve ...,
   and its rectangle is grey/dashed on pictures of other times. A gig for it can only be completed at those times
   (the gig text should hint at it indirectly - the game never tells the player the hours).
 - Schedule tab -> "Place her in the room...": "Show the picture of:" lets you place Ana on the picture of that time
   (it starts on the first time slot ticked in the entry).


PLACES: LOCKED PLACES AND OPENING HOURS (Places tab)
----------------------------------------------------
Pick a place (or one of its rooms, click the little arrow to open the list) and set:
 - "Unlocked at the start of Part 1" (places only): untick it and the place shows its lock picture
   (game/images/map/<place>_lock.png) on the map. The story unlocks it later.
 - "Open at": tick the times of day it can be entered. Library = Morning, Afternoon, Evening (no Night).
   A room can have its own hours (e.g. the combat ring only in the evening and at night) inside a place that is open all day.
 - "Message when closed": what the player reads (default: "<Name> is closed right now.").
In the game: a closed place shows the lock picture on the map and the message pops up when clicked; a closed room's tag is grey and
shows the message; if time passes while the player is inside and it closes, he is sent out (to the map, or to the first open room)
with the message. Ana is never in a closed room: if her schedule puts her there at a closed time the Overview shows a note and she
is simply absent. Data: game/data/places.json (save with Ctrl+S).


STORY RULES: ANA'S LOVE, RENT AND THE END OF EACH DAY  (version 1)
-------------------------------------------------------------------
All numbers live in game/data/story.json (plain JSON; the editor has no tab for it yet).
  start            love and Ana's followers when the game begins (love 2, followers 0)
  gates            love values that only a story quest can cross (5, 15, 25). Until a gate is crossed love stops one point before it.
  version_cap      love never passes this (30); the first time it is reached the "end of this version" message is shown
  daily            rules checked at the end of every day
                     {"event": "talk_game", "love": 1, "per_day": 1}                   +1 if the player did it today
                     {"missing": "dishes_done", "love": -1, "if": {"ana_followers_lt": 500}}   -1 if he did NOT do it
                   conditions in "if": love_lt, love_gte, ana_followers_lt, ana_followers_gte, gate_crossed, gate_not_crossed
  weekly / rent    weekday 0 = Monday, first_day (8 = the second Monday, so there is a week of grace), amount, missing_love (-5)
  show_numbers     true = the report shows the numbers; false = only short sentences (hints)
  dev_tools        true = press F9 in the game for the developer menu (log actions, pay rent, cross a gate, finish the day)
Test the rules WITHOUT starting the game:   python tools/masar_sim.py --days 20 --quiet --cross 5@2 --cross 15@8
Checks of the engine:                       python tools/test_story.py
Not wired yet: the talk game and the dishes as real actions in the rooms, the story quests that cross the gates.


TALK GAME, DISHES AND RENT (version 1)
  game/data/talk.json: "sequence_length" (arrows, now 6), "seconds" (time limit, now 10), Ana's lines after a win or a loss.
  One try per character per day; a win with Ana gives love +1 at the end of the day (rule "talk_game" in story.json).
  Dishes: kitchen of the house, once a day, +1 love (below 20) or -1 if skipped (Ana under 500 followers).
  Rent: on Mondays (from day 8) a "Pay the rent" button appears under "Pass time". Test the rules with: python tools/test_talk.py
