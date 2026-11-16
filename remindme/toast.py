"""react-hot-toast style notifications drawn with plain Tkinter.

Rounded white (or dark) cards that slide/fade in, stack in a screen corner,
pause their auto-dismiss timer while hovered and carry action buttons.
"""
import sys
import tkinter as tk
import tkinter.font as tkfont

from . import winapi

IS_WIN = sys.platform == "win32"
KEY = "#ff00fe"  # colour made transparent on Windows -> rounded corners

THEMES = {
    "light": dict(bg="#ffffff", border="#e5e7eb", title="#111827", text="#4b5563",
                  muted="#9ca3af", btn_bg="#f3f4f6", btn_fg="#111827", btn_hover="#e5e7eb",
                  primary_fg="#ffffff", progress_bg="#f3f4f6"),
    "dark": dict(bg="#1f2937", border="#374151", title="#f9fafb", text="#d1d5db",
                 muted="#9ca3af", btn_bg="#374151", btn_fg="#f9fafb", btn_hover="#4b5563",
                 primary_fg="#ffffff", progress_bg="#374151"),
}
ACCENTS = {"water": "#3b82f6", "blink": "#8b5cf6", "posture": "#10b981",
           "break": "#f59e0b", "info": "#6366f1", "success": "#22c55e"}

FONT_UI = "Segoe UI" if IS_WIN else "DejaVu Sans"
FONT_EMOJI = "Segoe UI Emoji" if IS_WIN else "Noto Color Emoji"


def _mix(hex_a, hex_b, t):
    """Blend colour a towards b by t (0..1)."""
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def _darken(hex_c, t=0.15):
    return _mix(hex_c, "#000000", t)


def rounded_rect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, splinesteps=24, **kw)


class Toast:
    WIDTH = 370

    def __init__(self, manager, kind, title, message, emoji="\U0001F514",
                 buttons=None, duration=None, on_close=None):
        self.m = manager
        self.kind = kind
        self.on_close = on_close
        self.closed = False
        self.hover = False
        self.duration = float(duration) if duration else None
        self.remaining = self.duration
        self.x = self.y = None
        self._anim = None

        s = manager.scale
        S = lambda v: int(round(v * s))  # noqa: E731
        th = THEMES.get(manager.theme, THEMES["light"])
        accent = ACCENTS.get(kind, ACCENTS["info"])
        self.th, self.accent = th, accent

        self.win = w = tk.Toplevel(manager.root)
        w.withdraw()
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        keycol = KEY if IS_WIN else th["bg"]
        w.configure(bg=keycol)
        if IS_WIN:
            w.attributes("-transparentcolor", KEY)

        W = self.W = S(self.WIDTH)
        pad = S(16)
        badge = S(42)
        c = self.c = tk.Canvas(w, width=W, height=S(120), bg=keycol,
                               highlightthickness=0, bd=0)
        c.pack()

        f_title = tkfont.Font(family=FONT_UI, size=11, weight="bold")
        f_text = tkfont.Font(family=FONT_UI, size=10)
        f_btn = tkfont.Font(family=FONT_UI, size=9, weight="bold")
        f_emoji = (FONT_EMOJI, 17)
        self._fonts = (f_title, f_text, f_btn)

        # emoji badge
        bx, by = pad, pad
        tint = _mix(accent, th["bg"], 0.82)
        c.create_oval(bx, by, bx + badge, by + badge, fill=tint, outline="")
        c.create_text(bx + badge / 2, by + badge / 2 + S(1), text=emoji, font=f_emoji)

        # title, message, close
        tx = bx + badge + S(12)
        text_w = W - tx - pad - S(14)
        title_id = c.create_text(tx, pad + S(1), text=title, anchor="nw", font=f_title,
                                 fill=th["title"], width=text_w)
        title_bottom = c.bbox(title_id)[3]
        self.msg_id = c.create_text(tx, title_bottom + S(3), text=message, anchor="nw",
                                    font=f_text, fill=th["text"], width=text_w)
        close = c.create_text(W - pad + S(4), pad - S(4), text="×", anchor="ne",
                              font=(FONT_UI, 13), fill=th["muted"])
        c.tag_bind(close, "<Button-1>", lambda e: self.close("dismiss"))
        c.tag_bind(close, "<Enter>", lambda e: c.itemconfigure(close, fill=th["title"]))
        c.tag_bind(close, "<Leave>", lambda e: c.itemconfigure(close, fill=th["muted"]))

        y = max(by + badge, c.bbox(self.msg_id)[3])

        # buttons
        if buttons:
            y += S(12)
            bx2 = tx
            bh = S(30)
            for spec in buttons:
                label, action = spec[0], spec[1]
                primary = spec[2] if len(spec) > 2 else False
                bw = f_btn.measure(label) + S(26)
                if bx2 > tx and bx2 + bw > W - pad:  # wrap to a new row
                    bx2 = tx
                    y += bh + S(8)
                self._make_button(bx2, y, bw, bh, label, action, primary, f_btn, S)
                bx2 += bw + S(8)
            y += bh

        y += pad
        self.progress = None
        if self.duration:
            y += S(2)
            self.prog_y = y - S(7)
            self.prog_x1, self.prog_x2 = pad, W - pad
            c.create_line(self.prog_x1, self.prog_y, self.prog_x2, self.prog_y,
                          fill=th["progress_bg"], width=S(3), capstyle="round")
            self.progress = c.create_line(self.prog_x1, self.prog_y, self.prog_x2, self.prog_y,
                                          fill=_mix(accent, th["bg"], 0.35), width=S(3),
                                          capstyle="round")

        self.H = H = y + S(2)
        c.configure(height=H)
        card = rounded_rect(c, 1, 1, W - 2, H - 2, S(14), fill=th["bg"], outline=th["border"])
        c.tag_lower(card)

        for seq, val in (("<Enter>", True), ("<Leave>", False)):
            w.bind(seq, lambda e, v=val: setattr(self, "hover", v))

        w.update_idletasks()
        winapi.make_no_activate(w)

    # ------------------------------------------------------------ widgets
    def _make_button(self, x, y, w, h, label, action, primary, font, S):
        c, th, acc = self.c, self.th, self.accent
        bg = acc if primary else th["btn_bg"]
        hov = _darken(acc) if primary else th["btn_hover"]
        fg = th["primary_fg"] if primary else th["btn_fg"]
        tag = f"btn{id(label)}_{x}"
        r = rounded_rect(c, x, y, x + w, y + h, S(8), fill=bg, outline="", tags=(tag,))
        c.create_text(x + w / 2, y + h / 2, text=label, font=font, fill=fg, tags=(tag,))

        def click(_e):
            keep = action() if action else None
            if keep != "keep":
                self.close("action")

        c.tag_bind(tag, "<Button-1>", click)
        c.tag_bind(tag, "<Enter>", lambda e: (c.itemconfigure(r, fill=hov),
                                              c.configure(cursor="hand2")))
        c.tag_bind(tag, "<Leave>", lambda e: (c.itemconfigure(r, fill=bg),
                                              c.configure(cursor="")))

    def set_message(self, text):
        if not self.closed:
            self.c.itemconfigure(self.msg_id, text=text)

    # ------------------------------------------------------------ lifecycle
    def show_at(self, x, y):
        """First placement: slide + fade in."""
        self.x, self.y = x, y
        from_bottom = self.m.position.startswith("bottom")
        offset = int(14 * self.m.scale) * (1 if from_bottom else -1)
        self.win.geometry(f"+{x}+{y + offset}")
        self._set_alpha(0.0)
        self.win.deiconify()
        steps = 10

        def frame(i=1):
            if self.closed:
                return
            t = i / steps
            ease = 1 - (1 - t) ** 3
            self._set_alpha(ease)
            self.win.geometry(f"+{self.x}+{int(self.y + offset * (1 - ease))}")
            if i < steps:
                self._anim = self.win.after(16, frame, i + 1)
            else:
                self._anim = None
                self._tick()

        frame()

    def move_to(self, x, y):
        self.x, self.y = x, y
        if self._anim is None and not self.closed:
            self.win.geometry(f"+{x}+{y}")

    def _set_alpha(self, a):
        try:
            self.win.attributes("-alpha", max(0.0, min(1.0, a)))
        except tk.TclError:
            pass

    def _tick(self):
        if self.closed or not self.duration:
            return
        if not self.hover:
            self.remaining -= 0.05
        if self.remaining <= 0:
            self.close("timeout")
            return
        frac = self.remaining / self.duration
        x2 = self.prog_x1 + (self.prog_x2 - self.prog_x1) * frac
        self.c.coords(self.progress, self.prog_x1, self.prog_y, x2, self.prog_y)
        self.win.after(50, self._tick)

    def close(self, reason="dismiss"):
        if self.closed:
            return
        self.closed = True
        if self._anim:
            try:
                self.win.after_cancel(self._anim)
            except tk.TclError:
                pass
        self.m._remove(self)
        if self.on_close:
            try:
                self.on_close(reason)
            except Exception:
                pass

        def fade(i=8):
            if i <= 0:
                self.win.destroy()
                return
            self._set_alpha(i / 8)
            self.win.after(15, fade, i - 1)

        fade()


