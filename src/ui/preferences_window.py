'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QWidget, QFrame
from PySide6.QtCore import Qt, QPoint
from config import load_config, save_config

class PreferencesWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ScreenCut Preferences")
        self.setFixedSize(380, 260)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            QDialog { background-color: transparent; }
            #BgWidget { 
                background-color: #1e1e1e; 
                border: 1px solid #444444;
                border-radius: 8px;
            }
            QLabel { color: #ffffff; font-size: 13px; }
            QLabel#Title { font-size: 14px; font-weight: bold; color: #aaaaaa; }
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #1976d2;
                selection-color: #ffffff;
                outline: 0px;
            }
            QComboBox::drop-down {
                border-left: 1px solid #555555;
            }
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 15px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton#CloseButton {
                background: transparent;
                color: #aaaaaa;
                font-weight: bold;
                font-size: 16px;
                border: none;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton#CloseButton:hover {
                background: #d32f2f;
                color: white;
            }
        """)

        bg_widget = QWidget(self)
        bg_widget.setObjectName("BgWidget")
        bg_widget.setGeometry(0, 0, self.width(), self.height())
        
        main_layout = QVBoxLayout(bg_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title Bar
        title_layout = QHBoxLayout()
        title_lbl = QLabel("⚙ Preferences")
        title_lbl.setObjectName("Title")
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        main_layout.addLayout(title_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #444444;")
        main_layout.addWidget(line)
        
        # --- Settings ---
        self.config_data = load_config()
        
        # Video Compression
        vid_layout = QHBoxLayout()
        vid_lbl = QLabel("Video Compression:")
        self.cb_compression = QComboBox()
        self.cb_compression.addItems(["ultrafast", "superfast", "fast", "medium", "slow", "veryslow"])
        
        curr_comp = self.config_data.get("video_compression", "medium")
        idx = self.cb_compression.findText(curr_comp)
        if idx >= 0:
            self.cb_compression.setCurrentIndex(idx)
            
        vid_layout.addWidget(vid_lbl)
        vid_layout.addWidget(self.cb_compression)
        main_layout.addLayout(vid_layout)
        
        # Audio Source
        aud_layout = QHBoxLayout()
        aud_lbl = QLabel("Audio Source:")
        self.cb_audio = QComboBox()
        self.cb_audio.addItem("None (Muted)")
        
        # Load audio devices dynamically
        self.load_audio_devices()
        
        curr_aud = self.config_data.get("audio_source", "None (Muted)")
        idx = self.cb_audio.findText(curr_aud)
        if idx >= 0:
            self.cb_audio.setCurrentIndex(idx)
            
        aud_layout.addWidget(aud_lbl)
        aud_layout.addWidget(self.cb_audio)
        main_layout.addLayout(aud_layout)
        
        # 1080p Limit
        limit_layout = QHBoxLayout()
        limit_lbl = QLabel("Limit Video to 1080p:")
        from ui.toggle_switch import ToggleSwitch
        self.toggle_1080p = ToggleSwitch()
        self.toggle_1080p.setChecked(self.config_data.get("limit_1080p", True))
        
        limit_layout.addWidget(limit_lbl)
        limit_layout.addStretch()
        limit_layout.addWidget(self.toggle_1080p)
        main_layout.addLayout(limit_layout)
        
        main_layout.addStretch()
        
        # Save Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_and_close)
        btn_layout.addWidget(save_btn)
        
        main_layout.addLayout(btn_layout)

    def load_audio_devices(self):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            # Add all devices that have >0 input channels
            # Also append WASAPI loopback generically if user wants system audio?
            # It's complicated on Windows. Let's just list inputs.
            for d in devices:
                if d['max_input_channels'] > 0:
                    # e.g., "Microphone (Realtek(R) Audio)"
                    self.cb_audio.addItem(d['name'])
                    
            # For System Audio on Windows, usually we need WASAPI.
            # We will just add a special entry for System Audio
            self.cb_audio.addItem("System Audio (WASAPI Loopback)")
            
        except Exception as e:
            import logging
            logging.warning("Error loading sound devices: %s", e)

    def save_and_close(self):
        self.config_data["video_compression"] = self.cb_compression.currentText()
        self.config_data["audio_source"] = self.cb_audio.currentText()
        self.config_data["limit_1080p"] = self.toggle_1080p.isChecked()
        save_config(self.config_data)
        self.accept()

    # --- Window Dragging Logic ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_pos'):
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'drag_pos'):
            del self.drag_pos
            event.accept()
