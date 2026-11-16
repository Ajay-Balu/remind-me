"""Base class for avatars rendered as shaded images, plus the frame cache.

Frames are keyed by (group, index, eyes, mouth). They are rendered with
Pillow (see art.py) in a background thread, kept in memory, and saved to
%APPDATA%\\RemindMe\\cache so later launches are instant.
"""
import logging
import math
import os
import threading
from collections import OrderedDict

from PIL import Image, ImageOps

from .. import config
from .base import Avatar
from .painter import LOGICAL, ORIGIN, eye_mode

log = logging.getLogger("remindme")
TWO_PI = 2 * math.pi


def mouth_mode(pose):
    st = pose.state
    if st == "angry":
        return "frown"
    if st in ("held", "drop", "fall"):
        return "o"
    if st in ("laugh", "happy", "hop") or (st == "wake" and pose.t < 0.9):
        return "open"
    if pose.mouth_open:
        return "talk"
    return "smile"


class ImageAvatar(Avatar):
    VERSION = 1
    WALK_FRAMES = 12

    # ------------------------------------------------------------ keys
    def frame_key(self, pose):
        st, t, g = pose.state, pose.t, pose.gt
        eye, mouth = eye_mode(pose), mouth_mode(pose)
        if st == "walk":
            return ("walk", int(pose.phase / TWO_PI * self.WALK_FRAMES) % self.WALK_FRAMES,
                    eye, mouth)
        if st == "sleep":
            return ("sleep", int((g * 0.5) % 1 * 6), "closed", "smile")
        if st == "stretch":
            return ("stretch", int(round((math.sin(t * 1.6) + 1) / 2 * 6)), eye, mouth)
        if st in ("happy", "laugh"):
            return ("excited", int(g * 10) % 6, eye, mouth)
        if st == "angry":
            return ("angry", int(g * 8) % 2, eye, mouth)
        if st in ("held", "fall"):
            return ("held", int(g * 7 / TWO_PI * 8) % 8, eye, mouth)
        if st == "dig":
            return ("dig", int(g * 9) % 4, eye, mouth)
        if st == "plant":
            return ("stretch", 4, eye, mouth)
        if st == "water":
            return ("stand", 0, eye, mouth)
        if st == "drink":
            return ("drink", 0, eye, mouth)
        return ("stand", int(g / 3 * 6) % 6, eye, mouth)

    def warm_keys(self):
        keys = []
        for i in range(6):
            keys += [("stand", i, "open", "smile"), ("stand", i, "closed", "smile")]
        keys += [("walk", i, "open", "smile") for i in range(self.WALK_FRAMES)]
        keys += [("stand", i, "open", "talk") for i in range(6)]
        keys += [("sleep", i, "closed", "smile") for i in range(6)]
        keys += [("excited", i, "happy", "open") for i in range(6)]
        keys += [("angry", i, "angry", "frown") for i in range(2)]
        keys += [("held", i, "wide", "o") for i in range(8)]
        keys += [("stretch", i, "happy", "smile") for i in range(7)]
        keys += [("drink", 0, "happy", "smile")]
        keys += [("dig", i, "happy", "smile") for i in range(4)]
        keys += [("stand", 0, "happy", "smile")]
        return keys

    # ------------------------------------------------------------ render
    def paint(self, art, key):
        """Subclasses draw one frame onto `art` (facing right)."""
        raise NotImplementedError

    def outline(self):
        return "#2a1c12"

    def outline_width(self):
        return 0.9

    def render(self, key, size_px):
        from .art import Art
        art = Art(size_px)
        self.paint(art, key)
        return art.finish(self.outline(), self.outline_width())

    # ------------------------------------------------------------ draw
    def draw(self, p, pose):
        key = self.frame_key(pose)
        photo = FRAMES.photo(self, key, p.size_px, pose.facing if self.mirror else 1)
        if photo is not None:
            p.c.create_image(p.ox - ORIGIN[0] * p.s, p.oy - ORIGIN[1] * p.s, image=photo,
                             anchor="nw")


class FrameCache:
    MAX_PHOTOS = 260

    def __init__(self):
        self.pil = {}                      # (avatar, ver, size, key) -> PIL image
        self.photos = OrderedDict()        # + facing -> PhotoImage
        self._lock = threading.Lock()
        self._warming = set()

    def _dir(self, av, size):
        d = os.path.join(config.config_dir(), "cache", f"{av.key}_v{av.VERSION}_{size}")
        os.makedirs(d, exist_ok=True)
        return d

    @staticmethod
    def _fname(key):
        return "_".join(str(k) for k in key) + ".png"

    def get_pil(self, av, key, size):
        ck = (av.key, av.VERSION, size, key)
        img = self.pil.get(ck)
        if img is not None:
            return img
        path = os.path.join(self._dir(av, size), self._fname(key))
        try:
            if os.path.exists(path):
                img = Image.open(path)
                img.load()
        except Exception:
            img = None
        if img is None:
            try:
                img = av.render(key, size)
            except Exception:
                log.exception("render failed for %s %s", av.key, key)
                img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            try:
                img.save(path)
            except Exception:
                pass
        self.pil[ck] = img
        return img

    def photo(self, av, key, size, facing):
        from PIL import ImageTk
        pk = (av.key, av.VERSION, size, key, facing)
        ph = self.photos.get(pk)
        if ph is not None:
            self.photos.move_to_end(pk)
            return ph
        img = self.get_pil(av, key, size)
        if facing < 0:
            img = ImageOps.mirror(img)
        ph = ImageTk.PhotoImage(img)
        self.photos[pk] = ph
        while len(self.photos) > self.MAX_PHOTOS:
            self.photos.popitem(last=False)
        return ph

    def warm(self, av, size):
        """Render the common frames in the background."""
        wk = (av.key, av.VERSION, size)
        if wk in self._warming:
            return
        self._warming.add(wk)

        def run():
            for key in av.warm_keys():
                try:
                    self.get_pil(av, key, size)
                except Exception:
                    log.exception("warm failed")
        threading.Thread(target=run, daemon=True).start()


FRAMES = FrameCache()


def logical_size(scale):
    return int(LOGICAL * scale)
