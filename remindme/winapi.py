"""Thin ctypes wrappers around the Windows APIs we need.

Every function degrades to a harmless no-op on non-Windows so the UI can be
developed/tested elsewhere.
"""
import ctypes
import os
import sys
import time

IS_WIN = sys.platform == "win32"

if IS_WIN:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    ULONG_PTR = ctypes.c_size_t

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
    user32.GetLastInputInfo.restype = wintypes.BOOL
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    kernel32.GetTickCount.restype = wintypes.DWORD
    kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
    kernel32.SetThreadExecutionState.restype = wintypes.DWORD

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

_T0 = time.monotonic()


# ---------------------------------------------------------------- idle / input
def tick_count():
    """Milliseconds since boot (32-bit, wraps every ~49 days)."""
    if IS_WIN:
        return int(kernel32.GetTickCount())
    return int((time.monotonic() - _T0) * 1000) & 0xFFFFFFFF


def last_input_tick():
    """Tick of the last keyboard/mouse input anywhere in the session."""
    if IS_WIN:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetLastInputInfo(ctypes.byref(info)):
            return int(info.dwTime)
    return tick_count()


def ticks_between(earlier, later):
    return (later - earlier) & 0xFFFFFFFF


def _send_move(dx, dy):
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, 0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def nudge_mouse(pixels=1):
    """Move the pointer by `pixels` and put it back exactly where it was.

    SendInput produces real input, so Windows / Teams / Slack see activity.
    SetCursorPos then restores the original position (pointer acceleration
    can make a relative move-back inaccurate).
    """
    if not IS_WIN:
        return
    pixels = max(1, int(pixels))
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    _send_move(pixels, pixels)
    time.sleep(0.04)
    _send_move(-pixels, -pixels)
    time.sleep(0.02)
    user32.SetCursorPos(pt.x, pt.y)


def keep_awake(on):
    """Ask Windows not to sleep / blank the display while the app runs."""
    if not IS_WIN:
        return
    flags = ES_CONTINUOUS
    if on:
        flags |= ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    kernel32.SetThreadExecutionState(flags)


# ---------------------------------------------------------------- display
def set_dpi_aware():
    if not IS_WIN:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def work_area(root):
    """(left, top, right, bottom) of the primary screen minus the taskbar."""
    if IS_WIN:
        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight() - 40


def virtual_screen(root):
    """(left, top, right, bottom) spanning all monitors."""
    if IS_WIN:
        gsm = ctypes.windll.user32.GetSystemMetrics
        x, y, w, h = gsm(76), gsm(77), gsm(78), gsm(79)
        if w and h:
            return x, y, x + w, y + h
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def hwnd_of(tk_window):
    """Top-level HWND of a Tk window (the frame Windows actually stacks)."""
    try:
        h = int(tk_window.wm_frame(), 16)
        if h:
            return h
    except Exception:
        pass
    return ctypes.windll.user32.GetParent(tk_window.winfo_id()) or tk_window.winfo_id()


if IS_WIN:
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]

HWND_TOPMOST = -1
SWP_FLAGS = 0x0001 | 0x0002 | 0x0010 | 0x0200  # NOSIZE | NOMOVE | NOACTIVATE | NOOWNERZORDER
SW_SHOWNOACTIVATE = 4


def keep_on_top(tk_window):
    """Re-assert always-on-top and un-hide the window if Windows minimised it
    (e.g. after Win+D / Show desktop or another app grabbing topmost)."""
    if not IS_WIN:
        return
    try:
        hwnd = hwnd_of(tk_window)
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    except Exception:
        pass


def make_no_activate(tk_window):
    """Stop a toast from stealing keyboard focus and hide it from Alt-Tab."""
    if not IS_WIN:
        return
    try:
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        hwnd = hwnd_of(tk_window)
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                            style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
    except Exception:
        pass


def beep():
    if IS_WIN:
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass


# ---------------------------------------------------------------- process
_mutex = None


def single_instance(name="RemindMe_SingleInstance"):
    """Return False if another copy is already running."""
    global _mutex
    if not IS_WIN:
        return True
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, name)
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def launch_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    script = os.path.abspath(sys.argv[0])
    return f'"{exe}" "{script}"'


def set_start_with_windows(enabled, name="RemindMe"):
    if not IS_WIN:
        return
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
