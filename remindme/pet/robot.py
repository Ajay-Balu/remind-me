"""Bolt - original glossy desk robot: white helmet head with a glass visor,
glowing eyes, antenna, little arms and treads."""
import math

from .dog import rot
from .illustrated import TWO_PI, ImageAvatar

WHITE = "#eef1f5"
METAL = "#b8c1cc"
METAL_DK = "#7c8796"
RUBBER = "#2b313a"
CYAN = "#3fe0ff"


class Robot(ImageAvatar):
    key, name, label = "robot", "Bolt", "Robot (Bolt)"
    VERSION = 3
    mirror = False   # faces you; eyes look left/right instead
    LINES = {
        "intro": ["Beep boop! I am {name}. Health protocols online."],
        "water": ["Beep boop. Hydration level low. Please drink water.",
                  "Alert! Water intake required."],
        "blink": ["Beep. Eye cooling cycle: look 20 feet away for 20 seconds.",
                  "Visual sensors need rest. Blink slowly, human."],
        "posture": ["Scanning posture... please sit up straight.",
                    "Beep! Spine alignment check. Shoulders back."],
        "break": ["Beep boop. Break protocol initiated. Time to stretch!",
                  "System says: take a break and move around."],
        "angry": ["Error! Do not hit the robot!", "Beep! Ouch! Warning!", "System overheat!"],
        "laugh": ["Ha ha ha! Tickle sensors activated!", "Beep hehe boop!"],
        "wake": ["Rebooting... welcome back, human!", "Beep! You're back!"],
        "done": ["Task complete! Great job.", "Beep boop, excellent!"],
        "done_water": ["Hydration restored. Cheers!"],
    }

    def outline(self):
        return "#3a4350"

    def outline_width(self):
        return 0.6

    def frame_key(self, pose):
        key = super().frame_key(pose)
        look = 0 if pose.state == "sleep" else pose.facing
        return key + (look,)

    def warm_keys(self):
        out = []
        for k in super().warm_keys():
            out += [k + (1,), k + (-1,)] if k[0] != "sleep" else [k + (0,)]
        return out

    def anchors(self, pose):
        look = 0 if pose.state == "sleep" else 5 * pose.facing
        hy = 4 if pose.state == "sleep" else 0
        return (60, 2 + hy), (66 + look, 48 + hy), (74 + look, 37 + hy)

    # ------------------------------------------------------------ params
    def params(self, key):
        grp, idx, eye, mouth, look = key
        P = dict(arms=(0.25, 0.25), tilt=0.0, hy=0.0, tread=idx, chest="#4ade80", eye=eye,
                 mouth=mouth, look=look * 5, ecol=CYAN, bob=0.0)
        if grp == "stand":
            P["hy"] = math.sin(idx / 6 * TWO_PI) * 0.6
        elif grp == "walk":
            ph = idx / self.WALK_FRAMES * TWO_PI
            P["arms"] = (0.3 + math.sin(ph) * 0.45, 0.3 - math.sin(ph) * 0.45)
            P["tilt"] = math.sin(ph) * 2
            P["bob"] = -abs(math.sin(ph)) * 0.8
        elif grp == "excited":
            w = math.sin(idx / 6 * TWO_PI) * 0.45
            P["arms"] = (2.5 + w, 2.5 - w)
            P["tilt"] = math.sin(idx / 6 * TWO_PI) * 5
            P["chest"] = "#facc15"
        elif grp == "angry":
            s = 1 if idx else -1
            P["arms"] = (1.7 + 0.3 * s, 1.7 - 0.3 * s)
            P["chest"] = "#ef4444"
            P["ecol"] = "#ff5a5a"
            P["tilt"] = 3 * s
        elif grp == "held":
            ph = idx / 8 * TWO_PI
            P["arms"] = (1.3 + math.sin(ph) * 0.6, 1.3 - math.sin(ph) * 0.6)
            P["tilt"] = math.sin(ph) * 6
        elif grp == "stretch":
            k = idx / 6
            P["arms"] = (2.2 + k * 0.8, 2.2 + k * 0.8)
            P["hy"] = -3 * k
        elif grp == "dig":
            sw = idx % 2
            P["arms"] = (0.15 + 0.7 * sw, 0.85 - 0.7 * sw)
            P["tilt"] = 4 if sw else -4
            P["chest"] = "#a3e635"
        elif grp == "drink":
            P["arms"] = (0.3, 2.6)
            P["chest"] = "#38bdf8"
        elif grp == "sleep":
            P["hy"] = 4
            P["chest"] = "#22c55e" if idx in (2, 3) else "#334155"
            P["ecol"] = "#0e7490"
        return P

    # ------------------------------------------------------------ paint
    def paint(self, a, key):
        P = self.params(key)
        hy, b = P["hy"], P["bob"]

        # treads
        a.paint(a.rrect(33, 98, 87, 112, 7), RUBBER, light=0.25, dark=0.4, rim=0.3,
                light_col="#5b6573")
        for i in range(9):
            x = 36 + ((i * 6 + P["tread"] * 2) % 50)
            a.stroke([(x, 98.6), (x, 100.2)], "#59626f", 0.9)
            a.stroke([(x, 110.0), (x, 111.4)], "#59626f", 0.9)
        for wx in (42, 60, 78):
            a.paint(a.ellipse(wx, 105, 4.6, 4.6), METAL, light=0.45, dark=0.35, rim=0.4,
                    gloss=0.3)
            for k in range(3):
                ang = math.radians(P["tread"] * 30 + k * 120)
                a.stroke([(wx, 105), (wx + math.cos(ang) * 3.4, 105 + math.sin(ang) * 3.4)],
                         METAL_DK, 0.8)
            a.paint(a.ellipse(wx, 105, 1.3, 1.3), METAL_DK, light=0.2, rim=0.1)

        # body
        a.paint(a.rrect(40, 66 + b, 80, 100, 10), WHITE, light=0.45, dark=0.3, rim=0.45,
                gloss=0.55, light_pos=(0.3, 0.15), shadow_col="#9aa6b5")
        a.stroke([(45, 93 + b * 0.5), (75, 93 + b * 0.5)], "#c5ccd6", 0.8)
        a.paint(a.ellipse(60, 81 + b, 6.5, 6.5), "#1f2937", light=0.2, rim=0.2)
        cm = a.ellipse(60, 81 + b, 4.6, 4.6)
        a.glow(cm, P["chest"], radius=3, strength=1.4)
        a.paint(cm, P["chest"], light=0.6, dark=0.1, rim=0.1, gloss=0.4)

        # arms
        for (sx, sy), ang, side in (((41, 73 + b), P["arms"][0], -1),
                                    ((79, 73 + b), P["arms"][1], 1)):
            ex, ey = sx + side * 9 * math.sin(ang), sy + 9 * math.cos(ang)
            hx_, hy_ = sx + side * 17 * math.sin(ang), sy + 17 * math.cos(ang)
            a.paint(a.capsule([(sx, sy), (ex, ey), (hx_, hy_)], 4.6), METAL, light=0.4,
                    dark=0.3, rim=0.35, gloss=0.2)
            a.paint(a.ellipse(sx, sy, 3.6, 3.6), METAL_DK, light=0.3, rim=0.3)
            a.paint(a.ellipse(hx_, hy_, 3.6, 3.6), "#8e98a6", light=0.45, dark=0.3, rim=0.3,
                    gloss=0.3)

        # neck
        a.paint(a.rrect(54, 58 + hy + b, 66, 68 + b, 3), METAL_DK, light=0.3, rim=0.3)

        # head (tilts)
        piv = (60, 60 + hy + b)

        def H(pts):
            return rot([(x, y + hy + b) for x, y in pts], piv, P["tilt"])

        # antenna
        tip = H([(60, 3)])[0]
        a.stroke(H([(60, 13), (60, 5)]), METAL_DK, 1.6)
        am = a.ellipse(tip[0], tip[1], 3.4, 3.4)
        ant = "#ff4d6d" if key[0] in ("angry", "excited") or key[1] % 2 == 0 else "#ffa3b5"
        a.glow(am, ant, radius=2.2, strength=1.2)
        a.paint(am, ant, light=0.6, dark=0.15, rim=0.2, gloss=0.5)

        head = a.blob(H([(40, 12), (80, 12), (92, 15), (97, 26), (97, 50), (92, 60), (80, 63),
                         (40, 63), (28, 60), (23, 50), (23, 26), (28, 15)]))
        a.paint(head, WHITE, light=0.5, dark=0.3, rim=0.45, gloss=0.6, light_pos=(0.3, 0.12),
                shadow_col="#98a4b4")
        visor = a.blob(H([(42, 19), (78, 19), (87, 22), (90, 31), (90, 46), (86, 54), (76, 57),
                          (44, 57), (34, 54), (30, 46), (30, 31), (33, 22)]))
        a.paint(visor, "#0b1220", grad=("#18243a", "#060a12"), light=0.15, dark=0.1, rim=0.5,
                light_col="#334155", shadow_col="#000000")
        # eyes / mouth glow
        self._face(a, P, H)
        # glass reflection streak
        refl = a.blob(H([(36, 24), (50, 21), (46, 26), (34, 33)]))
        a.flat(refl, "#ffffff", alpha=55)
        # little bolts on the helmet sides
        for x in (26.5, 93.5):
            a.paint(a.ellipse(*H([(x, 38)])[0], 1.6, 1.6), METAL, light=0.5, rim=0.3)

    def _face(self, a, P, H):
        ec, look, mode, mouth = P["ecol"], P["look"], P["eye"], P["mouth"]
        masks = []
        for i, x0 in enumerate((47, 73)):
            x, y = x0 + look, 36
            if mode in ("open", "wide"):
                k = 1.2 if mode == "wide" else 1.0
                masks.append(a.blob(H([(x - 6 * k, y - 8 * k), (x + 6 * k, y - 8 * k),
                                       (x + 6 * k, y + 8 * k), (x - 6 * k, y + 8 * k)]),
                                    smooth=True))
            elif mode == "angry":
                pts = ([(x - 7, y - 7), (x + 7, y - 1), (x + 7, y + 7), (x - 7, y + 7)] if i == 0
                       else [(x - 7, y - 1), (x + 7, y - 7), (x + 7, y + 7), (x - 7, y + 7)])
                masks.append(a.blob(H(pts), smooth=False))
            elif mode == "happy":
                masks.append(a.capsule(H([(x - 7, y + 4), (x - 3.5, y - 2), (x, y - 3.5),
                                          (x + 3.5, y - 2), (x + 7, y + 4)]), 3.2))
            else:  # closed
                masks.append(a.capsule(H([(x - 7, y + 2), (x + 7, y + 2)]), 2.6))
        mx = 60 + look
        if mouth in ("open",):
            masks.append(a.rrect(*H([(mx - 7, 46)])[0], *H([(mx + 7, 53)])[0], 3))
        elif mouth == "talk":
            masks.append(a.rrect(*H([(mx - 5, 47)])[0], *H([(mx + 5, 51)])[0], 1.8))
        elif mouth == "frown":
            masks.append(a.capsule(H([(mx - 7, 51), (mx - 3.5, 48), (mx, 51), (mx + 3.5, 48),
                                      (mx + 7, 51)]), 1.6))
        elif mouth == "o":
            masks.append(a.ellipse(*H([(mx, 49.5)])[0], 2.2, 2.2))
        elif P["eye"] != "closed":
            masks.append(a.capsule(H([(mx - 5, 47.5), (mx - 2, 50), (mx + 2, 50),
                                      (mx + 5, 47.5)]), 1.6))
        if not masks:
            return
        m = a.union(*masks)
        a.glow(m, ec, radius=2.6, strength=1.3)
        a.paint(m, ec, light=0.5, dark=0.15, rim=0.1, light_col="#d9fbff")
