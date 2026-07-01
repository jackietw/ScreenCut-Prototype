'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import os
from PySide6.QtWidgets import QScrollArea, QWidget, QToolButton, QPushButton
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon


class HorizontalScrollArea(QScrollArea):
    def wheelEvent(self, event):
        if event.angleDelta().y() != 0:
            delta = event.angleDelta().y()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
            event.accept()
        else:
            super().wheelEvent(event)


class ThumbnailWidget(QWidget):
    def __init__(self, filepath, thumb_pixmap, load_cb, delete_cb, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.setFixedSize(100, 62)
        filename = os.path.basename(filepath)
        self.setToolTip(filename)
        
        self.btn = QToolButton(self)
        self.btn.setGeometry(0, 0, 100, 62)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setToolTip(filename)
        self.btn.setIcon(QIcon(thumb_pixmap))
        self.btn.setIconSize(QSize(96, 58))
        self.btn.clicked.connect(lambda: load_cb(self.filepath))
        
        self.del_btn = QPushButton("×", self)
        self.del_btn.setGeometry(82, 2, 16, 16)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.9);
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 0px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgb(220, 38, 38);
            }
        """)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setToolTip("Delete file")
        self.del_btn.hide()
        self.del_btn.clicked.connect(lambda: delete_cb(self.filepath, self.del_btn))
        
    def enterEvent(self, event):
        super().enterEvent(event)
        self.del_btn.show()
        self.del_btn.raise_()
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.del_btn.hide()
