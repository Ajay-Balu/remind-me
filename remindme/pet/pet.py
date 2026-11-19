"""The on-screen pet: window, behaviour state machine and mouse interaction."""
import logging
import math
import random
import time
import tkinter as tk
from collections import deque

from .. import winapi
from ..toast import IS_WIN, KEY
from .avatars import AVATARS, make_avatar
from .bubble import Bubble
from .garden import MAX_PLANTS, Garden
from .painter import LOGICAL, ORIGIN, Painter, Pose

log = logging.getLogger("remindme")

FRAME_MS = 33
WALK_SPEED = 70     # logical units / second
FOLLOW_SPEED = 260
GRAVITY = 2200      # logical units / s^2 when falling
FEET = (ORIGIN[1] + 112) / LOGICAL   # where the feet are, as a fraction of the window


class Pet:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.dpi = app.toasts.scale
        self.avatar = make_avatar(self.cfg["avatar"])

        self.win = w = tk.Toplevel(self.root)
        w.withdraw()
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        self._key = KEY if IS_WIN else "#000001"
        w.configure(bg=self._key)
        if IS_WIN:
            w.attributes("-transparentcolor", KEY)
        self.c = tk.Canvas(w, bg=self._key, highlightthickness=0, bd=0)
        self.c.pack()
        self._resize()
        self._warm()

        # position (window top-left, floats)
        left, top, right, bottom = winapi.work_area(self.root)
        x, y = self.cfg.get("x"), self.cfg.get("y")
        if x is None or y is None:
            x, y = right - self.size - 60, bottom - self.size
        self.x, self.y = self._clamp(x, y, winapi.virtual_screen(self.root))

        # behaviour
        self.state, self.state_t0, self.state_until = "idle", time.monotonic(), None
        self.facing = -1
        self.target = None
        self.phase = 0.0
        self.next_blink = time.monotonic() + 3
        self.blink_until = 0
        self.speak_until = 0
        self.hold_until = 0         # stay put after being dropped
        self.away_sleep = False
        self.anger = 0
        self.last_anger = 0
        self.follow_side = 1
        self.t0 = time.monotonic()
        self._last = time.monotonic()
        self._last_ontop = 0
        self.vy = 0.0
        self.dormant = False        # PC locked / lid closed: freeze, draw nothing new
        self.job = None             # gardening job
        self.garden = Garden(self)
        self._gravity_on = self.gravity
        self.garden.set_visible(self._gravity_on)
        if self._gravity_on:
            self.y = self.ground_y()

        # bubbles
        self.bubble = None
        self.queue = []

        # mouse
        self._press = None
        self._dragging = False
        self._moves = deque(maxlen=40)
        c = self.c
        c.bind("<ButtonPress-1>", self._on_press)
        c.bind("<B1-Motion>", self._on_drag)
        c.bind("<ButtonRelease-1>", self._on_release)
        c.bind("<Motion>", self._on_motion)
        c.bind("<ButtonPress-3>", self._on_menu)

        self._apply_geometry()
        w.update_idletasks()
        winapi.make_no_activate(w)
        w.deiconify()
        self._after = None
        self._loop()

    # ------------------------------------------------------------ config
    @property
    def cfg(self):
        return self.app.cfg["pet"]

    def _resize(self):
        self.s = self.dpi * max(50, min(200, int(self.cfg.get("size", 100)))) / 100.0
        self.size = int(LOGICAL * self.s)
        self.c.configure(width=self.size, height=self.size)

    @property
    def gravity(self):
        return bool(self.cfg.get("gravity", False))

    def ground_y(self):
        _, _, _, bottom = winapi.work_area(self.root)
        return bottom - self.size * FEET + 1 * self.s

    def hole_offset(self, facing):
        """Window-x offset of the spot right in front of the pet's nose."""
        return (ORIGIN[0] + 60 + 51 * facing) * self.s

    def _warm(self):
        from .illustrated import FRAMES, ImageAvatar
        if isinstance(self.avatar, ImageAvatar):
            FRAMES.warm(self.avatar, self.size)

    def apply_config(self):
        """Called after settings change (avatar, size...)."""
        if self.avatar.key != self.cfg["avatar"]:
            self.avatar = make_avatar(self.cfg["avatar"])
            self.say(self.avatar.line("intro"), duration=4)
        old = self.size
        self._resize()
        self._warm()
        if old != self.size:
            self.x += (old - self.size) / 2
            self.y += old - self.size
            self.garden.rescale()
            self._apply_geometry()
        if self.gravity != self._gravity_on:
            self._set_gravity(self.gravity, announce=False)

    def set_avatar(self, key):
        if key in AVATARS:
            self.cfg["avatar"] = key
            self.app.save_cfg()
            self.apply_config()
            self.set_state("hop", 0.7)

    # ------------------------------------------------------------ helpers
    def _clamp(self, x, y, area):
        l, t, r, b = area
        return (max(l - self.size * 0.3, min(r - self.size * 0.7, x)),
                max(t - self.size * 0.2, min(b - self.size * 0.8, y)))

    def _apply_geometry(self):
        self.win.geometry(f"{self.size}x{self.size}+{int(self.x)}+{int(self.y)}")
        if self.bubble and not self.bubble.closed and self.bubble.opened:
            self.place_bubble(self.bubble)

    def set_state(self, name, duration=None):
        self.state = name
        self.state_t0 = time.monotonic()
        self.state_until = self.state_t0 + duration if duration else None

    def busy(self):
        return bool(self.bubble and not self.bubble.closed and self.bubble.blocking)

    def center(self):
        return self.x + self.size / 2, self.y + self.size / 2

    def save_position(self):
        self.cfg["x"], self.cfg["y"] = int(self.x), int(self.y)
        self.app.save_cfg()

    # ------------------------------------------------------------ main loop
    def _loop(self):
        now = time.monotonic()
        if self.dormant:   # locked / lid closed: no animation, no CPU
            self._last = now
            self._after = self.win.after(1000, self._loop)
            return
        dt = min(0.1, now - self._last)
        self._last = now
        try:
            self._update(now, dt)
            self._render(now)
        except Exception:
            log.exception("pet frame failed")
        self._after = self.win.after(100 if self.state == "sleep" else FRAME_MS, self._loop)

    def _update(self, now, dt):
        if now >= self.next_blink:
            self.blink_until = now + 0.13
            self.next_blink = now + random.uniform(2.5, 5.5)
        if now - self._last_ontop > 1.5:
            self._last_ontop = now
            self._keep_visible()
        if self._dragging:
            return
        if self.state == "fall":
            self.vy += GRAVITY * self.s * dt
            self.y += self.vy * dt
            g = self.ground_y()
            if self.y >= g:
                self.y, self.vy = g, 0.0
                self.set_state("drop", 0.6)
                self.hold_until = now + random.uniform(20, 40)
                self.save_position()
            self._apply_geometry()
            return
        if self.state_until and now >= self.state_until:
            self._state_ended(now)

        st = self.state
        moving = False
        if self.busy():
            if st == "walk":
                self.job = None
                self.set_state("idle")
        elif self.cfg.get("follow_mouse") and st in ("idle", "walk") and not self.away_sleep \
                and not self.job:
            moving = self._follow(dt)
        elif st == "walk" and self.target:
            moving = self._walk_to(self.target, WALK_SPEED * self.s, dt)
            if not moving:
                if self.job:
                    self._job_arrived()
                else:
                    self.set_state("idle", random.uniform(4, 12))
        if moving:
            self.phase += dt * (16 if self.cfg.get("follow_mouse") else 10)
            self._apply_geometry()

    def _walk_to(self, target, speed, dt):
        tx, ty = target
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 3:
            return False
        if abs(dx) > 2:
            self.facing = 1 if dx > 0 else -1
        step = min(dist, speed * dt)
        self.x += dx / dist * step
        self.y += dy / dist * step
        if self.state != "walk":
            self.set_state("walk", 60)
        return True

    def _follow(self, dt):
        px, py = self.root.winfo_pointerxy()
        cx = self.x + self.size / 2
        # stand beside the pointer (never on top of it, so clicks still work)
        if abs(px - cx) > self.size:
            self.follow_side = -1 if px > cx else 1
        tx = px + self.follow_side * (self.size * 0.55) - self.size / 2
        ty = py - self.size * 0.65
        tx, ty = self._clamp(tx, ty, winapi.virtual_screen(self.root))
        if self.gravity:  # only follow sideways along the taskbar
            left, _, right, _ = winapi.work_area(self.root)
            tx = max(left - self.size * 0.3, min(right - self.size * 0.7, tx))
            ty = self.ground_y()
        if math.hypot(tx - self.x, ty - self.y) < 14 * self.s:
            if self.state == "walk":
                self.set_state("idle")
            self.facing = 1 if px > cx else -1
            return False
        return self._walk_to((tx, ty), FOLLOW_SPEED * self.s, dt)

    def _state_ended(self, now):
        st = self.state
        if st == "wake":
            self.set_state("happy", 1.4)
            self.say(self.avatar.line("wake"), duration=4)
            return
        if st == "drink":
            near = self.garden.nearest(self.garden.plants, self.center()[0])
            if self.gravity and self.cfg.get("garden_on", True) and near and not self.busy():
                self.start_job("water", near)   # share the water with a plant
            else:
                self.set_state("happy", 1.4)
            return
        if st in ("dig", "plant", "water"):
            self._job_step(st)
            return
        if st == "idle":
            self._choose_next(now)
            return
        self.set_state("idle", random.uniform(3, 9))

    def _choose_next(self, now):
        if (not self.cfg.get("roam", True) or self.cfg.get("follow_mouse") or self.busy()
                or now < self.hold_until):
            self.set_state("idle", random.uniform(4, 9))
            return
        r = random.random()
        if self.gravity and self.cfg.get("garden_on", True) and r < 0.22:
            if self._plan_garden_job():
                return
        if r < 0.62:
            left, top, right, bottom = winapi.work_area(self.root)
            if self.gravity:
                self.target = (random.uniform(left, right - self.size), self.ground_y())
            else:
                self.target = (random.uniform(left, right - self.size),
                               random.uniform(top + self.size * 0.2, bottom - self.size))
            self.set_state("walk", 60)
        elif r < 0.72:
            self.set_state("sleep", random.uniform(15, 35))  # little nap
        else:
            if random.random() < 0.5:
                self.facing *= -1
            self.set_state("idle", random.uniform(3, 8))

    # ------------------------------------------------------------ drawing
    def _render(self, now):
        c = self.c
        c.delete("all")
        st, t = self.state, now - self.state_t0
        g = now - self.t0
        ox = oy = 0.0
        if st == "walk":
            oy = -abs(math.sin(self.phase)) * 2.5
        elif st in ("happy", "hop"):
            oy = -abs(math.sin(t * 9)) * 12
        elif st == "laugh":
            oy = -abs(math.sin(t * 14)) * 5
            ox = math.sin(t * 20) * 1.5
        elif st == "angry":
            ox = math.sin(t * 45) * (2 + self.anger)
        elif st == "drop":
            oy = -abs(math.sin(t * 2 * math.pi)) * 8 * max(0, 1 - t / 0.6)
        elif st == "dig":
            ox = math.sin(g * 30) * 0.6
        pose = Pose(st, t, g, self.phase, now < self.blink_until, self.facing,
                    now < self.speak_until)
        p = Painter(c, self.s, (ORIGIN[0] + ox) * self.s, (ORIGIN[1] + oy) * self.s,
                    self.facing if self.avatar.mirror else 1)
        self.avatar.draw(p, pose)
        self.avatar.draw_effects(p, pose)

    # ------------------------------------------------------------ speech
    def say(self, text, title=None, kind="info", buttons=None, duration=3.5, on_close=None,
            speak=None):
        """Show a bubble. Reminders (with buttons) queue up; chatter is dropped
        while a reminder is open. Returns the Bubble (may be queued)."""
        if speak is None:
            speak = bool(buttons) or self.cfg["voice"].get("reactions", False)
        b = Bubble(self, kind, title, text, buttons, duration, on_close, speak)
        if self.busy():
            if buttons:
                self.queue.append(b)
            else:
                b.closed = True
            return b
        self._open(b)
        return b

    def _open(self, b):
        if self.bubble and not self.bubble.closed:
            self.bubble.close("replaced")
        self.bubble = b
        b.open()
        if b.blocking:
            if self.state in ("sleep", "walk", "idle"):
                self.away_sleep = False
                self.set_state("hop", 0.6)
            left, _, right, _ = winapi.work_area(self.root)
            self.facing = 1 if self.center()[0] < (left + right) / 2 else -1
        if b.speak and self.cfg["voice"].get("enabled", True) and not self.dormant:
            v = self.cfg["voice"]
            self.app.voice.speak(b.text, v.get("name", ""), v.get("rate", 0), v.get("volume", 90))
            self.speak_until = time.monotonic() + self.app.voice.estimate_seconds(
                b.text, v.get("rate", 0))
        else:
            self.speak_until = time.monotonic() + min(2.5, len(b.text) / 18)

    def bubble_closed(self, b, reason):
        if b in self.queue:
            self.queue.remove(b)
            return
        if b is self.bubble:
            self.bubble = None
            if reason in ("action", "dismiss"):
                self.app.voice.stop()
                self.speak_until = 0
            if self.queue:
                self.win.after(2200 if reason == "action" else 400, self._show_next)

    def _show_next(self):
        if self.busy():
            return
        while self.queue:
            b = self.queue.pop(0)
            if not b.closed:
                self._open(b)
                return

    def place_bubble(self, b):
        bw, bh = b.size()
        left, top, right, bottom = winapi.virtual_screen(self.root)
        cx = self.x + self.size / 2
        head_y = self.y + self.size * 0.12
        x = max(left + 4, min(right - bw - 4, cx - bw / 2))
        if head_y - bh >= top + 4:
            y, tail_top = head_y - bh, False
        else:
            y, tail_top = self.y + self.size * 0.95, True
        b.place(x, y, cx - x, tail_top)

    # ------------------------------------------------------------ reactions
    def react(self, event):
        av = self.avatar
        if event == "done_water":
            self.set_state("drink", 2.6)
            self.say(av.line("done_water"), duration=3)
        elif event == "done":
            self.set_state("happy", 1.6)
            self.say(av.line("done"), duration=2.5)
        elif event == "snooze":
            self.say(av.line("snooze"), duration=3)
        elif event == "break_start":
            self.set_state("stretch")
        elif event == "break_end":
            self.set_state("happy", 2)

    def set_dormant(self, on):
        """Freeze while the PC is locked / lid closed; wake up afterwards."""
        if on == self.dormant:
            return
        if on:
            self.job = None
            self._dragging = False
            if self.bubble and not self.bubble.closed and not self.bubble.blocking:
                self.bubble.close("dormant")
            if self.state not in ("sleep",):
                self.set_state("sleep")
            self.away_sleep = True
            try:
                self._render(time.monotonic())   # leave it drawn asleep
            except Exception:
                pass
            self.dormant = True
        else:
            self.dormant = False
            self._last = time.monotonic()
            if self.gravity:
                self.y = self.ground_y()       # the taskbar may have moved
                self._apply_geometry()
            self.wake_up()

    def sleep_away(self):
        if self.state not in ("held", "fall"):
            self.away_sleep = True
            self.job = None
            self.set_state("sleep")

    def wake_up(self):
        if self.away_sleep or self.state == "sleep":
            self.away_sleep = False
            self.set_state("wake", 1.5)

    # ------------------------------------------------------------ mouse
    def _on_press(self, e):
        self._press = (e.x_root, e.y_root, self.x, self.y)
        self._dragging = False

    def _on_drag(self, e):
        if not self._press:
            return
        px, py, wx, wy = self._press
        dx, dy = e.x_root - px, e.y_root - py
        if not self._dragging and math.hypot(dx, dy) > 6:
            self._dragging = True
            self.away_sleep = False
            self.job = None
            self.set_state("held")
        if self._dragging:
            self.x, self.y = self._clamp(wx + dx, wy + dy, winapi.virtual_screen(self.root))
            if dx:
                self.facing = 1 if dx > 0 else -1
            self._apply_geometry()

    def _on_release(self, e):
        if self._dragging:
            self._dragging = False
            self.target = None
            if self.gravity and self.y < self.ground_y() - 4:
                self.vy = 0.0
                self.set_state("fall")
                if random.random() < 0.5:
                    self.say(self.avatar.line("fall"), duration=1.8)
                return self._release_done()
            if self.gravity:
                self.y = self.ground_y()
                self._apply_geometry()
            self.set_state("drop", 0.6)
            self.hold_until = time.monotonic() + random.uniform(25, 45)
            self.save_position()
            if random.random() < 0.5:
                self.say(self.avatar.line("drop"), duration=2.5)
        else:
            self._poke()
        self._press = None

    def _release_done(self):
        self._press = None

    def _poke(self):
        now = time.monotonic()
        was_sleeping = self.state == "sleep"
        self.away_sleep = False
        self.anger = min(3, self.anger + 1) if now - self.last_anger < 4 else 1
        self.last_anger = now
        self.job = None
        self.set_state("angry", 1.8 + 0.5 * self.anger)
        self.say(self.avatar.line("angry_sleep" if was_sleeping else "angry"), duration=2.5)

    def _on_motion(self, e):
        if self._dragging or e.state & 0x0100:  # button 1 held
            return
        now = time.monotonic()
        self._moves.append((now, e.x_root, e.y_root))
        while self._moves and now - self._moves[0][0] > 1.2:
            self._moves.popleft()
        if self.state in ("laugh", "held", "angry", "drop", "fall") or len(self._moves) < 5:
            return
        flips = 0
        for axis in (1, 2):
            last_sign, n = 0, 0
            for a, b in zip(self._moves, list(self._moves)[1:]):
                d = b[axis] - a[axis]
                if abs(d) < 2:
                    continue
                sign = 1 if d > 0 else -1
                if last_sign and sign != last_sign:
                    n += 1
                last_sign = sign
            flips = max(flips, n)
        if flips >= 4:
            self._moves.clear()
            self.away_sleep = False
            self.job = None
            self.set_state("laugh", 2.6)
            self.say(self.avatar.line("laugh"), duration=2.5)

    def _on_menu(self, e):
        m = tk.Menu(self.win, tearoff=0)
        av = tk.StringVar(value=self.avatar.key)
        self._menu_vars = [av]
        sub = tk.Menu(m, tearoff=0)
        for key, cls in AVATARS.items():
            sub.add_radiobutton(label=cls.label, variable=av, value=key,
                                command=lambda k=key: self.set_avatar(k))
        m.add_cascade(label="Change avatar", menu=sub)
        for label, key in (("Follow my mouse", "follow_mouse"), ("Stay in one place", "stay")):
            val = (not self.cfg.get("roam", True)) if key == "stay" else self.cfg.get(key, False)
            v = tk.BooleanVar(value=val)
            self._menu_vars.append(v)
            m.add_checkbutton(label=label, variable=v,
                              command=lambda k=key, v=v: self.toggle(k, v.get()))
        gv = tk.BooleanVar(value=self.gravity)
        self._menu_vars.append(gv)
        m.add_checkbutton(label="Gravity (live on the taskbar)", variable=gv,
                          command=lambda: self.toggle("gravity", gv.get()))
        if self.gravity:
            gm = tk.Menu(m, tearoff=0)
            gm.add_command(label="Plant a flower now", command=self.plant_now)
            gm.add_command(label="Water the plants", command=self.water_now)
            gv2 = tk.BooleanVar(value=self.cfg.get("garden_on", True))
            self._menu_vars.append(gv2)
            gm.add_checkbutton(label="Let it garden on its own", variable=gv2,
                               command=lambda: self.toggle("garden_on", gv2.get()))
            gm.add_separator()
            gm.add_command(label="Clear the garden", command=self.garden.clear)
            m.add_cascade(label="Garden", menu=gm)
        vv = tk.BooleanVar(value=self.cfg["voice"].get("enabled", True))
        self._menu_vars.append(vv)
        m.add_checkbutton(label="Voice", variable=vv,
                          command=lambda: self.toggle("voice", vv.get()))
        m.add_separator()
        m.add_command(label="Remind me: drink water",
                      command=lambda: self.app.show_reminder("water"))
        m.add_command(label="Pause reminders 1 hour", command=lambda: self.app.pause(60))
        m.add_separator()
        m.add_command(label="Settings…", command=self.app.open_settings)
        m.add_command(label="Hide avatar", command=lambda: self.app.set_pet_enabled(False))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def toggle(self, key, value):
        av = self.avatar
        if key == "follow_mouse":
            self.cfg["follow_mouse"] = value
            self.say(av.line("follow_on" if value else "follow_off"), duration=2.5)
        elif key == "stay":
            self.cfg["roam"] = not value
            if value and self.state == "walk":
                self.set_state("idle")
            self.say(av.line("stay_on" if value else "stay_off"), duration=2.5)
        elif key == "voice":
            self.cfg["voice"]["enabled"] = value
            if not value:
                self.app.voice.stop()
        elif key == "gravity":
            self.cfg["gravity"] = value
            self._set_gravity(value)
        elif key == "garden_on":
            self.cfg["garden_on"] = value
        self.app.save_cfg()
        self.app.tray.refresh()

    # ------------------------------------------------------------ gravity & garden
    def _set_gravity(self, on, announce=True):
        self._gravity_on = on
        self.garden.set_visible(on)
        self.job = None
        if on:
            if self.y < self.ground_y() - 4 and self.state not in ("held",):
                self.vy = 0.0
                self.set_state("fall")
            else:
                self.y = self.ground_y()
                self._apply_geometry()
        else:
            self.set_state("hop", 0.7)
        if announce:
            self.say(self.avatar.line("gravity_on" if on else "gravity_off"), duration=3)

    def _keep_visible(self):
        """Stay above other windows / come back after Show desktop."""
        winapi.keep_on_top(self.win)
        if self.bubble and self.bubble.opened and not self.bubble.closed and self.bubble.win:
            winapi.keep_on_top(self.bubble.win)
        self.garden.refresh()
        if self.gravity and self.state not in ("held", "fall") and not self._dragging:
            g = self.ground_y()
            if self.y < g - 4:          # taskbar moved / was dropped mid-air
                self.vy = 0.0
                self.set_state("fall")
            elif abs(self.y - g) > 0.5:
                self.y = g
                self._apply_geometry()

    def _plan_garden_job(self):
        g = self.garden
        thirsty = g.thirsty()
        if thirsty and (random.random() < 0.7 or len(g.plants) >= MAX_PLANTS):
            return self.start_job("water", g.nearest(thirsty, self.center()[0]))
        if len(g.plants) < MAX_PLANTS:
            x = g.free_spot(self.center()[0])
            if x is not None:
                return self.start_job("new", x)
        return False

    def plant_now(self):
        if len(self.garden.plants) >= MAX_PLANTS:
            self.say("The garden is full! Pull a plant out first.", duration=3)
            return
        x = self.garden.free_spot(self.center()[0])
        if x is None:
            self.say("No room left on the taskbar!", duration=3)
        else:
            self.start_job("new", x)

    def water_now(self):
        plants = self.garden.thirsty() or self.garden.plants
        if plants:
            self.start_job("water", self.garden.nearest(plants, self.center()[0]))

    def start_job(self, kind, target):
        """kind 'new' (target = screen x) or 'water' (target = Plant)."""
        if not self.gravity or target is None:
            return False
        px = target.screen_x() if kind == "water" else target
        facing = 1 if self.center()[0] < px else -1
        tx = px - self.hole_offset(facing)
        left, _, right, _ = winapi.work_area(self.root)
        if tx < left - self.size * 0.3 or tx > right - self.size * 0.7:  # too close to edge
            facing = -facing
            tx = px - self.hole_offset(facing)
        self.away_sleep = False
        self.job = {"kind": kind, "plant": target if kind == "water" else None, "x": px,
                    "facing": facing}
        self.target = (tx, self.ground_y())
        self.set_state("walk", 60)
        return True

    def _job_arrived(self):
        j = self.job
        self.facing = j["facing"]
        if j["kind"] == "new":
            self.set_state("dig", 3.2)
            if random.random() < 0.6:
                self.say(self.avatar.line("dig"), duration=2.5)
        else:
            if j["plant"] not in self.garden.plants:
                self.job = None
                self.set_state("idle", 3)
                return
            self.set_state("water", 3.0)

    def _job_step(self, st):
        j = self.job
        if not j:
            self.set_state("idle", random.uniform(3, 8))
            return
        if st == "dig":
            j["plant"] = self.garden.add(j["x"])
            self.set_state("plant", 2.2)
        elif st == "plant":
            if j["plant"] in self.garden.plants:
                self.garden.set_stage(j["plant"], 1)
            self.set_state("water", 3.0)
        elif st == "water":
            plant = j["plant"]
            self.job = None
            if plant in self.garden.plants:
                grew = self.garden.water(plant)
                if j["kind"] == "new":
                    line = "planted"
                elif grew and plant.stage == 5:
                    line = "bloom"
                else:
                    line = "watered"
                self.say(self.avatar.line(line), duration=3)
            self.set_state("happy", 1.4)
            self.hold_until = time.monotonic() + random.uniform(8, 20)

    # ------------------------------------------------------------ teardown
    def destroy(self):
        for b in list(self.queue):
            b.close("hidden")
        if self.bubble:
            self.bubble.close("hidden")
        self.save_position()
        self.garden.destroy()
        if self._after:
            try:
                self.win.after_cancel(self._after)
            except tk.TclError:
                pass
        self.win.destroy()

