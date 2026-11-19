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


# ---------------------------------------------------------------- lock / display / sleep
def is_session_locked():
    """True when the lock screen (or another secure desktop) is showing."""
    if not IS_WIN:
        return False
    try:
        hdesk = user32.OpenInputDesktop(0, False, 0x0001)  # DESKTOP_READOBJECTS
        if not hdesk:
            return True  # access denied -> Winlogon desktop (locked)
        try:
            buf = ctypes.create_unicode_buffer(256)
            needed = wintypes.DWORD()
            ok = user32.GetUserObjectInformationW(hdesk, 2, buf, ctypes.sizeof(buf),
                                                  ctypes.byref(needed))  # UOI_NAME
            return bool(ok) and buf.value.lower() != "default"
        finally:
            user32.CloseDesktop(hdesk)
    except Exception:
        return False


def screensaver_running():
    if not IS_WIN:
        return False
    try:
        running = wintypes.BOOL()
        user32.SystemParametersInfoW(0x0072, 0, ctypes.byref(running), 0)  # SPI_GETSCREENSAVERRUNNING
        return bool(running.value)
    except Exception:
        return False


if IS_WIN:
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                 wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    user32.GetUserObjectInformationW.restype = wintypes.BOOL
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]

    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                 wintypes.LPARAM)

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                    ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                    ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    class POWERBROADCAST_SETTING(ctypes.Structure):
        _fields_ = [("PowerSetting", GUID), ("DataLength", wintypes.DWORD),
                    ("Data", wintypes.DWORD)]

    def _guid(text):
        import uuid
        u = uuid.UUID(text)
        g = GUID(u.time_low, u.time_mid, u.time_hi_version)
        for i, b in enumerate(u.bytes[8:]):
            g.Data4[i] = b
        return g

    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                      wintypes.LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.RegisterClassW.restype = wintypes.ATOM
    user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                       wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                       wintypes.HINSTANCE, wintypes.LPVOID]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.RegisterPowerSettingNotification.argtypes = [wintypes.HANDLE, ctypes.POINTER(GUID),
                                                        wintypes.DWORD]
    user32.RegisterPowerSettingNotification.restype = wintypes.HANDLE
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE

GUID_CONSOLE_DISPLAY_STATE = "6FE69556-704A-47A0-8F24-C28D936FDA47"
GUID_LIDSWITCH_STATE_CHANGE = "BA3E0F4D-B817-4094-A2D1-D56379E6A0F3"
WM_WTSSESSION_CHANGE = 0x02B1
WM_POWERBROADCAST = 0x0218


class SystemWatcher:
    """Hidden window that hears Windows' lock/unlock, display on/off, lid
    and sleep/resume notifications. Tk's event loop pumps its messages, so
    the flags below are updated on the Tk thread.

    `dormant_reason()` says why the app should go quiet (or None).
    """

    def __init__(self):
        self.locked = False
        self.display_off = False
        self.lid_closed = False
        self.suspending_at = 0.0
        self.ok = False
        self.hwnd = None
        if IS_WIN:
            try:
                self._create()
                self.ok = True
            except Exception:
                import logging
                logging.getLogger("remindme").exception("system watcher unavailable")

    def _create(self):
        self._proc = WNDPROC(self._wndproc)   # keep a reference!
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._proc
        wc.hInstance = hinst
        wc.lpszClassName = "RemindMeSystemWatcher"
        self._wc = wc
        user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(0, wc.lpszClassName, "Remind Me watcher", 0,
                                           0, 0, 0, 0, None, None, hinst, None)
        if not self.hwnd:
            raise OSError("CreateWindowExW failed")
        try:
            wts = ctypes.WinDLL("wtsapi32")
            wts.WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
            wts.WTSRegisterSessionNotification(self.hwnd, 0)  # NOTIFY_FOR_THIS_SESSION
        except Exception:
            pass
        self._display_guid = _guid(GUID_CONSOLE_DISPLAY_STATE)
        self._lid_guid = _guid(GUID_LIDSWITCH_STATE_CHANGE)
        for g in (self._display_guid, self._lid_guid):
            user32.RegisterPowerSettingNotification(self.hwnd, ctypes.byref(g), 0)

    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_WTSSESSION_CHANGE:
                if wparam in (7, 2, 3):        # SESSION_LOCK, CONSOLE/REMOTE_DISCONNECT
                    self.locked = True
                elif wparam in (8, 1, 4):      # SESSION_UNLOCK, CONSOLE/REMOTE_CONNECT
                    self.locked = False
            elif msg == WM_POWERBROADCAST:
                if wparam == 0x8013 and lparam:  # PBT_POWERSETTINGCHANGE
                    s = ctypes.cast(lparam, ctypes.POINTER(POWERBROADCAST_SETTING)).contents
                    key = bytes(s.PowerSetting)
                    if key == bytes(self._display_guid):
                        self.display_off = (s.Data == 0)     # 0 off, 1 on, 2 dimmed
                    elif key == bytes(self._lid_guid):
                        self.lid_closed = (s.Data == 0)      # 0 closed, 1 open
                elif wparam == 0x0004:          # PBT_APMSUSPEND
                    self.suspending_at = time.time()
                elif wparam in (0x0007, 0x0012):  # PBT_APMRESUMESUSPEND / RESUMEAUTOMATIC
                    self.suspending_at = 0.0
                return 1
        except Exception:
            pass
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def dormant_reason(self):
        """Why the app should pause right now, or None."""
        if self.locked or is_session_locked():
            return "screen locked"
        if self.display_off:
            # covers lid closed (unless an external monitor keeps the display on)
            return "lid closed" if self.lid_closed else "display off"
        if self.suspending_at and time.time() - self.suspending_at < 20:
            return "going to sleep"
        if screensaver_running():
            return "screensaver"
        return None
