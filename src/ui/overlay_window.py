'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QApplication, QPushButton, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRect, QPoint, QSize, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QImage, QCursor, QShortcut, QKeySequence
import mss
import os
import time
import sys
import ctypes
from ctypes import wintypes

try:
    import win32gui
    import win32api
    import win32con
    HAS_WIN32 = True
    dwmapi = ctypes.windll.dwmapi
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    DWMWA_CLOAKED = 14
except ImportError:
    HAS_WIN32 = False

class FloatingToolbar(QWidget):
    def __init__(self, parent, on_done, on_cancel):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        bg = QWidget()
        bg.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555555; border-radius: 6px;")
        bg_layout = QHBoxLayout(bg)
        bg_layout.setContentsMargins(8, 4, 8, 4)
        
        self.lbl_size = QLabel("0 x 0")
        self.lbl_size.setStyleSheet("color: #aaaaaa; font-family: monospace; margin-right: 10px;")
        bg_layout.addWidget(self.lbl_size)
        
        btn_done = QPushButton("✔")
        btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_done.setStyleSheet("background-color: #1976d2; color: white; padding: 6px 20px; border-radius: 3px; font-weight: bold;")
        btn_done.clicked.connect(on_done)
        
        btn_cancel = QPushButton("✕")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("background-color: #4a4a4a; color: white; padding: 6px 15px; border-radius: 3px; font-weight: bold;")
        btn_cancel.clicked.connect(on_cancel)
        
        bg_layout.addWidget(btn_done)
        bg_layout.addWidget(btn_cancel)
        layout.addWidget(bg)
        self.adjustSize()
        
    def update_size(self, width, height):
        self.lbl_size.setText(f"{width} x {height}")
        self.adjustSize()
        self.adjustSize()

