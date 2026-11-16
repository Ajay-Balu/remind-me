"""Drawing helpers: avatars are drawn in a 140x140 logical box and the
Painter scales/mirrors everything onto the Tk canvas."""
import math

from ..toast import FONT_UI, rounded_rect

LOGICAL = 140   # canvas is LOGICAL x LOGICAL logical units
ORIGIN = (10, 24)  # avatar's 120x120 drawing box sits here (room above for Zzz etc.)


class Pose:
    """Everything an avatar needs to draw one frame."""

    def __init__(self, state, t, gt, phase, blink, facing, talking):
        self.state = state      # idle | walk | sleep | angry | laugh | happy | hop | held |
        #                          drop | drink | stretch | wake
        self.t = t              # seconds in current state
        self.gt = gt            # global clock (seconds)
        self.phase = phase      # walk cycle (radians)
        self.blink = blink
        self.facing = facing    # 1 = right, -1 = left
        self.talking = talking

    @property
    def mouth_open(self):
        return self.talking and math.sin(self.gt * 16) > -0.2


class Painter:
    def __init__(self, canvas, scale, ox, oy, facing=1, cx=60):
        self.c, self.s, self.ox, self.oy, self.f, self.cx = canvas, scale, ox, oy, facing, cx
        self.size_px = int(LOGICAL * scale)

    def X(self, x):
        return self.ox + (self.cx + (x - self.cx) * self.f) * self.s

    def Y(self, y):
        return self.oy + y * self.s

    def _kw(self, kw):
        if "width" in kw:
            kw["width"] = max(1.0, kw["width"] * self.s)
        return kw

    def _xs(self, x1, x2):
        a, b = self.X(x1), self.X(x2)
        return (a, b) if a <= b else (b, a)

    def oval(self, x1, y1, x2, y2, **kw):
        kw.setdefault("outline", "")
        a, b = self._xs(x1, x2)
        return self.c.create_oval(a, self.Y(y1), b, self.Y(y2), **self._kw(kw))

    def poly(self, pts, **kw):
        kw.setdefault("outline", "")
        flat = []
        for x, y in pts:
            flat += [self.X(x), self.Y(y)]
        return self.c.create_polygon(flat, **self._kw(kw))

    def line(self, pts, **kw):
        flat = []
        for x, y in pts:
            flat += [self.X(x), self.Y(y)]
        kw.setdefault("capstyle", "round")
        kw.setdefault("joinstyle", "round")
        return self.c.create_line(flat, **self._kw(kw))

    def thick(self, pts, fill, outline, width, smooth=False):
        """Outlined stroke (tails, legs, arms)."""
        self.line(pts, fill=outline, width=width + 3, smooth=smooth)
        self.line(pts, fill=fill, width=width, smooth=smooth)

    def rrect(self, x1, y1, x2, y2, r, **kw):
        kw.setdefault("outline", "")
        a, b = self._xs(x1, x2)
        return rounded_rect(self.c, a, self.Y(y1), b, self.Y(y2), r * self.s, **self._kw(kw))

    def arc(self, x1, y1, x2, y2, start, extent, **kw):
        a, b = self._xs(x1, x2)
        if self.f < 0:
            start = 180 - start - extent
        kw.setdefault("style", "arc")
        return self.c.create_arc(a, self.Y(y1), b, self.Y(y2), start=start, extent=extent,
                                 **self._kw(kw))

    def ellipse(self, cx, cy, rx, ry, angle=0, **kw):
        kw.setdefault("outline", "")
        ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        pts = []
        for i in range(28):
            a = 2 * math.pi * i / 28
            ex, ey = rx * math.cos(a), ry * math.sin(a)
            pts.append((cx + ex * ca - ey * sa, cy + ex * sa + ey * ca))
        return self.poly(pts, **kw)

    def text(self, x, y, txt, size, **kw):
        font = (FONT_UI, -max(6, int(size * self.s)), "bold")
        return self.c.create_text(self.X(x), self.Y(y), text=txt, font=font, **kw)

    def star(self, x, y, r, **kw):
        pts = []
        for i in range(8):
            rr = r if i % 2 == 0 else r * 0.35
            a = math.pi / 4 * i - math.pi / 2
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        return self.poly(pts, **kw)


def eye_mode(pose):
    st = pose.state
    if st in ("laugh", "happy", "drink", "stretch", "dig", "plant", "water"):
        return "happy"
    if st == "angry":
        return "angry"
    if st == "sleep":
        return "closed"
    if st in ("held", "drop", "fall"):
        return "wide"
    if st == "wake":
        return "closed" if pose.t < 0.9 else "open"
    if pose.blink:
        return "closed"
    return "open"


def draw_eye(p, x, y, r, mode, color="#1f2937", line=None):
    """Generic cartoon eye; `r` is the radius in logical units."""
    line = line or color
    if mode in ("open", "wide", "angry"):
        rr = r * (1.25 if mode == "wide" else 1.0)
        p.oval(x - rr * 0.85, y - rr, x + rr * 0.85, y + rr, fill=color)
        p.oval(x - rr * 0.05, y - rr * 0.75, x + rr * 0.5, y - rr * 0.2, fill="white")
        if mode == "angry":
            p.line([(x - r * 1.3, y - r * 1.9), (x + r * 1.4, y - r * 0.8)], fill=line, width=2.4)
    elif mode == "closed":
        p.arc(x - r, y - r * 0.9, x + r, y + r * 0.9, 200, 140, outline=line, width=2.2)
    elif mode == "happy":
        p.arc(x - r, y - r * 0.4, x + r, y + r * 1.6, 20, 140, outline=line, width=2.4)
