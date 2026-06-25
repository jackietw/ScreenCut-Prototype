'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import json
import os

CONFIG_PATH = os.path.join(os.path.expanduser("~"), "Documents", "ScreenCutLibrary", "config.json")

# ---------------------------------------------------------------------------
# Debug mode: set to True during development, False for release builds.
# Controlled by the "debug_mode" key in config.json.
# ---------------------------------------------------------------------------
DEFAULT_DEBUG = True  # Change to False before releasing

def is_debug_mode() -> bool:
    """Return True when debug dialogs / verbose output should be shown."""
    try:
        cfg = load_config()
        return bool(cfg.get("debug_mode", DEFAULT_DEBUG))
    except Exception:
        return DEFAULT_DEBUG

def setup_logging():
    """Configure the root logger based on debug_mode.
    
    - debug_mode=True  ??DEBUG level, output to console + log file
    - debug_mode=False ??WARNING level only, output to log file (silent on console)
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


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            import logging
            logging.warning("Error loading config: %s", e)
    return {}

def save_config(data):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        import logging
        logging.warning("Error saving config: %s", e)
