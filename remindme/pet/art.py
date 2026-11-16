"""Tiny painting toolkit on top of Pillow for the illustrated avatars.

Everything is drawn supersampled (SS x) in the avatar's logical coordinate
system (0..120 box, see painter.ORIGIN) and then downscaled with Lanczos, so
shapes get smooth edges, soft gradients, rim shading and fur texture.
"""
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from .painter import LOGICAL, ORIGIN

SS = 3


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    a, b = (hex2rgb(a) if isinstance(a, str) else a), (hex2rgb(b) if isinstance(b, str) else b)
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def catmull(points, closed=True, steps=8):
    """Smooth a polygon through `points` (Catmull-Rom)."""
    pts = list(points)
    n = len(pts)
    out = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if closed or i > 0 else pts[0]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed or i + 2 < n else pts[-1]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t +
                                    (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 +
                                    (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)
                             for k in (0, 1)))
    if not closed:
        out.append(pts[-1])
    return out


_RADIAL = None


def _radial():
    global _RADIAL
    if _RADIAL is None:
        _RADIAL = ImageOps.invert(Image.radial_gradient("L"))  # bright centre
    return _RADIAL


class Art:
    def __init__(self, size_px):
        self.N = int(size_px * SS)
        self.k = self.N / LOGICAL   # px per logical unit
        self.img = Image.new("RGBA", (self.N, self.N), (0, 0, 0, 0))
        self.dx = 0.0  # horizontal offset (logical units) for the whole drawing

    # ------------------------------------------------------------ coords
    def P(self, x, y):
        return ((x + ORIGIN[0] + self.dx) * self.k, (y + ORIGIN[1]) * self.k)

    def L(self, v):
        return v * self.k

    # ------------------------------------------------------------ masks
    def new_mask(self):
        return Image.new("L", (self.N, self.N), 0)

    def ellipse(self, cx, cy, rx, ry, angle=0, m=None):
        m = m or self.new_mask()
        if angle:
            ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
            pts = []
            for i in range(48):
                a = 2 * math.pi * i / 48
                ex, ey = rx * math.cos(a), ry * math.sin(a)
                pts.append(self.P(cx + ex * ca - ey * sa, cy + ex * sa + ey * ca))
            ImageDraw.Draw(m).polygon(pts, fill=255)
        else:
            x0, y0 = self.P(cx - rx, cy - ry)
            x1, y1 = self.P(cx + rx, cy + ry)
            ImageDraw.Draw(m).ellipse((x0, y0, x1, y1), fill=255)
        return m

    def blob(self, points, m=None, smooth=True):
        m = m or self.new_mask()
        pts = catmull(points) if smooth else points
        ImageDraw.Draw(m).polygon([self.P(*p) for p in pts], fill=255)
        return m

    def capsule(self, pts, width, m=None, taper=None):
        """Thick stroke through pts with round caps (legs, arms, tails)."""
        m = m or self.new_mask()
        d = ImageDraw.Draw(m)
        n = len(pts)
        for i in range(n - 1):
            w0 = width if taper is None else width + (taper - width) * i / (n - 1)
            w1 = width if taper is None else width + (taper - width) * (i + 1) / (n - 1)
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            steps = max(2, int(math.hypot(x1 - x0, y1 - y0) / 1.5))
            for s in range(steps + 1):
                t = s / steps
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                r = (w0 + (w1 - w0) * t) / 2
                a, b = self.P(x - r, y - r)
                c, e = self.P(x + r, y + r)
                d.ellipse((a, b, c, e), fill=255)
        return m

    def rrect(self, x0, y0, x1, y1, r, m=None):
        m = m or self.new_mask()
        a, b = self.P(x0, y0)
        c, d = self.P(x1, y1)
        ImageDraw.Draw(m).rounded_rectangle((a, b, c, d), radius=self.L(r), fill=255)
        return m

    def fluff(self, m, amount=2.2, n=70, seed=1):
        """Make a mask's edge fluffy by adding little circles along it."""
        edge = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(3)))
        bbox = edge.getbbox()
        if not bbox:
            return m
        rnd = random.Random(seed)
        px = edge.load()
        d = ImageDraw.Draw(m)
        tries = 0
        placed = 0
        while placed < n and tries < n * 40:
            tries += 1
            x = rnd.randint(bbox[0], bbox[2] - 1)
            y = rnd.randint(bbox[1], bbox[3] - 1)
            if px[x, y] > 0:
                r = self.L(amount * rnd.uniform(0.5, 1.0))
                d.ellipse((x - r, y - r, x + r, y + r), fill=255)
                placed += 1
        return m

    def wisps(self, m, colors, n=80, length=3.0, width=0.8, seed=1, center=None, alpha=255):
        """Stray hairs poking out of a mask's edge (drawn on the image)."""
        edge = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(5)))
        bbox = edge.getbbox()
        if not bbox:
            return
        if center is None:
            cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        else:
            cx, cy = self.P(*center)
        rnd = random.Random(seed)
        px = edge.load()
        d = ImageDraw.Draw(self.img)
        w = max(1, int(self.L(width)))
        cols = [hex2rgb(c) + (alpha,) for c in colors]
        placed = tries = 0
        while placed < n and tries < n * 60:
            tries += 1
            x = rnd.randint(bbox[0], bbox[2] - 1)
            y = rnd.randint(bbox[1], bbox[3] - 1)
            if not px[x, y]:
                continue
            vx, vy = x - cx, y - cy
            a = math.atan2(vy, vx) + rnd.uniform(-0.6, 0.6)
            L = self.L(length) * rnd.uniform(0.5, 1.1)
            bend = rnd.uniform(-0.5, 0.5)
            x0, y0 = x - math.cos(a) * L * 0.4, y - math.sin(a) * L * 0.4
            mx, my = x + math.cos(a) * L * 0.3, y + math.sin(a) * L * 0.3
            ex, ey = x + math.cos(a + bend) * L * 0.7, y + math.sin(a + bend) * L * 0.7
            d.line([(x0, y0), (mx, my), (ex, ey)], fill=rnd.choice(cols), width=w)
            placed += 1

    @staticmethod
    def union(*ms):
        out = ms[0]
        for m in ms[1:]:
            out = ImageChops.lighter(out, m)
        return out

    @staticmethod
    def minus(a, b):
        return ImageChops.subtract(a, b)

    @staticmethod
    def intersect(a, b):
        return ImageChops.darker(a, b)

    # ------------------------------------------------------------ painting
    def paint(self, m, color, light=0.28, dark=0.32, rim=0.45, light_pos=(0.3, 0.2),
              fur=None, gloss=0.0, shadow_col=None, light_col=None, grad=None):
        """Fill mask `m` with a shaded colour.

        fur = dict(angle=deg, length=lu, density=0..1, light=hex, dark=hex, seed=int)
        grad = (top_hex, bottom_hex) vertical gradient instead of flat colour.
        """
        bbox = m.getbbox()
        if not bbox:
            return
        x0, y0, x1, y1 = bbox
        w, h = x1 - x0, y1 - y0
        mc = m.crop(bbox)
        base = hex2rgb(color)
        dk = hex2rgb(shadow_col) if shadow_col else mix(base, (20, 10, 5), 0.45)
        lt = hex2rgb(light_col) if light_col else mix(base, (255, 250, 240), 0.55)

        if grad:
            g = Image.linear_gradient("L").resize((w, h))
            layer = Image.composite(Image.new("RGBA", (w, h), hex2rgb(grad[1]) + (255,)),
                                    Image.new("RGBA", (w, h), hex2rgb(grad[0]) + (255,)), g)
        else:
            layer = Image.new("RGBA", (w, h), base + (255,))
        # vertical shading (darker towards the bottom)
        if dark:
            g = Image.linear_gradient("L").resize((w, h)).point(lambda v: int(v * dark))
            layer = Image.composite(Image.new("RGBA", (w, h), dk + (255,)), layer, g)
        # soft key light
        if light:
            rw, rh = max(1, int(w * 1.1)), max(1, int(h * 1.1))
            hl = _radial().resize((rw, rh))
            hm = Image.new("L", (w, h), 0)
            hm.paste(hl, (int(w * light_pos[0] - rw / 2), int(h * light_pos[1] - rh / 2)))
            hm = hm.point(lambda v: int(v * light))
            layer = Image.composite(Image.new("RGBA", (w, h), lt + (255,)), layer, hm)
        # rim / ambient occlusion along the edges
        if rim:
            r = max(2, int(min(w, h) * 0.12))
            inner = mc.filter(ImageFilter.GaussianBlur(r))
            edge = ImageChops.subtract(mc, inner).point(lambda v: min(255, int(v * 2.2 * rim)))
            layer = Image.composite(Image.new("RGBA", (w, h), dk + (255,)), layer, edge)
        if gloss:
            gw, gh = max(1, int(w * 0.55)), max(1, int(h * 0.28))
            gm = Image.new("L", (w, h), 0)
            ImageDraw.Draw(gm).ellipse((int(w * 0.14), int(h * 0.06), int(w * 0.14) + gw,
                                        int(h * 0.06) + gh), fill=int(255 * gloss))
            gm = gm.filter(ImageFilter.GaussianBlur(max(1, int(min(w, h) * 0.05))))
            layer = Image.composite(Image.new("RGBA", (w, h), (255, 255, 255, 255)), layer, gm)
        if fur:
            self._fur(layer, mc, fur)
        self.img.paste(layer, (x0, y0), mc)

    def _fur(self, layer, mc, fur):
        w, h = layer.size
        rnd = random.Random(fur.get("seed", 7))
        over = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        n = int(w * h / (self.k * self.k) * fur.get("density", 0.35))
        n = min(n, 2500)
        length = self.L(fur.get("length", 4))
        ang0 = math.radians(fur.get("angle", 90))
        cols = [hex2rgb(fur.get("light", "#ffffff")), hex2rgb(fur.get("dark", "#000000"))]
        alpha = int(255 * fur.get("alpha", 0.35))
        width = max(1, int(self.k * fur.get("width", 0.45)))
        px = mc.load()
        for _ in range(n):
            x, y = rnd.randrange(w), rnd.randrange(h)
            if px[x, y] < 200:
                continue
            a = ang0 + rnd.uniform(-0.35, 0.35)
            ln = length * rnd.uniform(0.6, 1.2)
            col = cols[rnd.random() < 0.5]
            bend = rnd.uniform(-0.25, 0.25)
            mx, my = x + math.cos(a) * ln / 2, y + math.sin(a) * ln / 2
            ex, ey = x + math.cos(a + bend) * ln, y + math.sin(a + bend) * ln
            d.line([(x, y), (mx, my), (ex, ey)], fill=col + (alpha,), width=width)
        layer.alpha_composite(over)

    def glow(self, m, color, radius=3, strength=1.0):
        """Additive-looking glow around a mask (eyes, lights)."""
        g = m.filter(ImageFilter.GaussianBlur(self.L(radius))).point(
            lambda v: min(255, int(v * strength)))
        layer = Image.new("RGBA", (self.N, self.N), hex2rgb(color) + (0,))
        layer.putalpha(g)
        self.img.alpha_composite(layer)

    def flat(self, m, color, alpha=255):
        layer = Image.new("RGBA", (self.N, self.N), hex2rgb(color) + (alpha,))
        if alpha < 255:
            mm = m.point(lambda v: v * alpha // 255)
        else:
            mm = m
        self.img.paste(layer, (0, 0), mm) if alpha == 255 else self.img.alpha_composite(
            Image.composite(layer, Image.new("RGBA", layer.size, (0, 0, 0, 0)), mm))

    def stroke(self, pts, color, width, alpha=255, smooth=False):
        d = ImageDraw.Draw(self.img)
        if smooth and len(pts) > 2:
            pts = catmull(pts, closed=False, steps=6)
        pp = [self.P(*p) for p in pts]
        w = max(1, int(self.L(width)))
        col = hex2rgb(color) + (alpha,)
        d.line(pp, fill=col, width=w, joint="curve")
        r = w / 2
        for x, y in (pp[0], pp[-1]):
            d.ellipse((x - r, y - r, x + r, y + r), fill=col)

    # ------------------------------------------------------------ finish
    def finish(self, outline="#2a1c12", outline_w=0.9):
        """Add a thin outline, downscale, and make alpha binary so the
        Windows transparent-colour key doesn't leave fringes."""
        img = self.img
        a = img.getchannel("A")
        if outline:
            k = max(3, int(self.L(outline_w) * 2) | 1)
            grown = a.filter(ImageFilter.MaxFilter(k))
            ol = Image.new("RGBA", img.size, hex2rgb(outline) + (255,))
            ol.putalpha(grown)
            ol.alpha_composite(img)
            img = ol
        size = self.N // SS
        img = img.resize((size, size), Image.LANCZOS)
        # binary alpha: blend partial pixels onto the outline colour
        bg = Image.new("RGBA", img.size, hex2rgb(outline or "#202020") + (255,))
        solid = Image.alpha_composite(bg, img)
        alpha = img.getchannel("A").point(lambda v: 255 if v >= 110 else 0)
        solid.putalpha(alpha)
        return solid
