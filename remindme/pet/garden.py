"""A little garden on top of the taskbar (gravity mode).

Each plant is a tiny always-on-top window sitting on the taskbar edge.
Stages: 0 hole, 1 seed planted, 2 sprout, 3 young plant, 4 bud, 5 flower.
Plants grow one stage each time the pet waters them (at most once per
GROW_EVERY seconds). Saved in config["pet"]["garden"].
"""
import math
import random
import time
import tkinter as tk

from PIL import Image, ImageDraw, ImageFilter, ImageTk

from .. import winapi
from ..toast import IS_WIN, KEY

MAX_PLANTS = 6
GROW_EVERY = 15 * 60          # seconds between growth steps
FLOWERS = ["#f472b6", "#f87171", "#facc15", "#a78bfa", "#fb923c", "#60a5fa", "#f9fafb"]
PW, PH = 46, 74               # logical plant window size (scaled by pet scale)
SS = 3

_IMG_CACHE = {}


def _render(stage, color, w, h, seed):
    """Draw one plant image with Pillow (supersampled, binary alpha)."""
    key = (stage, color, w, h, seed)
    if key in _IMG_CACHE:
        return _IMG_CACHE[key]
    W, H = w * SS, h * SS
    k = W / PW
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)

    def P(x, y):
        return x * k, y * k

    def ell(cx, cy, rx, ry, fill, ang=0):
        if ang:
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            pts = [P(cx + rx * math.cos(t) * ca - ry * math.sin(t) * sa,
                     cy + rx * math.cos(t) * sa + ry * math.sin(t) * ca)
                   for t in [i * math.pi / 18 for i in range(36)]]
            d.polygon(pts, fill=fill)
        else:
            d.ellipse((*P(cx - rx, cy - ry), *P(cx + rx, cy + ry)), fill=fill)

    ground = PH - 4
    # soil mound
    ell(23, ground, 16, 5.5, "#5b3a1e")
    ell(23, ground - 0.8, 14.5, 4.4, "#7a5230")
    ell(20, ground - 2, 8, 2, "#9a6b40")
    for _ in range(10):
        x, y = rnd.uniform(10, 36), rnd.uniform(ground - 3, ground + 2)
        ell(x, y, 0.9, 0.7, "#4a2e18")
    if stage == 0:
        ell(23, ground - 1.4, 6, 2.2, "#2b1a0c")
    elif stage == 1:
        ell(23, ground - 2.6, 5, 1.6, "#8b5e34")
        ell(24, ground - 3.6, 1.2, 0.8, "#d6a756")
    if stage >= 2:
        heights = {2: 10, 3: 24, 4: 40, 5: 46}
        top = ground - heights[stage]
        sway = rnd.uniform(-2, 2)
        stem = [P(23, ground - 2), P(23 + sway * 0.5, (ground + top) / 2), P(23 + sway, top)]
        d.line(stem, fill="#2f7d32", width=int(2.2 * k), joint="curve")
        leaf_c, leaf_dk = "#4caf50", "#2e7d32"
        if stage == 2:
            ell(19.5, top + 1, 4.5, 2.2, leaf_c, -25)
            ell(26.5 + sway, top + 1, 4.5, 2.2, leaf_c, 25)
        else:
            n = 2 if stage == 3 else 3
            for i in range(n):
                y = ground - 6 - i * (heights[stage] - 10) / n
                ell(17.5, y, 5.5, 2.4, leaf_dk if i % 2 else leaf_c, -30)
                ell(28.5 + sway * 0.4, y - 3, 5.5, 2.4, leaf_c if i % 2 else leaf_dk, 30)
        if stage == 4:
            ell(23 + sway, top - 2, 3.2, 4.4, "#3f9142")
            ell(23 + sway, top - 4.5, 2.2, 2.2, color)
        if stage == 5:
            cx, cy = 23 + sway, top - 3
            for i in range(8):
                a = i * math.pi / 4
                ell(cx + math.cos(a) * 5.2, cy + math.sin(a) * 5.2, 4.2, 2.6, color,
                    math.degrees(a))
            ell(cx, cy, 3.4, 3.4, "#f59e0b")
            ell(cx - 0.8, cy - 0.8, 1.2, 1.2, "#fde68a")

    img = img.filter(ImageFilter.SMOOTH)
    img = img.resize((w, h), Image.LANCZOS)
    bg = Image.new("RGBA", img.size, (60, 40, 20, 255))
    solid = Image.alpha_composite(bg, img)
    solid.putalpha(img.getchannel("A").point(lambda v: 255 if v >= 110 else 0))
    _IMG_CACHE[key] = solid
    return solid


