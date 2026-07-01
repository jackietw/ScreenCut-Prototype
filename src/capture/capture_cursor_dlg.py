'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from config import save_config
from capture.capture_cursor_ui import CursorSettingsUI

class CursorSettings(CursorSettingsUI):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.cursor_settings["highlight"] = self.chk_highlight.isChecked()
        self.cursor_settings["highlight_color"] = self.btn_hl_color.current_color
        self.cursor_settings["click"] = self.chk_click.isChecked()
        self.cursor_settings["click_color"] = self.btn_cl_color.current_color
        
        self.config_data["cursor_settings"] = self.cursor_settings
        save_config(self.config_data)
