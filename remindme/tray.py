"""System-tray icon and menu (pystray). Runs on its own thread; every action
is forwarded to the Tk thread through App.call()."""
from PIL import Image, ImageDraw

try:
    import pystray
    from pystray import Menu, MenuItem as Item
except Exception:  # pragma: no cover - lets the UI run where no tray exists
    pystray = None


def make_icon(color="#3b82f6", size=256, dot=None):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, size - 4, size - 4), fill=color)
    # white water drop
    cx = size / 2
    d.polygon([(cx, size * 0.17), (size * 0.305, size * 0.56), (size * 0.695, size * 0.56)],
              fill="white")
    d.ellipse((size * 0.29, size * 0.40, size * 0.71, size * 0.82), fill="white")
    if dot:  # small status dot (e.g. paused)
        r = size * 0.17
        d.ellipse((size - 2 * r - 2, size - 2 * r - 2, size - 2, size - 2),
                  fill=dot, outline="white", width=max(2, size // 40))
    return img


def save_ico(path="icon.ico"):
    make_icon().save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])


ICON_ACTIVE = "#3b82f6"
ICON_PAUSED = "#9ca3af"


class Tray:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self._paused_drawn = None

    def start(self):
        if pystray is None:
            return
        a = self.app
        c = a.call
        menu = Menu(
            Item(lambda item: a.status_line(), None, enabled=False),
            Menu.SEPARATOR,
            Item("Remind me now", Menu(
                Item("\U0001F4A7  Drink water", lambda: c(a.show_reminder, "water")),
                Item("\U0001F440  Rest eyes", lambda: c(a.show_reminder, "blink")),
                Item("\U0001F9CD  Posture", lambda: c(a.show_reminder, "posture")),
                Item("☕  Break", lambda: c(a.show_reminder, "break")),
            )),
            Item("Pause reminders", Menu(
                Item("30 minutes", lambda: c(a.pause, 30)),
                Item("1 hour", lambda: c(a.pause, 60)),
                Item("2 hours", lambda: c(a.pause, 120)),
                Item("Until I resume", lambda: c(a.pause, None)),
            ), visible=lambda item: not a.is_paused()),
            Item("Resume reminders", lambda: c(a.resume), visible=lambda item: a.is_paused()),
            Menu.SEPARATOR,
            Item("Show avatar", lambda: c(a.toggle_pet),
                 checked=lambda item: a.cfg["pet"]["enabled"]),
            Item("Avatar follows my mouse", lambda: c(a.toggle_follow),
                 checked=lambda item: a.cfg["pet"].get("follow_mouse", False),
                 enabled=lambda item: a.cfg["pet"]["enabled"]),
            Item("Gravity (avatar lives on the taskbar)", lambda: c(a.toggle_gravity),
                 checked=lambda item: a.cfg["pet"].get("gravity", False),
                 enabled=lambda item: a.cfg["pet"]["enabled"]),
            Menu.SEPARATOR,
            Item("Settings…", lambda: c(a.open_settings), default=True),
            Item("Quit", lambda: c(a.quit)),
        )
        self.icon = pystray.Icon("RemindMe", make_icon(ICON_ACTIVE, 64), "Remind Me", menu)
        self.icon.run_detached()

    def refresh(self):
        """Update tooltip, icon colour and dynamic menu items."""
        if not self.icon:
            return
        paused = self.app.is_paused()
        try:
            if paused != self._paused_drawn:
                self.icon.icon = make_icon(ICON_PAUSED if paused else ICON_ACTIVE, 64,
                                           dot="#f59e0b" if paused else None)
                self._paused_drawn = paused
            self.icon.title = self.app.tooltip()[:127]
            self.icon.update_menu()
        except Exception:
            pass

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
