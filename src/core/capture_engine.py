'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QApplication, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QImage, QColor, QPainter, QPen, QPixmap, QFont
import mss
import cv2
import numpy as np
import time
import os
import sys
import json
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from version import PROJECT_VERSION
from platforms import Platform

class BorderOverlay(QWidget):
    def __init__(self, physical_rect):
        super().__init__()
        # Added NoDropShadowWindowHint to prevent Windows shadow from bleeding into the screenshot
        flags = Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.NoDropShadowWindowHint
        if sys.platform == 'darwin':
            flags |= Qt.WindowType.ToolTip
        else:
            flags |= Qt.WindowType.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        Platform.set_window_hides_on_deactivate(int(self.winId()), False)
        
        # Hide this red border from screen capture APIs just to be absolutely bulletproof
        try:
            import ctypes
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass
        
        self.ratio = QApplication.primaryScreen().devicePixelRatio()
        # Keep a small padding (2px) for sides/bottom, but more for top to draw the size text
        self.padding = 2
        self.top_padding = 25
        
        self.logical_w = int(physical_rect.width() / self.ratio)
        self.logical_h = int(physical_rect.height() / self.ratio)
        self.physical_w = physical_rect.width()
        self.current_h = physical_rect.height()
        
        logical_x = int(physical_rect.x() / self.ratio) - self.padding
        logical_y = int(physical_rect.y() / self.ratio) - self.top_padding
        logical_w = self.logical_w + self.padding * 2
        logical_h = self.logical_h + self.top_padding + self.padding
        
        self.setGeometry(logical_x, logical_y, logical_w, logical_h)
        
    def set_current_height(self, height):
        self.current_h = height
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw red border
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(self.padding - 1, self.top_padding - 1, self.logical_w + 1, self.logical_h + 1)
        
        # Draw size label (width x height)
        size_str = f"{self.physical_w} x {self.current_h}"
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        metrics = painter.fontMetrics()
        tw = metrics.horizontalAdvance(size_str)
        th = metrics.height()
        
        text_x = self.padding
        text_y = self.top_padding - th - 6
        if text_y < 0:
            text_y = self.top_padding + 4
            
        # Draw background for text
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(text_x - 4, text_y, tw + 8, th + 4)
        
        # Draw text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(text_x, text_y + metrics.ascent() + 2, size_str)