class OverlayWindow(QWidget):
    class State:
        SNAPPING = 0
        DRAWING = 1
        ADJUSTING = 2

    def __init__(self, library_dir, capture_cursor=False):
        super().__init__()
        self.library_dir = library_dir
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Use QShortcut for Esc key as it's more reliable than keyPressEvent
        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self.on_cancel)

        # 1. Freeze the screen by taking a full screenshot immediately
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            self.bg_data = sct_img.bgra 
            self.bg_image = QImage(self.bg_data, sct_img.width, sct_img.height, QImage.Format.Format_ARGB32)
            self.screen_offset_x = monitor["left"]
            self.screen_offset_y = monitor["top"]
            
        # Handle DPI scaling
        self.ratio = self.screen().devicePixelRatio()
        self.bg_image.setDevicePixelRatio(self.ratio)
        
        # Draw cursor if requested
        if capture_cursor:
            self._draw_cursor_on_bg()
            
        self.setGeometry(int(monitor["left"] / self.ratio), 
                         int(monitor["top"] / self.ratio), 
                         int(monitor["width"] / self.ratio), 
                         int(monitor["height"] / self.ratio))

        # 2. Cache all visible window rects at the moment of freeze
        self.window_rects = []
        if HAS_WIN32:
            my_hwnd = int(self.winId())
            def enum_cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                    if hwnd == my_hwnd:
                        return True
                    
                    # Check if cloaked (invisible Windows 10/11 apps)
                    cloaked = ctypes.c_int(0)
                    dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                    if cloaked.value != 0:
                        return True
                        
                    rect = wintypes.RECT()
                    res = dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect))
                    if res == 0:
                        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
                    else:
                        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                        
                    if right > left and bottom > top:
                        left -= self.screen_offset_x
                        right -= self.screen_offset_x
                        top -= self.screen_offset_y
                        bottom -= self.screen_offset_y
                        
                        logical_rect = QRect(int(left / self.ratio), 
                                             int(top / self.ratio), 
                                             int((right - left) / self.ratio), 
                                             int((bottom - top) / self.ratio))
                        self.window_rects.append(logical_rect)
                return True
            try:
                win32gui.EnumWindows(enum_cb, None)
            except Exception:
                pass

        self.state = self.State.SNAPPING
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.snapped_rect = QRect()
        self.selected_rect = QRect()
        
        self.handles = []
        self.active_handle = -1
        self.handle_size = 12
        
        self.toolbar = FloatingToolbar(self, self.on_done, self.on_cancel)
        self.toolbar.hide()
        
        self.is_mouse_down = False
        self.current_mouse_pos = QPoint(-1000, -1000)

        # Load last selection
        from config import load_config
        config_data = load_config()
        last_sel = config_data.get("last_selection")
        if last_sel and last_sel.get("width", 0) > 0 and last_sel.get("height", 0) > 0:
            rect = QRect(last_sel["x"], last_sel["y"], last_sel["width"], last_sel["height"])
            if self.rect().intersects(rect):
                self.selected_rect = rect
                self.state = self.State.ADJUSTING
                self.update_handles()
                from PySide6.QtCore import QTimer
                QTimer.singleShot(50, self.update_toolbar_pos)

    def _draw_cursor_on_bg(self):
        from PySide6.QtGui import QPainterPath, QBrush, QColor, QPen, QPainter
        painter = QPainter(self.bg_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a sharp, generic vector arrow cursor
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(0, 16)
        path.lineTo(4, 12)
        path.lineTo(8, 20)
        path.lineTo(10, 19)
        path.lineTo(6, 11)
        path.lineTo(12, 11)
        path.closeSubpath()
        
        # QPainter on a QImage with devicePixelRatio > 1.0 automatically uses logical coordinates.
        # We must use purely logical coordinates here.
        cursor_pos = QCursor.pos()
        
        # self.screen_offset_x is physical, so convert it to logical
        logical_offset_x = self.screen_offset_x / self.ratio
        logical_offset_y = self.screen_offset_y / self.ratio
        
        rel_x = cursor_pos.x() - logical_offset_x
        rel_y = cursor_pos.y() - logical_offset_y
        
        painter.translate(rel_x, rel_y)
        # NO painter.scale() needed! QPainter already scales our drawing by self.ratio.
        
        painter.setPen(QPen(QColor(255, 255, 255), 1.5, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawPath(path)
        painter.end()

    def get_snapped_window(self, pos):
        # self.window_rects is populated via EnumWindows, which returns windows in Z-order (topmost first).
        # We simply return the first window that contains the point to only snap to visible, unobscured windows.
        for r in self.window_rects:
            if r.contains(pos):
                return r
        return QRect()

    def update_handles(self):
        r = self.selected_rect
        s = self.handle_size
        hs = s // 2
        self.handles = [
            QRect(r.left() - hs, r.top() - hs, s, s),
            QRect(r.center().x() - hs, r.top() - hs, s, s),
            QRect(r.right() - hs, r.top() - hs, s, s),
            QRect(r.right() - hs, r.center().y() - hs, s, s),
            QRect(r.right() - hs, r.bottom() - hs, s, s),
            QRect(r.center().x() - hs, r.bottom() - hs, s, s),
            QRect(r.left() - hs, r.bottom() - hs, s, s),
            QRect(r.left() - hs, r.center().y() - hs, s, s)
        ]

    def update_toolbar_pos(self):
        r = self.selected_rect
        
        # Update size label with physical size
        phys_w = int(r.width() * self.ratio)
        phys_h = int(r.height() * self.ratio)
        self.toolbar.update_size(phys_w, phys_h)
        
        self.toolbar.adjustSize()
        
        tw = self.toolbar.width()
        th = self.toolbar.height()
        
        x = r.center().x() - tw // 2
        y = r.bottom() + 10
        
        screen = QApplication.screenAt(self.mapToGlobal(r.center()))
        if screen:
            sg = screen.geometry()
            my_global = self.mapToGlobal(QPoint(0,0))
            
            mon_top = sg.top() - my_global.y()
            mon_bottom = sg.bottom() - my_global.y()
            mon_left = sg.left() - my_global.x()
            mon_right = sg.right() - my_global.x()
            
            if y + th > mon_bottom:
                y = r.top() - th - 10
                if y < mon_top:
                    y = r.bottom() - th - 10
                    
            if x < mon_left + 5:
                x = mon_left + 5
            elif x + tw > mon_right - 5:
                x = mon_right - tw - 5
        else:
            if y + th > self.height():
                y = r.top() - th - 10
                if y < 0:
                    y = r.bottom() - th - 10
            if x < 0:
                x = 0
            elif x + tw > self.width():
                x = self.width() - tw
            
        self.toolbar.move(x, y)
        self.toolbar.show()
        self.toolbar.raise_()

    def paintEvent(self, event):
        from PySide6.QtGui import QRegion
        painter = QPainter(self)
        
        if hasattr(self, 'bg_image'):
            painter.drawImage(0, 0, self.bg_image)
            
        draw_rect = QRect()
        pen_color = QColor(255, 165, 0)
        
        if self.state == self.State.SNAPPING:
            draw_rect = self.snapped_rect
        elif self.state == self.State.DRAWING:
            # Check if they are just clicking (with jitter) or actually dragging
            dist = (self.start_point - self.end_point).manhattanLength()
            if dist < 10 and not self.snapped_rect.isEmpty():
                draw_rect = self.snapped_rect
                pen_color = QColor(255, 165, 0) # Keep orange while clicking down
            else:
                draw_rect = QRect(self.start_point, self.end_point).normalized()
                pen_color = QColor(255, 0, 0) # Turn red when actually dragging
        elif self.state == self.State.ADJUSTING:
            draw_rect = self.selected_rect
            pen_color = QColor(255, 200, 0)
            
        # Draw the dim overlay using clipping to create a "hole"
        dim_region = QRegion(self.rect())
        if not draw_rect.isEmpty():
            dim_region = dim_region.subtracted(QRegion(draw_rect))
            
        painter.setClipRegion(dim_region)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        painter.setClipping(False) # Turn off clipping to draw the borders and handles
            
        if not draw_rect.isEmpty():
            painter.setPen(QPen(pen_color, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(draw_rect)
            
            if self.state == self.State.ADJUSTING:
                painter.setBrush(QColor(255, 255, 255))
                painter.setPen(QPen(QColor(100, 100, 100), 1))
                for h in self.handles:
                    painter.drawEllipse(h)
                    
        self._draw_magnifier(painter, draw_rect)

    def _draw_magnifier(self, painter, draw_rect):
        if not hasattr(self, 'current_mouse_pos') or self.current_mouse_pos.x() < -500:
            return
            
        cx, cy = self.current_mouse_pos.x(), self.current_mouse_pos.y()
        
        # Draw full screen crosshairs
        painter.setPen(QPen(QColor(255, 255, 255, 150), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, cy, self.width(), cy)
        painter.drawLine(cx, 0, cx, self.height())
        
        # Only draw magnifier if SNAPPING or DRAWING
        if self.state not in (self.State.SNAPPING, self.State.DRAWING):
            return
            
        radius = 60
        zoom = 6
        
        mag_x = cx + 20
        mag_y = cy + 20
        
        if mag_x + radius * 2 > self.width():
            mag_x = cx - 20 - radius * 2
        if mag_y + radius * 2 + 30 > self.height():
            mag_y = cy - 20 - radius * 2
            
        mag_rect = QRect(mag_x, mag_y, radius * 2, radius * 2)
        
        phys_cx = int(cx * self.ratio)
        phys_cy = int(cy * self.ratio)
        
        src_w = (radius * 2) // zoom
        src_h = (radius * 2) // zoom
        src_rect = QRect(phys_cx - src_w // 2, phys_cy - src_h // 2, src_w, src_h)
        
        mag_img = self.bg_image.copy(src_rect)
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False) # Pixelated look
        
        from PySide6.QtGui import QPainterPath
        from PySide6.QtCore import QRectF
        path = QPainterPath()
        path.addEllipse(QRectF(mag_rect))
        painter.setClipPath(path)
        
        painter.drawImage(mag_rect, mag_img)
        
        # Draw pixel grid
        painter.setPen(QPen(QColor(200, 200, 200, 100), 1, Qt.PenStyle.SolidLine))
        for i in range(1, src_w):
            x = mag_x + i * zoom
            painter.drawLine(x, mag_y, x, mag_y + radius * 2)
        for i in range(1, src_h):
            y = mag_y + i * zoom
            painter.drawLine(mag_x, y, mag_x + radius * 2, y)
        
        # Center crosshair in magnifier
        painter.setPen(QPen(QColor(255, 0, 0, 200), 1, Qt.PenStyle.SolidLine))
        painter.drawLine(mag_x, mag_y + radius, mag_x + radius * 2, mag_y + radius)
        painter.drawLine(mag_x + radius, mag_y, mag_x + radius, mag_y + radius * 2)
        
        painter.setClipping(False)
        
        # Border
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(mag_rect)
        
        # Dimensions Text
        if self.state == self.State.SNAPPING:
            if not draw_rect.isEmpty():
                txt = f"{int(draw_rect.width() * self.ratio)} x {int(draw_rect.height() * self.ratio)}"
            else:
                txt = f"X: {phys_cx}, Y: {phys_cy}"
        else:
            txt = f"{int(draw_rect.width() * self.ratio)} x {int(draw_rect.height() * self.ratio)}"
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(txt)
        th = fm.height()
        
        lbl_rect = QRect(mag_x + radius - tw//2 - 5, mag_y + radius*2 + 5, tw + 10, th + 4)
        painter.drawRoundedRect(lbl_rect, 4, 4)
        
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, txt)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_mouse_down = True
            
            if self.state == self.State.SNAPPING:
                self.start_point = event.pos()
                self.end_point = event.pos()
                self.state = self.State.DRAWING
                
            elif self.state == self.State.ADJUSTING:
                self.active_handle = -1
                for i, h in enumerate(self.handles):
                    if h.contains(event.pos()):
                        self.active_handle = i
                        break
                
                if self.active_handle == -1:
                    if self.selected_rect.contains(event.pos()):
                        self.active_handle = 8
                        self.start_point = event.pos()
                    else:
                        self.state = self.State.SNAPPING
                        self.toolbar.hide()
                        
        elif event.button() == Qt.MouseButton.RightButton:
            self.on_cancel()
        self.update()

    def mouseMoveEvent(self, event):
        self.current_mouse_pos = event.pos()
        
        if self.state == self.State.SNAPPING:
            self.snapped_rect = self.get_snapped_window(event.pos())
            self.snapped_rect = self.snapped_rect.intersected(self.rect())
            self.setCursor(Qt.CursorShape.CrossCursor)
            
        elif self.state == self.State.DRAWING:
            self.end_point = event.pos()
            self.update()
            
        elif self.state == self.State.ADJUSTING:
            if self.is_mouse_down and self.active_handle != -1:
                self.toolbar.hide()
                p = event.pos()
                r = self.selected_rect
                
                if self.active_handle == 8:
                    delta = p - self.start_point
                    r.translate(delta)
                    self.start_point = p
                else:
                    if self.active_handle in (0, 6, 7): r.setLeft(p.x())
                    if self.active_handle in (2, 3, 4): r.setRight(p.x())
                    if self.active_handle in (0, 1, 2): r.setTop(p.y())
                    if self.active_handle in (4, 5, 6): r.setBottom(p.y())
                    
                self.selected_rect = r.normalized()
                self.update_handles()
                self.update()
            else:
                cursor = Qt.CursorShape.CrossCursor
                for i, h in enumerate(self.handles):
                    if h.contains(event.pos()):
                        if i in (0, 4): cursor = Qt.CursorShape.SizeFDiagCursor
                        elif i in (2, 6): cursor = Qt.CursorShape.SizeBDiagCursor
                        elif i in (1, 5): cursor = Qt.CursorShape.SizeVerCursor
                        elif i in (3, 7): cursor = Qt.CursorShape.SizeHorCursor
                        break
                if cursor == Qt.CursorShape.CrossCursor and self.selected_rect.contains(event.pos()):
                    cursor = Qt.CursorShape.SizeAllCursor
                self.setCursor(cursor)
                
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_mouse_down = False
            
            if self.state == self.State.DRAWING:
                dist = (self.start_point - self.end_point).manhattanLength()
                if dist < 10 and not self.snapped_rect.isEmpty():
                    self.selected_rect = self.snapped_rect
                else:
                    self.selected_rect = QRect(self.start_point, self.end_point).normalized()
                
                if not self.selected_rect.isEmpty():
                    self.state = self.State.ADJUSTING
                    self.update_handles()
                    self.update_toolbar_pos()
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                else:
                    self.state = self.State.SNAPPING
                self.update()
                
            elif self.state == self.State.ADJUSTING:
                self.active_handle = -1
                self.update_toolbar_pos()

    def on_done(self):
        rect = self.selected_rect
        if not rect.isEmpty():
            from config import load_config, save_config
            config_data = load_config()
            config_data["last_selection"] = {
                "x": rect.x(),
                "y": rect.y(),
                "width": rect.width(),
                "height": rect.height()
            }
            save_config(config_data)
            
        self.toolbar.hide()
        self.close()
        QApplication.processEvents()
        
        if rect.width() > 0 and rect.height() > 0:
            # Convert logical rect back to physical rect to crop from the high-res physical bg_image
            phys_rect = QRect(int(rect.left() * self.ratio), 
                              int(rect.top() * self.ratio), 
                              int(rect.width() * self.ratio), 
                              int(rect.height() * self.ratio))
            cropped_image = self.bg_image.copy(phys_rect)
            
            # Reset device pixel ratio on the cropped image before saving so it saves at full physical resolution
            cropped_image.setDevicePixelRatio(1.0)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"Capture_{timestamp}.png"
            filepath = os.path.join(self.library_dir, filename)
            cropped_image.save(filepath, "PNG")
            
            clipboard = QApplication.clipboard()
            clipboard.setImage(cropped_image)
            print(f"Captured: {filepath} and copied to clipboard.")
                
    def on_cancel(self):
        self.toolbar.hide()
        self.close()
