"""Buddy - an illustrated Golden Retriever (side view, facing right)."""
import math

from .illustrated import TWO_PI, ImageAvatar


def rot(pts, pivot, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    px, py = pivot
    return [(px + (x - px) * ca - (y - py) * sa, py + (x - px) * sa + (y - py) * ca)
            for x, y in pts]


def shift(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


GOLD = "#d89a4f"
GOLD_LT = "#ecc183"
CREAM = "#f3d9a8"
DEEP = "#b4752f"
FAR = "#a86a2a"
NOSE = "#2a201d"


class Dog(ImageAvatar):
    def outline(self):
        return "#6e4519"

    def outline_width(self):
        return 0.55

    key, name, label = "dog", "Buddy", "Golden Retriever (Buddy)"
    VERSION = 4
    LINES = {
        "water": ["Woof! Time to drink some water!", "Woof woof! Water break, let's drink!"],
        "blink": ["Woof! Look at something far away for 20 seconds and blink.",
                  "Your eyes need a rest, buddy. Look far away for 20 seconds."],
        "posture": ["Woof! Sit up straight, like a good human!",
                    "Posture check! Shoulders back, tail up!"],
        "break": ["Woof! Walk time! Let's take a break and stretch.",
                  "Break time! Let's stretch our legs."],
        "angry": ["Grrr! Woof!", "Hey! No hitting!", "Ouch! Bad human!"],
        "laugh": ["Hehehe! Belly rubs!", "Hahaha! That tickles!"],
    }

    def anchors(self, pose):
        d = self.DX
        if pose.state == "sleep":
            return (92 + d, 60), (114 + d, 92), (100 + d, 80)
        hx, hy = self._head_off(pose.state, pose.t)
        return (93 + hx + d, 12 + hy), (118 + hx + d, 50 + hy), (101 + hx + d, 34 + hy)

    @staticmethod
    def _head_off(state, t):
        if state == "stretch":
            k = (math.sin(t * 1.6) + 1) / 2
            return 0, 12 * k
        if state == "dig":
            return 0, 12
        if state == "plant":
            return 0, 8
        if state == "drink":
            return 0, 3
        if state == "angry":
            return 0, 3
        return 0, 0

    # ------------------------------------------------------------ pose params
    def params(self, key):
        grp, idx, eye, mouth = key
        P = dict(breath=0.0, hx=0.0, hy=0.0, tilt=0.0, tail=0.0, ear=0.0, bob=0.0,
                 legs=[(0.0, 0.0)] * 4, front_down=0.0, eye=eye, mouth=mouth)
        if grp == "stand":
            c = idx / 6 * TWO_PI
            P["breath"] = math.sin(c) * 0.7
            P["tail"] = math.sin(c) * 6
        elif grp == "walk":
            ph = idx / self.WALK_FRAMES * TWO_PI
            legs = []
            for off in (0, math.pi, math.pi, 0):  # front near, front far, back near, back far
                legs.append((math.cos(ph + off) * 4.5, max(0, math.sin(ph + off)) * 4.5))
            P["legs"] = legs
            P["tail"] = math.sin(ph * 2) * 9
            P["ear"] = math.sin(ph) * 5
            P["bob"] = -abs(math.sin(ph)) * 1.2
        elif grp == "excited":
            c = idx / 6 * TWO_PI
            P["tail"] = math.sin(c) * 14 + 8
            P["ear"] = math.sin(c) * 4
            P["tilt"] = math.sin(c) * 3
        elif grp == "angry":
            P["tail"] = -18
            P["ear"] = -10
            P["hy"] = 3
            P["front_down"] = 1.5 + idx
        elif grp == "held":
            ph = idx / 8 * TWO_PI
            P["legs"] = [(math.sin(ph + o) * 3, -3.5) for o in (0, 1.6, 3.1, 4.7)]
            P["tail"] = -24
            P["ear"] = 8
        elif grp == "stretch":
            k = idx / 6
            P["front_down"] = 9 * k
            P["hx"], P["hy"] = 0, 12 * k
            P["legs"] = [(9 * k, 0), (8 * k, 0), (0, 0), (0, 0)]
            P["tail"] = 18 * k
        elif grp == "drink":
            P["hy"] = 3
            P["tail"] = 10
        elif grp == "dig":  # play-bow, front paws paddling
            sw = idx % 2
            P["front_down"] = 9
            P["hx"], P["hy"] = 0, 12
            P["legs"] = [(13 - 6 * sw, 4 * (1 - sw)), (7 + 6 * sw, 4 * sw), (0, 0), (0, 0)]
            P["tail"] = 14 + 8 * (idx // 2)
            P["ear"] = 6 * sw
        return P

    # ------------------------------------------------------------ painting
    DX = -7

    def paint(self, a, key):
        a.dx = self.DX
        if key[0] == "sleep":
            return self._paint_sleep(a, key)
        P = self.params(key)
        b, br = P["bob"] - 3.5, P["breath"]   # -3.5: longer legs
        fd = P["front_down"]
        legs = P["legs"]

        fur_body = dict(angle=165, length=4.5, density=0.5, light="#f6d7a0", dark="#9b6024",
                        alpha=0.32, seed=3)
        fur_leg = dict(angle=95, length=3.0, density=0.5, light="#f3d29a", dark="#8f5822",
                       alpha=0.3, seed=5)

        # ---- far legs (behind the body)
        dx, lift = legs[1]
        a.paint(a.capsule([(74, 84 + b + fd * 0.5), (75 + dx, 104 - lift + fd * 0.1),
                           (76 + dx, 110 - lift)], 7, taper=6), FAR, light=0.1, rim=0.3,
                fur=fur_leg)
        a.paint(a.ellipse(78 + dx, 110.5 - lift, 5, 2.4), DEEP, light=0.1)
        dx, lift = legs[3]
        a.paint(a.capsule([(30, 80 + b), (35, 93 + b), (28 + dx, 103 - lift),
                           (30 + dx, 110 - lift)], 9, taper=6), FAR, light=0.1, rim=0.3,
                fur=fur_leg)
        a.paint(a.ellipse(32 + dx, 110.5 - lift, 5, 2.4), DEEP, light=0.1)

        # ---- tail (feathered plume)
        base = (24, 70 + b)
        tail = rot([base, (14, 66 + b), (8, 58 + b), (6, 48 + b), (9, 40 + b)], base,
                   -P["tail"])
        tm = a.capsule(tail, 5.5, taper=3)
        feather = a.capsule(shift(tail[1:], -2, 3.2), 6, taper=2)
        a.fluff(feather, amount=2.0, n=45, seed=11)
        tm = a.union(tm, feather)
        a.paint(tm, GOLD_LT, light=0.35, dark=0.25, rim=0.35,
                fur=dict(angle=200, length=5, density=0.6, light="#f8e2b5", dark="#a96b2b",
                         alpha=0.35, seed=12))
        a.wisps(feather, [GOLD_LT, CREAM, DEEP], n=50, length=3.2, seed=13)

        # ---- torso
        torso = [(88, 64 + b + fd * 0.6), (78, 57 + b - br * 0.4 + fd * 0.5),
                 (60, 59 + b - br * 0.3), (42, 60 + b), (28, 62 + b), (19, 71 + b),
                 (21, 84 + b), (31, 91 + b), (48, 92 + b + br * 0.3), (64, 94 + b + br * 0.4),
                 (78, 92 + b + fd), (89, 85 + b + fd), (93, 74 + b + fd)]
        tm = a.blob(torso)
        a.fluff(tm, amount=0.9, n=28, seed=21)
        a.paint(tm, GOLD, light=0.3, dark=0.32, rim=0.45, light_pos=(0.45, 0.15), fur=fur_body)
        # belly / chest feathering (lighter)
        chest = a.blob([(86, 70 + b + fd), (93, 76 + b + fd), (90, 88 + b + fd),
                        (80, 95 + b + fd), (70, 95 + b + br), (78, 84 + b + fd)])
        a.fluff(chest, amount=1.0, n=18, seed=22)
        a.paint(chest, CREAM, light=0.3, dark=0.2, rim=0.2,
                fur=dict(angle=100, length=4, density=0.5, light="#fff1d6", dark="#c9965a",
                         alpha=0.35, seed=23))
        a.wisps(chest, [CREAM, GOLD_LT], n=30, length=3.0, seed=26, center=(78, 70))
        belly = a.ellipse(54, 93 + b, 16, 3.5)
        a.fluff(belly, amount=1.6, n=25, seed=24)
        a.paint(belly, GOLD_LT, light=0.2, dark=0.2, rim=0.2)

        # ---- near back leg (big thigh + hock)
        dx, lift = legs[2]
        thigh = a.ellipse(34, 80 + b, 13, 12, angle=-20)
        hock = a.capsule([(38, 88 + b), (40, 96 + b), (33 + dx, 104 - lift),
                          (35 + dx, 110 - lift)], 9, taper=6.5)
        lm = a.union(thigh, hock)
        a.fluff(lm, amount=1.5, n=30, seed=31)
        a.paint(lm, GOLD, light=0.3, dark=0.3, rim=0.4, light_pos=(0.4, 0.2), fur=fur_leg)
        a.paint(a.ellipse(37 + dx, 110.5 - lift, 5.5, 2.6), GOLD_LT, light=0.3)
        for i in range(3):  # toes
            a.stroke([(34 + dx + i * 2.3, 109.5 - lift), (34.5 + dx + i * 2.3, 111.8 - lift)],
                     "#9b6024", 0.5, alpha=160)

        # ---- near front leg
        dx, lift = legs[0]
        fl = a.capsule([(84, 84 + b + fd * 0.7), (85 + dx * 0.6, 98 - lift * 0.5 + fd * 0.2),
                        (86 + dx, 110 - lift)], 8, taper=6.5)
        feather = a.capsule([(81, 88 + b + fd * 0.6), (82 + dx * 0.5, 99 - lift * 0.4)], 5)
        lm = a.union(fl, feather)
        a.fluff(lm, amount=1.2, n=20, seed=41)
        a.paint(lm, GOLD, light=0.32, dark=0.3, rim=0.4, fur=fur_leg)
        a.paint(a.ellipse(88 + dx, 110.5 - lift, 5.5, 2.6), GOLD_LT, light=0.3)
        for i in range(3):
            a.stroke([(86 + dx + i * 2.3, 109.5 - lift), (86.5 + dx + i * 2.3, 111.8 - lift)],
                     "#9b6024", 0.5, alpha=160)

        self._paint_head(a, P, b)

    def _paint_head(self, a, P, b):
        hx, hy = P["hx"], P["hy"] + b
        piv = (88 + hx, 50 + hy)

        def H(pts, k=1.17, c=(86, 54)):
            pts = [(c[0] + (x - c[0]) * k, c[1] + (y - c[1]) * k - 2) for x, y in pts]
            return rot(shift(pts, hx, hy), piv, P["tilt"])

        # neck
        neck = a.blob(H([(80, 58), (86, 42), (100, 44), (101, 60), (92, 72), (80, 70)]))
        a.paint(neck, GOLD, light=0.25, dark=0.25, rim=0.3,
                fur=dict(angle=120, length=4, density=0.45, light="#f6d7a0", dark="#9b6024",
                         alpha=0.3, seed=51))

        # skull + muzzle
        skull = a.blob(H([(83, 38), (87, 29), (96, 25), (105, 28), (109, 37), (107, 48),
                          (98, 54), (88, 52)]))
        muzzle = a.blob(H([(103, 38), (112, 39), (119, 41), (122, 46), (121, 52), (114, 56),
                           (104, 56), (100, 48)]))
        head = a.union(skull, muzzle)
        a.paint(head, GOLD, light=0.38, dark=0.28, rim=0.4, light_pos=(0.35, 0.15),
                fur=dict(angle=180, length=2.5, density=0.45, light="#f6d7a0", dark="#a26628",
                         alpha=0.25, seed=52))
        a.paint(a.blob(H([(105, 42), (114, 42), (120, 46), (118, 53), (108, 55), (103, 50)])),
                GOLD_LT, light=0.35, dark=0.15, rim=0.2)

        mouth = P["mouth"]
        # mouth
        if mouth in ("open", "talk"):
            open_amt = 1.0 if mouth == "open" else 0.6
            inner = a.blob(H([(104, 52), (119, 52), (117, 55 + 5 * open_amt),
                              (107, 56 + 5 * open_amt)]))
            a.paint(inner, "#5a1f1c", light=0.1, dark=0.3, rim=0.3)
            tongue = a.blob(H([(105, 55), (113, 54.5), (114, 59 + 5 * open_amt),
                               (110, 62 + 5 * open_amt), (105, 59 + 3 * open_amt)]))
            a.paint(tongue, "#e5717f", light=0.4, dark=0.25, rim=0.3)
            a.stroke(H([(110, 56), (110.5, 59 + 3 * open_amt)]), "#b84b5a", 0.5, alpha=160)
            a.paint(a.blob(H([(104, 51), (119, 51), (120, 53.5), (103, 54)])), GOLD_LT,
                    light=0.3, dark=0.1, rim=0.2)
        elif mouth == "frown":
            a.stroke(H([(120, 52), (113, 55), (105, 54.5)]), "#3a2414", 0.9)
            for i in range(3):
                x = 111 + i * 2.4
                a.paint(a.blob(H([(x, 53.5), (x + 1.8, 53.5), (x + 0.9, 56.2)]), smooth=False),
                        "#fbf7ee", light=0.1, dark=0.1, rim=0)
        elif mouth == "o":
            a.paint(a.ellipse(*H([(114, 55)])[0], 2.4, 2.0), "#5a1f1c", light=0.05, rim=0.1)
        else:
            a.stroke(H([(120.5, 51), (114, 54.5), (107, 54), (104, 52)]), "#4a2e18", 0.8,
                     smooth=True)

        # nose
        nose = a.blob(H([(116, 41), (121, 41.5), (123.5, 44), (122, 47.5), (118, 47.5),
                         (115.5, 44.5)]))
        a.paint(nose, NOSE, light=0.35, dark=0.2, rim=0.2, gloss=0.45,
                light_col="#7a6a66")
        a.stroke(H([(119, 46.6), (119, 50)]), "#5c3a20", 0.5, alpha=180)

        # eye
        ex, ey = H([(99, 38)])[0]
        mode = P["eye"]
        if mode in ("open", "wide", "angry"):
            k = 1.2 if mode == "wide" else 1.0
            ry = 2.5 * k if mode != "angry" else 1.8
            a.paint(a.ellipse(ex, ey, 3.2 * k, ry, angle=-8), "#2a170b", light=0.25, dark=0.1,
                    rim=0.15, light_col="#7a4a22")
            a.paint(a.ellipse(ex + 0.4, ey + 0.2, 2.0 * k, min(ry, 2.0 * k)), "#5a3214",
                    light=0.4, dark=0.0, rim=0.25, light_col="#a0632c")
            a.paint(a.ellipse(ex + 0.3, ey + 0.2, 1.2 * k, 1.3 * k), "#120a05", light=0, dark=0,
                    rim=0)
            a.paint(a.ellipse(ex - 0.9, ey - 0.9, 0.75, 0.75), "#ffffff", light=0, dark=0,
                    rim=0)
            if mode == "angry":
                a.stroke(H([(95, 33), (103.5, 35.5)]), "#5a3214", 1.0)
            else:
                a.stroke(H([(96, 34.5), (101.5, 34)]), "#b9813f", 0.6, alpha=170, smooth=True)
        elif mode == "happy":
            a.stroke(H([(96, 39.5), (99, 36.8), (102, 39.2)]), "#2a170b", 1.0, smooth=True)
        else:  # closed
            a.stroke(H([(96, 37.8), (99, 39.6), (102, 37.8)]), "#2a170b", 0.9, smooth=True)

        # ear (droopy, feathered) - drawn last so it overlaps the skull
        ear = H(rot([(90, 31), (96, 32), (97.5, 40), (96, 50), (91, 56), (85, 54), (84, 44),
                     (86, 35)], (92, 32), P["ear"]))
        em = a.blob(ear)
        a.fluff(em, amount=1.3, n=30, seed=61)
        a.paint(em, DEEP, light=0.3, dark=0.35, rim=0.45, light_pos=(0.4, 0.1),
                fur=dict(angle=100, length=4.5, density=0.6, light="#e2a865", dark="#7a4a1c",
                         alpha=0.35, seed=62))
        a.wisps(em, [DEEP, "#c98a45"], n=26, length=2.6, seed=63)

    def _paint_sleep(self, a, key):
        idx = key[1]
        br = math.sin(idx / 6 * TWO_PI) * 0.9
        fur_body = dict(angle=170, length=4.5, density=0.5, light="#f6d7a0", dark="#9b6024",
                        alpha=0.32, seed=3)
        # tail curled around the front
        tail = [(24, 98), (16, 104), (24, 110), (44, 111), (62, 110)]
        tm = a.capsule(tail, 7, taper=4)
        a.fluff(tm, amount=2.4, n=50, seed=11)
        a.paint(tm, GOLD_LT, light=0.35, dark=0.25, rim=0.35,
                fur=dict(angle=180, length=5, density=0.6, light="#f8e2b5", dark="#a96b2b",
                         alpha=0.35, seed=12))
        body = a.blob([(20, 98), (24, 86 - br), (40, 80 - br), (62, 79 - br), (82, 84),
                       (94, 96), (92, 108), (70, 111), (40, 111), (24, 108)])
        a.fluff(body, amount=1.5, n=45, seed=21)
        a.paint(body, GOLD, light=0.3, dark=0.32, rim=0.45, light_pos=(0.4, 0.15), fur=fur_body)
        a.paint(a.ellipse(32, 98 - br * 0.5, 12, 10, angle=-10), GOLD, light=0.3, dark=0.3,
                rim=0.35, fur=fur_body)
        # front paws
        for x in (88, 98):
            pm = a.capsule([(x - 10, 106), (x + 8, 108)], 6.5)
            a.paint(pm, GOLD_LT, light=0.3, dark=0.25, rim=0.35)
        # head resting on paws
        head = a.blob([(82, 76), (90, 68), (100, 66), (108, 70), (116, 78), (122, 86),
                       (121, 94), (112, 99), (98, 100), (86, 96), (80, 88)])
        a.paint(head, GOLD, light=0.38, dark=0.28, rim=0.4,
                fur=dict(angle=180, length=2.5, density=0.45, light="#f6d7a0", dark="#a26628",
                         alpha=0.25, seed=52))
        a.paint(a.blob([(106, 84), (116, 84), (121, 89), (118, 95), (108, 97), (104, 92)]),
                GOLD_LT, light=0.35, dark=0.15, rim=0.2)
        nose = a.blob([(116, 83), (121, 84), (123.5, 87), (121.5, 90), (117, 89.5)])
        a.paint(nose, NOSE, light=0.35, dark=0.2, rim=0.2, gloss=0.4, light_col="#7a6a66")
        a.stroke([(119, 94), (112, 96), (106, 95)], "#4a2e18", 0.8, smooth=True)
        a.stroke([(96, 80), (99.5, 82), (103, 80)], "#2a170b", 0.9, smooth=True)
        ear = a.blob([(88, 72), (95, 74), (95, 86), (90, 98), (82, 100), (78, 92), (80, 80)])
        a.fluff(ear, amount=1.6, n=35, seed=61)
        a.paint(ear, DEEP, light=0.3, dark=0.35, rim=0.45,
                fur=dict(angle=100, length=4.5, density=0.6, light="#e2a865", dark="#7a4a1c",
                         alpha=0.35, seed=62))
