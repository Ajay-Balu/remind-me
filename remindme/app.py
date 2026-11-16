"""Main application: scheduler, idle tracking, mouse nudge, glue."""
import datetime as dt
import logging
import os
import queue
import sys
import time
import tkinter as tk
import traceback

from . import config, winapi
from .config import REMINDER_ORDER
from .toast import ToastManager
from .tray import Tray
from .voice import Voice

log = logging.getLogger("remindme")


def _fmt_secs(sec):
    sec = max(0, int(sec))
    if sec >= 3600:
        return f"{sec // 3600}h {sec % 3600 // 60}m"
    if sec >= 60:
        return f"{sec // 60}m"
    return f"{sec}s"


class App:
    TICK_MS = 1000

    def __init__(self):
        winapi.set_dpi_aware()
        self.cfg = config.load()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Remind Me")
        self.root.report_callback_exception = self._tk_error
        self.toasts = ToastManager(self.root, lambda: self.cfg)
        self.q = queue.Queue()
        self.tray = Tray(self)
        self.settings_win = None
        self.voice = Voice()
        self.pet = None

        now = time.time()
        self.next_due = {k: now + self._interval(k) for k in REMINDER_ORDER}
        self.active = {}            # kind -> open Toast
        self.paused_until = None    # None | epoch seconds | inf
        self.break_end = None
        self.break_toast = None
        self.stats_day = dt.date.today()
        self.stats = {k: 0 for k in REMINDER_ORDER}

        # idle tracking that ignores our own synthetic mouse input
        self._last_real_input = winapi.last_input_tick()
        self._seen_input = self._last_real_input
        self._jiggle_tick = None
        self.last_jiggle = 0.0
        self.jiggle_count = 0
        self.away_since = None
        self._ticks = 0

        winapi.keep_awake(self.cfg["jiggle"]["enabled"] and self.cfg["jiggle"]["prevent_sleep"])
        if self.cfg["start_with_windows"]:
            self._safe(winapi.set_start_with_windows, True)

    # ------------------------------------------------------------ plumbing
    def call(self, fn, *args):
        """Thread-safe: run fn(*args) on the Tk thread (used by the tray)."""
        self.q.put((fn, args))

    def _poll_queue(self):
        try:
            while True:
                fn, args = self.q.get_nowait()
                self._safe(fn, *args)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _safe(self, fn, *args):
        try:
            return fn(*args)
        except Exception:
            log.exception("error in %s", getattr(fn, "__name__", fn))

    def _tk_error(self, *exc):
        log.error("Tk callback error:\n%s", "".join(traceback.format_exception(*exc)))

    def run(self):
        self.tray.start()
        self.root.after(self.TICK_MS, self._tick)
        self.root.after(100, self._poll_queue)
        if self.cfg["pet"]["enabled"]:
            self.root.after(300, lambda: self.set_pet_enabled(True, announce=True))
        else:
            self.root.after(400, lambda: self.toasts.show(
                "success", "Remind Me is running",
                "It lives in the system tray (click ^ near the clock). "
                "Left-click the drop icon for settings.", "✅", duration=8))
        self.tray.refresh()
        self.root.mainloop()

    def quit(self):
        winapi.keep_awake(False)
        self.voice.stop()
        if self.pet:
            self._safe(self.pet.save_position)
        self.tray.stop()
        self.root.after(50, self.root.destroy)

    def save_cfg(self):
        self._safe(config.save, self.cfg)

    # ------------------------------------------------------------ avatar
    def set_pet_enabled(self, on, announce=False):
        from .pet.pet import Pet
        self.cfg["pet"]["enabled"] = on
        if on and self.pet is None:
            try:
                self.pet = Pet(self)
            except Exception:
                log.exception("could not start avatar")
                self.pet = None
                return
            self.pet.say(self.pet.avatar.line("intro"), duration=6, speak=announce)
        elif not on and self.pet is not None:
            for kind in list(self.active):
                self._close_active(kind)
            pet, self.pet = self.pet, None
            self._safe(pet.destroy)
            self.voice.stop()
            self.toasts.show("info", "Avatar hidden", "Turn it back on from the tray menu "
                             "(Show avatar) or Settings.", "\U0001F43E", duration=5)
        self.save_cfg()
        self.tray.refresh()

    def toggle_pet(self):
        self.set_pet_enabled(not self.cfg["pet"]["enabled"])

    def toggle_gravity(self):
        if self.pet:
            self.pet.toggle("gravity", not self.cfg["pet"].get("gravity", False))

    def toggle_follow(self):
        if self.pet:
            self.pet.toggle("follow_mouse", not self.cfg["pet"].get("follow_mouse", False))

    def _notify(self, kind, title, message, emoji, buttons=None, duration=None,
                on_close=None, speak=False, pet_text=None):
        """Show a message through the avatar if it's on, otherwise as a toast."""
        if self.pet is not None:
            return self.pet.say(pet_text or message, title=title, kind=kind, buttons=buttons,
                                duration=duration, on_close=on_close, speak=speak)
        return self.toasts.show(kind, title, message, emoji, buttons, duration=duration,
                                on_close=on_close)

    def _close_active(self, kind):
        t = self.active.pop(kind, None)
        if t is not None and not t.closed:
            t.close("replaced")

    # ------------------------------------------------------------ helpers
    def _interval(self, kind):
        return max(1, int(self.cfg["reminders"][kind]["interval_min"])) * 60

    def is_paused(self):
        return self.paused_until is not None

    def real_idle_seconds(self):
        return winapi.ticks_between(self._last_real_input, winapi.tick_count()) / 1000.0

    def _update_idle(self):
        last = winapi.last_input_tick()
        if last != self._seen_input:
            self._seen_input = last
            ours = (self._jiggle_tick is not None
                    and winapi.ticks_between(self._jiggle_tick, last) <= 1500)
            if not ours:
                self._last_real_input = last

    # ------------------------------------------------------------ main loop
    def _tick(self):
        try:
            self._tick_inner()
        except Exception:
            log.exception("tick failed")
        self.root.after(self.TICK_MS, self._tick)

    def _tick_inner(self):
        now = time.time()
        self._ticks += 1
        if dt.date.today() != self.stats_day:
            self.stats_day = dt.date.today()
            self.stats = {k: 0 for k in REMINDER_ORDER}

        self._update_idle()
        idle = self.real_idle_seconds()

        # away / back
        if idle >= self.cfg["away_after_min"] * 60:
            if self.away_since is None:
                self.away_since = now - idle
                if self.pet:
                    self.pet.sleep_away()
        elif self.away_since is not None:
            self._on_return(now, now - self.away_since)
            self.away_since = None
            if self.pet:
                self.pet.wake_up()

        # keep-active nudge (only while idle)
        j = self.cfg["jiggle"]
        if j["enabled"] and idle >= j["idle_seconds"] and now - self.last_jiggle >= j["idle_seconds"]:
            self.nudge(j["pixels"])

        # pause expiry
        if self.paused_until is not None and now >= self.paused_until:
            self.resume()

        # break countdown
        if self.break_end is not None:
            left = self.break_end - now
            if left <= 0:
                self.end_break(completed=True)
            elif self.break_toast:
                self.break_toast.set_message(self._break_text(left))

        # due reminders
        if not self.is_paused() and self.away_since is None and self.break_end is None:
            for kind in REMINDER_ORDER:
                r = self.cfg["reminders"][kind]
                if r["enabled"] and now >= self.next_due[kind] and kind not in self.active:
                    self.show_reminder(kind)
                    self.next_due[kind] = now + self._interval(kind)

        if self._ticks % 15 == 1:
            self.tray.refresh()

    def _on_return(self, now, away_secs):
        log.info("back after %.0fs away", away_secs)
        # you were away from the screen: eyes & posture got a rest
        for kind in ("blink", "posture"):
            self.next_due[kind] = now + self._interval(kind)
        if away_secs >= self.cfg["reminders"]["break"]["break_min"] * 60:
            self.next_due["break"] = now + self._interval("break")

    # ------------------------------------------------------------ mouse nudge
    def nudge(self, pixels=None):
        px = pixels or self.cfg["jiggle"]["pixels"]
        self._jiggle_tick = winapi.tick_count()
        winapi.nudge_mouse(px)
        self.last_jiggle = time.time()
        self.jiggle_count += 1

    def toggle_jiggle(self):
        j = self.cfg["jiggle"]
        j["enabled"] = not j["enabled"]
        winapi.keep_awake(j["enabled"] and j["prevent_sleep"])
        self._safe(config.save, self.cfg)
        self.tray.refresh()
        self._notify("info", "Keep active " + ("on" if j["enabled"] else "off"),
                     (f"I'll nudge the mouse {j['pixels']}px after {j['idle_seconds']}s idle."
                      if j["enabled"] else "The mouse won't be moved."),
                     "\U0001F5B1\uFE0F", duration=4)

    def jiggle_status(self):
        j = self.cfg["jiggle"]
        idle = self.real_idle_seconds()
        if not j["enabled"]:
            return f"Off  ·  you've been idle {_fmt_secs(idle)}"
        if idle < j["idle_seconds"]:
            nxt = j["idle_seconds"] - idle
        else:
            nxt = j["idle_seconds"] - (time.time() - self.last_jiggle)
        return (f"Idle {_fmt_secs(idle)}  ·  next nudge in {_fmt_secs(max(0, nxt))}  "
                f"·  {self.jiggle_count} nudges this session")

    # ------------------------------------------------------------ reminders
    def show_reminder(self, kind, preview=False):
        r = self.cfg["reminders"][kind]
        sn = self.cfg["snooze_min"]
        if not preview:
            self._close_active(kind)
        if kind == "break":
            buttons = [("Start break", self.start_break, True),
                       (f"Snooze {sn}m", lambda: self.snooze(kind)),
                       ("Skip", None)]
        else:
            buttons = [("Done", lambda: self.done(kind), True),
                       (f"Snooze {sn}m", lambda: self.snooze(kind))]
        auto = self.cfg["toast"]["auto_dismiss_sec"] or None

        def closed(_reason, k=kind):
            if self.active.get(k) is t:
                self.active.pop(k, None)

        if preview:
            t = self.toasts.show(kind, r["title"], r["message"], r["emoji"], buttons,
                                 duration=auto)
        else:
            pet_text = self.pet.avatar.line(kind) if self.pet else None
            t = self._notify(kind, r["title"], r["message"], r["emoji"], buttons, duration=auto,
                             on_close=closed, speak=True, pet_text=pet_text)
            self.active[kind] = t
            self.next_due[kind] = time.time() + self._interval(kind)
        if self.cfg["toast"]["sound"] and (self.pet is None or preview
                                           or not self.cfg["pet"]["voice"]["enabled"]):
            winapi.beep()
        return t

    def done(self, kind):
        self.stats[kind] += 1
        if self.pet:
            self.pet.react("done_water" if kind == "water" else "done")
        self.tray.refresh()

    def snooze(self, kind):
        self.next_due[kind] = time.time() + self.cfg["snooze_min"] * 60
        if self.pet:
            self.pet.react("snooze")

    def _break_text(self, secs):
        return (f"Step away from the screen, stretch, look outside.\n"
                f"{int(secs) // 60:02d}:{int(secs) % 60:02d} remaining")

    def start_break(self):
        mins = self.cfg["reminders"]["break"]["break_min"]
        self.break_end = time.time() + mins * 60
        for kind in list(self.active):
            self._close_active(kind)
        if self.pet:
            self.pet.react("break_start")
        self.break_toast = self._notify(
            "break", "Break time ☕", self._break_text(mins * 60), "\U0001F9D8",
            buttons=[("End break", lambda: self.end_break(completed=False))], duration=None)

    def end_break(self, completed):
        now = time.time()
        self.break_end = None
        if self.break_toast and not self.break_toast.closed:
            self.break_toast.close("done")
        self.break_toast = None
        self.stats["break"] += 1
        for kind in ("break", "blink", "posture"):
            self.next_due[kind] = now + self._interval(kind)
        if self.pet:
            self.pet.react("break_end")
        if completed:
            iv = self.cfg["reminders"]["break"]["interval_min"]
            pet_text = (self.pet.avatar.line("break_over") + f" Next break in {iv} minutes."
                        if self.pet else None)
            self._notify("success", "Break over \U0001F389",
                         f"Welcome back! Your next break is in {iv} min.", "\U0001F4AA",
                         duration=8, speak=True, pet_text=pet_text)
            if self.cfg["toast"]["sound"] and self.pet is None:
                winapi.beep()
        self.tray.refresh()

    # ------------------------------------------------------------ pause
    def pause(self, minutes):
        self.paused_until = float("inf") if minutes is None else time.time() + minutes * 60
        for kind in list(self.active):
            self._close_active(kind)
        self.tray.refresh()
        msg = "until you resume" if minutes is None else f"for {_fmt_secs(minutes * 60)}"
        self._notify("info", "Reminders paused", f"Reminders paused {msg}.", "⏸️", duration=5)

    def resume(self):
        self.paused_until = None
        now = time.time()
        for k in REMINDER_ORDER:
            self.next_due[k] = now + self._interval(k)
        self.tray.refresh()

    # ------------------------------------------------------------ settings
    def open_settings(self):
        from .settings_window import SettingsWindow
        if self.settings_win is not None:
            self.settings_win.focus()
            return
        self.settings_win = SettingsWindow(self)

    def apply_settings(self, new_cfg, persist=True):
        now = time.time()
        for k in REMINDER_ORDER:
            old_iv = self.cfg["reminders"][k]["interval_min"]
            if new_cfg["reminders"][k]["interval_min"] != old_iv or (
                    new_cfg["reminders"][k]["enabled"] and not self.cfg["reminders"][k]["enabled"]):
                self.next_due[k] = now + new_cfg["reminders"][k]["interval_min"] * 60
        startup_changed = new_cfg["start_with_windows"] != self.cfg["start_with_windows"]
        pet_on = new_cfg["pet"]["enabled"]
        if self.pet is not None:  # keep position the pet has now
            new_cfg["pet"]["x"], new_cfg["pet"]["y"] = int(self.pet.x), int(self.pet.y)
        self.cfg = new_cfg
        if pet_on != (self.pet is not None):
            self.set_pet_enabled(pet_on)
        elif self.pet is not None:
            self.pet.apply_config()
        j = new_cfg["jiggle"]
        winapi.keep_awake(j["enabled"] and j["prevent_sleep"])
        if persist:
            self._safe(config.save, new_cfg)
            if startup_changed:
                self._safe(winapi.set_start_with_windows, new_cfg["start_with_windows"])
        self.tray.refresh()

    def reload_saved_appearance(self):
        self.cfg["toast"] = config.load()["toast"]

    # ------------------------------------------------------------ tray text
    def _next_up(self):
        now = time.time()
        due = [(self.next_due[k] - now, k) for k in REMINDER_ORDER
               if self.cfg["reminders"][k]["enabled"]]
        return min(due) if due else None

    def status_line(self):
        if self.break_end is not None:
            return f"On a break – {_fmt_secs(self.break_end - time.time())} left"
        if self.is_paused():
            if self.paused_until == float("inf"):
                return "Reminders paused"
            return f"Paused – resumes in {_fmt_secs(self.paused_until - time.time())}"
        nxt = self._next_up()
        if not nxt:
            return "All reminders off"
        secs, kind = nxt
        return f"Next: {self.cfg['reminders'][kind]['title']} in {_fmt_secs(secs)}"

    def tooltip(self):
        return (f"Remind Me – {self.status_line()}\n"
                f"Water today: {self.stats['water']}")


def _setup_logging():
    path = os.path.join(config.config_dir(), "remindme.log")
    logging.basicConfig(filename=path, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    sys.excepthook = lambda *e: log.error("Uncaught:\n%s",
                                          "".join(traceback.format_exception(*e)))


def main():
    _setup_logging()
    if not winapi.single_instance():
        return
    log.info("starting")
    App().run()
