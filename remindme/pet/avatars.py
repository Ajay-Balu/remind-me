"""Avatar registry.

Built-in illustrated avatars + any PNG sprite packs found on disk.
To add a code-drawn avatar: subclass ImageAvatar (see dog.py), then add it
to BUILTIN below. To add art: see assets/avatars/_template.
"""
import logging

from .cat import Cat
from .dog import Dog
from .robot import Robot

log = logging.getLogger("remindme")

BUILTIN = (Dog, Cat, Robot)
DEFAULT_AVATAR = "dog"

AVATARS = {cls.key: cls for cls in BUILTIN}
try:
    from .sprites import load_sprite_packs
    AVATARS.update(load_sprite_packs())
except Exception:  # never let a bad pack stop the app
    log.exception("sprite packs not loaded")


def make_avatar(key):
    return AVATARS.get(key, AVATARS[DEFAULT_AVATAR])()
