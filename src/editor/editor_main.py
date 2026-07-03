'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import os
import time
import math
import json
import cv2
import numpy as np

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QScrollArea, QSlider, QComboBox, 
                             QFontComboBox, QSpinBox, QColorDialog, QFileDialog, 
                             QApplication, QButtonGroup, QToolButton, QFrame, QLineEdit)
from PySide6.QtCore import Qt, QPoint, QRect, QSize, Signal, QTimer, QBuffer, QByteArray, QIODevice
from PySide6.QtGui import (QImage, QPixmap, QPainter, QColor, QPen, QBrush, 
                         QFont, QPainterPath, QKeySequence, QShortcut, QIcon)

from resources.icon_utils import (create_svg_icon, SVG_SELECT, SVG_ARROW, SVG_TEXT, SVG_SHAPE, 
                         SVG_STAMP, SVG_CROP, SVG_BLUR, SVG_PEN, SVG_STEP, 
                         SVG_UNDO, SVG_REDO, SVG_SAVE, SVG_COPY, SVG_ZOOM_IN, 
                         SVG_ZOOM_OUT, SVG_CLOSE, SVG_RECENT, SVG_TAG, 
                         SVG_EFFECTS, SVG_PROPERTIES)
from version import EDITOR_VERSION, PROJECT_VERSION
from widgets.common_notification import Notification

from editor.editor_main_ui import (ImageEditorUI, AnnotationObject, ArrowObject, ShapeObject, TextObject, StepObject, ImageCanvas, ToolPropertiesPanel, ResizePopup, DeleteConfirmPopup, HorizontalScrollArea, ThumbnailWidget)

