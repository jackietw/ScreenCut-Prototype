'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QRect, QPoint, QTimer, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QCursor
from platforms import Platform
from capture.capture_overlay_ui import OverlayUI
from capture.capture_countdown import Countdown

class Overlay(OverlayUI):
    def __init__(self, library_dir, capture_cursor=False, is_scroll=False, is_video=False):
        super().__init__(library_dir, capture_cursor, is_scroll, is_video)

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
                        if hasattr(self, 'ready_panel') and self.ready_panel:
                            self.ready_panel.hide()
                        
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
                if hasattr(self, 'ready_panel') and self.ready_panel:
                    self.ready_panel.hide()
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
            mss_rect = QRect(int(rect.left() * self.mss_ratio), 
                             int(rect.top() * self.mss_ratio), 
                             int(rect.width() * self.mss_ratio), 
                             int(rect.height() * self.mss_ratio))
            img_phys_rect = QRect(int(rect.left() * self.ratio), 
                                  int(rect.top() * self.ratio), 
                                  int(rect.width() * self.ratio), 
                                  int(rect.height() * self.ratio))
            
            if hasattr(self, 'is_video') and self.is_video:
                self.state = self.State.COUNTDOWN
                self.toolbar.hide()
                
                if hasattr(self, 'ready_panel') and self.ready_panel:
                    self._recording_settings = {
                        "capture_cursor": self.toolbar.btn_cursor.isChecked(),
                        "audio": self.toolbar.btn_audio.isChecked()
                    }
                    self.ready_panel.hide()
                else:
                    self._recording_settings = None
                    
                from PySide6.QtCore import QVariantAnimation
                self.countdown_anim = QVariantAnimation(self)
                self.countdown_anim.setDuration(3000)
                self.countdown_anim.setStartValue(3.0)
                self.countdown_anim.setEndValue(0.0)
                self.countdown_anim.valueChanged.connect(self._on_countdown_anim)
                self.countdown_anim.finished.connect(self._start_actual_recording)
                self.countdown_anim.start()
                return
            else:
                self.toolbar.hide()
                self.close()
                QApplication.processEvents()
                
                if hasattr(self, 'is_scroll') and self.is_scroll:
                    from core.capture_engine import ScrollCaptureManager
                    self.scroll_manager = ScrollCaptureManager(mss_rect, self.library_dir)
                    self.scroll_manager.show()
                else:
                    from core.capture_engine import ImageCaptureManager
                    from widgets.common_toast import Notification
                    self.__class__._active_toast = ImageCaptureManager.save_static_capture(
                        self.bg_image, img_phys_rect, self.library_dir, Notification
                    )
            
            if not (hasattr(self, 'is_scroll') and self.is_scroll):
                self.capture_finished.emit()
                
    def _on_countdown_anim(self, value):
        import math
        self.countdown_num = math.ceil(value)
        if self.countdown_num == 0:
            return
            
        frac = value - math.floor(value) # 1.0 down to 0.0
        self.countdown_scale = 1.0 + (1.0 - frac) * 2.0
        self.countdown_opacity = int(frac * 255)
        self.update()
        
    def _start_actual_recording(self):
        rect = self.selected_rect
        mss_rect = QRect(int(rect.left() * self.mss_ratio), 
                         int(rect.top() * self.mss_ratio), 
                         int(rect.width() * self.mss_ratio), 
                         int(rect.height() * self.mss_ratio))
                          
        self.state = self.State.RECORDING
        if hasattr(self, 'bg_image'):
            del self.bg_image
            
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        hwnd = int(self.winId())
        Platform.set_window_click_through(hwnd)
        Platform.set_window_capture_excluded(hwnd)
        
        img_phys_rect = QRect(int(rect.left() * self.ratio), 
                              int(rect.top() * self.ratio), 
                              int(rect.width() * self.ratio), 
                              int(rect.height() * self.ratio))
        from core.capture_engine import BorderOverlay
        self.border_overlay = BorderOverlay(img_phys_rect)
        Platform.set_window_click_through(int(self.border_overlay.winId()))
        Platform.set_window_capture_excluded(int(self.border_overlay.winId()))
        self.border_overlay.show()
        self.hide()
        
        from core.capture_video import VideoCaptureManager
        cw_pos = getattr(self.toolbar, 'pos', lambda: QPoint(0,0))()
        self.__class__.video_manager = VideoCaptureManager(
            mss_rect, self.library_dir, cw_pos.x(), cw_pos.y(),
            override_settings=getattr(self, '_recording_settings', None), 
            existing_toolbar=self.toolbar, 
            logical_rect=rect
        )
        # When recording finishes or is cancelled, close the overlay and emit finished signal
        def _cleanup_recording(path):
            if hasattr(self, 'border_overlay') and self.border_overlay:
                self.border_overlay.close()
            self.close()
        self.__class__.video_manager.thread.finished_signal.connect(_cleanup_recording)
        self.__class__.video_manager.thread.finished_signal.connect(lambda path: self.capture_finished.emit())
        
        self.update()
        
        # Ensure toolbar stays on top of the overlay
        self.__class__.video_manager.toolbar.show()
        self.__class__.video_manager.toolbar.raise_()
        self.__class__.video_manager.toolbar.activateWindow()
                
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
