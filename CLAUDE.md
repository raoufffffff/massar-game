# CLAUDE.md - read this first (project notes for Claude, written for future sessions)

Last updated: 2026-11-26 (quests, player stats, bag, shops, immediate love).  Keep this file current: when a system changes, change the matching section.

## 1. What this project is
**Masar** - a Ren'Py 8.6.1 life-sim / photography game by Raouf (root on his PC: `C:\fun\Masar`).
All in-game text is **English**. The player is a poor 22-year-old student turned photographer.
Core character: **Ana** (39, recently divorced landlady, cooking-content creator, later an influencer).
Photography is the core mechanic. Mini-games (gym: bench press, running, yoga) are recurring interactions.
Long-term: Supernova (in-game viral platform, followers/views), more characters (Sara, Vivian, Tom, Chris...), rivals,
Supabase-fed content, maybe Unreal later. **Current prototype scope = map + photography + Ana only.** Do not build
other characters/rivals unless Raouf says so. Full design lives in his "game bible" (one .md per character, outside this repo).

## 2. How to work with Raouf (important)
- Talk to him in **formal Modern Standard Arabic (MSA)**, enthusiastic but concise. Never Moroccan dialect.
  (Code, file names, in-game text and the editor UI stay English.)
- **Discuss first, build only when he says "ابدأ" (start).** When he explains a design he wants listening, not code.
- He wants to be **taught the method / tools to add content himself** (poses, subjects, gigs, backgrounds) instead of
  asking Claude each time. Prefer building an editor feature over inserting content by hand.
- **Deliver only changed/added files**, with paths relative to the project root, as a zip via SendUserFile.
  His unzip view sometimes shows the files flat (no folders): then also send a flat zip + `install.py` that copies by
  filename (done once, see `schedule_flat.zip` pattern: `python install.py C:\fun\Masar`).
- Few clarifying questions; infer. Ask only real design choices.
- Be honest about what could not be tested: no Ren'Py in the sandbox, so `.rpy` files are only reviewed by eye.
  He runs the game and reports errors (usually a traceback).
- The sandbox copy may drift from his real project (he adds scenes/files I do not have, e.g. `playground_bench`).
  Code must tolerate missing entries (use `.get`, `getattr`, `renpy.loadable`).

