"""Mochi - an illustrated grey & white Persian cat (body side-on, face to you)."""
import math

from .dog import rot, shift
from .illustrated import TWO_PI, ImageAvatar

GREY = "#8f969f"
GREY_LT = "#b9bec5"
GREY_DK = "#6b727b"
WHITE = "#f5f3ef"
WHITE_SH = "#d9d6d0"
PINK = "#e9a3ad"
IRIS = "#d9822b"
IRIS_LT = "#f7c04f"


class Cat(ImageAvatar):
    key, name, label = "cat", "Mochi", "Persian Cat (Mochi)"
    VERSION = 3
    LINES = {
        "water": ["Meow~ Drink some water, human.", "Purr... water time. Stay hydrated!"],
        "blink": ["Meow. Look far away for 20 seconds and blink slowly, like a cat.",
                  "Slow blink time! Rest those eyes."],
        "posture": ["Meow! Sit up straight. Even cats have better posture.",
                    "Posture check, human. Shoulders back."],
        "break": ["Meow~ Break time. Stretch like a cat!",
                  "Time to stretch. Big cat stretch!"],
        "angry": ["Hiss!", "Mrrow! Don't touch me!", "Hsss! Rude human!"],
        "laugh": ["Purr purr! Hehe!", "Mew hehe, that tickles!"],
        "wake": ["Mrrp? Oh, you're back!", "Meow~ welcome back."],
    }

    def outline(self):
        return "#5f656d"

    def outline_width(self):
        return 0.5

    def anchors(self, pose):
        if pose.state == "sleep":
            return (88, 60), (92, 92), (92, 84)
        hx, hy = self._head_off(pose.state, pose.t)
        return (88 + hx, 22 + hy), (92 + hx, 62 + hy), (96 + hx, 52 + hy)

    @staticmethod
    def _head_off(state, t):
        if state == "stretch":
            k = (math.sin(t * 1.6) + 1) / 2
            return 3 * k, 10 * k
        if state == "dig":
            return 3, 10
        if state == "plant":
            return 2, 6.7
        if state in ("drink", "angry"):
            return 0, 2
        return 0, 0

    # ------------------------------------------------------------ params
    def params(self, key):
        grp, idx, eye, mouth = key
        P = dict(breath=0.0, hx=0.0, hy=0.0, tilt=0.0, tail=0.0, ears=0.0, bob=0.0, puff=0.0,
                 legs=[(0.0, 0.0)] * 4, front_down=0.0, eye=eye, mouth=mouth)
        if grp == "stand":
            c = idx / 6 * TWO_PI
            P["breath"] = math.sin(c) * 0.8
            P["tail"] = math.sin(c) * 5
            P["tilt"] = math.sin(c) * 1.5
        elif grp == "walk":
            ph = idx / self.WALK_FRAMES * TWO_PI
            P["legs"] = [(math.cos(ph + o) * 3.5, max(0, math.sin(ph + o)) * 3.5)
                         for o in (0, math.pi, math.pi, 0)]
            P["tail"] = math.sin(ph) * 6
            P["bob"] = -abs(math.sin(ph)) * 1.0
        elif grp == "excited":
            c = idx / 6 * TWO_PI
            P["tail"] = math.sin(c) * 12 + 6
            P["tilt"] = math.sin(c) * 6
        elif grp == "angry":
            P["ears"] = 1.0
            P["puff"] = 1.0 + idx * 0.2
            P["tail"] = 10
            P["bob"] = -1
        elif grp == "held":
            ph = idx / 8 * TWO_PI
            P["legs"] = [(math.sin(ph + o) * 2.5, -3) for o in (0, 1.6, 3.1, 4.7)]
            P["tail"] = -30
        elif grp == "stretch":
            k = idx / 6
            P["front_down"] = 7 * k
            P["hx"], P["hy"] = 3 * k, 10 * k
            P["legs"] = [(8 * k, 0), (7 * k, 0), (0, 0), (0, 0)]
            P["tail"] = 14 * k
        elif grp == "drink":
            P["hy"] = 2
        elif grp == "dig":
            sw = idx % 2
            P["front_down"] = 7
            P["hx"], P["hy"] = 3, 10
            P["legs"] = [(11 - 6 * sw, 4 * (1 - sw)), (5 + 6 * sw, 4 * sw), (0, 0), (0, 0)]
            P["tail"] = 10 + 6 * (idx // 2)
        return P

    # ------------------------------------------------------------ paint
    def paint(self, a, key):
        if key[0] == "sleep":
            return self._sleep(a, key)
        P = self.params(key)
        b, br, fd, legs, pf = P["bob"], P["breath"], P["front_down"], P["legs"], P["puff"]
        fur_grey = dict(angle=160, length=5, density=0.55, light="#d3d7dc", dark="#5d636b",
                        alpha=0.33, seed=3)
        fur_white = dict(angle=95, length=4.5, density=0.5, light="#ffffff", dark="#bdb8b0",
                         alpha=0.35, seed=4)

        # far legs
        dx, lift = legs[1]
        a.paint(a.capsule([(76, 96 + b + fd * 0.4), (77 + dx, 110.5 - lift)], 9), GREY_DK,
                light=0.1, rim=0.3, fur=fur_grey)
        dx, lift = legs[3]
        a.paint(a.capsule([(32, 96 + b), (31 + dx, 110.5 - lift)], 9.5), GREY_DK,
                light=0.1, rim=0.3, fur=fur_grey)

        # tail: big fluffy plume
        base = (26, 86 + b)
        tail = rot([base, (15, 82 + b), (9, 72 + b), (9, 60 + b), (14, 50 + b)], base,
                   -P["tail"])
        tm = a.capsule(tail, 10 + pf * 3, taper=8 + pf * 3)
        a.fluff(tm, amount=2.0 + pf, n=170, seed=11)
        a.paint(tm, GREY, light=0.35, dark=0.25, rim=0.4, light_col="#dfe2e6",
                fur=dict(angle=220, length=6, density=0.6, light="#dfe3e8", dark="#5a6068",
                         alpha=0.38, seed=12))
        a.wisps(tm, [GREY_LT, GREY, GREY_DK], n=90, length=3.5, seed=13)

        # body
        body = a.blob([(22, 84 + b), (28, 72 + b - br * 0.4), (44, 66 + b - br * 0.5),
                       (64, 66 + b - br * 0.5), (80, 70 + b + fd * 0.4),
                       (91, 82 + b + fd * 0.6), (89, 98 + b + fd * 0.6), (76, 106 + b),
                       (56, 108 + b + br * 0.3), (34, 106 + b), (22, 98 + b)])
        a.fluff(body, amount=1.5 + pf, n=200, seed=21)
        a.paint(body, GREY, light=0.32, dark=0.3, rim=0.45, light_pos=(0.4, 0.1),
                light_col="#d6dade", fur=fur_grey)
        a.wisps(body, [GREY_LT, GREY, GREY_DK], n=110, length=3.2 + pf, seed=24)
        under = a.blob([(36, 98 + b), (58, 100 + b), (80, 95 + b + fd * 0.5),
                        (91, 86 + b + fd * 0.6), (89, 100 + b + fd * 0.5), (76, 108 + b),
                        (54, 110 + b), (34, 107 + b)])
        a.fluff(under, amount=1.3, n=110, seed=22)
        a.paint(under, WHITE, light=0.25, dark=0.25, rim=0.3, shadow_col=WHITE_SH,
                fur=fur_white)
        a.wisps(under, [WHITE, WHITE_SH], n=50, length=2.8, seed=25, center=(60, 90))

        # near legs (short, fluffy, white socks)
        dx, lift = legs[2]
        a.paint(a.ellipse(36, 92 + b, 13, 12, angle=-15), GREY, light=0.3, dark=0.3, rim=0.4,
                fur=fur_grey)
        lm = a.capsule([(40, 98 + b), (41 + dx, 110 - lift)], 11)
        a.fluff(lm, amount=1.1, n=60, seed=31)
        a.paint(lm, WHITE, light=0.3, dark=0.25, rim=0.35, shadow_col=WHITE_SH, fur=fur_white)
        dx, lift = legs[0]
        lm = a.capsule([(84, 96 + b + fd * 0.5), (86 + dx, 110 - lift)], 10.5)
        a.fluff(lm, amount=1.1, n=60, seed=41)
        a.paint(lm, WHITE, light=0.3, dark=0.25, rim=0.35, shadow_col=WHITE_SH, fur=fur_white)
        for x, l in ((41 + legs[2][0], legs[2][1]), (86 + legs[0][0], legs[0][1])):
            for i in (-2.2, 0, 2.2):
                a.stroke([(x + i, 108.5 - l), (x + i, 111 - l)], "#c9c4bc", 0.5)

        self._head(a, P, b)

    def _head(self, a, P, b):
        hx, hy = P["hx"], P["hy"] + b
        piv = (88 + hx, 60 + hy)

        def H(pts):
            return rot(shift(pts, hx, hy), piv, P["tilt"])

        pf = P["puff"]
        # ruff (white mane under the face)
        ruff = a.ellipse(*H([(86, 72)])[0], 19 + pf * 2, 12)
        a.fluff(ruff, amount=1.8, n=140, seed=50)
        a.paint(ruff, WHITE, light=0.3, dark=0.3, rim=0.35, shadow_col=WHITE_SH,
                fur=dict(angle=90, length=5, density=0.55, light="#ffffff", dark="#b8b2a9",
                         alpha=0.35, seed=51))
        a.wisps(ruff, [WHITE, WHITE_SH], n=70, length=3.5, seed=52)

        # ears (small, rounded, set wide)
        ef = P["ears"]
        for pts, inner, pv, sgn in (
                ([(68, 42), (69, 31), (73, 27), (79, 33)], [(70.5, 39), (72, 31), (76, 34)],
                 (73, 38), -1),
                ([(97, 33), (103, 27), (107, 30), (108, 42)], [(100, 34), (104, 30), (106, 38)],
                 (103, 38), 1)):
            em = a.blob(H(rot(pts, pv, sgn * 35 * ef)))
            a.fluff(em, amount=1.0, n=12, seed=60 + sgn)
            a.paint(em, GREY, light=0.3, dark=0.3, rim=0.4)
            a.paint(a.blob(H(rot(inner, pv, sgn * 35 * ef))), PINK, light=0.3, dark=0.3,
                    rim=0.3)
            tip = H(rot([inner[1], (inner[1][0], inner[1][1] + 6)], pv, sgn * 35 * ef))
            a.stroke(tip, "#e8e8e8", 0.6, alpha=200)

        # head: round with cheek fluff
        head = a.ellipse(*H([(88, 52)])[0], 22 + pf, 19 + pf * 0.5)
        a.fluff(head, amount=1.6 + pf, n=160, seed=70)
        a.paint(head, GREY, light=0.38, dark=0.25, rim=0.4, light_pos=(0.35, 0.15),
                light_col="#dde0e4",
                fur=dict(angle=200, length=3.5, density=0.5, light="#d9dde1", dark="#5d636b",
                         alpha=0.3, seed=71))
        a.wisps(head, [GREY_LT, GREY, GREY_DK], n=70, length=2.8 + pf, seed=74)
        # white blaze (inverted V) + muzzle and chin
        blaze = a.blob(H([(88, 40), (93, 50), (101, 58), (100, 66), (88, 71), (76, 66),
                          (75, 58), (83, 50)]))
        a.fluff(blaze, amount=1.2, n=24, seed=72)
        a.paint(blaze, WHITE, light=0.35, dark=0.25, rim=0.25, shadow_col=WHITE_SH,
                fur=dict(angle=90, length=2.5, density=0.45, light="#ffffff", dark="#c0bab1",
                         alpha=0.3, seed=73))

        # eyes: big round copper eyes
        mode = P["eye"]
        for ex0 in (79.5, 96.5):
            ex, ey = H([(ex0, 52)])[0]
            if mode in ("open", "wide", "angry"):
                k = 1.15 if mode == "wide" else 1.0
                a.paint(a.ellipse(ex, ey, 5.4 * k, 5.2 * k), "#2b2523", light=0, dark=0, rim=0)
                a.paint(a.ellipse(ex, ey, 4.6 * k, 4.5 * k), IRIS, light=0.55, dark=0.35,
                        rim=0.35, light_pos=(0.5, 0.75), light_col=IRIS_LT,
                        shadow_col="#8a4a12")
                a.paint(a.ellipse(ex, ey + 0.2, 2.3 * k, 2.4 * k), "#0f0b09", light=0, dark=0,
                        rim=0)
                a.paint(a.ellipse(ex - 1.5, ey - 1.6, 1.2, 1.0), "#ffffff", light=0, dark=0,
                        rim=0)
                a.paint(a.ellipse(ex + 1.6, ey + 1.6, 0.5, 0.5), "#ffffff", light=0, dark=0,
                        rim=0)
                if mode == "angry":  # heavy upper lid
                    lid = a.ellipse(ex, ey - 4.6, 6.2, 3.6)
                    a.paint(lid, GREY_DK, light=0.1, dark=0.1, rim=0.1)
                    d = -1 if ex0 < 88 else 1
                    a.stroke(H([(ex0 - 5 * d, 44.5), (ex0 + 4 * d, 47.5)]), "#3b3f45", 1.0)
            elif mode == "happy":
                a.stroke(H([(ex0 - 4, 53.5), (ex0, 50), (ex0 + 4, 53.5)]), "#3b3f45", 1.1,
                         smooth=True)
            else:
                a.stroke(H([(ex0 - 4, 51.5), (ex0, 54), (ex0 + 4, 51.5)]), "#3b3f45", 1.0,
                         smooth=True)

        # nose (tiny, high, flat Persian face) + mouth
        nose = a.blob(H([(85.6, 57.6), (90.4, 57.6), (88, 60.6)]), smooth=False)
        a.paint(nose, PINK, light=0.4, dark=0.2, rim=0.2, gloss=0.3)
        a.stroke(H([(88, 60.6), (88, 62)]), "#9c7d7f", 0.45)
        mouth = P["mouth"]
        if mouth in ("open", "talk"):
            o = 1.0 if mouth == "open" else 0.6
            a.paint(a.ellipse(*H([(88, 64 + o)])[0], 2.6, 1.6 + 1.6 * o), "#6b2a2e",
                    light=0.1, rim=0.2)
            a.paint(a.ellipse(*H([(88, 65.5 + o * 1.4)])[0], 1.6, 0.9 + 0.6 * o), "#e98b98",
                    light=0.3, rim=0.1)
        elif mouth == "frown":
            a.paint(a.ellipse(*H([(88, 64.5)])[0], 3.2, 2.2), "#6b2a2e", light=0.1, rim=0.2)
            for tx in (86.4, 89.6):
                a.paint(a.blob(H([(tx - 0.6, 62.8), (tx + 0.6, 62.8), (tx, 65)]), smooth=False),
                        "#ffffff", light=0, dark=0, rim=0)
        elif mouth == "o":
            a.paint(a.ellipse(*H([(88, 64)])[0], 1.4, 1.4), "#6b2a2e", light=0.1, rim=0.1)
        else:
            a.stroke(H([(85, 62.6), (86.6, 63.4), (88, 62), (89.4, 63.4), (91, 62.6)]),
                     "#8a6f70", 0.55, smooth=True)
        # whiskers
        for side in (-1, 1):
            for i, dy in enumerate((-0.8, 0.8, 2.2)):
                x0, y0 = 88 + side * 5, 61.5 + dy * 0.6
                a.stroke(H([(x0, y0), (x0 + side * 9, y0 + dy - 1), (x0 + side * 17,
                                                                     y0 + dy * 2.2 - 0.5)]),
                         "#f2f2f2", 0.35, alpha=200, smooth=True)

    def _sleep(self, a, key):
        br = math.sin(key[1] / 6 * TWO_PI) * 0.9
        fur_grey = dict(angle=160, length=5, density=0.55, light="#d3d7dc", dark="#5d636b",
                        alpha=0.33, seed=3)
        body = a.blob([(18, 100), (24, 86 - br), (44, 78 - br), (68, 78 - br), (88, 84),
                       (100, 98), (96, 110), (70, 112), (40, 112), (22, 110)])
        a.fluff(body, amount=1.6, n=200, seed=21)
        a.paint(body, GREY, light=0.32, dark=0.3, rim=0.45, light_col="#d6dade", fur=fur_grey)
        tail = a.capsule([(22, 104), (30, 111), (54, 112), (76, 110)], 9, taper=7)
        a.fluff(tail, amount=2.6, n=60, seed=11)
        a.paint(tail, GREY_LT, light=0.35, dark=0.25, rim=0.4, fur=fur_grey)
        paws = a.capsule([(80, 108), (98, 109)], 8)
        a.fluff(paws, amount=1.4, n=20, seed=41)
        a.paint(paws, WHITE, light=0.3, dark=0.25, rim=0.35, shadow_col=WHITE_SH)
        ruff = a.ellipse(90, 98, 15, 9)
        a.fluff(ruff, amount=2.4, n=40, seed=50)
        a.paint(ruff, WHITE, light=0.3, dark=0.3, rim=0.35, shadow_col=WHITE_SH)
        for pts, inner in (([(76, 74), (78, 64), (86, 68)], [(78, 72), (79, 66), (84, 69)]),
                           ([(96, 67), (103, 63), (106, 73)], [(98, 69), (102, 65), (104, 72)])):
            a.paint(a.blob(pts), GREY, light=0.3, dark=0.3, rim=0.4)
            a.paint(a.blob(inner), PINK, light=0.3, rim=0.3)
        head = a.ellipse(91, 84, 19, 16)
        a.fluff(head, amount=1.5, n=140, seed=70)
        a.paint(head, GREY, light=0.38, dark=0.25, rim=0.4, light_col="#dde0e4", fur=fur_grey)
        blaze = a.blob([(91, 74), (96, 82), (102, 88), (100, 96), (91, 99), (81, 96), (80, 88),
                        (86, 82)])
        a.paint(blaze, WHITE, light=0.35, dark=0.25, rim=0.25, shadow_col=WHITE_SH)
        for ex in (84, 98):
            a.stroke([(ex - 3.6, 84), (ex, 86.4), (ex + 3.6, 84)], "#3b3f45", 1.0, smooth=True)
        a.paint(a.blob([(89, 89), (93, 89), (91, 91.6)], smooth=False), PINK, light=0.3)
        a.stroke([(88.4, 93.4), (91, 94.4), (93.6, 93.4)], "#8a6f70", 0.5, smooth=True)
