'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCursor

class CountdownWindow(QWidget):
    finished = Signal()
    
    def __init__(self, seconds=5):
        super().__init__()
        self.seconds = seconds
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(str(self.seconds))
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 80px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 128); /* 50% alpha black */
                border-radius: 15px;
                padding: 10px 40px;
            }
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.label)
        
        self.adjustSize()
        
        # Position at top right of the current screen
        screen = QApplication.screenAt(QCursor.pos())
        if not screen:
            screen = QApplication.primaryScreen()
        screen_geo = screen.geometry()
        
        self.move(screen_geo.right() - self.width() - 50, screen_geo.top() + 50)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        
    def tick(self):
        self.seconds -= 1
        if self.seconds > 0:
            self.label.setText(str(self.seconds))
        else:
            self.timer.stop()
            self.close()
            self.finished.emit()
            
    def mousePressEvent(self, event):
        # Cancel the countdown if the user clicks on the timer widget
        if event.button() == Qt.MouseButton.LeftButton:
            self.timer.stop()
            self.close()
            print("Countdown cancelled by user.")