class ScrollCaptureManager(QWidget):
    def __init__(self, rect, library_dir, on_done_callback=None):
        super().__init__()
        self.rect = rect # Physical QRect
        self.library_dir = library_dir
        self.on_done_callback = on_done_callback
        
        # Add WindowDoesNotAcceptFocus so clicking buttons won't steal focus from target window
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.accumulated_image = None
        self.last_frame = None
        
        # Setup UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        bg = QWidget()
        bg.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555555; border-radius: 8px;")
        bg_layout = QHBoxLayout(bg)
        bg_layout.setContentsMargins(15, 8, 15, 8)
        
        self.preview_lbl = QLabel()
        self.preview_lbl.setFixedSize(80, 120)
        self.preview_lbl.setStyleSheet("background-color: #111111; border: 1px solid #666666; border-radius: 4px; margin-right: 15px;")
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        from widgets.capture_toolbar import ScrollCaptureToolbar
        self.toolbar_controls = ScrollCaptureToolbar()
        self.toolbar_controls.finish_requested.connect(self.finish_capture)
        self.toolbar_controls.cancel_requested.connect(self.cancel_capture)
        self.status_lbl = self.toolbar_controls.status_lbl
        
        bg_layout.addWidget(self.preview_lbl)
        bg_layout.addWidget(self.toolbar_controls)
        layout.addWidget(bg)
        
        # Position the UI near the bottom of the capture rect
        self.adjustSize()
        tw = self.width()
        th = self.height()
        
        ratio = QApplication.primaryScreen().devicePixelRatio()
        import sys
        coord_ratio = 1.0 if sys.platform == 'darwin' else ratio
        logical_rect_center_x = int((rect.x() + rect.width() / 2) / coord_ratio)
        logical_rect_bottom = int((rect.y() + rect.height()) / coord_ratio)
        logical_rect_top = int(rect.y() / coord_ratio)
        
        x = logical_rect_center_x - tw // 2
        y = logical_rect_bottom + 15
        
        # Keep it within screen bounds
        screen = QApplication.screenAt(QPoint(logical_rect_center_x, int(rect.y() / coord_ratio)))
        if not screen:
            screen = QApplication.primaryScreen()
            
        sg = screen.geometry()
        
        if y + th > sg.bottom():
            y = logical_rect_top - th - 15
            if y < sg.top():
                y = sg.bottom() - th - 15
                
        if x < sg.left() + 5:
            x = sg.left() + 5
        elif x + tw > sg.right() - 5:
            x = sg.right() - tw - 5
            
        self.move(x, y)
        
        # Hide this UI from screen capture APIs (Windows 10 2004+)
        try:
            import ctypes
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass
        
        # Init MSS
        self.sct = mss.mss()
        self.monitor = {"left": rect.x(), "top": rect.y(), "width": rect.width(), "height": rect.height()}
        
        # Show red border
        self.border_overlay = BorderOverlay(rect)
        self.border_overlay.show()
        
        # Take first frame
        self.last_frame = self.grab_frame()
        self.accumulated_image = self.last_frame.copy()
        self.current_y = 0
        self.update_preview()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(33) # 30 times a second to handle faster scrolling
        
    def grab_frame(self):
        sct_img = self.sct.grab(self.monitor)
        # Convert bgra to bgr for opencv template matching
        return cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
        
    def process_frame(self):
        current_frame = self.grab_frame()
        
        # We need to find how much we scrolled.
        # Take a slice from the bottom of the last frame as the template
        # Use a larger template (e.g. 1/3 of the height) for better matching, up to 300px
        template_height = min(300, current_frame.shape[0] // 3)
        if template_height < 10:
            return # Region is too small to scroll capture effectively
            
        mid = self.last_frame.shape[0] // 2
        start_y = mid - (template_height // 2)
        end_y = start_y + template_height
        template = self.last_frame[start_y:end_y, :]
        
        # Check if template has enough variance (don't match solid colors)
        if np.std(template) < 5.0:
            self.last_frame = current_frame
            return
            
        # Match template in the current frame
        res = cv2.matchTemplate(current_frame, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if max_val > 0.85:
            match_y = max_loc[1]
            expected_y = start_y
            scrolled_pixels = expected_y - match_y
            
            if scrolled_pixels != 0:
                self.current_y += scrolled_pixels
                frame_h = current_frame.shape[0]
                
                # Check if we need to add to the bottom
                if self.current_y + frame_h > self.accumulated_image.shape[0]:
                    pixels_to_add = (self.current_y + frame_h) - self.accumulated_image.shape[0]
                    new_part = current_frame[-pixels_to_add:, :]
                    self.accumulated_image = np.vstack((self.accumulated_image, new_part))
                    
                # Check if we need to add to the top
                if self.current_y < 0:
                    pixels_to_add = abs(self.current_y)
                    new_part = current_frame[:pixels_to_add, :]
                    self.accumulated_image = np.vstack((new_part, self.accumulated_image))
                    self.current_y = 0
                    
                self.last_frame = current_frame
                self.update_preview()
                
                # Prevent going to infinity
                if self.accumulated_image.shape[0] > 20000:
                    self.timer.stop()
                    self.finish_capture()
        else:
            # Correlation low -> view changed completely or scrolling too fast.
            # Update last_frame to current to try to resync.
            self.last_frame = current_frame
            self.current_y = max(0, self.accumulated_image.shape[0] - current_frame.shape[0])

    def update_preview(self):
        if self.accumulated_image is not None:
            img_rgb = cv2.cvtColor(self.accumulated_image, cv2.COLOR_BGR2RGB)
            h, w, ch = img_rgb.shape
            
            # Update the size label on the border overlay
            if hasattr(self, 'border_overlay'):
                self.border_overlay.set_current_height(h)
                
            # Update the status label
            self.status_lbl.setText(f"Scrolling... ({w} x {h})")
            
            bytes_per_line = ch * w
            q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img).scaled(
                80, 120, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_lbl.setPixmap(pixmap)

    def _close_mss(self):
        if hasattr(self, 'sct') and self.sct:
            try:
                self.sct.close()
            except Exception:
                pass
            self.sct = None

    def closeEvent(self, event):
        self._close_mss()
        super().closeEvent(event)

    def finish_capture(self):
        self.timer.stop()
        self._close_mss()
        if hasattr(self, 'border_overlay'):
            self.border_overlay.close()
        self.close()
        
        if self.accumulated_image is not None:
            # Save accumulated_image
            timestamp = time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time()*1000)%1000:03d}"
            filename = f"ScrollCapture_{timestamp}.scut"
            filepath = os.path.join(self.library_dir, filename)
            
            # Copy to clipboard
            img_rgb = cv2.cvtColor(self.accumulated_image, cv2.COLOR_BGR2RGB)
            h, w, ch = img_rgb.shape
            bytes_per_line = ch * w
            q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Ensure proper memory handling for QImage created from numpy array
            q_img_copy = q_img.copy() 
            save_image_as_scut(q_img_copy, filepath)
            
            clipboard = QApplication.clipboard()
            clipboard.setImage(q_img_copy)
            
            import logging
            logging.info("Scroll Capture saved: %s", filepath)
            
            from config import load_config
            config = load_config()
            try:
                from editor.editor_main import ImageEditor
                if ImageEditor._instance:
                    ImageEditor._instance._hidden_by_capture = False
            except Exception:
                pass

            if config.get("toggles", {}).get("Preview in Editor", True):
                from editor.editor_main import ImageEditor
                ImageCaptureManager._active_editor = ImageEditor.get_instance(self.library_dir, initial_image=q_img_copy, current_filepath=filepath)
            
        if self.on_done_callback:
            self.on_done_callback()
            
    def cancel_capture(self):
        self.timer.stop()
        self._close_mss()
        if hasattr(self, 'border_overlay'):
            self.border_overlay.close()
        self.close()
        if self.on_done_callback:
            self.on_done_callback()

def save_image_as_scut(q_img: QImage, filepath: str):
    try:
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        q_img.save(buf, "PNG")
        img_b64 = ba.toBase64().data().decode('ascii')
        
        thumb = q_img.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        t_ba = QByteArray()
        t_buf = QBuffer(t_ba)
        t_buf.open(QIODevice.OpenModeFlag.WriteOnly)
        thumb.save(t_buf, "PNG")
        thumb_b64 = t_ba.toBase64().data().decode('ascii')
        
        data = {
            "version": "1.0",
            "timestamp": time.time(),
            "image": img_b64,
            "image_base64": img_b64,
            "thumbnail": thumb_b64,
            "thumbnail_base64": thumb_b64,
            "annotations": []
        }
        tmp_filepath = f"{filepath}.tmp.{int(time.time()*1000)}"
        with open(tmp_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_filepath, filepath)
    except Exception as e:
        print(f"Error saving scut capture: {e}")


class ImageCaptureManager:
    @staticmethod
    def save_static_capture(bg_image, phys_rect, library_dir, toast_class=None):
        # Crop the image
        cropped_image = bg_image.copy(phys_rect)
        
        # Reset device pixel ratio on the cropped image before saving so it saves at full physical resolution
        cropped_image.setDevicePixelRatio(1.0)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time()*1000)%1000:03d}"
        filename = f"Capture_{timestamp}.scut"
        filepath = os.path.join(library_dir, filename)
        save_image_as_scut(cropped_image, filepath)
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setImage(cropped_image)
        
        from config import load_config
        config = load_config()
        try:
            from editor.editor_main import ImageEditor
            if ImageEditor._instance:
                ImageEditor._instance._hidden_by_capture = False
        except Exception:
            pass

        if config.get("toggles", {}).get("Preview in Editor", True):
            from editor.editor_main import ImageEditor
            ImageCaptureManager._active_editor = ImageEditor.get_instance(library_dir, initial_image=cropped_image, current_filepath=filepath)
            return None

        # Show toast notification if class provided
        if toast_class:
            toast = toast_class(f"Project saved successfully:\n{filename}")
            toast.show_toast()
            return toast
        return None
