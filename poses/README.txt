HOW TO ADD A NEW POSE (no code editing)
=======================================
1. Make the pictures with the AI image generator (green background, same character, same framing):
     raw_blink/<raw>_neutral.jpg   required  (the base picture)
     raw_blink/<raw>_smile.jpg     optional  (same pose, smiling)
     raw_blink/<raw>_shy.jpg       optional
     raw_blink/<raw>_blink.jpg     optional  (eyes closed)
   Always send the NEUTRAL picture as the reference for the other expressions, never a previous result.
   If you only have the neutral picture the pose works, but without blinking/smiling.

2. Copy poses/eating.json to poses/<name>.json and edit:
     key        short id used for the file names (e.g. "sofa")
     raw        file prefix of your raw pictures (e.g. "pose_sofa")
     pose       pose name in the game (e.g. "sofa")        scene: unique scene id (e.g. "living_sofa")
     title      name shown on the photo board              place / room: where she does it (home / living ...)
     xoff       4 normally;  "right" if the picture is cut by its right edge (she is then placed flush right)
     ax         centre of her picture on the 1920 screen: 1274 normal, 1520 when xoff is "right"
     despill    true removes a green fringe around the hair
     eyes_box / mouth_box   rectangles [x0,y0,x1,y1] in the 1600x2160 camera picture (only if you have smile/shy/blink)
     parts      the photo targets: roi = [x, y, w, h] in the 800x1080 picture, zoom = ideal zoom, expr_w 0..1 = how much
                her expression matters for that target (face = 1.0, objects = 0.0)
     shots      list of [part, expression] challenges (expression must exist as a picture)

3. Run from the project root (pip install pillow numpy opencv-python once):
     python tools/add_pose.py <name>             builds everything
     python tools/add_pose.py <name> --preview   draws poses/_preview_<name>.png : red = target frames, blue = eyes,
                                                 green = mouth. Adjust the numbers in the json until the boxes sit
                                                 right, then run the build again. (First build once, then preview.)

4. Copy to the game (Ren'Py): game/images/ (new files), game/face_layers.py, game/poses_data.py. Done:
   she appears in that room at random times (use the T key to pass time), and the photo menu lists the pose.

Room-only poses (no photo scene yet, like coffee): just drop game/images/ana/pose_<name>.png and add the name
to ANA_POSES in game/masar_core.py.
