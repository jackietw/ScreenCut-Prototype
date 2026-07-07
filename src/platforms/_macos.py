'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import os
import logging
from platforms._base import PlatformBase

# macOS modifier flags for CGEventFlags (used internally by pynput)
# These are mapped from our internal mod bit-flags to pynput Key objects.
MOD_ALT     = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT   = 0x0004
MOD_WIN     = 0x0008  # On macOS this maps to the Command key

try:
    from pynput import keyboard as _kb
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

# Active global hotkey listeners: {hotkey_id: pynput.HotKey}
_hotkey_listeners: dict = {}
_hotkey_listener_thread = None
_registered_hotkeys: dict = {}  # {hotkey_id: callable}

def _get_hotkey_listener():
    """Return (or create) a single background pynput keyboard listener."""
    global _hotkey_listener_thread
    if _hotkey_listener_thread is None or not _hotkey_listener_thread.running:
        _hotkey_listener_thread = _kb.Listener(
            on_press=_on_press, on_release=_on_release
        )
        _hotkey_listener_thread.daemon = True
        _hotkey_listener_thread.start()
    return _hotkey_listener_thread

_pressed_keys = set()

def _on_press(key):
    _pressed_keys.add(key)
    for hk_id, (combo, callback) in list(_registered_hotkeys.items()):
        if combo.issubset(_pressed_keys):
            callback()

def _on_release(key):
    _pressed_keys.discard(key)

def _mods_vk_to_pynput_combo(mods: int, vk: int) -> set:
    """Convert our internal (mods, vk) format to a set of pynput keys."""
    combo = set()
    if mods & MOD_CONTROL:
        combo.add(_kb.Key.ctrl)
    if mods & MOD_ALT:
        combo.add(_kb.Key.alt)
    if mods & MOD_SHIFT:
        combo.add(_kb.Key.shift)
    if mods & MOD_WIN:
        combo.add(_kb.Key.cmd)  # Command key on macOS
    # Map vk (Windows Virtual Key code) to pynput KeyCode
    combo.add(_kb.KeyCode.from_vk(vk))
    return combo


