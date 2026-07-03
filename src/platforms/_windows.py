'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import ctypes
import ctypes.wintypes
import logging
from platforms._base import PlatformBase

try:
    import win32gui
    import win32api
    import win32con
    _dwmapi = ctypes.windll.dwmapi
    _DWMWA_EXTENDED_FRAME_BOUNDS = 9
    _DWMWA_CLOAKED = 14
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Modifier flag constants (same as in hotkey.py)
MOD_ALT     = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT   = 0x0004
MOD_WIN     = 0x0008

class WindowsPlatform(PlatformBase):

    # --- Documents Folder ---
    @staticmethod
    def get_documents_folder() -> str:
        CSIDL_PERSONAL = 5
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
        return buf.value

    # --- Screen Capture Exclusion ---
    @staticmethod
    def set_window_capture_excluded(hwnd: int) -> None:
        try:
            # WDA_EXCLUDEFROMCAPTURE = 0x00000011
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except Exception as e:
            logging.debug("SetWindowDisplayAffinity failed: %s", e, exc_info=True)

    # --- Window Pass-Through ---
    @staticmethod
    def set_window_click_through(hwnd: int) -> None:
        if not HAS_WIN32:
            return
        try:
            exStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                hwnd, win32con.GWL_EXSTYLE,
                exStyle | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
            )
        except Exception as e:
            logging.debug("set_window_click_through failed: %s", e, exc_info=True)

    @staticmethod
    def set_window_hides_on_deactivate(hwnd: int, hides: bool = False) -> None:
        pass

    # --- Visible Window Enumeration ---
    @staticmethod
    def enum_visible_windows() -> list:
        if not HAS_WIN32:
            return []
        results = []
        def enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                # Skip cloaked (invisible Windows 10/11 UWP) windows
                cloaked = ctypes.c_int(0)
                _dwmapi.DwmGetWindowAttribute(hwnd, _DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                if cloaked.value != 0:
                    return True
                rect = ctypes.wintypes.RECT()
                res = _dwmapi.DwmGetWindowAttribute(hwnd, _DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect))
                if res == 0:
                    l, t, r, b = rect.left, rect.top, rect.right, rect.bottom
                else:
                    l, t, r, b = win32gui.GetWindowRect(hwnd)
                if r > l and b > t:
                    results.append((l, t, r, b))
            return True
        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception as e:
            logging.debug("EnumWindows failed: %s", e, exc_info=True)
        return results

    # --- Global Hotkeys ---
    @staticmethod
    def check_hotkey_conflict(mods: int, vk: int, config_key: str = None) -> bool:
        """Returns True if hotkey is available (no conflict)."""
        try:
            from config import load_config
            cfg = load_config()
            hotkeys = cfg.get("hotkeys", {})
            if config_key and config_key in hotkeys:
                hk = hotkeys[config_key]
                if isinstance(hk, dict) and hk.get("vk") == vk and hk.get("modifiers") == mods:
                    return True
            for hk in hotkeys.values():
                if isinstance(hk, dict) and hk.get("vk") == vk and hk.get("modifiers") == mods:
                    return True
        except Exception as e:
            logging.debug("Error checking hotkey config in check_hotkey_conflict: %s", e, exc_info=True)

        TEST_ID = 9999
        success = ctypes.windll.user32.RegisterHotKey(0, TEST_ID, mods, vk)
        if success:
            ctypes.windll.user32.UnregisterHotKey(0, TEST_ID)
            return True
        return False

    @staticmethod
    def register_hotkey(hwnd: int, hotkey_id: int, mods: int, vk: int) -> bool:
        return bool(ctypes.windll.user32.RegisterHotKey(hwnd, hotkey_id, mods, vk))

    @staticmethod
    def unregister_hotkey(hwnd: int, hotkey_id: int) -> None:
        ctypes.windll.user32.UnregisterHotKey(hwnd, hotkey_id)

    # --- Cursor / Mouse ---
    @staticmethod
    def get_cursor_pos() -> tuple:
        if not HAS_WIN32:
            return (0, 0)
        try:
            _, _, (cx, cy) = win32gui.GetCursorInfo() # type: ignore
            return (cx, cy)
        except Exception as e:
            logging.debug("GetCursorInfo failed: %s", e, exc_info=True)
            return (0, 0)

    @staticmethod
    def get_left_button_down() -> bool:
        if not HAS_WIN32:
            return False
        try:
            state = win32api.GetAsyncKeyState(0x01)  # VK_LBUTTON
            return (state & 0x8000) != 0
        except Exception as e:
            logging.debug("GetAsyncKeyState failed: %s", e, exc_info=True)
            return False
