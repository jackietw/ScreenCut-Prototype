'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QApplication, QPushButton, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRect, QPoint, QSize, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QCursor, QShortcut, QKeySequence, QFontMetrics, QFont
import mss
import os
import time
import sys
import ctypes
from ctypes import wintypes
from ui.ready_to_record_panel import ReadyToRecordPanel
from ui.video_toolbar import VideoToolbar

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
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Exclude from screen capture
        try:
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except:
            pass
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        bg = QWidget()
        bg.setObjectName("bg_widget")
        bg.setStyleSheet("#bg_widget { background-color: #2b2b2b; border: 1px solid #555555; border-radius: 6px; }")
        bg_layout = QHBoxLayout(bg)
        bg_layout.setContentsMargins(8, 4, 8, 4)
        
        self.lbl_size = QLabel("0 x 0")
        self.lbl_size.setStyleSheet("color: #aaaaaa; font-family: monospace; margin-right: 10px;")
        bg_layout.addWidget(self.lbl_size)
        
        from ui.icon_utils import create_svg_icon, SVG_DONE, SVG_CANCEL
        
        btn_done = QPushButton()
        btn_done.setIcon(create_svg_icon(SVG_DONE))
        btn_done.setIconSize(QSize(20, 20))
        btn_done.setStyleSheet("background-color: #246bb2; padding: 6px 15px; border-radius: 3px; border: none;")
        btn_cancel = QPushButton()
        btn_cancel.setIcon(create_svg_icon(SVG_CANCEL))
        btn_cancel.setIconSize(QSize(20, 20))
            
        btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_done.clicked.connect(on_done)
        
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("background-color: #4a4a4a; padding: 6px 15px; border-radius: 3px; border: none;")
        btn_cancel.clicked.connect(on_cancel)
        
        bg_layout.addWidget(btn_done)
        bg_layout.addWidget(btn_cancel)
        layout.addWidget(bg)
        self.adjustSize()
        
    def update_size(self, width, height):
        self.lbl_size.setText(f"{width} x {height}")
        self.adjustSize()

