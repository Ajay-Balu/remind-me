"""Avatar base class, shared phrases and overlay effects (Zzz, anger mark...)."""
import math
import random

from .painter import eye_mode  # noqa: F401  (re-exported for avatars)

BASE_LINES = {
    "intro": ["Hi! I'm {name}. I'll keep you healthy today!"],
    "water": ["Time to drink some water!", "Hydration time! Grab a glass of water."],
    "blink": ["Rest your eyes: look at something far away for 20 seconds and blink slowly.",
              "Eye break! Look 20 feet away for 20 seconds."],
    "posture": ["Posture check! Shoulders back, sit up straight.",
                "Are you slouching? Sit up tall and relax your shoulders."],
    "break": ["Time for a break! Stand up and stretch your legs.",
              "You've worked hard. Let's take a short break!"],
    "angry": ["Hey! That hurts!", "Stop poking me!", "Grrr!", "Rude!", "Ouch!"],
    "angry_sleep": ["Hey! I was sleeping!", "Let me sleep!"],
    "laugh": ["Hahaha! That tickles!", "Hehe, stop it!", "Haha, no tickling!"],
    "wake": ["Welcome back!", "Oh, you're back! I missed you."],
    "done": ["Great job!", "Nice one!", "Well done!"],
    "done_water": ["Cheers! Gulp gulp gulp.", "Ahh, refreshing!"],
    "snooze": ["Okay, a few more minutes.", "Fine, I'll remind you again soon."],
    "break_over": ["Break's over. Let's get back to it!"],
    "drop": ["Whee!", "Nice spot!", "I like it here."],
    "follow_on": ["I'll follow you around!"],
    "follow_off": ["Okay, I'll wander on my own."],
    "stay_on": ["I'll stay right here."],
    "stay_off": ["Time to explore!"],
    "gravity_on": ["Whoa, gravity! I'll hang out on the taskbar."],
    "gravity_off": ["Wheee, I can float around again!"],
    "dig": ["Dig dig dig!", "Let's plant something!", "Time for some gardening!"],
    "planted": ["I planted a seed! Let's watch it grow.", "Seed planted!"],
    "watered": ["There you go, little plant.", "Grow big and strong!", "Splish splash!"],
    "bloom": ["Look! It bloomed!", "Our flower is blooming!"],
    "fall": ["Aaaah!", "Wheee!"],
}


