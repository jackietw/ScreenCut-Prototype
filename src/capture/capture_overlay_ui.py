'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QCursor, QShortcut, QKeySequence, QFont
import mss
from platforms import Platform
from capture.capture_status import RecStatus
from widgets.capture_toolbar import VideoToolbar, FloatingToolbar

# Windows-only: DWM extended frame info

class OverlayUI(QWidget):
    capture_finished = Signal()
    
    class State:
        SNAPPING = 0
        DRAWING = 1
        ADJUSTING = 2
        RECORDING = 3
        COUNTDOWN = 4

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
        import sys
        self.mss_ratio = 1.0 if sys.platform == 'darwin' else self.ratio

        if hasattr(self, 'bg_image'):
            self.bg_image.setDevicePixelRatio(self.ratio)
            
        # Draw cursor if requested
        if capture_cursor and hasattr(self, 'bg_image'):
            self._draw_cursor_on_bg()
            
        self.setGeometry(int(monitor["left"] / self.mss_ratio), 
                         int(monitor["top"] / self.mss_ratio), 
                         int(monitor["width"] / self.mss_ratio), 
                         int(monitor["height"] / self.mss_ratio))

        # 2. Cache all visible window rects at the moment of freeze
        self.window_rects = []
        raw_rects = Platform.enum_visible_windows()
        my_hwnd = int(self.winId())
        for (l, t, r, b) in raw_rects:
            if r > l and b > t:
                l -= self.screen_offset_x
                r -= self.screen_offset_x
                t -= self.screen_offset_y
                b -= self.screen_offset_y
                logical_rect = QRect(
                    int(l / self.mss_ratio), int(t / self.mss_ratio),
                    int((r - l) / self.mss_ratio), int((b - t) / self.mss_ratio)
                )
                self.window_rects.append(logical_rect)

        self.state = self.State.SNAPPING
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.snapped_rect = QRect()
        self.selected_rect = QRect()
        
        self.handles = []
        self.active_handle = -1
        self.handle_size = 12
        
        if self.is_video:
            self.toolbar = VideoToolbar(self, init_cursor=capture_cursor)
            self.toolbar.start_requested.connect(self.on_done)
            self.toolbar.cancel_requested.connect(self.on_cancel)
        else:
            self.toolbar = FloatingToolbar(self, self.on_done, self.on_cancel)
        self.toolbar.hide()
        
        self.ready_panel = None
        if self.is_video:
            self.ready_panel = RecStatus(self)
            self.ready_panel.hide()
            
            # Connect toolbar toggles to update the panel
            self.toolbar.cursor_toggled.connect(self.ready_panel.update_cursor_status)
            self.toolbar.audio_toggled.connect(self.ready_panel.update_audio_status)
            self.toolbar.sys_audio_toggled.connect(self.ready_panel.update_sys_audio_status)
            
            # Sync initial states
            self.ready_panel.update_cursor_status(self.toolbar.btn_cursor.isChecked())
            self.ready_panel.update_audio_status(self.toolbar.btn_audio.isChecked())
            self.ready_panel.update_sys_audio_status(self.toolbar.btn_sys_audio.isChecked())
            
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
        
        # self.screen_offset_x is physical on Win, but logical on Mac
        logical_offset_x = self.screen_offset_x / self.mss_ratio
        logical_offset_y = self.screen_offset_y / self.mss_ratio
        
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
        
        if hasattr(self, 'bg_image') and self.state != self.State.RECORDING:
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
        elif self.state in (self.State.RECORDING, self.State.COUNTDOWN):
            draw_rect = self.selected_rect
            pen_color = QColor(255, 0, 0)
            
        # Draw the dim overlay using clipping to create a "hole"
        if self.state not in (self.State.RECORDING, self.State.COUNTDOWN):
            dim_region = QRegion(self.rect())
            if not draw_rect.isEmpty():
                dim_region = dim_region.subtracted(QRegion(draw_rect))
                
            painter.setClipRegion(dim_region)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
            painter.setClipping(False) # Turn off clipping to draw the borders and handles
            
        if not draw_rect.isEmpty():
            painter.setPen(QPen(pen_color, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(draw_rect)
            
            if self.state not in (self.State.RECORDING, self.State.COUNTDOWN):
                painter.fillRect(draw_rect, QColor(0, 0, 0, 1))
                
            if self.state == self.State.COUNTDOWN:
                painter.setClipRegion(QRegion(draw_rect))
                painter.fillRect(draw_rect, QColor(0, 0, 0, 150))
                painter.setClipping(False)
                
                if hasattr(self, 'countdown_num'):
                    text = str(self.countdown_num)
                    font = QFont("Arial", int(80 * getattr(self, 'countdown_scale', 1.0)), QFont.Weight.Bold)
                    painter.setFont(font)
                    painter.setPen(QColor(255, 255, 255, getattr(self, 'countdown_opacity', 255)))
                    painter.drawText(draw_rect, Qt.AlignmentFlag.AlignCenter, text)
            
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
            
        # Only draw crosshairs and magnifier if SNAPPING or DRAWING
        if self.state not in (self.State.SNAPPING, self.State.DRAWING):
            return
            
        cx, cy = self.current_mouse_pos.x(), self.current_mouse_pos.y()
        
        # Draw full screen crosshairs
        painter.setPen(QPen(QColor(255, 255, 255, 150), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, cy, self.width(), cy)
        painter.drawLine(cx, 0, cx, self.height())
            
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


    def on_done(self): pass
    def on_cancel(self): pass
    def _on_countdown_anim(self, value): pass
    def _start_actual_recording(self): pass
