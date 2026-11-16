"""Comic speech bubble that floats next to the pet and can carry buttons."""
import tkinter as tk
import tkinter.font as tkfont

from .. import winapi
from ..toast import ACCENTS, FONT_UI, IS_WIN, KEY, THEMES, _darken, rounded_rect


class Bubble:
    WIDTH = 260

    def __init__(self, pet, kind, title, text, buttons=None, duration=None, on_close=None,
                 speak=False):
        self.pet = pet
        self.kind = kind
        self.title = title
        self.text = text
        self.buttons = buttons or []
        self.blocking = bool(buttons)
        self.duration = float(duration) if duration else None
        self.remaining = self.duration
        self.on_close = on_close
        self.speak = speak
        self.closed = False
        self.opened = False
        self.hover = False
        self.win = None
        self._layout_key = None

    # ------------------------------------------------------------ build
    def open(self):
        self.opened = True
        pet = self.pet
        s = pet.dpi
        S = lambda v: int(round(v * s))  # noqa: E731
        th = THEMES.get(pet.app.cfg["toast"].get("theme", "light"), THEMES["light"])
        accent = ACCENTS.get(self.kind, ACCENTS["info"])
        self.th, self.accent, self.S = th, accent, S

        self.win = w = tk.Toplevel(pet.root)
        w.withdraw()
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        keycol = KEY if IS_WIN else "#000001"
        w.configure(bg=keycol)
        if IS_WIN:
            w.attributes("-transparentcolor", KEY)
        self.W = W = S(self.WIDTH)
        pad = S(12)
        self.T = S(12)  # tail height
        c = self.c = tk.Canvas(w, width=W, height=S(80), bg=keycol, highlightthickness=0, bd=0)
        c.pack()

        f_title = tkfont.Font(family=FONT_UI, size=10, weight="bold")
        f_text = tkfont.Font(family=FONT_UI, size=10)
        f_btn = tkfont.Font(family=FONT_UI, size=9, weight="bold")
        self._fonts = (f_title, f_text, f_btn)

        y = pad
        if self.title:
            tid = c.create_text(pad, y, text=self.title, anchor="nw", font=f_title, fill=accent,
                                width=W - 2 * pad - S(14), tags=("content",))
            y = c.bbox(tid)[3] + S(2)
        self.msg_id = c.create_text(pad, y, text=self.text, anchor="nw", font=f_text,
                                    fill=th["title"], width=W - 2 * pad - S(10),
                                    tags=("content",))
        y = c.bbox(self.msg_id)[3]
        close = c.create_text(W - S(8), S(6), text="×", anchor="ne", font=(FONT_UI, 12),
                              fill=th["muted"], tags=("content",))
        c.tag_bind(close, "<Button-1>", lambda e: self.close("dismiss"))

        if self.buttons:
            y += S(10)
            bx, bh = pad, S(26)
            for spec in self.buttons:
                label, action = spec[0], spec[1]
                primary = spec[2] if len(spec) > 2 else False
                bw = f_btn.measure(label) + S(22)
                if bx > pad and bx + bw > W - pad:
                    bx, y = pad, y + bh + S(6)
                self._button(bx, y, bw, bh, label, action, primary, f_btn)
                bx += bw + S(6)
            y += bh
        self.Hb = y + pad
        c.configure(height=self.Hb + self.T)
        self._offset = 0  # content shift (T when tail is on top)

        for seq, v in (("<Enter>", True), ("<Leave>", False)):
            w.bind(seq, lambda e, v=v: setattr(self, "hover", v))
        w.update_idletasks()
        winapi.make_no_activate(w)
        pet.place_bubble(self)
        w.deiconify()
        if self.duration:
            w.after(100, self._tick)

    def _button(self, x, y, w, h, label, action, primary, font):
        c, th, acc, S = self.c, self.th, self.accent, self.S
        bg = acc if primary else th["btn_bg"]
        hov = _darken(acc) if primary else th["btn_hover"]
        fg = th["primary_fg"] if primary else th["btn_fg"]
        tag = f"b{x}_{y}"
        r = rounded_rect(c, x, y, x + w, y + h, S(7), fill=bg, outline="", tags=(tag, "content"))
        c.create_text(x + w / 2, y + h / 2, text=label, font=font, fill=fg, tags=(tag, "content"))

        def click(_e):
            self.close("action")  # close first so the pet can react straight away
            if action:
                action()

        c.tag_bind(tag, "<Button-1>", click)
        c.tag_bind(tag, "<Enter>", lambda e: (c.itemconfigure(r, fill=hov),
                                              c.configure(cursor="hand2")))
        c.tag_bind(tag, "<Leave>", lambda e: (c.itemconfigure(r, fill=bg),
                                              c.configure(cursor="")))

    # ------------------------------------------------------------ geometry
    def size(self):
        return self.W, self.Hb + self.T

    def place(self, x, y, tail_x, tail_on_top):
        """Called by the pet every frame with the computed position."""
        if self.closed or not self.win:
            return
        key = (int(tail_x), tail_on_top)
        if key != self._layout_key:
            self._layout_key = key
            self._draw_shape(tail_x, tail_on_top)
        self.win.geometry(f"+{int(x)}+{int(y)}")

    def _draw_shape(self, tail_x, top):
        c, th, S, T, W, Hb = self.c, self.th, self.S, self.T, self.W, self.Hb
        want = T if top else 0
        if want != self._offset:
            c.move("content", 0, want - self._offset)
            self._offset = want
        c.delete("shape")
        y0 = T if top else 0
        body = rounded_rect(c, 1, y0 + 1, W - 2, y0 + Hb - 1, S(14), fill=th["bg"],
                            outline=th["border"], width=max(1, S(1.5)), tags=("shape",))
        tx = max(S(22), min(W - S(22), tail_x))
        hw = S(8)
        if top:
            pts = [tx - hw, y0 + 2, tx, 1, tx + hw, y0 + 2]
            seam = y0 + 1
        else:
            pts = [tx - hw, y0 + Hb - 2, tx, y0 + Hb + T - 1, tx + hw, y0 + Hb - 2]
            seam = y0 + Hb - 1
        c.create_polygon(pts, fill=th["bg"], outline=th["border"], width=max(1, S(1.5)),
                         tags=("shape",))
        c.create_line(tx - hw + S(2), seam, tx + hw - S(2), seam, fill=th["bg"],
                      width=max(2, S(3)), tags=("shape",))
        c.tag_lower("shape")
        del body

    # ------------------------------------------------------------ lifecycle
    def set_message(self, text):
        self.text = text
        if self.opened and not self.closed:
            self.c.itemconfigure(self.msg_id, text=text)

    def _tick(self):
        if self.closed:
            return
        if not self.hover:
            self.remaining -= 0.1
        if self.remaining <= 0:
            self.close("timeout")
            return
        self.win.after(100, self._tick)

    def close(self, reason="dismiss"):
        if self.closed:
            return
        self.closed = True
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
        self.pet.bubble_closed(self, reason)
        if self.on_close:
            try:
                self.on_close(reason)
            except Exception:
                pass
