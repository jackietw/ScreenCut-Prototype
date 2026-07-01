'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from platforms import Platform
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QCursor

class CursorOverlay(QWidget):
    def __init__(self, hl_enabled=True, hl_color="#ffff00", cl_enabled=True, cl_color="#ff0000", capture_rect=None):
        super().__init__()
        self.hl_enabled = hl_enabled
        self.cl_enabled = cl_enabled
        self.capture_rect = capture_rect

        # Convert hex to QColor
        self.hl_color = QColor(hl_color)
        self.hl_color.setAlphaF(0.4)  # Semi-transparent highlight
        self.cl_color = QColor(cl_color)

        # Frameless, stay on top, tool window (no taskbar icon), transparent for input
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Cover all screens
        geom = QRect()
        for screen in QApplication.screens():
            geom = geom.united(screen.geometry())
        self.setGeometry(geom)

        # Exclude from capture via platform abstraction
        Platform.set_window_capture_excluded(int(self.winId()))

        self.cursor_pos = None
        self.click_animations = []
        self.prev_clicked = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_overlay)
        # Update every 16ms (~60 FPS)
        self.timer.start(16)

    def update_overlay(self):
        # Update cursor position
        global_pos = QCursor.pos()
        self.cursor_pos = self.mapFromGlobal(global_pos)

        # Check clicks via platform abstraction
        if self.cl_enabled:
            is_clicked = Platform.get_left_button_down()
            if is_clicked and not self.prev_clicked:
                self.click_animations.append({"pos": self.cursor_pos, "radius": 5})
            self.prev_clicked = is_clicked

        # Update animations
        if self.cl_enabled and self.click_animations:
            new_anims = []
            for anim in self.click_animations:
                anim["radius"] += 2
                if anim["radius"] < 40:
                    new_anims.append(anim)
            self.click_animations = new_anims

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.capture_rect:
            painter.setClipRect(self.capture_rect)

        # Clear background explicitly to prevent trails
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if self.cursor_pos:
            cx = self.cursor_pos.x()
            cy = self.cursor_pos.y()

            if self.hl_enabled:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(self.hl_color))
                painter.drawEllipse(cx - 20, cy - 20, 40, 40)

        if self.cl_enabled and self.click_animations:
            for anim in self.click_animations:
                ax = anim["pos"].x()
                ay = anim["pos"].y()
                r = anim["radius"]
                pen = QPen(self.cl_color, 2)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(int(ax - r), int(ay - r), int(r * 2), int(r * 2))

        painter.end()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
