'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QCheckBox
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, Property, QEasingCurve, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._position = 3
        
        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.animation.setDuration(150)
        
        self.stateChanged.connect(self.setup_animation)

    def getPosition(self):
        return self._position

    def setPosition(self, pos):
        self._position = pos
        self.update()

    position = Property(int, getPosition, setPosition)

    def setup_animation(self, value):
        self.animation.stop()
        if value:
            self.animation.setEndValue(self.width() - 19)
        else:
            self.animation.setEndValue(3)
        self.animation.start()

    def hitButton(self, pos: QPoint) -> bool:
        return self.contentsRect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        bg_color = QColor("#1976d2") if self.isChecked() else QColor("#5a5a5a")
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height() / 2, self.height() / 2)
        
        # Draw knob
        painter.setBrush(QBrush(QColor("#ffffff")))
        knob_radius = self.height() - 6
        painter.drawEllipse(self._position, 3, knob_radius, knob_radius)
        
        painter.end()
