'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt
from widgets.capture_hotkey import Hotkey
from config import load_config

class ImageTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        config_data = load_config()
        toggles_config = config_data.get("toggles", {})
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Left side: Settings with Toggles
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(15)
        
        self.main_window.add_setting_row(settings_layout, "Preview in Editor", toggles_config.get("Preview in Editor", True))
        self.main_window.add_setting_row(settings_layout, "Copy to Clipboard", toggles_config.get("Copy to Clipboard", True))
        self.main_window.add_setting_row(settings_layout, "Capture Cursor", toggles_config.get("Capture Cursor", False))
        self.main_window.add_setting_row(settings_layout, "5 Second Delay", toggles_config.get("5 Second Delay", False))
        self.main_window.add_setting_row(settings_layout, "Scroll Capture", toggles_config.get("Scroll Capture", False))
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout, stretch=2)
        
        # Right side: Capture Button
        capture_layout = QVBoxLayout()
        
        self.capture_btn = QPushButton("Capture")
        self.capture_btn.setObjectName("CaptureButton")
        self.capture_btn.setFixedSize(100, 100)
        self.capture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.capture_btn.clicked.connect(self.main_window.start_capture)
        self.main_window.capture_btn = self.capture_btn
        
        lbl_hotkey = Hotkey("Ctrl+Shift+P", "image_hotkey")
        lbl_hotkey.hotkey_changed.connect(self.main_window.update_hotkey)
        
        capture_layout.addStretch()
        capture_layout.addWidget(self.capture_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addWidget(lbl_hotkey, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addStretch()
        
        layout.addLayout(capture_layout, stretch=1)


class VideoTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        config_data = load_config()
        toggles_config = config_data.get("toggles", {})
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(15)
        
        self.main_window.add_setting_row(settings_layout, "Capture Cursor", toggles_config.get("Capture Cursor (Video)", False), has_details=True, key_name="Capture Cursor (Video)")
        self.main_window.add_setting_row(settings_layout, "Record Microphone", toggles_config.get("Record Microphone", True))
        self.main_window.add_setting_row(settings_layout, "Record System Audio", toggles_config.get("Record System Audio", True))
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout, stretch=2)
        
        capture_layout = QVBoxLayout()
        
        self.record_btn = QPushButton("Record")
        self.record_btn.setObjectName("CaptureButton")
        self.record_btn.setFixedSize(100, 100)
        self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_btn.clicked.connect(self.main_window.start_video_capture)
        self.main_window.record_btn = self.record_btn
        
        lbl_hotkey = Hotkey("Ctrl+Shift+V", "video_hotkey")
        lbl_hotkey.hotkey_changed.connect(self.main_window.update_hotkey)

        capture_layout.addStretch()
        capture_layout.addWidget(self.record_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addWidget(lbl_hotkey, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addStretch()
        
        layout.addLayout(capture_layout, stretch=1)