class Avatar:
    key = "base"
    name = "Pet"
    label = "Pet"
    mirror = True          # flip the drawing when walking left
    LINES = {}

    def line(self, kind):
        options = self.LINES.get(kind) or BASE_LINES.get(kind) or [""]
        return random.choice(options).format(name=self.name)

    # anchors (logical units, facing right) used by shared effects
    head_top = (84, 22)
    mouth = (104, 64)
    eye_pos = (88, 42)

    def anchors(self, pose):
        return self.head_top, self.mouth, self.eye_pos

    def draw(self, p, pose):
        raise NotImplementedError

    # ------------------------------------------------------------ effects
    def draw_effects(self, p, pose):
        (hx, hy), (mx, my), (ex, ey) = self.anchors(pose)
        st, g, t = pose.state, pose.gt, pose.t
        if st == "sleep":
            for i in range(3):
                k = (g * 0.45 + i / 3.0) % 1.0
                shade = "#94a3b8" if k > 0.66 else "#64748b"
                p.text(hx + 8 + k * 22, max(-18, hy - 2 - k * 26), "z" if i % 2 else "Z", 8 + k * 9,
                       fill=shade)
        elif st == "angry":
            cx, cy = hx + 14, hy + 4
            puff = 1 + 0.15 * math.sin(g * 12)
            for dx, dy, start in ((-1, -1, 270), (1, -1, 180), (1, 1, 90), (-1, 1, 0)):
                ax, ay = cx + dx * 6 * puff, cy + dy * 6 * puff
                p.arc(ax - 5, ay - 5, ax + 5, ay + 5, start, 90, outline="#ef4444", width=2.6)
        elif st == "laugh":
            for i, (dx, dy) in enumerate(((-26, -4), (10, -14), (26, 6))):
                bob = math.sin(g * 10 + i) * 3
                p.text(hx + dx, hy + dy + bob, "HA", 10, fill="#f59e0b")
            drop = (t * 2) % 1
            p.oval(ex + 4, ey + 4 + drop * 10, ex + 8, ey + 10 + drop * 10, fill="#7dd3fc")
        elif st in ("happy", "wake") and not (st == "wake" and t < 0.9):
            for i, (dx, dy) in enumerate(((-30, 6), (24, -8), (34, 22))):
                tw = (math.sin(g * 7 + i * 2) + 1) / 2
                p.star(hx + dx, hy + dy, 3 + tw * 4, fill="#facc15")
        elif st == "drink":
            level = max(0.0, 1 - t / 2.4)
            gx, gy = mx + 2, my - 6
            p.rrect(gx, gy, gx + 12, gy + 18, 2, fill="#e0f2fe", outline="#38bdf8", width=1.5)
            if level > 0:
                p.rrect(gx + 1.5, gy + 16 - 14 * level, gx + 10.5, gy + 16.5, 1.5, fill="#38bdf8")
        elif st in ("held", "fall"):
            p.oval(hx + 16, hy + 8, hx + 21, hy + 16, fill="#7dd3fc")
        elif st == "dig":
            # dirt mound in front + clumps flying backwards
            p.oval(98, 107, 124, 115, fill="#7a5230")
            p.oval(104, 106, 118, 111, fill="#9a6b40")
            for i in range(7):
                k = (g * 1.7 + i / 7.0) % 1.0
                x = 104 - k * 64
                y = 108 - math.sin(k * math.pi) * (22 + (i % 3) * 6)
                r = 1.6 + (i % 3) * 0.7
                p.oval(x - r, y - r, x + r, y + r, fill="#6b4626" if i % 2 else "#8b5e34")
        elif st == "plant":
            p.oval(100, 107, 124, 115, fill="#7a5230")
            k = min(1.0, t / 0.9)
            sx, sy = mx + 4, my + 4 + (110 - my - 4) * k
            p.oval(sx - 2, sy - 1.4, sx + 2, sy + 1.4, fill="#d6a756", outline="#7a5230",
                   width=0.6)
            if t > 1.0:
                for i in range(3):
                    p.line([(103 + i * 6, 104), (106 + i * 6, 106)], fill="#5b3a1e", width=1.2)
        elif st == "water":
            tilt = 0.75 + 0.12 * math.sin(g * 3)
            cx, cy = mx - 2, my + 1
            ca, sa = math.cos(tilt), math.sin(tilt)
            k = 1.3

            def R(x, y):
                return (cx + (x * ca - y * sa) * k, cy + (x * sa + y * ca) * k)

            p.poly([R(-7, -6), R(7, -6), R(8, 7), R(-8, 7)], fill="#22a6a0",
                   outline="#0f5f5c", width=1)
            p.line([R(-6, -6), R(-1, -13), R(5, -6)], fill="#0f5f5c", width=1.8, smooth=True)
            p.line([R(7, 2), R(17, -3)], fill="#22a6a0", width=3.2)
            (ax, ay), (bx, by) = R(16, -5), R(20, -1)
            p.oval(min(ax, bx), min(ay, by), max(ax, bx), max(ay, by), fill="#7dd3fc",
                   outline="#0f5f5c", width=0.8)
            sx, sy = R(19, -2)
            for i in range(7):
                q = (g * 2.4 + i / 7.0) % 1.0
                x = sx + (111 - sx) * q + (i % 2 - 0.5) * 2
                y = sy + (110 - sy) * q
                p.oval(x - 1, y - 1.6, x + 1, y + 1.6, fill="#38bdf8")
        elif st == "stretch":
            k = (math.sin(t * 1.6) + 1) / 2
            p.text(hx + 22, hy - 6 - k * 4, "~", 14, fill="#94a3b8")
