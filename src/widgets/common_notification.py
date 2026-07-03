'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer

class Notification(QWidget):
    def __init__(self, message, parent=None, duration=3000, is_error=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # Pass clicks through
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.bg = QWidget()
        bg_color = "rgba(180, 40, 40, 210)" if is_error else "rgba(0, 0, 0, 180)"
        self.bg.setStyleSheet(f"background-color: {bg_color}; border-radius: 8px; padding: 15px 30px;")
        bg_layout = QVBoxLayout(self.bg)
        
        self.lbl_msg = QLabel(message)
        self.lbl_msg.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bg_layout.addWidget(self.lbl_msg)
        
        layout.addWidget(self.bg)
        self.adjustSize()
        
        self.duration = duration

    def show_toast(self):
        # Position at bottom center of the primary screen
        screen = QApplication.primaryScreen().geometry()
        x = screen.center().x() - self.width() // 2
        y = screen.bottom() - 100 - self.height()
        self.move(x, y)
        self.show()
        
        # Auto-hide timer
        QTimer.singleShot(self.duration, self.close)