class MacOSPlatform(PlatformBase):

    # --- Documents Folder ---
    @staticmethod
    def get_documents_folder() -> str:
        return os.path.expanduser("~/Documents")

    # --- Screen Capture Exclusion ---
    @staticmethod
    def set_window_capture_excluded(hwnd: int) -> None:
        try:
            import objc  # type: ignore
            view = objc.objc_object(c_void_p=hwnd)
            window = view.window() if hasattr(view, 'window') else view
            if window and hasattr(window, 'setSharingType_'):
                window.setSharingType_(0)  # NSWindowSharingNone
        except Exception as e:
            logging.debug("set_window_capture_excluded failed on macOS: %s", e, exc_info=True)

    # --- Window Pass-Through ---
    @staticmethod
    def set_window_click_through(hwnd: int) -> None:
        try:
            import objc  # type: ignore
            view = objc.objc_object(c_void_p=hwnd)
            window = view.window() if hasattr(view, 'window') else view
            if window and hasattr(window, 'setIgnoresMouseEvents_'):
                window.setIgnoresMouseEvents_(True)
        except Exception as e:
            logging.debug("set_window_click_through failed on macOS: %s", e, exc_info=True)

    @staticmethod
    def set_window_hides_on_deactivate(hwnd: int, hides: bool = False) -> None:
        try:
            import objc  # type: ignore
            view = objc.objc_object(c_void_p=hwnd)
            window = view.window() if hasattr(view, 'window') else view
            if window and hasattr(window, 'setHidesOnDeactivate_'):
                window.setHidesOnDeactivate_(hides)
        except Exception as e:
            logging.debug("set_window_hides_on_deactivate failed on macOS: %s", e, exc_info=True)

    # --- Visible Window Enumeration ---
    @staticmethod
    def enum_visible_windows() -> list:
        # On macOS we use Quartz to enumerate visible windows
        try:
            import Quartz  # type: ignore
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID
            )
            results = []
            for w in window_list:
                bounds = w.get('kCGWindowBounds', {})
                x = int(bounds.get('X', 0))
                y = int(bounds.get('Y', 0))
                width = int(bounds.get('Width', 0))
                height = int(bounds.get('Height', 0))
                if width > 0 and height > 0:
                    results.append((x, y, x + width, y + height))
            return results
        except ImportError:
            return []

    # --- Global Hotkeys ---
    @staticmethod
    def check_hotkey_conflict(mods: int, vk: int, config_key: str = None) -> bool:
        try:
            from config import load_config
            cfg = load_config()
            hotkeys = cfg.get("hotkeys", {})
            for k, hk in hotkeys.items():
                if isinstance(hk, dict) and hk.get("vk") == vk and hk.get("modifiers") == mods:
                    if config_key and k == config_key:
                        return True
                    return False
        except Exception as e:
            logging.debug("Error checking hotkey config on macOS: %s", e, exc_info=True)
        return True

    @staticmethod
    def register_hotkey(hwnd: int, hotkey_id: int, mods: int, vk: int) -> bool:
        """Register a global hotkey using pynput background listener."""
        if not HAS_PYNPUT:
            return False
        from PySide6.QtCore import Qt
        combo = _mods_vk_to_pynput_combo(mods, vk)
        # Store combo + a no-op callback; actual dispatch done via Signal in main_window
        _registered_hotkeys[hotkey_id] = (combo, lambda: None)
        _get_hotkey_listener()
        return True

    @staticmethod
    def unregister_hotkey(hwnd: int, hotkey_id: int) -> None:
        _registered_hotkeys.pop(hotkey_id, None)

    @staticmethod
    def set_hotkey_callback(hotkey_id: int, callback) -> None:
        """Assign an actual callback to an already-registered hotkey."""
        if hotkey_id in _registered_hotkeys:
            combo, _ = _registered_hotkeys[hotkey_id]
            _registered_hotkeys[hotkey_id] = (combo, callback)

    # --- Cursor / Mouse ---
    @staticmethod
    def get_cursor_pos() -> tuple:
        try:
            from pynput.mouse import Controller
            m = Controller()
            return (int(m.position[0]), int(m.position[1]))
        except Exception as e:
            logging.debug("get_cursor_pos failed on macOS: %s", e, exc_info=True)
            return (0, 0)

    @staticmethod
    def get_left_button_down() -> bool:
        if not HAS_PYNPUT:
            return False
        try:
            from pynput.mouse import Controller
            # pynput does not expose button state directly; use Quartz as fallback
            import Quartz  # type: ignore
            state = Quartz.CGEventSourceButtonState(
                Quartz.kCGEventSourceStateHIDSystemState,
                Quartz.kCGMouseButtonLeft
            )
            return bool(state)
        except Exception as e:
            logging.debug("get_left_button_down failed on macOS: %s", e, exc_info=True)
            return False

    # --- Executable / Bundle Icon Updating ---
    @staticmethod
    def update_app_icon(target_path: str, icon_path: str) -> bool:
        import os
        import shutil

        if not os.path.exists(target_path):
            print(f"Error: Target bundle not found at {target_path}")
            return False
        if not os.path.exists(icon_path):
            print(f"Error: Icon file not found at {icon_path}")
            return False

        print(f"Detected macOS Application Bundle: {target_path}")
        resources_dir = os.path.join(target_path, "Contents", "Resources")
        if not os.path.exists(resources_dir):
            print(f"Error: Resources directory not found in {target_path}")
            return False
        
        icns_files = [f for f in os.listdir(resources_dir) if f.endswith(".icns")]
        target_icns_name = icns_files[0] if icns_files else "Icons.icns"
        target_icns_path = os.path.join(resources_dir, target_icns_name)

        print(f"Updating macOS bundle icon at {target_icns_path} using {icon_path}...")
        
        if icon_path.endswith(".icns"):
            shutil.copyfile(icon_path, target_icns_path)
            print(f"Successfully copied ICNS to {target_icns_path}!")
            return True

        try:
            import tempfile
            import subprocess
            with tempfile.TemporaryDirectory() as tmpdir:
                iconset_dir = os.path.join(tmpdir, "icon.iconset")
                os.makedirs(iconset_dir, exist_ok=True)
                for size, name in [(16, "16x16"), (32, "16x16@2x"), (32, "32x32"), (64, "32x32@2x"), (128, "128x128"), (256, "128x128@2x"), (256, "256x256"), (512, "256x256@2x"), (512, "512x512"), (1024, "512x512@2x")]:
                    out_png = os.path.join(iconset_dir, f"icon_{name}.png")
                    subprocess.run(["sips", "-z", str(size), str(size), icon_path, "--out", out_png], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                res = subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", target_icns_path])
                if res.returncode == 0 and os.path.exists(target_icns_path):
                    print(f"Successfully updated macOS bundle icon using iconutil at {target_icns_path}!")
                    return True
        except Exception as e_mac:
            print(f"macOS native iconutil failed: {e_mac}")

        try:
            from PySide6.QtGui import QPixmap
            pix = QPixmap(icon_path)
            if not pix.isNull():
                pix.save(target_icns_path, "ICNS")
                print(f"Successfully updated macOS bundle icon using PySide6 at {target_icns_path}!")
                return True
        except Exception as e:
            print(f"PySide6 ICNS save failed: {e}")
        return False
