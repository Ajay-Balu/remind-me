"""Settings storage: %APPDATA%\\RemindMe\\config.json"""
import copy
import json
import os

APP_NAME = "RemindMe"

DEFAULTS = {
    "reminders": {
        "water": {
            "enabled": True,
            "interval_min": 45,
            "emoji": "\U0001F4A7",  # droplet
            "title": "Drink some water",
            "message": "Time for a glass of water. Stay hydrated!",
        },
        "blink": {
            "enabled": True,
            "interval_min": 20,
            "emoji": "\U0001F440",  # eyes
            "title": "Rest your eyes",
            "message": "20-20-20: look at something 20 feet away for 20 seconds and blink slowly.",
        },
        "posture": {
            "enabled": True,
            "interval_min": 30,
            "emoji": "\U0001F9CD",  # standing person
            "title": "Check your posture",
            "message": "Shoulders back, feet flat, screen at eye level. Maybe stand for a bit.",
        },
        "break": {
            "enabled": True,
            "interval_min": 60,
            "break_min": 5,
            "emoji": "☕",  # coffee
            "title": "Take a break",
            "message": "You've been at it for a while. Step away and stretch.",
        },
    },
    "snooze_min": 5,
    # If you don't touch keyboard/mouse for this long you're "away": reminders
    # wait, and an away period at least as long as a break counts as a break.
    "away_after_min": 5,
    "jiggle": {
        "enabled": True,
        "idle_seconds": 60,   # nudge after this many idle seconds (and every N s while idle)
        "pixels": 1,          # how far the pointer moves (it always returns to where it was)
        "prevent_sleep": True,  # also tell Windows not to sleep / turn off display
    },
    "toast": {
        "position": "bottom-right",  # bottom-right | bottom-left | top-right | top-center | bottom-center
        "theme": "light",            # light | dark
        "auto_dismiss_sec": 60,      # 0 = stay until you click
        "sound": True,
    },
    "start_with_windows": False,
    "pet": {
        "enabled": True,
        "avatar": "dog",        # dog | cat | robot
        "size": 100,            # percent
        "roam": True,           # wander around the screen
        "follow_mouse": False,
        "gravity": False,       # live on top of the taskbar
        "garden_on": True,      # in gravity mode, plant & water a little garden
        "garden": [],           # saved plants
        "x": None,              # last position (set when you drop it)
        "y": None,
        "voice": {
            "enabled": True,
            "name": "",         # "" = Windows default voice
            "rate": 0,          # -10 .. 10
            "volume": 90,       # 0 .. 100
            "reactions": False,  # also speak chatter like "Ouch!" / "Hahaha"
        },
    },
}

REMINDER_ORDER = ["water", "blink", "posture", "break"]


def config_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def config_path():
    return os.path.join(config_dir(), "config.json")


def _merge(defaults, saved):
    out = copy.deepcopy(defaults)
    if not isinstance(saved, dict):
        return out
    for key, val in saved.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _merge(out[key], val)
        else:
            out[key] = val
    return out


def load():
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            return _merge(DEFAULTS, json.load(f))
    except (OSError, ValueError):
        return copy.deepcopy(DEFAULTS)


def save(cfg):
    tmp = config_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, config_path())
