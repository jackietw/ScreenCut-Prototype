'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QColorDialog
from PySide6.QtCore import Qt, Signal
from ui.toggle_switch import ToggleSwitch
from config import load_config, save_config

class ColorButton(QPushButton):
    color_changed = Signal(str)

    def __init__(self, color_hex="#ffff00"):
        super().__init__()
        self.setFixedSize(40, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.current_color = color_hex
        self.update_style()
        self.clicked.connect(self.pick_color)

    def update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color};
                border: 1px solid #555555;
                border-radius: 2px;
            }}
        """)

    def pick_color(self):
        from PySide6.QtGui import QColor
        dlg = QColorDialog(QColor(self.current_color), self)
        dlg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        if dlg.exec():
            color = dlg.currentColor()
            self.current_color = color.name()
            self.update_style()
            self.color_changed.emit(self.current_color)

class CursorSettingsPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.config_data = load_config()
        self.cursor_settings = self.config_data.get("cursor_settings", {
            "highlight": False,
            "highlight_color": "#ffff00",
            "click": False,
            "click_color": "#ff0000"
        })
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        bg = QWidget()
        bg.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b; 
                border: 1px solid #555555; 
                border-radius: 4px;
            }
            QLabel { color: #ffffff; font-size: 13px; border: none; }
        """)
        bg_layout = QVBoxLayout(bg)
        bg_layout.setContentsMargins(10, 10, 10, 10)
        bg_layout.setSpacing(10)
        
        # Highlight Row
        hl_row = QHBoxLayout()
        self.chk_highlight = ToggleSwitch()
        self.chk_highlight.setChecked(self.cursor_settings.get("highlight", False))
        self.chk_highlight.stateChanged.connect(self.save_settings)
        
        lbl_hl = QLabel("Highlight Cursor")
        
        self.btn_hl_color = ColorButton(self.cursor_settings.get("highlight_color", "#ffff00"))
        self.btn_hl_color.color_changed.connect(self.save_settings)
        
        hl_row.addWidget(self.chk_highlight)
        hl_row.addWidget(lbl_hl)
        hl_row.addStretch()
        hl_row.addWidget(self.btn_hl_color)
        bg_layout.addLayout(hl_row)
        
        # Click Row
        cl_row = QHBoxLayout()
        self.chk_click = ToggleSwitch()
        self.chk_click.setChecked(self.cursor_settings.get("click", False))
        self.chk_click.stateChanged.connect(self.save_settings)
        
        lbl_cl = QLabel("Click Animation")
        
        self.btn_cl_color = ColorButton(self.cursor_settings.get("click_color", "#ff0000"))
        self.btn_cl_color.color_changed.connect(self.save_settings)
        
        cl_row.addWidget(self.chk_click)
        cl_row.addWidget(lbl_cl)
        cl_row.addStretch()
        cl_row.addWidget(self.btn_cl_color)
        bg_layout.addLayout(cl_row)
        
        layout.addWidget(bg)
        
        self.setFixedSize(240, 90)
        
    def save_settings(self, *_):
        self.cursor_settings["highlight"] = self.chk_highlight.isChecked()
        self.cursor_settings["highlight_color"] = self.btn_hl_color.current_color
        self.cursor_settings["click"] = self.chk_click.isChecked()
        self.cursor_settings["click_color"] = self.btn_cl_color.current_color
        
        self.config_data["cursor_settings"] = self.cursor_settings
        save_config(self.config_data)