class ToastManager:
    MAX = 5

    def __init__(self, root, get_cfg):
        self.root = root
        self.get_cfg = get_cfg
        self.toasts = []
        try:
            self.scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
        except tk.TclError:
            self.scale = 1.0

    @property
    def theme(self):
        return self.get_cfg()["toast"].get("theme", "light")

    @property
    def position(self):
        return self.get_cfg()["toast"].get("position", "bottom-right")

    def show(self, kind, title, message, emoji="\U0001F514", buttons=None,
             duration=None, on_close=None):
        while len(self.toasts) >= self.MAX:
            self.toasts[0].close("overflow")
        t = Toast(self, kind, title, message, emoji, buttons, duration, on_close)
        self.toasts.append(t)
        self._layout(new=t)
        return t

    def _remove(self, t):
        if t in self.toasts:
            self.toasts.remove(t)
            self._layout()

    def _layout(self, new=None):
        left, top, right, bottom = winapi.work_area(self.root)
        s = self.scale
        margin, gap = int(18 * s), int(10 * s)
        pos = self.position
        from_bottom = pos.startswith("bottom")
        y = bottom - margin if from_bottom else top + margin
        for t in reversed(self.toasts):  # newest nearest the screen edge
            if pos.endswith("right"):
                x = right - margin - t.W
            elif pos.endswith("left"):
                x = left + margin
            else:
                x = (left + right - t.W) // 2
            if from_bottom:
                ty = y - t.H
                y = ty - gap
            else:
                ty = y
                y = ty + t.H + gap
            if t is new:
                t.show_at(x, ty)
            else:
                t.move_to(x, ty)

    def close_kind(self, kind):
        for t in list(self.toasts):
            if t.kind == kind:
                t.close("replaced")