**Repo and workflow (added 2026-11-25).** The project lives on GitHub: `raoufffffff/massar-game` (public, branch `main`; push straight to `main`, no PRs).
Raouf works on two PCs and keeps `git pull` / `git push` in sync; the sandbox only mirrors what he sends. A session can clone it read-only; to push
it must attach the repo with push access (`add_repo`, access "push"). `.gitignore` excludes `__pycache__`, `game/data/_backup`, `chars_trash`, `poses_trash`,
saves/cache. Not in the repo / not known to Claude: his "game bible" (one .md per character), his chat decisions that are not written here, and whether any
`.rpy` change really runs (no Ren'Py in the sandbox - he reports tracebacks). When something here and the code disagree, trust the code and fix this file.

**Art rule (Raouf, 2026-11-27).** The game is NOT built on suggestive pictures; its base is the mini-games. Ana's stages change her stance, clothes style, voice and confidence,
not the level of exposure. Keep realistic body proportions, normal/elegant clothes (closed shirt, suits, dresses), eye-level camera, focus on face and expression.
The old "corruption" meter is now the **CONFIDENCE meter** (`confidence`, "self-confidence", 0-99; decided 2026-11-27). Only the NAME changed (to avoid a bad impression); its function and rise rules stay as designed in section 8. It drives Ana's personality, clothes, stance, voice and the style of her photos. No `corruption` or `fame` name anywhere, code or UI. Quick test: could the picture run as an ad on Facebook/Google? If not, it is too far.

## 3. Layout
```
game/                    Ren'Py project (scripts, images, data)
  script.rpy             start, city_loop, place_loop (time, ana_here, ana_pose_name, ana_look_entry)
  rooms.rpy              room screen room_nav, Ana as imagebutton (ana_look() reads her schedule entry), minimap
  ana.rpy                Ana sprites, transforms (ana_pos, ana_place, ana_place_at), ana_click menu
  map.rpy, map_shapes.py city map + per-place shapes
  masar_core.py          places, rooms, time (4 slots), schedule logic (reads data/schedule.json), photo spots
  masar_data.py          load(name)/save(name, data) for game/data/*.json (works in packed builds)
  masar_shot.py          shot analysis (what is in the frame): subjects, Ana parts, rating
  masar_photo.py         camera engine maths (view, zoom, sway, blink, expression timeline)
  masar_photo*.rpy       camera screens; masar_photo_free.rpy = the free camera now used everywhere
  masar_phone.py/.rpy    phone: gallery, Snapjob gigs, bank, etc.
  masar_story.py/.rpy    story engine: Ana's love, day ledger, end-of-day report (rules in data/story.json)
  masar_quests.py/.rpy   quests (data/quests.json), masar_player.py (stats + bag, data/player.json), masar_shops.py (data/shops.json)
  masar_gym*.rpy/.py     gym mini-games (lift, run, yoga) + rules
  poses_data.py, face_layers.py   GENERATED by tools/add_pose.py - never edit by hand
  data/                  snapjob.json, ana_regions.json, schedule.json, characters.json (+ _backup/ auto copies)
  chars/<char>/          library pictures (cut-out + _glow), made by the editor, NOT under images/ on purpose
  images/                ana/ bg/ camera/ gym/ map/ ui/
poses/*.json             one file per photo scene (input of tools/add_pose.py)
raw_blink/, raw_*/       original green-screen pictures (sources, keep them)
chars_src/               originals of the character library (sources)
tools/                   editor and pipelines (see 6)
```
Ren'Py auto-defines every file under `game/images/` as an image by its file name - that is why the character
library lives in `game/chars/` (loaded by path, no auto names).

## 4. Systems (how they work)
**Time**: day counter (Day 1 = Monday) and 4 slots: 0 Morning, 1 Afternoon, 2 Evening, 3 Night. `mc.advance_time`.
Travel is free; "Pass time" (T), photo sessions and training cost a slot.

**Places/rooms**: `masar_core.PLACES` and `rooms_of(pid)`. Room picture `images/bg/<place>_<room>.jpg`.

**Ana in rooms** (data-driven): `game/data/schedule.json`. Entries = days x slots x (place, room | away) x look
(`pose` activity picture, `stand`, or `char` library picture) + optional `at` placement (feet x,y on the 1920x1080 screen,
scale, flip). Several matching entries -> one is picked at random, stable for the whole slot
(`random.Random(day*100+part*10+3)`); later this becomes mood/personality based (room for a `condition` field).
Library pictures are trimmed to the body plus a 48 px transparent margin (`params.margin`); the game offsets by that
margin so the feet land on (x, y). Default scale for them = 950 / picture height.
Clicking Ana (`ana_click`): greeting, "Let's talk", and "Can I take your photo?" **only if** `mp.poses_here(...)` finds a scene here.

**Panoramic rooms** (stages 1+2 done): a room picture wider than 16:9 (`images/bg/<place>_<room>.jpg`, e.g. 2900x1080) is
detected by `room_world_w()` (rooms.rpy; height fitted to 1080, width = rest). `room_prepare()` (place_loop) sets `room_w`,
`room_home_x` (start view, `data/rooms.json` -> `mc.room_start`, 0..1, default 0.5) and `room_vx` (current scroll, kept while
staying in the room). Screen `room_pano` = a `viewport` (draggable, inertia and drag-vs-click come from Ren'Py) + own edge
scrolling in `room_tick` (70 px zone, only y 430..880 so UI corners do not scroll) + arrow keys/A/D + `<` `>` hints.
Everything inside is in WORLD pixels (schedule `at`, subject boxes). Camera: `mp.set_world(room_w)` in `ff_setup`
(clamp_view uses `mp.WORLD_W`), lens opens on the current view (`cam_reset`), Ana's camera x = `ana_world_ax()`, photos keep
`p["ww"]`. Subject boxes are FRACTIONS of the whole picture, so replacing a room picture by a wider one shifts them
(editor: Subjects tab "Shift rectangles..." + undo). Time-of-day variants must have identical sizes. Untested in Ren'Py
(written by eye) except what Raouf reported working: drag/edge scroll in the lake room and talking to Ana (dialogue background
= `room_view_bg()`, the visible part of the panorama, because the screen is hidden while she talks). `mc.bg_path` accepts
jpg/png/jpeg/webp (`mc.bg_exists` is set to `renpy.loadable` in rooms.rpy). Position strip at the top of the room (`room_bar`)
and under the lens (`cam_bar`); camera pans faster in wide rooms. Editor: `tools/masar_rooms.py` (size info, start view,
shift, `box_problems`: subject rectangles the lens can never cover 55% of = error). `masar_shot.detect_subjects` lowers the
10% frame-share rule for tiny subjects so a squirrel in a treetop is detectable when zoomed in.

**Places/ids changed by Raouf**: the old place `fine` is now `restaurant` ("Fine Dining") with rooms `main` (Outside) and `inside` (Inside); its map icons may still be
`images/map/fine_*.png` (`mc.map_art` falls back to that alias). The gym has a room `combat` ("Combat Ring"). All room pictures are now wide (32:9, 3840x1080-ish, the
player sees 50%) with 4 time versions (`_noon` counts as afternoon); some old plain pictures (1920x1080 / 2752x1536) are still next to them and make the editor report
"different sizes" - they should be moved out of `game/images/bg/` once all four times exist. `data/places.json` holds his opening hours (cafe, etc.) and the unlocked list.

**Pictures by time of day** (stage 3, built 2026-11-24, untested in Ren'Py): `images/bg/<place>_<room>_<morning|afternoon|evening|night>.<ext>`
(aliases noon/midday/day, dusk/sunset). `mc.bg_path(pid, rid, part=None)` (part None = current slot via `mc.part_now`, set in rooms.rpy)
tries that time -> plain `<place>_<room>` -> nearest time; stems equal to another room's plain name are skipped (room `combat_night`
vs room `combat`). place_loop dissolves when time passes in the same room (`bg_last`). Subjects may have `"times": ["night"]` in
snapjob.json (`mph.SUBJECT_TIMES`, `subject_in_time`, `subjects_here(place, room, part=None)` filters; detection and the subject
picker use it; `mph.part_now` set in rooms.rpy). Editor: `masar_rooms.time_files/find_bg(part)/size_problems/missing_times/name_clash`,
Subjects tab time selector + "Only at these times" in the subject dialog, schedule placement dialog time selector.
Raouf's gym room `combat_night` (Fight Night) has 4 time pictures 2576x718 (32:9); fights/spectators are baked into some pictures.

**Opening hours / locks** (built 2026-11-25, untested in Ren'Py): `game/data/places.json` {unlocked, places:{pid:{open:[slots],message}}, rooms:{"pid/rid":{...}}}.
`mc.can_enter(unlocked, pid, part)` (story lock AND hours), `place_open`, `room_open`, `closed_text`, `first_open_room`; `PART1_UNLOCKED` is read
from the file. map.rpy: closed places show `<id>_lock.png` and Notify the message; room_nav tags grey + Notify; place_loop sends the player out
(`"[closed_note]"` then city_loop / first open room) when time passes and it closes; `ana_location` returns None when her room is closed.
Editor: `tools/masar_places.py` (Places tab; validate warns about Ana scheduled in closed rooms).

**Free camera** (`masar_photo_free.rpy`): lens window 330,80 / 1260x820 on a 1920x1080 world; zoom limits ZMAX_ROOM 3.4,
ZMAX_ANA 2.6; steadiness and sway; max 5 shots per session. Ana pictures are 1600x2160 shown at IMG_ZOOM 0.5.
`masar_shot.analyze`: any named subject in frame counts (match from framing + steadiness), Ana shots are classified by
what is at the centre of the frame (face / upper / full / lower / feet / hands / object / wide), `influencer_rating`
gives a /10 score (hand 1, feet <= 4, face+shoulders portrait ~9). Untargeted shots are "Random shot N".

**Snapjob** (`masar_phone.py` + `snapjob.json`): categories, levels (L1 Beginner from 0 followers, L2 Amateur at 300),
gigs (id, subject, title, client, brief, reward <= ~200 for now, level), subjects with a rectangle per room, accepted
at >= 80 % match, 5 gigs on the board per day. Planned ladder: L3 event photographer, L4 investigator/paparazzi
(gigs tied to side stories). Snapjob photography XP will later raise Ana's Supernova popularity.

**Gym**: bench press (5 lifts, 3 fails, green/orange/red zones), runner (player and Ana, chibi style), yoga (Ana: 5 poses,
arrow sequences, 20 s per round, 3 fails). Stats are not wired in yet.

**Save compatibility**: the phone object is pickled. New fields must be read with `getattr(obj, "x", default)` / `.get`.

**Story engine v1** (built 2026-11-25, step 1; `.rpy` part untested in Ren'Py): `game/masar_story.py` (pure Python: `Story` object with love, ana_followers,
gates_crossed, ledger, history, pending; `log(event, day, part)`, `end_of_day(day, phone)` -> report, `cross_gate(n)`, `cap()`, `rent_due(day)`, `pay_rent(phone, day, part)`),
rules in `game/data/story.json` (start 2/0, gates 5/15/25, version_cap 30, daily rules talk_game +1, dishes_done +1 (love < 20), missing dishes -1 (Ana followers < 500),
rent 150 every Monday from day 8, -5 if unpaid, show_numbers, dev_tools). `game/masar_story.rpy`: `default story`, wraps `mc.advance_time` once so every Night -> Morning
calls `story_end_of_day`, screen `day_report` (shown by city_loop/place_loop when `story.pending`), F9 dev menu (`story_dev`). Simulator `tools/masar_sim.py`, checks `tools/test_story.py`.
NOT wired yet (next steps): the story quests that cross gates, tier-based Ana looks,
a "Story" tab in the editor (rules are edited in the JSON by hand for now). Note: with start love 2 and +2/day the first cap (4) is reached on day 1.

**Talk game, dishes, rent button** (talk game rebuilt 2026-11-26 as a SITTING CONVERSATION, `.rpy` untested in Ren'Py): `game/masar_talk.py` (pure: `TalkSession(who, day)`: 3 moments, 2 wins needed, stops as soon as decided; each moment = Ana says a line, the player answers with 2/3/3 arrows in 7 s; `round_res`, `next_round()`),
`game/masar_talk.rpy` (screens `talk_intro/ask/play/react/hud`, label `talk_game(who)`), `game/data/talk.json` (rounds, need_wins, arrows, seconds, `conversations.ana` = list of {ana, you, win, fail}, closing `lines`), `game/data/talk_scenes.json` (place/room -> pictures neutral/smile/annoyed; `default` home/kitchen is used where a room has no scene).
Pictures `game/images/talk/kitchen_<neutral|smile|annoyed>.jpg` (2560x1440, made by Raouf, flat cartoon style; the 3 must keep identical pose/background). The scene picture is shown with `show expression ... as talkbg` and moves: breathing, slow push-in during the countdown (`talk_cam_to`), pulse on success, lean away on failure; UI lives in the bottom band over `images/ui/talk_shade.png` so her face is free.
Scenes built (2026-11-27): kitchen table (default), living-room sofa (`home/living`, also used for `home/ana_door` upstairs), bench by the lake (`park/lake`, pictures `garden_*`); other rooms fall back to the kitchen. Maybe later: own upstairs scene; add one = 3 pictures + an entry in talk_scenes.json (a scene editor tab is a good next step).
Menu item "Have a real conversation (talk game)" in `ana_click` (hidden once played today: `story.talked_today`); it returns "talkgame" and place_loop passes one time slot (win or lose). `story.talk_result(who, success, day, part)` logs `talk_try` and, on a win, `talk_game` (Ana) or `talk_game_<who>` (others, no Ana love).
Dishes: action "Wash the dishes" (`story_actions` in masar_story.rpy, only home/kitchen, once a day, `label act_dishes`, logs `dishes_done`, costs a slot). Rent: button "Pay the rent ($N)" in every room on rent days (`__rent__` in place_loop -> `story.pay_rent`).
Checks: `tools/test_talk.py`.

**Immediate vs end-of-day rules, stats, bag, shops, quests** (built 2026-11-26, `.rpy` untested in Ren'Py, Python tested by `tools/test_quests.py`):
- Engine: every rule in `story.json` "daily" has `"when": "now" | "end_of_day"`. `story.log(event)` applies the "now" rules at once (per_day limit, conditions, gate cap) and queues short notes (`story.pop_notes()`).
  Talk game and dishes are "now"; unwashed dishes, unpaid rent and fitness decay are end-of-day. The day report lists everything of the day (`lines`, `stat_lines`). `cross_gate` also counts in the day.
- Player (`masar_player.py`, `data/player.json`): fitness 5, charisma 5, intelligence 15; gym points -> fitness (10: +2, 6-9: +1, <=5: 0) for `gym_bench_press` and `gym_run_player` (`GYM_TRAINING` in masar_quests.rpy);
  talk game charisma +1/-1 (never fades); fitness -0.5 a day in the end-of-day report. Bag = `player.bag` {item: count}. Phone app "Me" shows numbers and bag.
- Shops (`masar_shops.py`, `data/shops.json`): a room with an entry "place/room" shows the action "Shop: <title>" (`act_shop`, no time passes). New mall room `store` = "General Store" (toolkit $90, unique);
  placeholder picture `images/bg/mall_store.jpg` (Raouf replaces it). Later shops: just add entries; jobs and seller characters will come with Raouf's descriptions.
- Quests (`masar_quests.py/.rpy`, `data/quests.json`): steps with conditions computed from state (love_gte, flag, item, stat_gte, gigs_done_gte, money_gte, quest_done); a quest is done when all steps are; the first open step is shown
  with its hint and a bar. A step may have an `action` (who: "ana" = extra choice when clicking Ana in that room, "room" = button under "Pass time"; label = scene; flag; time slots; needs; fail_text). Reward: gate / money / message.
  Phone app "Quests" (the old Tasks app, same icon). Quests now: `ana_know` (love 4), `ana_plumber` (ask Ana in the living room -> buy toolkit -> fix the kitchen pipes, needs intelligence >= 10; reward: gate 5), `snap_first` (3 level-1 gigs, $50).
  `flush_notes()` (called in the loops, after actions, after uploads) shows love/stat/quest changes as one notification and finishes quests. Gates 15 and 25 have no quest yet (love stalls at 14 until one exists).
- NOT built yet: quests for gates 15 and 25, the character panel, tier-based Ana looks, editor tabs for quests/shops/story rules, shop sellers as characters.

## 5. Conventions and pitfalls learned
- Ren'Py: `default` for saved state, `init python` for code; transforms accept python expressions as args; menu items can
  have `if cond`; text interpolation is limited (compute strings first).
- Camera pictures are 1600x2160 (`game/images/camera/<key>_<expr>.png`), room pictures 800x1080.
- Face expressions are small eye/mouth layers over the neutral picture (`face_layers.py`) to avoid wobble; the boxes are
  in 1600x2160 coordinates.
- Editor (tkinter): the editor must be started from the project root (it reads `os.getcwd()`; from `tools/` it steps up).
  Widget stacking order matters (create a widget inside its final parent). Headless tests: xvfb + `/usr/bin/python3.12`
  (has tk + Pillow); `/usr/local/bin/python3` 3.13 has numpy/cv2 but no tkinter; the editor runs `add_pose.py` through
  `MASAR_PYTHON` (or `sys.executable`).
- JSON data is saved with backups in `game/data/_backup`. Deleted pictures/scenes are moved to `chars_trash/` or
  `poses_trash/`, never erased.

## 6. Tools (Raouf adds content with these; teach, do not hand-edit)
Start: `python tools/masar_editor.py` from the project root. Tabs:
- **Overview**: rooms table + problems (errors vs notes).
- **Subjects**: draw a rectangle per photo subject in a room (wide rooms scroll); optionally make a Snapjob gig at once;
  room panel: panorama info, start view, shift rectangles.
- **Gigs**, **Levels**: Snapjob gigs, rewards, levels, categories, settings.
- **Ana boxes**: body-part rectangles per photo scene (`ana_regions.json`); scenes without boxes use rough defaults.
- **Characters**: import green-screen pictures -> cut-out + glow (`tools/masar_chars.py`, Pillow only).
- **Photo scenes**: wizard around `tools/add_pose.py` (needs `pip install pillow numpy opencv-python`); writes
  `poses/<id>.json`, raw pictures, camera pictures, face layers, `poses_data.py`. Auto-suggests eye/mouth boxes.
- **Schedule** (redesigned 2026-11-26, `tools/masar_schedule.py`): week grid with pictures per cell, place colours and red warnings (closed rooms via the `hours` ctx callback = Places tab, missing pictures); one "studio" window per entry (live room preview, drag her feet, wheel = size, gallery of looks, live warnings); Duplicate, Copy slot to..., Undo (Ctrl+Z); scrolls in panoramic rooms. Tested headless (xvfb + python3.12).
Other scripts in `tools/` generate art/placeholder assets (`make_*.py`, `key_sprites.py`) and previews.
`tools/README_EDITOR.txt` is the user manual (English).

## 7. Roadmap (agreed order)
1. DONE: free camera, Snapjob + levels, Ana rating, editor (subjects/gigs/levels/Ana boxes), character library,
   photo-scene wizard, weekly schedule + placement, schedule-driven Ana in rooms.
2. IN PROGRESS: panoramic rooms (stage 1 = engine done, stage 2 = editor done; stage 3 = backgrounds per time of day + subject times (built; next: gig hints, auto-graded variants tool, Ana companion); stage 4 = optional companion of Ana). NEXT after: **backgrounds per time of day** (morning/afternoon/evening/night, fall back to the default picture), then
   subjects/gigs tied to a time (e.g. crocodile at the lake at night). Raouf is making the pictures himself.
3. Then: the **bag/inventory**, game foundations (stats, relationships, money), then the story (Part 1 = Ana's first
   challenges: persuade her to join Supernova at love 10 %, 500 subscribers + $5000/month, the debt bomb, ...).
4. Ideas parked: followers/Supernova tied to posting Ana photos, photography XP affecting steadiness/zoom/reach, Snapjob
   levels unlocked by followers, darkness at night lowering sharpness, Ana's appearance stages (2 for now),
   mood-based schedule choice, Supabase-fed content.
Open art items: Warrior II crop, f0 start-fail image, yoga start pose sneakers, run frames/backgrounds/obstacles, yoga background.

## 8. DRAFT (planning only, NOT built): Ana's state and what it drives
(2026-11-27: the old corruption meter was renamed CONFIDENCE; tier keys below are internal labels only, rename freely.)
Raouf's design, 2026-11-25. Do not build until he says so; Part 1 (chapter 1) comes first, start small
(confidence + current stage only), add the rest one by one.

Ana's state record (one place; everything else reads it, nothing recomputes):
- Numbers: confidence (0-99, formerly corruption/liberation), fitness, love, mood, followers. Mood = computed daily from the player's
  actions plus a little randomness (not pure random). Followers = derived from published photos (not a free number).
- Labels: current stage/path (chapter 1, Supernova week, ...), most-attracted-to (1st), second most-attracted-to,
  her photographer, her manager.

| Output | Inputs |
|---|---|
| Where she appears | confidence, stage |
| Her photo poses | confidence, place, mood, stage |
| How she talks to the player | love, confidence, mood |
| Who she appears with | 1st and 2nd attraction, stage, photographer |
| Her Supernova photos/stories (when the player is not her photographer) | confidence, 1st and 2nd attraction |
| Follower growth | fitness + current followers always; plus the player's photos if he shoots her; otherwise only those two |

Corruption phases (CONFIRMED thresholds, 2026-11-25; max 100; tier names are the keys for pictures/expressions/dialogue/schedule):
- 0-24 `shy_housewife`, 25-49 `mature_woman`, 50-74 `arrogant_star`, 75-100 `seduction_queen` (75-100 share one personality).
Older notes on how each range rises (still draft):
- 0-24: rises with each successful photo published on Supernova and with the player's compliments (talk games).
- 25-49: rises when the player accepts her working with a male model and makes decisions such as flirting in public.
- 50-74: becomes hard to control, rises by itself daily; the player must try to lower it.
- 75-99: nothing stops it; at 90-99 it falls by itself over about a month down to 5; Ana is mostly absent then.
Computed once at the end of each day from a day ledger (Night -> next Morning). Show hints, not raw numbers.

Method: no content per combination; rules with 1-2 conditions, ordered by priority, fall back to the generic version.
Names are labels only (internal key e.g. `liberation`). Raouf still looking for the "final recipe": draft first, he corrects.

## 9. DRAFT (planning only, NOT built): Chapter 1 and Ana's love rules
Raouf's plan, 2026-11-25. Everything here is Part 1 rules; later parts change the sources (more professional duties).

**Story opening** (narrative, plain Ren'Py with pictures + text, no free play): player is a last-year university student, parents went
bankrupt and vanished; an acquaintance of his mother, Ana, rents him a room in her house for a very low price. Ana: ordinary,
unconfident housewife, sad because her ex-husband cheated; first scene she welcomes him ("don't worry about the rent"); a huge
broken wedding photo hangs in the house (player notices it, nobody explains). Then a 6-month jump (shown as narrative scenes).
Player leaves university, sees his girlfriend with another man, she says she is tired of him because he is poor. He sits in the park;
a camera flash: **Chris**, a photographer ("you are the saddest person I photographed today"; "that is not your business", both laugh).
Player tells his story; Chris: "why not work in photography, at least you will not be broke", "I will teach you". (Plan continues, Raouf has not told the rest yet.)
Chris is a candidate for "her photographer" label? (not confirmed).

**Scene types**: 1) narrative scenes (normal Ren'Py, choices may change story and stats); 2) talk games (rhythm game with arrows,
like a dance game, "at first"; later levels may change style).

**Love (Ana's love/admiration for the player; "love" = "admiration", assumed one number)**, rules of Part 1 only:
- Talk game: once per day with Ana, +1; gets harder every 10 points of love (difficulty table by love band; style may change at higher levels).
- Dishes: washing +1 and raises her mood, when love < 20 AND love increase not locked AND (she dates the player OR she dates nobody and lives in her first home).
- Not washing: -1 love when Ana's followers < 500 (regardless of where the player slept).
- Max normal day: +2; can be 0 or -1.
- She never agrees to be photographed (be a model) unless love >= 15. That is a barrier broken by the quest below.
- (Replaced by the eviction rule below: the old "love < 10 locks the house" idea is dropped.)

**Barriers (gates)** at love 5, 15, 25 (and further ones after 25 up to 75, same pattern): not crossed by dishes/talk games, only by a story quest.
Between barriers love rises by dishes/talk games (0-4, 6-14, 16-24). A crossed barrier stays crossed even if love later falls
(he may climb again with games). Implement as a quest chain, no separate gate field: number quest ("raise love to 4") -> story quest
("fix her TV", example) sets love 5 -> number quest ("reach 14") -> story quest ("help her with $1000") sets love 15 -> ... The cap of daily
gains = the current unfinished story quest. Needs: quest system, money system (the $1000 quest), maybe the bag.
After love 25 (up to 75, mandatory story path) love no longer rises with talk games; other sources: training, gifts, occasions, a flirting game
(different from talk games). Love up to 75 is forced by the quests.

**Open questions**: what happens at the barrier numbers exactly (stops at 4/14/24 and quest sets 5/15/25?); starting love after the 6-month
narrative; whether talk game / dishes take a time slot (4 slots per day); is complimenting in the talk game also raising confidence (his 0-24 note);
what happens to the dishes penalty when the player is away all day (suggested: excused); how the chapter ends and what the Snapjob lesson with Chris looks like.

**Update 2026-11-25 (later): rent, eviction, money, requests, loneliness, time.**
- **Time is the currency of the game**: 4 slots a day, an action that takes time moves to the next slot (Morning -> Afternoon ...). On purpose the player can
  never do everything in one day. Take time: training, photography, talk game, dishes. Free: random chat with Ana. Keep numbers editable.
- **Rent (only before the player crosses barrier 50)**: 150 USD per week. Every Monday morning Ana sends a "pay rent" message; the player must pay that same day;
  if Monday ends unpaid, love -5. Not paying is allowed (Ana says "don't worry about the rent", it is cheap, but unpaid rent costs love because she
  assumes he will always pay). After barrier 50 there is no rent.
- **Eviction**: before barrier 50 she never evicts, love may sit at 0 (she still sees him as her friend's son). After barrier 50 she sees him as a partner,
  so when love falls to <= 15 she evicts him: he cannot enter her house until he repairs the relationship and love is above 15 again (if the story allows it).
  First-Monday grace period: to decide (Day 1 is a Monday).
- **Money sources**: Snapjob gigs; a job at John's cafe; Supernova (50 % of Ana's earnings and of any character he is the photographer of); side stories
  and their paths. (Roadmap numbers: Snapjob rewards <= ~200; rent 150/week is about one gig a week.)
- **Gifts** start at love 25. At love >= 40 many things open (dates, Ana messages him a lot with requests: dinner, meet-up, help). Ignoring a request lowers love.
  To avoid invitations the player spends time with her once or twice a week; then she writes only for something important, not for dates.
  Open: polite refusal softer than ignoring? weekly cap of requests? one free postpone?
- **Loneliness/company meter** appears at love 40. Suggested internal name `company` (high = not lonely; display name to decide). Falls 10 per day; a date or a gift
  raises it by 10-30 depending on gift/date quality. Below 20 % each night love -2. Easy to keep safe (a good date or gift every 3 days) on purpose.
  Check: with -10/day the meter is flat only with a 30-point event every 3 days; weak gifts (10) make it drift down slowly. All numbers editable. Open: starting value
  at 40 (suggested 100), whether it vanishes if love drops below 40, a daily cap on penalties (ignored request + meter).
- Love sources by range: 0-25 talk game + dishes; 25-75 training, gifts, occasions, a flirting game (not the talk game). Barriers at 5, 15, 25, 40, ... up to 75 and the
  barrier at 50 (crossing it changes how she sees him, see eviction); every barrier = a story quest that sets the love value.

## 10. DRAFT (planning only, NOT built): after love 40 - sudden drops, discovery, rivals, defense games
Raouf's design, 2026-11-25. Not built. Numbers editable in the future editor.

**Two ways love falls**: slow (neglect: dishes, company meter, ignored requests, rent) and sudden (a fatal mistake she discovers: love set to a value like 5; with barrier 50
crossed this evicts him at once). Recovery after a sudden fall: hard, not impossible (a long apology quest back above 15). Give hints before disasters (fairness).
**Discovery** of secret acts (player cheats): (1) by place: he takes another woman on a date to a place that is in Ana's schedule for that slot, so she sees him
(`ana_location` already knows her place per slot; a "companion" state is needed); (2) by platform: a model who dates him posts photos with him on Supernova or stories
(per-character `posts_about_him` chance). Secret acts go to the day ledger with an exposure risk; the discovery check runs at day end. Warn the player first (e.g. "Ana may be there tonight").

**Rivals (5)**: Chris, Tom, John, Evan, Leo (Chris is also his mentor; John owns the cafe where the player can work). A rival can enter when the company meter is low (< 20 % for ~3 days, to confirm)
and love < 60. Each person has their own love points for Ana; "first/second most attracted to" are DERIVED from these numbers (top two), not stored.
**Defense games** (like talk games): start when the player's love is 50 and some rival has > 30 (becomes second). Warning appears; the player may ignore it, or search the map for Ana
(her schedule is knowledge; searching costs time slots) and play the defense game. Win: rival -10. Lose or ignore: rival +10 AND the player's love -10. Every loss/ignore makes the next defense game harder.
The war ends when someone drops below 15: rival < 15 -> he leaves the fight, Ana "gives the player a chance" and love can be raised again; player < 15 -> Ana leaves / evicts him.
While the war is on love CANNOT be raised by other sources (she is really thinking of leaving). Winning does not raise the player's love; it only pushes the rival away.
After winning, the player repairs the relationship by climbing to barrier 60 (a story quest). Open: rival's starting points and daily growth; one defense game or one per rival (suggested: one, tuned
by difficulty); a "war bar" showing both numbers during the fight (suggested).

## 11. Agreed next step (2026-11-25): build a small playable slice FIRST
Do not build rivals/discovery/loneliness yet. Slice = two weeks in Ana's house: day ledger + end-of-day review, rent message every Monday (150 USD, -5 love if unpaid),
dishes (+1 / -1 when followers < 500), one talk game (arrows, once per day), love barrier 5 with one story quest, 4 time slots with actions that move time, simulator to test.
Then Raouf plays it and we judge whether scarcity is fun or tiring before adding more. Wait for his "ابدأ". Remaining questions for him: starting numbers (love, followers, money),
first-Monday grace, how Chris's lesson/chapter end go, what the barrier numbers do exactly (stop at 4 and quest sets 5?). Risk noted to him: too many penalties after love 40
may make the relationship feel like chores; keep all numbers editable. Ana must keep her own arc and motives (not a reward).

## 12. SCOPE OF VERSION 1 (decided by Raouf 2026-11-25) - supersedes the slice in section 11 where they differ
IN: chapter 1 only, Ana's love 0-30 only; her confidence never passes 30, so only TWO Ana poses/looks (shy_housewife 0-24, mature_woman 25-30);
only 3 side stories, built from conversations with Ana (not deep); the goal is a SMOOTH, SUSTAINABLE play experience.
OUT (future): rivals and their system (defense games, loneliness meter from 40, requests, discovery), the player working as photographer for other models.
Consequence: love barriers 5, 15, 25 and the end of the chapter around 30; rent/dishes/talk game/Snapjob/Supernova-for-Ana stay in; everything from love 40 up stays in the drafts (sections 9-10) untouched.

**Version 1 side stories (decided 2026-11-25)**: three stories NOT connected to Ana (stories tied to her come later), meant to show the variety of the world and things players may enjoy besides photography:
1. Light racing games for money, with Carlos and Samantha (Samantha is a core character in the big design: here only a cameo, no romance branch opened yet - to confirm).
2. Boxing: train and win first place in the district championship (gym room `combat` exists).
3. Private investigator work with policewoman Lilian (idea: investigations with the camera, ties to Snapjob level 4 "investigator").
Rewards for each: money, a relationship with another woman (v1: only "door opened"/flag, no active romance or infidelity system), and unlocking future branches.
Because they do not touch Ana's love, Ana's rules stay simple; they only compete for time slots and give money. Suggested order: investigator (reuses the camera), boxing, then racing (reuse the runner mini-game).

**Version 1 decisions (2026-11-25, later)**: End of the version: when Ana's love passes 30 a message says the player reached the end of the current version; no indicator can go higher and no new
poses open (cap at 30). Starting numbers when free play begins: Ana's love 2, player's money 100 USD, Ana's followers 0 (she has no Supernova account yet; it is created when she agrees, love 15).
Samantha = a university classmate of the player; "Carlos" (racing story) = the player's close friend (Raouf wrote "Chris" once; Chris is the photography mentor - assumed typo, to confirm).
Open: 100 USD < rent 150 USD and Day 1 is a Monday -> needs a first-week grace (suggested: first rent on the second Monday).

## 13. DECISIONS 2026-11-26 (quests, stats, timing) - agreed with Raouf; the quest system, stats, timing rule and the General Store are BUILT (see section 4); the character panel is not
- **Quest system (next build, on his "ابدأ")**: phone app "Quests", list grouped by domain (Ana, Snapjob, ...). Opening a quest shows the goal, a progress bar (2/4, 1/3) and a hint that tells the player what to do
  (e.g. "find Ana and talk to her"). Examples he gave: "complete 3 Snapjob gigs of level 1", "raise Ana's love to 4". Progress is COMPUTED from game state (love, gigs done), no separate counters.
  Quest = domain, title, text/hint, completion condition, reward, prerequisite; data in `game/data/quests.json` (editor tab later). Ana chain: number quest -> story quest that crosses the gate
  (cap of daily love = current unfinished story quest). Several domains may be active at once. Completion shows a notification and unlocks the next one. Needs a check that the phone stores completed gigs per level (else add a counter).
  The Plumber quest needs intelligence > 10, so a minimal player-stats object (fitness 5, charisma 5, intelligence 15 at start) is built in the same batch.
- **Timing rule**: effects tied to games/actions apply IMMEDIATELY (talk game: Ana love +1, charisma +1/-1; washing dishes: love +1 while love < 20; gym training: fitness +2 on 10 points, +1 on 6-9, 0 on <= 5;
  a notification shows the change). Penalties apply at END OF DAY: unwashed dishes -1 (Ana followers < 500), unpaid rent -5, fitness -0.5 per day. Charisma never decays. Keep the daily limits (1 talk game per character, 1 dishes) and the gate cap.
  Plan: each rule in story.json gets `"when": "now" | "end_of_day"`. Quest conditions are checked as soon as a stat changes.
- **Shops**: Raouf wants places in the mall (General Store first) where the player buys things; later each shop he describes (some are jobs, some sell special things, sellers are characters). Data-driven (shops.json).
- **Character panel (LATER, when Raouf gives a mock-up)**: one button opens a screen with the player's stats and each important character (Ana first): picture of her current state, current personality/tier, stats, love points earned. Not built.
