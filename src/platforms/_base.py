'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

class PlatformBase:
    """Abstract base class defining all platform-specific operations."""

    # --- Documents Folder ---
    @staticmethod
    def get_documents_folder() -> str:
        """Return the path to the user's Documents folder."""
        raise NotImplementedError

    # --- DPI Awareness ---
    @staticmethod
    def init_dpi_awareness() -> None:
        """Initialize high-DPI awareness for the process before application startup."""
        pass

    # --- Screen Capture Exclusion ---
    @staticmethod
    def set_window_capture_excluded(hwnd: int) -> None:
        """Exclude a window (by native handle) from screen capture recordings."""
        pass  # Graceful no-op if not supported

    # --- Window Pass-Through ---
    @staticmethod
    def set_window_click_through(hwnd: int) -> None:
        """Make a window transparent for mouse clicks (click-through)."""
        pass  # Graceful no-op if not supported

    @staticmethod
    def set_window_hides_on_deactivate(hwnd: int, hides: bool = False) -> None:
        """Prevent or allow window hiding when application loses focus."""
        pass

    # --- Visible Window Enumeration ---
    @staticmethod
    def enum_visible_windows() -> list:
        """
        Return a list of (left, top, right, bottom) tuples (physical pixels)
        for all visible, non-iconified, non-cloaked windows on screen.
        """
        return []

    # --- Global Hotkeys ---
    @staticmethod
    def check_hotkey_conflict(mods: int, vk: int, config_key: str = None) -> bool:
        """
        Return True if the hotkey (mods + vk) can be registered (no conflict).
        Return False if another application already owns it.
        """
        raise NotImplementedError

    @staticmethod
    def register_hotkey(hwnd: int, hotkey_id: int, mods: int, vk: int) -> bool:
        """Register a global hotkey. Returns True on success."""
        raise NotImplementedError

    @staticmethod
    def unregister_hotkey(hwnd: int, hotkey_id: int) -> None:
        """Unregister a previously registered global hotkey."""
        raise NotImplementedError

    # --- Cursor / Mouse ---
    @staticmethod
    def get_cursor_pos() -> tuple:
        """Return (x, y) of the current cursor in physical screen pixels."""
        raise NotImplementedError

    @staticmethod
    def get_left_button_down() -> bool:
        """Return True if the left mouse button is currently held down."""
        raise NotImplementedError

    # --- Executable / Bundle Icon Updating ---
    @staticmethod
    def update_app_icon(target_path: str, icon_path: str) -> bool:
        """Update the embedded application icon of an executable or app bundle."""
        raise NotImplementedError
