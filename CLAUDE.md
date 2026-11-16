# CLAUDE.md

Guidance for Claude (and other AI coding agents) working in this repository.

## What this is
**Remind Me** is a Windows-only tray app written in Python 3.10+ with Tkinter, Pillow and pystray. It has no other runtime dependencies. It shows wellness reminders through an animated desktop pet (or toast notifications), can speak them with Windows TTS, and can optionally nudge the mouse while the user is idle.

## Run / build / lint
```bat
run.bat                     :: install deps + start (pythonw, no console)
py run.pyw                  :: run with a console to see tracebacks
build.bat                   :: PyInstaller one-file exe -> dist\RemindMe.exe
py -m pip install -r requirements-dev.txt
ruff check .                :: lint (config in pyproject.toml)
```
There's no unit-test suite yet. Runtime errors go to `%APPDATA%\RemindMe\remindme.log`.

### Testing on Linux / CI (no Windows)
Every Windows call in `winapi.py` and `voice.py` falls back to a no-op when not on Windows, so the UI runs under Xvfb:
```bash
sudo apt-get install python3-tk xvfb imagemagick
pip install pystray pillow
APPDATA=/tmp/rm xvfb-run -s "-screen 0 1280x800x24" python3 run.pyw
```
For visual checks, drive the app from a script: create `App()`, schedule actions with `root.after`, and grab screenshots with `import -window root shot.png`. Transparency keys, the tray, the voice and the mouse nudge only work on Windows, so call those out as untested when changing them.

## Architecture
- **Threads:** Tk runs on the main thread. pystray runs detached on its own thread, and **every tray callback must go through `App.call(fn, *args)`**, which queues the call onto the Tk thread. Never touch Tk from another thread. Voice listing and frame warm-up use daemon threads and touch only Pillow and plain data.
- **`app.App`** owns the config, the 1-second `_tick` scheduler (reminders, away detection, mouse nudge, break countdown), and `_notify()`. `_notify()` sends a message to the pet's bubble when the pet is on, and to a toast otherwise. `self.active[kind]` holds the open reminder UI object. Toasts and bubbles share an interface: `.close(reason)`, `.closed`, `.set_message()`.
- **Idle tracking:** `GetLastInputInfo` is used, and the app ignores input that arrives within 1.5 s of its own synthetic nudge (`_jiggle_tick`). Without that, the nudge would reset the "away" detection.
- **`pet/pet.py`** is a state machine. `self.state` is one of idle, walk, sleep, angry, laugh, happy, hop, held, fall, drop, drink, stretch, wake, dig, plant, water. `state_until` holds the timed end of a state, and `_state_ended` decides what comes next. Gardening is driven by `self.job` (`start_job` → `_job_arrived` → `_job_step`). The frame loop runs every 33 ms (100 ms while asleep).
- **Bubbles queue up:** reminders (bubbles with buttons) wait in `Pet.queue`, and chatter bubbles are dropped while a reminder is open. A bubble button closes the bubble *before* running its action, so the pet can react straight away.
- **Rendering:** illustrated avatars (`illustrated.ImageAvatar`) map a `Pose` to a frame key `(group, index, eyes, mouth[, look])`. Each frame is painted with `art.Art` (Pillow, 3× supersampled) and cached in memory and in `%APPDATA%\RemindMe\cache\<key>_v<VERSION>_<size>\`. **Bump the avatar's `VERSION` whenever you change its drawing**, or users will keep seeing stale cached frames. Overlay effects (Zzz, anger mark, dirt, watering can) are vector shapes drawn on the Tk canvas in `base.Avatar.draw_effects`.
- **Coordinates:** avatars draw in a 140×140 logical box (`painter.LOGICAL`). The 120-unit drawing box is offset by `ORIGIN = (10, 24)`, the feet sit at y = 112, and drawings face right. Mirroring is automatic for `mirror = True` avatars.
- **Windows transparency:** windows use `-transparentcolor` with the key colour `#ff00fe`. Images must have **binary alpha** (`Art.finish()` does this), or edges get pink fringes. All pop-ups are `overrideredirect`, topmost, and `WS_EX_NOACTIVATE` (`winapi.make_no_activate`) so they never steal focus. `winapi.keep_on_top()` re-asserts topmost every 1.5 s and restores the window after Win+D.
- **Config:** `config.DEFAULTS` is deep-merged with the user's `config.json`, so new keys need a default there. `App.save_cfg()` persists the config. The settings dialog edits a copy and applies it with `App.apply_settings()`.

## Conventions
- Keep it dependency-light: standard library, Pillow and pystray only. PowerShell (`System.Speech`) is used for TTS, so no pywin32 or pyttsx3.
- Every OS-specific call goes in `winapi.py` (or `voice.py`) with a non-Windows fallback.
- Wrap anything that could crash the UI loop in `try/except` and log it with `log.exception`. Don't let one bad frame kill the pet.
- User-facing text is short, friendly and plain. Avatar phrases live in `BASE_LINES` / per-avatar `LINES`.
- Ruff: line length 110 (see `pyproject.toml`).
- To add an avatar in code, subclass `ImageAvatar` (copy `dog.py`), implement `paint()` and `params()`, add `anchors()` and `LINES`, and register it in `pet/avatars.py`. To add one as art, use a PNG sprite pack (`assets/avatars/_template`).
- Avatars must be original. Don't recreate trademarked or copyrighted characters or commercial product designs.

## Gotchas
- `tk.Toplevel.wm_frame()` gives the real top-level HWND; `winfo_id()` gives a child window.
- Tk font sizes are in points and are DPI-scaled; canvas geometry is in pixels. Multiply pixel sizes by `ToastManager.scale` (DPI) and the pet's `self.s`.
- `pystray` menus with dynamic `checked=`/`visible=` callables only refresh on `icon.update_menu()` (`Tray.refresh()`).
- The "Keep active" settings tab is hidden on purpose and shown with the ⚙ icon. Keep it out of the tray and pet menus.