class OverlayWindow(QWidget):
    capture_finished = Signal()
    
    class State:
        SNAPPING = 0
        DRAWING = 1
        ADJUSTING = 2
        RECORDING = 3

    def __init__(self, library_dir, capture_cursor=False, is_scroll=False, is_video=False):
        super().__init__()
        self.library_dir = library_dir
        self.is_scroll = is_scroll
        self.is_video = is_video
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
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
        if hasattr(self, 'bg_image'):
            self.bg_image.setDevicePixelRatio(self.ratio)
            
        # Draw cursor if requested
        if capture_cursor and hasattr(self, 'bg_image'):
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
        
        if self.is_video:
            self.toolbar = VideoToolbar(self)
            self.toolbar.start_requested.connect(self.on_done)
            self.toolbar.cancel_requested.connect(self.on_cancel)
        else:
            self.toolbar = FloatingToolbar(self, self.on_done, self.on_cancel)
        self.toolbar.hide()
        
        self.ready_panel = None
        if self.is_video:
            self.ready_panel = ReadyToRecordPanel(self)
            self.ready_panel.hide()
            
            # Connect toolbar toggles to update the panel
            self.toolbar.cursor_toggled.connect(self.ready_panel.update_cursor_status)
            self.toolbar.audio_toggled.connect(self.ready_panel.update_audio_status)
            
            # Pass audio device name from config
            from config import load_config
            cfg = load_config()
            audio_device = cfg.get("audio_source", "System Default")
            self.ready_panel.set_audio_device_name(audio_device)
        
        self.is_mouse_down = False
        self.current_mouse_pos = QPoint(-1000, -1000)

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
        
        if hasattr(self, 'ready_panel') and self.ready_panel:
            self.ready_panel.adjustSize()
            pw = self.ready_panel.width()
            ph = self.ready_panel.height()
            px = r.center().x() - pw // 2
            py = r.center().y() - ph // 2
            
            # Ensure it fits inside the selected region if possible, else just center it
            if px < r.left(): px = r.left() + 5
            if py < r.top(): py = r.top() + 5
            
            self.ready_panel.move(px, py)
            self.ready_panel.show()
            self.ready_panel.raise_()

    def paintEvent(self, event):
        from PySide6.QtGui import QRegion, QPainter
        painter = QPainter(self)
        
        if hasattr(self, 'bg_image'):
            painter.drawImage(0, 0, self.bg_image)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
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
        elif self.state == self.State.RECORDING:
            # In RECORDING state, draw nothing - the overlay should be invisible
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
            painter.end()
            return
            
        # Draw the dim overlay using clipping to create a "hole"
        if self.state != self.State.RECORDING:
            dim_region = QRegion(self.rect())
            if not draw_rect.isEmpty():
                dim_region = dim_region.subtracted(QRegion(draw_rect))
                
            painter.setClipRegion(dim_region)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
            painter.setClipping(False) # Turn off clipping to draw the borders and handles
            
        if not draw_rect.isEmpty():
            painter.setPen(QPen(pen_color, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(draw_rect)
            
            if self.state != self.State.RECORDING:
                painter.fillRect(draw_rect, QColor(0, 0, 0, 1))
            
            if self.state == self.State.ADJUSTING:
                painter.setBrush(QColor(255, 255, 255))
                painter.setPen(QPen(QColor(100, 100, 100), 1))
                for h in self.handles:
                    painter.drawEllipse(h)
                    
        if hasattr(self, 'bg_image'):
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
                    if hasattr(self, 'is_scroll') and self.is_scroll:
                        from PySide6.QtCore import QTimer
                        # Use singleShot to allow mouse grab to be released properly
                        QTimer.singleShot(0, self.on_done)
                    else:
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
            
        if rect.width() > 0 and rect.height() > 0:
            phys_rect = QRect(int(rect.left() * self.ratio), 
                              int(rect.top() * self.ratio), 
                              int(rect.width() * self.ratio), 
                              int(rect.height() * self.ratio))
            
            if hasattr(self, 'is_video') and self.is_video:
                self.state = self.State.RECORDING
                if hasattr(self, 'bg_image'):
                    del self.bg_image
                
                settings = None
                if hasattr(self, 'ready_panel') and self.ready_panel:
                    settings = {
                        "capture_cursor": self.toolbar.btn_cursor.isChecked(),
                        "audio": self.toolbar.btn_audio.isChecked()
                    }
                    self.ready_panel.hide()
                
                self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                import win32gui, win32con
                import ctypes
                hwnd = int(self.winId())
                exStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exStyle | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED)
                # Also exclude this window from screen capture
                try:
                    ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
                except Exception:
                    pass
                
                from core.video_capture import VideoCaptureManager
                cw_pos = self.toolbar.pos()
                self.__class__.video_manager = VideoCaptureManager(
                    phys_rect, self.library_dir, cw_pos.x(), cw_pos.y(),
                    override_settings=settings, existing_toolbar=self.toolbar, logical_rect=rect
                )
                # When recording finishes or is cancelled, close the overlay and emit finished signal
                self.__class__.video_manager.thread.finished_signal.connect(lambda path: self.close())
                self.__class__.video_manager.thread.finished_signal.connect(lambda path: self.capture_finished.emit())
                
                self.update()
                
                # Ensure toolbar stays on top of the overlay
                self.__class__.video_manager.toolbar.raise_()
                self.__class__.video_manager.toolbar.activateWindow()
                return
            else:
                self.toolbar.hide()
                self.close()
                QApplication.processEvents()
                
                if hasattr(self, 'is_scroll') and self.is_scroll:
                    from core.scroll_capture import ScrollCaptureManager
                    self.scroll_manager = ScrollCaptureManager(phys_rect, self.library_dir)
                    self.scroll_manager.show()
                else:
                    cropped_image = self.bg_image.copy(phys_rect)
            
            if not (hasattr(self, 'is_scroll') and self.is_scroll) and not (hasattr(self, 'is_video') and self.is_video):
                # Reset device pixel ratio on the cropped image before saving so it saves at full physical resolution
                cropped_image.setDevicePixelRatio(1.0)
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"Capture_{timestamp}.png"
                filepath = os.path.join(self.library_dir, filename)
                cropped_image.save(filepath, "PNG")
                
                clipboard = QApplication.clipboard()
                clipboard.setImage(cropped_image)
                from ui.toast_notification import ToastNotification
                self.__class__._active_toast = ToastNotification(f"Image saved successfully:\n{filename}")
                self.__class__._active_toast.show_toast()
                
            if not (hasattr(self, 'is_scroll') and self.is_scroll):
                self.capture_finished.emit()
                
    def on_cancel(self):
        if self.state == self.State.RECORDING:
            # cancel_requested is already connected to VideoCaptureManager.cancel_capture
            # Do NOT re-emit here or it will cause an infinite loop
            return
            
        self.toolbar.hide()
        if hasattr(self, 'ready_panel') and self.ready_panel:
            self.ready_panel.hide()
        self.close()
        self.capture_finished.emit()
