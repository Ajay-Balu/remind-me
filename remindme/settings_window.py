"""Settings dialog (Tkinter / ttk)."""
import copy
import tkinter as tk
from tkinter import ttk

from .config import REMINDER_ORDER
from .pet.avatars import AVATARS

POSITIONS = ["bottom-right", "bottom-left", "bottom-center", "top-right", "top-center"]
LABELS = {"water": "\U0001F4A7  Drink water", "blink": "\U0001F440  Rest eyes (20-20-20)",
          "posture": "\U0001F9CD  Posture check", "break": "☕  Take a break"}


def _int(var, lo, hi, default):
    try:
        v = int(float(var.get()))
    except (tk.TclError, ValueError):
        return default
    return max(lo, min(hi, v))


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        cfg = app.cfg
        self.win = w = tk.Toplevel(app.root)
        w.title("Remind Me – Settings")
        w.resizable(False, False)
        w.protocol("WM_DELETE_WINDOW", self.close)
        try:
            from PIL import ImageTk
            from .tray import make_icon
            self._ico = ImageTk.PhotoImage(make_icon(size=64))
            w.iconphoto(False, self._ico)
        except Exception:
            pass

        style = ttk.Style(w)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Hint.TLabel", foreground="#6b7280")
        style.configure("Head.TLabel", font=("Segoe UI", 10, "bold"))

        outer = ttk.Frame(w, padding=14)
        outer.pack(fill="both", expand=True)
        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)

        # ---------------------------------------------------------- Reminders
        tab = ttk.Frame(nb, padding=14)
        nb.add(tab, text="Reminders")
        ttk.Label(tab, text="Reminder", style="Head.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(tab, text="Every (min)", style="Head.TLabel").grid(row=0, column=1, padx=10)
        self.rem_vars = {}
        row = 1
        for kind in REMINDER_ORDER:
            r = cfg["reminders"][kind]
            en = tk.BooleanVar(value=r["enabled"])
            iv = tk.StringVar(value=str(r["interval_min"]))
            ttk.Checkbutton(tab, text=LABELS[kind], variable=en).grid(
                row=row, column=0, sticky="w", pady=4)
            ttk.Spinbox(tab, from_=1, to=480, textvariable=iv, width=6).grid(
                row=row, column=1, padx=10)
            self.rem_vars[kind] = (en, iv)
            row += 1

        ttk.Separator(tab).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        row += 1
        self.break_min = tk.StringVar(value=str(cfg["reminders"]["break"]["break_min"]))
        self.snooze = tk.StringVar(value=str(cfg["snooze_min"]))
        self.away = tk.StringVar(value=str(cfg["away_after_min"]))
        for label, var, hi in (("Break length (min)", self.break_min, 60),
                               ("Snooze (min)", self.snooze, 120),
                               ("I'm away after idle (min)", self.away, 120)):
            ttk.Label(tab, text=label).grid(row=row, column=0, sticky="w", pady=3)
            ttk.Spinbox(tab, from_=1, to=hi, textvariable=var, width=6).grid(
                row=row, column=1, padx=10)
            row += 1
        ttk.Label(tab, style="Hint.TLabel", wraplength=330, justify="left",
                  text="While you're away, reminders wait. Being away for at least a break's "
                       "length counts as a break.").grid(row=row, column=0, columnspan=3,
                                                         sticky="w", pady=(8, 0))

        # ---------------------------------------------------------- Keep active
        tab = ttk.Frame(nb, padding=14)
        nb.add(tab, text="Keep active")
        self._ka_tab = tab
        j = cfg["jiggle"]
        self.j_en = tk.BooleanVar(value=j["enabled"])
        self.j_sec = tk.StringVar(value=str(j["idle_seconds"]))
        self.j_px = tk.StringVar(value=str(j["pixels"]))
        self.j_sleep = tk.BooleanVar(value=j["prevent_sleep"])
        ttk.Checkbutton(tab, text="Nudge the mouse when I'm idle", variable=self.j_en).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(tab, text="Nudge after idle for (seconds)").grid(row=1, column=0, sticky="w",
                                                                   pady=(10, 3))
        ttk.Spinbox(tab, from_=5, to=3600, increment=5, textvariable=self.j_sec, width=7).grid(
            row=1, column=1, padx=10, pady=(10, 3))
        ttk.Label(tab, text="Move distance (pixels)").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Spinbox(tab, from_=1, to=200, textvariable=self.j_px, width=7).grid(
            row=2, column=1, padx=10)
        ttk.Checkbutton(tab, text="Also stop Windows from sleeping / turning off the screen",
                        variable=self.j_sleep).grid(row=3, column=0, columnspan=2, sticky="w",
                                                    pady=(10, 0))
        ttk.Label(tab, style="Hint.TLabel", wraplength=330, justify="left",
                  text="Only runs while you're idle - it never moves the pointer while you "
                       "work. The pointer moves out and returns to the same spot.").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.j_status = ttk.Label(tab, text="", foreground="#2563eb")
        self.j_status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Button(tab, text="Test nudge now", command=self._test_nudge).grid(
            row=6, column=0, sticky="w", pady=(10, 0))

        # ---------------------------------------------------------- Avatar
        tab = ttk.Frame(nb, padding=14)
        nb.add(tab, text="Avatar")
        pc = cfg["pet"]
        vc = pc["voice"]
        self.p_en = tk.BooleanVar(value=pc["enabled"])
        self.p_av = tk.StringVar(value=AVATARS.get(pc["avatar"], AVATARS["dog"]).label)
        self.p_size = tk.StringVar(value=f"{pc['size']}%")
        self.p_roam = tk.BooleanVar(value=pc["roam"])
        self.p_follow = tk.BooleanVar(value=pc["follow_mouse"])
        self.v_en = tk.BooleanVar(value=vc["enabled"])
        self.v_react = tk.BooleanVar(value=vc.get("reactions", False))
        self.v_name = tk.StringVar()
        self.v_rate = tk.IntVar(value=vc["rate"])
        self.v_vol = tk.IntVar(value=vc["volume"])
        r = 0
        ttk.Checkbutton(tab, text="Show the avatar (reminders appear in its speech bubble)",
                        variable=self.p_en).grid(row=r, column=0, columnspan=3, sticky="w")
        r += 1
        ttk.Label(tab, text="Avatar").grid(row=r, column=0, sticky="w", pady=(10, 3))
        ttk.Combobox(tab, textvariable=self.p_av, state="readonly", width=18,
                     values=[c.label for c in AVATARS.values()]).grid(
            row=r, column=1, columnspan=2, sticky="w", padx=10, pady=(10, 3))
        r += 1
        ttk.Label(tab, text="Size").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Combobox(tab, textvariable=self.p_size, state="readonly", width=8,
                     values=["75%", "100%", "125%", "150%", "200%"]).grid(
            row=r, column=1, sticky="w", padx=10)
        r += 1
        ttk.Checkbutton(tab, text="Walk around the screen", variable=self.p_roam).grid(
            row=r, column=0, columnspan=3, sticky="w", pady=(6, 0))
        r += 1
        ttk.Checkbutton(tab, text="Follow my mouse", variable=self.p_follow).grid(
            row=r, column=0, columnspan=3, sticky="w")
        r += 1
        self.p_grav = tk.BooleanVar(value=pc.get("gravity", False))
        self.p_garden = tk.BooleanVar(value=pc.get("garden_on", True))
        ttk.Checkbutton(tab, text="Gravity: live on top of the taskbar",
                        variable=self.p_grav).grid(row=r, column=0, columnspan=3, sticky="w")
        r += 1
        gf = ttk.Frame(tab)
        gf.grid(row=r, column=0, columnspan=3, sticky="w", padx=(22, 0))
        ttk.Checkbutton(gf, text="Let it plant and water a little garden",
                        variable=self.p_garden).pack(side="left")
        ttk.Button(gf, text="Clear garden", command=self._clear_garden).pack(side="left",
                                                                             padx=8)
        r += 1
        ttk.Separator(tab).grid(row=r, column=0, columnspan=3, sticky="ew", pady=10)
        r += 1
        ttk.Checkbutton(tab, text="Speak reminders out loud", variable=self.v_en).grid(
            row=r, column=0, columnspan=3, sticky="w")
        r += 1
        ttk.Checkbutton(tab, text="Also speak reactions (\"Ouch!\", \"Hahaha\")",
                        variable=self.v_react).grid(row=r, column=0, columnspan=3, sticky="w")
        r += 1
        ttk.Label(tab, text="Voice").grid(row=r, column=0, sticky="w", pady=(8, 3))
        self.v_combo = ttk.Combobox(tab, textvariable=self.v_name, state="readonly", width=34)
        self.v_combo.grid(row=r, column=1, columnspan=2, sticky="w", padx=10, pady=(8, 3))
        r += 1
        ttk.Label(tab, text="Speed").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Scale(tab, from_=-5, to=5, variable=self.v_rate, orient="horizontal",
                  length=160, command=lambda v: self.v_rate.set(round(float(v)))).grid(
            row=r, column=1, columnspan=2, sticky="w", padx=10)
        r += 1
        ttk.Label(tab, text="Volume").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Scale(tab, from_=0, to=100, variable=self.v_vol, orient="horizontal",
                  length=160, command=lambda v: self.v_vol.set(round(float(v)))).grid(
            row=r, column=1, columnspan=2, sticky="w", padx=10)
        r += 1
        ttk.Button(tab, text="Test voice", command=self._test_voice).grid(
            row=r, column=0, sticky="w", pady=(10, 0))
        r += 1
        ttk.Label(tab, style="Hint.TLabel", wraplength=340, justify="left",
                  text="Voices come from Windows' desktop speech voices (e.g. Microsoft David, "
                       "Zira). Some voices added in Windows Settings > Speech may not appear.").grid(
            row=r, column=0, columnspan=3, sticky="w", pady=(10, 0))
        self._voice_names = {}
        self._fill_voices()

        # ---------------------------------------------------------- General
        tab = ttk.Frame(nb, padding=14)
        nb.add(tab, text="Appearance & startup")
        t = cfg["toast"]
        self.t_pos = tk.StringVar(value=t["position"])
        self.t_theme = tk.StringVar(value=t["theme"])
        self.t_auto = tk.StringVar(value=str(t["auto_dismiss_sec"]))
        self.t_sound = tk.BooleanVar(value=t["sound"])
        self.startup = tk.BooleanVar(value=cfg["start_with_windows"])
        ttk.Label(tab, text="Toast position").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Combobox(tab, textvariable=self.t_pos, values=POSITIONS, state="readonly",
                     width=15).grid(row=0, column=1, padx=10, sticky="w")
        ttk.Label(tab, text="Theme").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Combobox(tab, textvariable=self.t_theme, values=["light", "dark"], state="readonly",
                     width=15).grid(row=1, column=1, padx=10, sticky="w")
        ttk.Label(tab, text="Auto-hide after (sec, 0 = never)").grid(row=2, column=0, sticky="w",
                                                                     pady=3)
        ttk.Spinbox(tab, from_=0, to=3600, increment=5, textvariable=self.t_auto, width=7).grid(
            row=2, column=1, padx=10, sticky="w")
        ttk.Checkbutton(tab, text="Play a sound", variable=self.t_sound).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Checkbutton(tab, text="Start Remind Me when Windows starts",
                        variable=self.startup).grid(row=4, column=0, columnspan=2, sticky="w",
                                                    pady=(4, 0))
        ttk.Button(tab, text="Preview toast", command=self._preview).grid(
            row=5, column=0, sticky="w", pady=(14, 0))

        # ---------------------------------------------------------- footer
        foot = ttk.Frame(outer)
        foot.pack(fill="x", pady=(12, 0))
        # the "Keep active" tab stays tucked away behind this small icon
        self._nb = nb
        nb.hide(self._ka_tab)
        gear = tk.Label(foot, text="\u2699", fg="#9ca3af", cursor="hand2",
                        font=("Segoe UI Symbol", 9))
        gear.pack(side="left")
        gear.bind("<Button-1>", lambda e: self._toggle_hidden_tab())
        ttk.Button(foot, text="Save", command=self.save).pack(side="right")
        ttk.Button(foot, text="Cancel", command=self.close).pack(side="right", padx=8)

        self._status_loop()
        w.update_idletasks()
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        w.geometry(f"+{(sw - w.winfo_width()) // 2}+{(sh - w.winfo_height()) // 3}")
        w.lift()
        w.focus_force()

    # ------------------------------------------------------------ helpers
    def collect(self):
        cfg = copy.deepcopy(self.app.cfg)
        for kind, (en, iv) in self.rem_vars.items():
            r = cfg["reminders"][kind]
            r["enabled"] = bool(en.get())
            r["interval_min"] = _int(iv, 1, 480, r["interval_min"])
        b = cfg["reminders"]["break"]
        b["break_min"] = _int(self.break_min, 1, 60, b["break_min"])
        cfg["snooze_min"] = _int(self.snooze, 1, 120, cfg["snooze_min"])
        cfg["away_after_min"] = _int(self.away, 1, 120, cfg["away_after_min"])
        j = cfg["jiggle"]
        j["enabled"] = bool(self.j_en.get())
        j["idle_seconds"] = _int(self.j_sec, 5, 3600, j["idle_seconds"])
        j["pixels"] = _int(self.j_px, 1, 200, j["pixels"])
        j["prevent_sleep"] = bool(self.j_sleep.get())
        t = cfg["toast"]
        t["position"] = self.t_pos.get() if self.t_pos.get() in POSITIONS else t["position"]
        t["theme"] = self.t_theme.get() if self.t_theme.get() in ("light", "dark") else t["theme"]
        t["auto_dismiss_sec"] = _int(self.t_auto, 0, 3600, t["auto_dismiss_sec"])
        t["sound"] = bool(self.t_sound.get())
        cfg["start_with_windows"] = bool(self.startup.get())
        pc = cfg["pet"]
        pc["enabled"] = bool(self.p_en.get())
        for key, cls in AVATARS.items():
            if cls.label == self.p_av.get():
                pc["avatar"] = key
        try:
            pc["size"] = max(50, min(200, int(self.p_size.get().rstrip("%"))))
        except ValueError:
            pass
        pc["roam"] = bool(self.p_roam.get())
        pc["follow_mouse"] = bool(self.p_follow.get())
        pc["gravity"] = bool(self.p_grav.get())
        pc["garden_on"] = bool(self.p_garden.get())
        if self.app.pet is not None:
            pc["garden"] = self.app.cfg["pet"].get("garden", [])
        v = pc["voice"]
        v["enabled"] = bool(self.v_en.get())
        v["reactions"] = bool(self.v_react.get())
        v["name"] = self._voice_names.get(self.v_name.get(), v.get("name", ""))
        v["rate"] = _int(self.v_rate, -10, 10, 0)
        v["volume"] = _int(self.v_vol, 0, 100, 90)
        return cfg

    def _toggle_hidden_tab(self):
        if self._nb.tab(self._ka_tab, "state") == "hidden":
            self._nb.add(self._ka_tab)
            self._nb.select(self._ka_tab)
        else:
            self._nb.hide(self._ka_tab)

    def _clear_garden(self):
        if self.app.pet is not None:
            self.app.pet.garden.clear()
        else:
            self.app.cfg["pet"]["garden"] = []
            self.app.save_cfg()

    # ------------------------------------------------------------ voices
    DEFAULT_VOICE = "(Windows default)"

    def _fill_voices(self):
        if not self.win.winfo_exists():
            return
        voices = self.app.voice.voices
        if voices is None:
            self.v_combo.configure(values=["Loading voices…"])
            self.v_name.set("Loading voices…")
            self.win.after(500, self._fill_voices)
            return
        self._voice_names = {self.DEFAULT_VOICE: ""}
        for v in voices:
            self._voice_names[self.app.voice.label(v)] = v["name"]
        self.v_combo.configure(values=list(self._voice_names))
        current = self.app.cfg["pet"]["voice"].get("name", "")
        label = next((k for k, n in self._voice_names.items() if n == current),
                     self.DEFAULT_VOICE)
        self.v_name.set(label)

    def _test_voice(self):
        name = getattr(self, "_voice_names", {}).get(self.v_name.get(), "")
        av = AVATARS.get(self.app.cfg["pet"]["avatar"], AVATARS["dog"])()
        self.app.voice.speak(av.line("water"), name, _int(self.v_rate, -10, 10, 0),
                             _int(self.v_vol, 0, 100, 90))

    def _status_loop(self):
        if not self.win.winfo_exists():
            return
        self.j_status.configure(text=self.app.jiggle_status())
        self.win.after(1000, self._status_loop)

    def _test_nudge(self):
        px = _int(self.j_px, 1, 200, 1)
        self.app.nudge(px)

    def _preview(self):
        # temporarily apply only the look; reverted on Cancel
        self.app.cfg["toast"] = self.collect()["toast"]
        self.app.show_reminder("water", preview=True)

    def save(self):
        self.app.apply_settings(self.collect(), persist=True)
        self.close()

    def close(self):
        if self.app.settings_win is self:
            self.app.settings_win = None
        # undo un-saved preview changes
        self.app.reload_saved_appearance()
        self.win.destroy()

    def focus(self):
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()
