"""PNG sprite-pack avatars.

Drop a folder into  assets\\avatars\\<name>\\  (next to run.pyw) or
%APPDATA%\\RemindMe\\avatars\\<name>\\  containing avatar.json + PNG frames.
See assets\\avatars\\_template\\ for the format. Folders starting with "_"
are ignored.
"""
import glob
import json
import logging
import os
import sys

from PIL import Image, ImageOps

from .. import config
from .base import Avatar
from .painter import ORIGIN

log = logging.getLogger("remindme")

# which frames to use when a pack doesn't have a state
FALLBACK = {
    "hop": ["happy", "idle"], "drop": ["idle"], "wake": ["happy", "idle"],
    "laugh": ["happy", "idle"], "happy": ["idle"], "angry": ["idle"], "held": ["idle"],
    "drink": ["happy", "idle"], "stretch": ["idle"], "sleep": ["idle"], "walk": ["idle"],
    "talk": ["idle"], "fall": ["held", "idle"], "dig": ["stretch", "idle"],
    "plant": ["stretch", "idle"], "water": ["happy", "idle"],
}


def app_dirs():
    dirs = [os.path.join(config.config_dir(), "avatars")]
    if getattr(sys, "frozen", False):
        dirs.append(os.path.join(os.path.dirname(sys.executable), "assets", "avatars"))
        base = getattr(sys, "_MEIPASS", None)
        if base:
            dirs.append(os.path.join(base, "assets", "avatars"))
    else:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dirs.append(os.path.join(root, "assets", "avatars"))
    return dirs


class SpriteAvatar(Avatar):
    def __init__(self, folder, meta):
        self.folder = folder
        slug = os.path.basename(folder.rstrip("\\/"))
        self.key = "sprite:" + slug
        self.name = meta.get("name", slug)
        self.label = meta.get("label", f"{self.name} (sprite pack)")
        self.native_facing = -1 if meta.get("facing", "right") == "left" else 1
        self.fps = float(meta.get("fps", 8))
        self.LINES = meta.get("lines", {})
        anc = meta.get("anchors", {})
        self._anchors = (tuple(anc.get("head_top", (70, 20))), tuple(anc.get("mouth", (90, 60))),
                         tuple(anc.get("eye", (84, 40))))
        self.states = {}
        for state, patterns in meta.get("states", {}).items():
            if isinstance(patterns, str):
                patterns = [patterns]
            files = []
            for pat in patterns:
                files += sorted(glob.glob(os.path.join(folder, pat)))
            if files:
                self.states[state] = files
        self._photos = {}
        self._pils = {}

    def __call__(self):  # registry entries are "classes"; a pack is its own instance
        return self

    def anchors(self, pose):
        return self._anchors

    def _frames(self, pose):
        st = pose.state
        if pose.talking and "talk" in self.states and st in ("idle", "hop"):
            st = "talk"
        if st not in self.states:
            for alt in FALLBACK.get(st, ["idle"]):
                if alt in self.states:
                    st = alt
                    break
            else:
                st = next(iter(self.states), None)
        return self.states.get(st, [])

    def _load(self, path, size_px):
        key = (path, size_px)
        img = self._pils.get(key)
        if img is not None:
            return img
        img = Image.open(path).convert("RGBA")
        box_w, box_h = int(120 * size_px / 140), int(118 * size_px / 140)
        img.thumbnail((box_w, box_h), Image.LANCZOS)
        canvas = Image.new("RGBA", (size_px, size_px), (0, 0, 0, 0))
        ox = int(ORIGIN[0] * size_px / 140 + (box_w - img.width) / 2)
        oy = int((ORIGIN[1] + 112) * size_px / 140 - img.height)
        canvas.alpha_composite(img, (max(0, ox), max(0, oy)))
        # binary alpha so the Windows transparency key leaves no fringe
        bg = Image.new("RGBA", canvas.size, (40, 40, 40, 255))
        solid = Image.alpha_composite(bg, canvas)
        solid.putalpha(canvas.getchannel("A").point(lambda v: 255 if v >= 110 else 0))
        self._pils[key] = solid
        return solid

    def draw(self, p, pose):
        frames = self._frames(pose)
        if not frames:
            return
        if pose.state == "walk":
            i = int(pose.phase / 6.2832 * len(frames)) % len(frames)
        else:
            i = int(pose.gt * self.fps) % len(frames)
        flip = pose.facing != self.native_facing
        k = (frames[i], p.size_px, flip)
        ph = self._photos.get(k)
        if ph is None:
            from PIL import ImageTk
            try:
                img = self._load(frames[i], p.size_px)
            except Exception:
                log.exception("bad sprite %s", frames[i])
                return
            ph = ImageTk.PhotoImage(ImageOps.mirror(img) if flip else img)
            self._photos[k] = ph
        p.c.create_image(p.ox - ORIGIN[0] * p.s, p.oy - ORIGIN[1] * p.s, image=ph, anchor="nw")


def load_sprite_packs():
    packs = {}
    for d in app_dirs():
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            folder = os.path.join(d, name)
            meta_path = os.path.join(folder, "avatar.json")
            if name.startswith("_") or not os.path.isfile(meta_path):
                continue
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    av = SpriteAvatar(folder, json.load(f))
                if av.states:
                    packs[av.key] = av
                else:
                    log.warning("sprite pack %s has no frames", folder)
            except Exception:
                log.exception("could not load sprite pack %s", folder)
    return packs
