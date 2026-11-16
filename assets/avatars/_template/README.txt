HOW TO ADD YOUR OWN AVATAR (PNG sprite pack)
============================================

1. Copy this _template folder and rename it, e.g.  assets\avatars\rex
   (folders whose names start with "_" are ignored).
   You can also put packs in  %APPDATA%\RemindMe\avatars\
2. Put transparent PNG frames in the folder, for example:
     idle_01.png idle_02.png ...   walk_01.png ... walk_08.png   sleep_01.png ...
   - All frames should be the same size and show the character standing on
     the bottom edge, facing the direction set in "facing".
   - Only "idle" is required. Missing states fall back (laugh -> happy -> idle).
3. Edit avatar.json: name, label (shown in Settings), fps, file patterns.
   "anchors" place the Zzz / anger mark / glass, in a 120 x 120 box
   (x to the right, y down, feet at y = 112).
   "lines" overrides what the avatar says (water, blink, posture, break,
   angry, laugh, wake, done, done_water, snooze, drop, intro...).
4. Restart Remind Me and pick the avatar in Settings > Avatar.

Only use art you made or have a licence for.
