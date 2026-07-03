'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import json
import os
import sys
import copy

def get_app_config_dir() -> str:
    """Return OS-specific application settings directory for ScreenCut."""
    if sys.platform == 'win32':
        appdata = os.getenv("APPDATA")
        if not appdata:
            appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        return os.path.join(appdata, "ScreenCut")
    elif sys.platform == 'darwin':
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "ScreenCut")
    else:
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        if not xdg_config:
            xdg_config = os.path.join(os.path.expanduser("~"), ".config")
        return os.path.join(xdg_config, "ScreenCut")

CONFIG_PATH = os.path.join(get_app_config_dir(), "config.json")

# ---------------------------------------------------------------------------
# Debug mode: set to True during development, False for release builds.
# Controlled by the "debug_mode" key in config.json.
# ---------------------------------------------------------------------------
DEFAULT_DEBUG = "--debug" in sys.argv or "-d" in sys.argv or os.getenv("SCREENCUT_DEBUG", "0") in ("1", "true", "True")

def is_debug_mode() -> bool:
    """Return True when debug dialogs / verbose output should be shown."""
    if "--debug" in sys.argv or "-d" in sys.argv or os.getenv("SCREENCUT_DEBUG", "0") in ("1", "true", "True"):
        return True
    try:
        cfg = load_config()
        return bool(cfg.get("debug_mode", DEFAULT_DEBUG))
    except Exception:
        return DEFAULT_DEBUG

def setup_logging():
    """Configure the root logger based on debug_mode.
    
    - debug_mode=True  -> DEBUG level, output to console + log file
    - debug_mode=False -> WARNING level only, output to log file (silent on console)
    """
    import logging
    import os

    log_dir = os.path.dirname(CONFIG_PATH)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "screencut.log")

    level = logging.DEBUG if is_debug_mode() else logging.WARNING

    handlers = [logging.FileHandler(log_path, encoding="utf-8")]
    if is_debug_mode():
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.getLogger(__name__).debug("Logging initialised (debug_mode=%s)", is_debug_mode())


_config_cache = None
_config_mtime = 0

def load_config():
    global _config_cache, _config_mtime
    if not os.path.exists(CONFIG_PATH):
        # Check old location for backward compatibility / migration
        old_path = os.path.join(os.path.expanduser("~"), "Documents", "ScreenCutLibrary", "config.json")
        initial_config = {"debug_mode": DEFAULT_DEBUG}
        if os.path.exists(old_path):
            try:
                with open(old_path, "r", encoding="utf-8") as f:
                    initial_config = json.load(f)
            except Exception:
                pass
        save_config(initial_config)
        return copy.deepcopy(initial_config)

    try:
        mtime = os.path.getmtime(CONFIG_PATH)
        if _config_cache is not None and mtime == _config_mtime:
            return copy.deepcopy(_config_cache)
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
            _config_mtime = mtime
            return copy.deepcopy(_config_cache)
    except Exception as e:
        import logging
        logging.warning("Error loading config: %s", e)
        return {}

def save_config(data):
    global _config_cache, _config_mtime
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        _config_cache = copy.deepcopy(data)
        if os.path.exists(CONFIG_PATH):
            _config_mtime = os.path.getmtime(CONFIG_PATH)
    except Exception as e:
        import logging
        logging.warning("Error saving config: %s", e)