class ImageEditor(ImageEditorUI):
    _instance = None

    @classmethod
    def get_instance(cls, library_dir: str, initial_image: QImage = None, current_filepath: str = None, parent=None):
        create_new = False
        if cls._instance is None:
            create_new = True
        else:
            try:
                _ = cls._instance.objectName()
            except RuntimeError:
                create_new = True

        if create_new:
            cls._instance = cls(library_dir, initial_image, current_filepath, parent)
        else:
            cls._instance.library_dir = library_dir
            if current_filepath and os.path.exists(current_filepath):
                cls._instance.load_image_from_path(current_filepath)
            elif initial_image and not initial_image.isNull():
                cls._instance.canvas.set_image(initial_image)
                cls._instance.current_image_path = current_filepath
                cls._instance.canvas.current_filepath = current_filepath
                cls._instance.update_resolution_label()
                cls._instance.update_thumbnail_highlights()
            cls._instance.refresh_library_strip()
            cls._instance.auto_fit_image()
            
        cls._instance.show()
        cls._instance.raise_()
        cls._instance.activateWindow()
        return cls._instance

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def showEvent(self, event):
        super().showEvent(event)
        from resources.icon_utils import apply_dark_titlebar, get_app_icon
        apply_dark_titlebar(self)
        self.setWindowIcon(get_app_icon(True))
        if getattr(self, 'is_auto_fit', False):
            QTimer.singleShot(10, self.auto_fit_image)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, 'is_auto_fit', False):
            self.auto_fit_image()

    def auto_fit_image(self):
        self.is_auto_fit = True
        if hasattr(self, 'scroll_area') and self.canvas.base_image:
            vp = self.scroll_area.viewport().size()
            iw = self.canvas.base_image.width()
            ih = self.canvas.base_image.height()
            if iw > 0 and ih > 0 and vp.width() > 0 and vp.height() > 0:
                zoom_w = (vp.width() - 40) / iw
                zoom_h = (vp.height() - 40) / ih
                fit_z = min(1.0, min(zoom_w, zoom_h))
                self.canvas.set_zoom(max(0.1, fit_z))
        self.is_auto_fit = True
        self.update_zoom_label()

    def manual_set_zoom(self, z):
        self.is_auto_fit = False
        self.canvas.set_zoom(z)
        self.update_zoom_label()

    def __init__(self, library_dir: str, initial_image: QImage = None, current_filepath: str = None, parent=None):
        super().__init__(library_dir, initial_image, current_filepath, parent)
        self.is_auto_fit = True
        self.canvas.new_image_loaded.connect(self.auto_fit_image)
        if current_filepath and os.path.exists(current_filepath):
            if current_filepath.lower().endswith('.scut'):
                self.canvas.load_scut_project(current_filepath)
            elif initial_image and not initial_image.isNull():
                self.canvas.set_image(initial_image)
                self.canvas.current_filepath = current_filepath
        elif initial_image and not initial_image.isNull():
            self.canvas.set_image(initial_image)
            self.canvas.current_filepath = current_filepath
        else:
            self._load_latest_library_image()
            
        self.canvas.image_changed.connect(self.update_resolution_label)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.canvas.redo)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_to_clipboard)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_image)
        QShortcut(QKeySequence("Del"), self, self.canvas.delete_selected)
        QShortcut(QKeySequence("Backspace"), self, self.canvas.delete_selected)
        QShortcut(QKeySequence("Esc"), self, self.close)


    def toggle_recent_strip(self):
        is_vis = self.recent_strip_container.isVisible()
        self.recent_strip_container.setVisible(not is_vis)
        if is_vis:
            self.btn_toggle_recent.setText(" Show Recent")
        else:
            self.btn_toggle_recent.setText(" Hide Recent")

    def update_zoom_label(self):
        if hasattr(self, 'btn_zoom'):
            if getattr(self, 'is_auto_fit', False):
                self.btn_zoom.setText(f"Auto Fit ({int(self.canvas.zoom_factor * 100)}%) ▼")
            else:
                self.btn_zoom.setText(f"{int(self.canvas.zoom_factor * 100)}% ▼")

    def update_resolution_label(self):
        if hasattr(self, 'btn_resize'):
            if self.canvas.isHidden():
                self.btn_resize.setText("No Image")
                self.btn_resize.setEnabled(False)
            else:
                self.btn_resize.setText(f"{self.canvas.base_image.width()} x {self.canvas.base_image.height()}px ▼")
                self.btn_resize.setEnabled(True)

    def show_resize_dialog(self):
        if not hasattr(self, 'resize_popup') or self.resize_popup is None:
            self.resize_popup = ResizePopup(self)
        else:
            self.resize_popup.w_spin.setValue(self.canvas.base_image.width())
            self.resize_popup.h_spin.setValue(self.canvas.base_image.height())
            self.resize_popup.ratio = self.canvas.base_image.width() / max(1, self.canvas.base_image.height())
            
        pos = self.btn_resize.mapToGlobal(self.btn_resize.rect().topLeft())
        self.resize_popup.move(pos.x(), pos.y() - self.resize_popup.height() - 6)
        self.resize_popup.show()

    def update_thumbnail_highlights(self):
        for fp, btn in self.thumb_buttons:
            if fp == self.current_image_path:
                btn.setStyleSheet("QToolButton { background: #1e293b; border: 3px solid #3b82f6; border-radius: 8px; padding: 0px; }")
            else:
                btn.setStyleSheet("QToolButton { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 0px; } QToolButton:hover { border-color: #60a5fa; }")

    def refresh_library_strip(self):
        while self.lib_layout.count():
            item = self.lib_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.thumb_buttons.clear()
                
        if not os.path.exists(self.library_dir):
            self.current_image_path = None
            self.canvas.clear_canvas()
            self.update_resolution_label()
            return
            
        files = [os.path.join(self.library_dir, f) for f in os.listdir(self.library_dir) if f.lower().endswith('.scut')]
        files.sort(key=os.path.getmtime, reverse=True)
        
        for filepath in files[:25]:
            pix = QPixmap()
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                thumb_b64 = data.get("thumbnail_base64", "") or data.get("image_base64", "")
                if thumb_b64:
                    ba = QByteArray.fromBase64(thumb_b64.encode('ascii'))
                    pix.loadFromData(ba, "PNG")
            except Exception as e:
                import logging
                logging.debug("Error loading thumbnail for %s: %s", filepath, e, exc_info=True)
                
            if not pix.isNull():
                thumb = pix.scaled(96, 58, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                if thumb.width() > 96 or thumb.height() > 58:
                    thumb = thumb.copy((thumb.width() - 96)//2, (thumb.height() - 58)//2, 96, 58)
                item_widget = ThumbnailWidget(filepath, thumb, self.load_image_from_path, self.delete_library_file)
                self.lib_layout.addWidget(item_widget)
                self.thumb_buttons.append((filepath, item_widget.btn))
                
        self.lib_layout.addStretch()
        if not self.thumb_buttons:
            self.current_image_path = None
            self.canvas.clear_canvas()
            self.update_resolution_label()
        self.update_thumbnail_highlights()

    def delete_library_file(self, filepath, target_btn=None):
        self._delete_popup = DeleteConfirmPopup(self, filepath, target_btn)
        self._delete_popup.show()

    def load_image_from_path(self, filepath):
        if os.path.exists(filepath):
            self.current_image_path = filepath
            if filepath.lower().endswith('.scut'):
                self.canvas.load_scut_project(filepath)
            else:
                img = QImage(filepath)
                if not img.isNull():
                    self.canvas.set_image(img)
                    self.canvas.current_filepath = filepath
            self.update_resolution_label()
            self.update_thumbnail_highlights()

    def select_tool(self, tool_id):
        self.canvas.current_tool = tool_id
        if hasattr(self, 'toolbar'):
            self.toolbar.set_active_tool(tool_id)
        if tool_id != "select":
            self.canvas.selected_annotation = None
            self.canvas.update()
        self.props_panel.update_properties()

    def _load_latest_library_image(self):
        if not os.path.exists(self.library_dir):
            return
        files = [os.path.join(self.library_dir, f) for f in os.listdir(self.library_dir) if f.lower().endswith('.scut')]
        if files:
            latest = max(files, key=os.path.getmtime)
            self.load_image_from_path(latest)

    def copy_to_clipboard(self):
        cb = QApplication.clipboard()
        cb.setImage(self.canvas.flatten_image())
        toast = Notification("Image copied to clipboard!", self)
        toast.show_toast()

    def save_image(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_path = self.current_image_path if (self.current_image_path and self.current_image_path.lower().endswith('.scut')) else os.path.join(self.library_dir, f"Project_{timestamp}.scut")
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", default_path, "ScreenCut Project (*.scut);;PNG Image (*.png);;JPEG Image (*.jpg)")
        if path:
            if path.lower().endswith('.scut'):
                self.canvas.save_scut_project(path)
                self.current_image_path = path
                self.canvas.current_filepath = path
            else:
                self.canvas.flatten_image().save(path)
                self.current_image_path = path
                self.canvas.current_filepath = path
            self.copy_to_clipboard()
            toast = Notification(f"Saved & copied:\n{os.path.basename(path)}", self)
            toast.show_toast()
            self.refresh_library_strip()

    def start_new_capture(self):
        # 1. Try finding Main capture window in top-level widgets
        for w in QApplication.topLevelWidgets():
            if w.__class__.__name__ == "Main":
                w.start_capture()
                return

        # 2. Try IPC connection to ScreenCut_IPC_Server
        from PySide6.QtNetwork import QLocalSocket
        sock = QLocalSocket()
        sock.connectToServer("ScreenCut_IPC_Server")
        if sock.waitForConnected(300):
            sock.write("START_CAPTURE".encode('utf-8'))
            sock.flush()
            sock.waitForBytesWritten(300)
            sock.disconnectFromServer()
            return

        # 3. If neither worked, launch ScreenCut capture executable or script
        import subprocess, sys
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            capture_exe = os.path.join(exe_dir, "ScreenCut.exe")
            if os.path.exists(capture_exe):
                subprocess.Popen([capture_exe], creationflags=creationflags)
        else:
            src_dir = os.path.dirname(os.path.abspath(__file__))
            root_src = os.path.dirname(src_dir)
            screencut_py = os.path.join(root_src, "screencut.py")
            if os.path.exists(screencut_py):
                py_exe = sys.executable
                if sys.platform == "win32" and py_exe.lower().endswith("python.exe"):
                    pythonw = os.path.join(os.path.dirname(py_exe), "pythonw.exe")
                    if os.path.exists(pythonw):
                        py_exe = pythonw
                subprocess.Popen([py_exe, screencut_py], creationflags=creationflags)