class Plant:
    def __init__(self, garden, data):
        self.g = garden
        self.data = data
        self.photo = None
        self.win = w = tk.Toplevel(garden.root)
        w.withdraw()
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        keycol = KEY if IS_WIN else "#000001"
        w.configure(bg=keycol)
        if IS_WIN:
            w.attributes("-transparentcolor", KEY)
        self.c = tk.Canvas(w, bg=keycol, highlightthickness=0, bd=0)
        self.c.pack()
        self.c.bind("<ButtonPress-3>", self._menu)
        self.c.bind("<ButtonPress-1>", lambda e: self._wiggle())
        self.redraw()
        w.update_idletasks()
        winapi.make_no_activate(w)

    @property
    def stage(self):
        return self.data.get("stage", 0)

    def size(self):
        s = self.g.pet.s
        return int(PW * s), int(PH * s)

    def screen_x(self):
        left, _, right, _ = winapi.work_area(self.g.root)
        return left + self.data["x"] * (right - left)

    def redraw(self):
        w, h = self.size()
        img = _render(self.stage, self.data.get("color", FLOWERS[0]), w, h,
                      self.data.get("seed", 1))
        self.photo = ImageTk.PhotoImage(img)
        self.c.configure(width=w, height=h)
        self.c.delete("all")
        self.c.create_image(0, 0, image=self.photo, anchor="nw")
        self.place()

    def place(self):
        w, h = self.size()
        _, _, _, bottom = winapi.work_area(self.g.root)
        x = int(self.screen_x() - w / 2)
        y = int(bottom - h + 3 * self.g.pet.s)
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def show(self):
        self.place()
        self.win.deiconify()

    def hide(self):
        self.win.withdraw()

    def _wiggle(self, n=6):
        if n <= 0:
            self.place()
            return
        w, h = self.size()
        _, _, _, bottom = winapi.work_area(self.g.root)
        x = int(self.screen_x() - w / 2 + (2 if n % 2 else -2))
        self.win.geometry(f"+{x}+{int(bottom - h + 3 * self.g.pet.s)}")
        self.win.after(40, self._wiggle, n - 1)

    def _menu(self, e):
        m = tk.Menu(self.win, tearoff=0)
        names = {0: "Hole", 1: "Seed", 2: "Sprout", 3: "Young plant", 4: "Bud", 5: "Flower"}
        m.add_command(label=names.get(self.stage, "Plant"), state="disabled")
        m.add_separator()
        m.add_command(label="Water it now", command=lambda: self.g.pet.start_job("water", self))
        m.add_command(label="Pull it out", command=lambda: self.g.remove(self))
        m.add_command(label="Clear the whole garden", command=self.g.clear)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class Garden:
    def __init__(self, pet):
        self.pet = pet
        self.root = pet.root
        self.plants = []
        self.visible = False
        for data in list(self.cfg_list()):
            try:
                self.plants.append(Plant(self, data))
            except Exception:
                pass

    def cfg_list(self):
        return self.pet.cfg.setdefault("garden", [])

    def save(self):
        self.pet.cfg["garden"] = [p.data for p in self.plants]
        self.pet.app.save_cfg()

    # ------------------------------------------------------------ visibility
    def set_visible(self, on):
        self.visible = on
        for p in self.plants:
            p.show() if on else p.hide()

    def refresh(self):
        """Re-place (taskbar/resolution changes) and keep on top."""
        if not self.visible:
            return
        for p in self.plants:
            p.place()
            winapi.keep_on_top(p.win)

    def rescale(self):
        for p in self.plants:
            p.redraw()

    # ------------------------------------------------------------ plants
    def frac(self, screen_x):
        left, _, right, _ = winapi.work_area(self.root)
        return max(0.0, min(1.0, (screen_x - left) / max(1, right - left)))

    def free_spot(self, near_x=None):
        """Screen x for a new plant, away from existing ones."""
        left, _, right, _ = winapi.work_area(self.root)
        margin = self.pet.size * 0.6
        gap = PW * self.pet.s * 1.6
        for _ in range(40):
            x = random.uniform(left + margin, right - margin)
            if near_x is not None and random.random() < 0.5:
                x = max(left + margin, min(right - margin, near_x + random.uniform(-300, 300)))
            if all(abs(x - p.screen_x()) > gap for p in self.plants):
                return x
        return None

    def add(self, screen_x):
        data = {"x": self.frac(screen_x), "stage": 0, "color": random.choice(FLOWERS),
                "seed": random.randint(1, 9999), "watered": 0}
        p = Plant(self, data)
        self.plants.append(p)
        if self.visible:
            p.show()
        self.save()
        return p

    def set_stage(self, plant, stage):
        plant.data["stage"] = max(0, min(5, stage))
        plant.redraw()
        self.save()

    def water(self, plant):
        """Returns True if the plant grew."""
        now = time.time()
        grew = False
        if plant.stage in (0, 1) or now - plant.data.get("watered", 0) >= GROW_EVERY:
            if plant.stage < 5:
                plant.data["stage"] = max(2, plant.stage + 1)
                grew = True
        plant.data["watered"] = now
        plant.redraw()
        self.save()
        return grew

    def thirsty(self):
        now = time.time()
        return [p for p in self.plants
                if p.stage < 5 and now - p.data.get("watered", 0) >= GROW_EVERY]

    def nearest(self, plants, x):
        return min(plants, key=lambda p: abs(p.screen_x() - x)) if plants else None

    def remove(self, plant):
        if plant in self.plants:
            self.plants.remove(plant)
            plant.destroy()
            self.save()

    def clear(self):
        for p in list(self.plants):
            p.destroy()
        self.plants = []
        self.save()

    def destroy(self):
        for p in self.plants:
            p.destroy()
        self.plants = []
