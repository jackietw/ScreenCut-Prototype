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

from PySide6.QtWidgets import QWidget, QApplication, QScrollArea
from PySide6.QtCore import Qt, QPoint, QRect, QSize, Signal, QTimer, QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QFontMetrics

from core.editor_engine import calculate_expansion, apply_canvas_expansion, calculate_temporary_size, constrain_square
from core.editor_models import AnnotationObject, ArrowObject, ShapeObject, TextObject, StepObject
from widgets.editor_text import CanvasTextEdit


def handle_canvas_wheel_event(widget, event):
    delta = event.angleDelta().y()
    if delta == 0:
        delta = event.angleDelta().x()
    if delta == 0:
        return

    win = widget.window()
    canvas = getattr(win, 'canvas', None) if win else None
    if not canvas and isinstance(widget, ImageCanvas):
        canvas = widget
    scroll_area = getattr(win, 'scroll_area', None) if win else None
    if not scroll_area and isinstance(widget, QScrollArea):
        scroll_area = widget

    mods = event.modifiers()
    if mods & Qt.KeyboardModifier.ControlModifier:
        if canvas:
            old_zoom = canvas.zoom_factor
            if delta > 0:
                new_zoom = old_zoom * 1.15
            else:
                new_zoom = old_zoom / 1.15
            new_zoom = max(0.1, min(5.0, new_zoom))
            
            vp_pos = None
            if scroll_area:
                vp_pos = scroll_area.viewport().mapFromGlobal(event.globalPosition().toPoint())
                old_h = scroll_area.horizontalScrollBar().value()
                old_v = scroll_area.verticalScrollBar().value()
                canvas_x = (old_h + vp_pos.x()) / old_zoom
                canvas_y = (old_v + vp_pos.y()) / old_zoom

            if hasattr(win, 'manual_set_zoom'):
                win.manual_set_zoom(new_zoom)
            else:
                canvas.set_zoom(new_zoom)

            if scroll_area and vp_pos:
                new_h = int(canvas_x * new_zoom - vp_pos.x())
                new_v = int(canvas_y * new_zoom - vp_pos.y())
                scroll_area.horizontalScrollBar().setValue(new_h)
                scroll_area.verticalScrollBar().setValue(new_v)
        event.accept()
    elif mods & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier):
        if scroll_area:
            h_bar = scroll_area.horizontalScrollBar()
            if h_bar:
                step = max(40, h_bar.singleStep() * 4)
                if delta > 0:
                    h_bar.setValue(h_bar.value() - step)
                else:
                    h_bar.setValue(h_bar.value() + step)
        event.accept()
    else:
        if scroll_area:
            v_bar = scroll_area.verticalScrollBar()
            if v_bar:
                step = max(40, v_bar.singleStep() * 4)
                if delta > 0:
                    v_bar.setValue(v_bar.value() - step)
                else:
                    v_bar.setValue(v_bar.value() + step)
        event.accept()


class CanvasScrollArea(QScrollArea):
    def wheelEvent(self, event):
        handle_canvas_wheel_event(self, event)


class ImageCanvas(QWidget):
    zoom_changed = Signal(int)
    step_changed = Signal(int)
    image_changed = Signal()
    new_image_loaded = Signal()
    undo_state_changed = Signal(bool, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_image = QImage(600, 400, QImage.Format.Format_ARGB32)
        self.base_image.fill(QColor("#333333"))
        
        self.annotations = []
        self.selected_annotation = None
        self.active_handle = None
        self.is_dragging_object = False
        
        self.is_dragging_canvas = False
        self.active_canvas_handle = None
        self.canvas_drag_offset_x = 0
        self.canvas_drag_offset_y = 0
        
        self.undo_stack = []
        self.redo_stack = []
        
        self.zoom_factor = 1.0
        self.default_canvas_w = self.base_image.width()
        self.default_canvas_h = self.base_image.height()
        
        # Tool state
        self.current_tool = "select" # select, arrow, text, shape, stamp, crop, blur, pen, step
        self.tool_color = QColor("#ff3333")
        self.tool_width = 4
        
        # Sub-options
        self.arrow_type = "Single Arrow" # Single Arrow, Double Arrow, Plain Line
        self.font_family = "Arial"
        self.font_size = 24
        self.shape_type = "Rectangle" # Rectangle, Rounded Rectangle, Ellipse
        self.line_style = "Solid" # Solid, Dashed
        self.blur_type = "Mosaic" # Mosaic, Gaussian Blur
        self.blur_intensity = 15 # block size or kernel radius
        self.pen_style = "Solid Pen" # Solid Pen, Highlighter
        
        # Step counter
        self.step_counter = 1
        
        # Interactive drawing state
        self.is_drawing = False
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.pen_path = []
        self.crop_rect = QRect()
        
        # Live Text Input overlay
        self.text_input = CanvasTextEdit(self)
        self.text_input.hide()
        self.text_input.commit_requested.connect(self.commit_text)
        
        self.current_filepath = None
        self.setMouseTracking(True)
        self.update_canvas_size()

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.setInterval(1200) # 1.2s debounce
        self._auto_save_timer.timeout.connect(self._perform_auto_save)

    def trigger_auto_save(self):
        if self.current_filepath and self.current_filepath.lower().endswith('.scut'):
            self._auto_save_timer.start()

    def _perform_auto_save(self):
        if self.current_filepath and self.current_filepath.lower().endswith('.scut'):
            self.save_scut_project(self.current_filepath)

    def save_scut_project(self, filepath):
        try:
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            self.base_image.save(buf, "PNG")
            img_b64 = ba.toBase64().data().decode('ascii')
            
            thumb = self.flatten_image().scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            t_ba = QByteArray()
            t_buf = QBuffer(t_ba)
            t_buf.open(QIODevice.OpenModeFlag.WriteOnly)
            thumb.save(t_buf, "PNG")
            thumb_b64 = t_ba.toBase64().data().decode('ascii')
            
            data = {
                "version": PROJECT_VERSION,
                "timestamp": time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time()*1000)%1000:03d}",
                "image": img_b64,
                "image_base64": img_b64,
                "thumbnail": thumb_b64,
                "thumbnail_base64": thumb_b64,
                "annotations": [obj.to_dict() for obj in self.annotations],
                "default_canvas_w": getattr(self, 'default_canvas_w', self.base_image.width()),
                "default_canvas_h": getattr(self, 'default_canvas_h', self.base_image.height()),
                "extra_left": getattr(self, 'extra_left', 0),
                "extra_top": getattr(self, 'extra_top', 0)
            }
            tmp_filepath = f"{filepath}.tmp.{int(time.time()*1000)}"
            with open(tmp_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_filepath, filepath)
                
            win = self.window()
            if hasattr(win, 'refresh_library_strip'):
                win.refresh_library_strip()
        except Exception as e:
            import logging
            logging.error("Error auto-saving scut project: %s", e, exc_info=True)

    def load_scut_project(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            img_b64 = data.get("image_base64", "")
            if img_b64:
                ba = QByteArray.fromBase64(img_b64.encode('ascii'))
                img = QImage()
                img.loadFromData(ba, "PNG")
                self.base_image = img.convertToFormat(QImage.Format.Format_ARGB32)
                self.default_canvas_w = data.get("default_canvas_w", self.base_image.width())
                self.default_canvas_h = data.get("default_canvas_h", self.base_image.height())
                self.extra_left = data.get("extra_left", 0)
                self.extra_top = data.get("extra_top", 0)
            
            annots_data = data.get("annotations", [])
            self.annotations = []
            for ad in annots_data:
                obj = AnnotationObject.from_dict(ad)
                if obj:
                    self.annotations.append(obj)
            self.selected_annotation = None
            self.undo_stack = []
            self.redo_stack = []
            self.current_filepath = filepath
            self.update_canvas_size()
            self.show()
            self.image_changed.emit()
            self.new_image_loaded.emit()
            self._emit_undo_state()
            self.update()
        except Exception as e:
            import logging
            logging.error("Error loading scut project: %s", e, exc_info=True)

    def set_image(self, img: QImage):
        self.base_image = img.convertToFormat(QImage.Format.Format_ARGB32)
        self.default_canvas_w = self.base_image.width()
        self.default_canvas_h = self.base_image.height()
        self.extra_left = 0
        self.extra_top = 0
        self.annotations = []
        self.selected_annotation = None
        self.undo_stack = []
        self.redo_stack = []
        self.update_canvas_size()
        self.show()
        self.image_changed.emit()
        self.new_image_loaded.emit()
        self._emit_undo_state()
        self.update()

    def clear_canvas(self):
        self.base_image = QImage(1, 1, QImage.Format.Format_ARGB32)
        self.base_image.fill(QColor("transparent"))
        self.extra_left = 0
        self.extra_top = 0
        self.annotations = []
        self.selected_annotation = None
        self.undo_stack = []
        self.redo_stack = []
        self.current_filepath = None
        self.update_canvas_size()
        self.hide()
        self.image_changed.emit()
        self.new_image_loaded.emit()
        self._emit_undo_state()
        self.update()

    def _emit_undo_state(self):
        self.undo_state_changed.emit(bool(self.undo_stack), bool(self.redo_stack))

    def push_undo(self):
        state = {
            "image": self.base_image.copy(),
            "annotations": [obj.clone() for obj in self.annotations],
            "default_canvas_w": getattr(self, 'default_canvas_w', self.base_image.width()),
            "default_canvas_h": getattr(self, 'default_canvas_h', self.base_image.height()),
            "extra_left": getattr(self, 'extra_left', 0),
            "extra_top": getattr(self, 'extra_top', 0)
        }
        self.undo_stack.append(state)
        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self._emit_undo_state()

    def undo(self):
        if not self.undo_stack:
            return
        current_state = {
            "image": self.base_image.copy(),
            "annotations": [obj.clone() for obj in self.annotations],
            "default_canvas_w": getattr(self, 'default_canvas_w', self.base_image.width()),
            "default_canvas_h": getattr(self, 'default_canvas_h', self.base_image.height()),
            "extra_left": getattr(self, 'extra_left', 0),
            "extra_top": getattr(self, 'extra_top', 0)
        }
        self.redo_stack.append(current_state)
        state = self.undo_stack.pop()
        self.base_image = state["image"]
        self.annotations = state["annotations"]
        self.default_canvas_w = state.get("default_canvas_w", self.base_image.width())
        self.default_canvas_h = state.get("default_canvas_h", self.base_image.height())
        self.extra_left = state.get("extra_left", 0)
        self.extra_top = state.get("extra_top", 0)
        self.selected_annotation = None
        self.update_canvas_size()
        self.image_changed.emit()
        self.update()
        self.trigger_auto_save()
        self._emit_undo_state()

    def redo(self):
        if not self.redo_stack:
            return
        current_state = {
            "image": self.base_image.copy(),
            "annotations": [obj.clone() for obj in self.annotations],
            "default_canvas_w": getattr(self, 'default_canvas_w', self.base_image.width()),
            "default_canvas_h": getattr(self, 'default_canvas_h', self.base_image.height()),
            "extra_left": getattr(self, 'extra_left', 0),
            "extra_top": getattr(self, 'extra_top', 0)
        }
        self.undo_stack.append(current_state)
        state = self.redo_stack.pop()
        self.base_image = state["image"]
        self.annotations = state["annotations"]
        self.default_canvas_w = state.get("default_canvas_w", self.base_image.width())
        self.default_canvas_h = state.get("default_canvas_h", self.base_image.height())
        self.extra_left = state.get("extra_left", 0)
        self.extra_top = state.get("extra_top", 0)
        self.selected_annotation = None
        self.update_canvas_size()
        self.image_changed.emit()
        self.update()
        self.trigger_auto_save()
        self._emit_undo_state()

    def set_zoom(self, factor: float):
        self.zoom_factor = max(0.1, min(5.0, factor))
        self.update_canvas_size()
        self.zoom_changed.emit(int(self.zoom_factor * 100))
        self.update()

    def update_canvas_size(self):
        w = int(self.base_image.width() * self.zoom_factor)
        h = int(self.base_image.height() * self.zoom_factor)
        self.setFixedSize(w, h)

    def reset_step(self):
        self.step_counter = 1
        self.step_changed.emit(self.step_counter)

    def apply_crop(self):
        if not self.crop_rect.isValid() or self.crop_rect.width() < 10 or self.crop_rect.height() < 10:
            return
        self.push_undo()
        self.base_image = self.base_image.copy(self.crop_rect)
        self.crop_rect = QRect()
        self.default_canvas_w = self.base_image.width()
        self.default_canvas_h = self.base_image.height()
        self.extra_left = 0
        self.extra_top = 0
        self.update_canvas_size()
        self.image_changed.emit()
        self.update()
        self.trigger_auto_save()

    def resize_image(self, new_w, new_h):
        if new_w <= 0 or new_h <= 0:
            return
        self.push_undo()
        self.base_image = self.base_image.scaled(new_w, new_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.default_canvas_w = self.base_image.width()
        self.default_canvas_h = self.base_image.height()
        self.extra_left = 0
        self.extra_top = 0
        self.update_canvas_size()
        self.image_changed.emit()
        self.update()
        self.trigger_auto_save()

    def _draw_checkerboard(self, painter: QPainter, rect: QRect):
        grid_size = 12
        c1 = QColor("#ffffff")
        c2 = QColor("#e0e0e0")
        if not hasattr(self, '_checker_brush'):
            pix = QPixmap(grid_size * 2, grid_size * 2)
            p = QPainter(pix)
            p.fillRect(0, 0, grid_size, grid_size, c1)
            p.fillRect(grid_size, grid_size, grid_size, grid_size, c1)
            p.fillRect(grid_size, 0, grid_size, grid_size, c2)
            p.fillRect(0, grid_size, grid_size, grid_size, c2)
            p.end()
            self._checker_brush = QBrush(pix)
        painter.fillRect(rect, self._checker_brush)

    def auto_expand_for_annotations(self, extra_rect=None):
        if not hasattr(self, 'default_canvas_w'):
            self.default_canvas_w = self.base_image.width()
            self.default_canvas_h = self.base_image.height()
            
        W = self.base_image.width()
        H = self.base_image.height()
        extra_l = getattr(self, 'extra_left', 0)
        extra_t = getattr(self, 'extra_top', 0)
        
        shift_x, shift_y, shrink_x, shrink_y, target_w, target_h, needs_expand, needs_crop = calculate_expansion(
            W, H, self.default_canvas_w, self.default_canvas_h, self.annotations, extra_rect, extra_l, extra_t
        )
        
        if needs_expand:
            self.base_image = apply_canvas_expansion(self.base_image, target_w, target_h, shift_x, shift_y)
            if shift_x > 0 or shift_y > 0:
                self.extra_left = extra_l + shift_x
                self.extra_top = extra_t + shift_y
                self.default_canvas_w += shift_x
                self.default_canvas_h += shift_y
                for obj in self.annotations:
                    obj.move_by(shift_x, shift_y)
            self.update_canvas_size()
            self.image_changed.emit()
            return (shift_x, shift_y)
        elif needs_crop:
            self.base_image = self.base_image.copy(shrink_x, shrink_y, target_w, target_h)
            if shrink_x > 0 or shrink_y > 0:
                self.extra_left = extra_l - shrink_x
                self.extra_top = extra_t - shrink_y
                self.default_canvas_w -= shrink_x
                self.default_canvas_h -= shrink_y
                for obj in self.annotations:
                    obj.move_by(-shrink_x, -shrink_y)
            self.update_canvas_size()
            self.image_changed.emit()
            return (-shrink_x, -shrink_y)
        else:
            self.update_canvas_size()
        return (0, 0)

    def update_temporary_canvas_size(self):
        min_x, min_y = 0, 0
        for obj in self.annotations:
            b = obj.bounds()
            if b.left() < min_x: min_x = b.left()
            if b.top() < min_y: min_y = b.top()
        if self.is_drawing and hasattr(self, 'end_pos') and self.end_pos:
            if self.end_pos.x() < min_x: min_x = self.end_pos.x()
            if self.end_pos.y() < min_y: min_y = self.end_pos.y()
            
        if min_x < 0 or min_y < 0:
            shift_x = -min_x if min_x < 0 else 0
            shift_y = -min_y if min_y < 0 else 0
            self.base_image = apply_canvas_expansion(self.base_image, self.base_image.width() + shift_x, self.base_image.height() + shift_y, shift_x, shift_y)
            self.extra_left = getattr(self, 'extra_left', 0) + shift_x
            self.extra_top = getattr(self, 'extra_top', 0) + shift_y
            if hasattr(self, 'default_canvas_w'):
                self.default_canvas_w += shift_x
                self.default_canvas_h += shift_y
            for obj in self.annotations:
                obj.move_by(shift_x, shift_y)
            if hasattr(self, 'drag_last_pos') and self.drag_last_pos:
                self.drag_last_pos += QPoint(shift_x, shift_y)
            if self.is_drawing:
                if hasattr(self, 'start_pos') and self.start_pos:
                    self.start_pos += QPoint(shift_x, shift_y)
                if hasattr(self, 'end_pos') and self.end_pos:
                    self.end_pos += QPoint(shift_x, shift_y)
                if hasattr(self, 'pen_path') and self.pen_path:
                    self.pen_path = [pt + QPoint(shift_x, shift_y) for pt in self.pen_path]
            self.image_changed.emit()

        w, h = calculate_temporary_size(self.base_image.width(), self.base_image.height(), self.annotations, self.is_drawing, getattr(self, 'end_pos', None))
        self.setFixedSize(int(w * self.zoom_factor), int(h * self.zoom_factor))

    def get_canvas_handle_at(self, pt: QPoint):
        W = self.base_image.width()
        H = self.base_image.height()
        tol = max(12, int(14 / self.zoom_factor))
        
        if pt.x() <= tol and pt.y() <= tol: return "tl"
        if pt.x() >= W - tol and pt.y() <= tol: return "tr"
        if pt.x() <= tol and pt.y() >= H - tol: return "bl"
        if pt.x() >= W - tol and pt.y() >= H - tol: return "br"
        
        if abs(pt.x() - W//2) <= tol and pt.y() <= tol: return "t"
        if abs(pt.x() - W//2) <= tol and pt.y() >= H - tol: return "b"
        if pt.x() <= tol and abs(pt.y() - H//2) <= tol: return "l"
        if pt.x() >= W - tol and abs(pt.y() - H//2) <= tol: return "r"
        return None

    # -------------------------------------------------------------------------
    # Mouse Events
    # -------------------------------------------------------------------------
    def delete_selected(self):
        if self.selected_annotation in self.annotations:
            self.push_undo()
            self.annotations.remove(self.selected_annotation)
            self.selected_annotation = None
            self.auto_expand_for_annotations()
            self.update()
            self.trigger_auto_save()

    def get_handle_at(self, pt: QPoint):
        if not self.selected_annotation:
            return None
        obj = self.selected_annotation
        if obj.obj_type == "arrow":
            if (pt - obj.start_pos).manhattanLength() <= 12:
                return "start"
            if (pt - obj.end_pos).manhattanLength() <= 12:
                return "end"
        elif obj.obj_type in ("shape", "text"):
            b = obj.bounds()
            for name, corner in [("tl", b.topLeft()), ("tr", b.topRight()), ("bl", b.bottomLeft()), ("br", b.bottomRight())]:
                if (pt - corner).manhattanLength() <= 12:
                    return name
        return None

    def wheelEvent(self, event):
        handle_canvas_wheel_event(self, event)

    def mousePressEvent(self, event):
        if getattr(self, 'text_input', None) and self.text_input.isVisible():
            self.commit_text()
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return
            
        pos = event.pos() / self.zoom_factor
        pt = QPoint(int(pos.x()), int(pos.y()))
        
        # Check if clicking a handle on currently selected object
        if self.selected_annotation:
            h = self.get_handle_at(pt)
            if h:
                self.active_handle = h
                self.drag_last_pos = pt
                self.is_dragging_object = True
                self.has_pushed_drag_undo = False
                return

        # Check if clicking one of the 8 canvas handles
        h_canvas = self.get_canvas_handle_at(pt)
        if h_canvas:
            self.push_undo()
            self.is_dragging_canvas = True
            self.active_canvas_handle = h_canvas
            self.orig_canvas_image = self.base_image.copy()
            self.orig_canvas_annotations = [obj.clone() for obj in self.annotations]
            self.canvas_drag_offset_x = 0
            self.canvas_drag_offset_y = 0
            self.update()
            return

        # Check if clicking inside an object to select or move it
        if self.current_tool == "select" or self.selected_annotation:
            hit_obj = None
            for obj in reversed(self.annotations):
                if obj.hit_test(pt):
                    hit_obj = obj
                    break
            if hit_obj:
                self.selected_annotation = hit_obj
                self.active_handle = "move"
                self.drag_last_pos = pt
                self.is_dragging_object = True
                self.has_pushed_drag_undo = False
                self.update()
                win = self.window()
                if hasattr(win, 'props_panel'):
                    win.props_panel.sync_from_selected()
                return
            elif self.current_tool == "select":
                self.selected_annotation = None
                self.update()
                return

        self.selected_annotation = None
        self.start_pos = pt
        self.end_pos = self.start_pos
        self.is_drawing = True
            
        if self.current_tool == "step":
            self.push_undo()
            step_obj = StepObject(self.start_pos, self.step_counter, self.tool_color, self.tool_width)
            self.annotations.append(step_obj)
            self.selected_annotation = step_obj
            self.step_counter += 1
            self.step_changed.emit(self.step_counter)
            self.is_drawing = False
            self.auto_expand_for_annotations()
            self.update()
            win = self.window()
            if hasattr(win, 'props_panel'):
                win.props_panel.sync_from_selected()
            self.trigger_auto_save()
            return
            
        if self.current_tool == "pen":
            self.pen_path = [self.start_pos]
            
        if self.current_tool == "crop":
            self.crop_rect = QRect()

    def mouseMoveEvent(self, event):
        pos = event.pos() / self.zoom_factor
        pt = QPoint(int(pos.x()), int(pos.y()))
        
        if getattr(self, 'is_dragging_canvas', False) and self.active_canvas_handle:
            orig_pt = pt + QPoint(getattr(self, 'canvas_drag_offset_x', 0), getattr(self, 'canvas_drag_offset_y', 0))
            W_orig = self.orig_canvas_image.width()
            H_orig = self.orig_canvas_image.height()
            
            left = 0
            top = 0
            right = W_orig
            bottom = H_orig
            
            h = self.active_canvas_handle
            if 'l' in h:
                left = min(orig_pt.x(), right - 20)
            if 'r' in h:
                right = max(orig_pt.x(), left + 20)
            if 't' in h:
                top = min(orig_pt.y(), bottom - 20)
            if 'b' in h:
                bottom = max(orig_pt.y(), top + 20)
                
            new_w = max(20, right - left)
            new_h = max(20, bottom - top)
            
            self.canvas_drag_offset_x = left
            self.canvas_drag_offset_y = top
            
            preview_img = QImage(new_w, new_h, QImage.Format.Format_ARGB32)
            preview_img.fill(QColor("transparent"))
            
            p = QPainter(preview_img)
            p.drawImage(-left, -top, self.orig_canvas_image)
            p.end()
            
            self.base_image = preview_img
            self.default_canvas_w = preview_img.width()
            self.default_canvas_h = preview_img.height()
            self.annotations = [obj.clone() for obj in self.orig_canvas_annotations]
            for obj in self.annotations:
                obj.move_by(-left, -top)
                
            self.update_canvas_size()
            self.image_changed.emit()
            self.update()
            return

        if not getattr(self, 'is_dragging_object', False) and not self.is_drawing:
            ah = self.get_handle_at(pt) if self.selected_annotation else None
            if ah:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                h = self.get_canvas_handle_at(pt)
                if h in ["tl", "br"]:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif h in ["tr", "bl"]:
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif h in ["t", "b"]:
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                elif h in ["l", "r"]:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif self.selected_annotation and self.selected_annotation.hit_test(pt):
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    self.unsetCursor()

        if getattr(self, 'is_dragging_object', False) and self.selected_annotation:
            dx = pt.x() - self.drag_last_pos.x()
            dy = pt.y() - self.drag_last_pos.y()
            if dx != 0 or dy != 0:
                if not getattr(self, 'has_pushed_drag_undo', False):
                    self.push_undo()
                    self.has_pushed_drag_undo = True
            obj = self.selected_annotation
            if self.active_handle == "move":
                obj.move_by(dx, dy)
            elif obj.obj_type == "arrow":
                if self.active_handle == "start":
                    obj.start_pos = pt
                elif self.active_handle == "end":
                    obj.end_pos = pt
            elif obj.obj_type == "shape":
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if self.active_handle == "tl":
                        obj.start_pos = constrain_square(obj.end_pos, pt)
                    elif self.active_handle == "br":
                        obj.end_pos = constrain_square(obj.start_pos, pt)
                    elif self.active_handle == "tr":
                        opp = QPoint(obj.start_pos.x(), obj.end_pos.y())
                        target_pt = constrain_square(opp, pt)
                        obj.start_pos = QPoint(obj.start_pos.x(), target_pt.y())
                        obj.end_pos = QPoint(target_pt.x(), obj.end_pos.y())
                    elif self.active_handle == "bl":
                        opp = QPoint(obj.end_pos.x(), obj.start_pos.y())
                        target_pt = constrain_square(opp, pt)
                        obj.start_pos = QPoint(target_pt.x(), obj.start_pos.y())
                        obj.end_pos = QPoint(obj.end_pos.x(), target_pt.y())
                else:
                    if self.active_handle == "tl":
                        obj.start_pos = pt
                    elif self.active_handle == "br":
                        obj.end_pos = pt
                    elif self.active_handle == "tr":
                        obj.start_pos = QPoint(obj.start_pos.x(), pt.y())
                        obj.end_pos = QPoint(pt.x(), obj.end_pos.y())
                    elif self.active_handle == "bl":
                        obj.start_pos = QPoint(pt.x(), obj.start_pos.y())
                        obj.end_pos = QPoint(obj.end_pos.x(), pt.y())
            elif obj.obj_type == "text":
                b = obj.bounds()
                if self.active_handle == "br":
                    new_w = max(40, pt.x() - obj.pos.x())
                    new_h = max(20, pt.y() - obj.pos.y())
                    obj.box_width = new_w
                    obj.font_size = max(10, min(200, int(new_h * 0.75)))
                elif self.active_handle == "bl":
                    new_w = max(40, b.right() - pt.x())
                    new_h = max(20, pt.y() - obj.pos.y())
                    obj.pos = QPoint(pt.x(), obj.pos.y())
                    obj.box_width = new_w
                    obj.font_size = max(10, min(200, int(new_h * 0.75)))
                elif self.active_handle == "tr":
                    new_w = max(40, pt.x() - obj.pos.x())
                    new_h = max(20, b.bottom() - pt.y())
                    obj.pos = QPoint(obj.pos.x(), pt.y())
                    obj.box_width = new_w
                    obj.font_size = max(10, min(200, int(new_h * 0.75)))
                elif self.active_handle == "tl":
                    new_w = max(40, b.right() - pt.x())
                    new_h = max(20, b.bottom() - pt.y())
                    obj.pos = QPoint(pt.x(), pt.y())
                    obj.box_width = new_w
                    obj.font_size = max(10, min(200, int(new_h * 0.75)))
                win = self.window()
                if hasattr(win, 'props_panel'):
                    win.props_panel.sync_from_selected()
            self.drag_last_pos = pt
            self.update_temporary_canvas_size()
            self.update()
            return

        if not self.is_drawing:
            return
        self.end_pos = pt
        if self.current_tool == "shape" and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.end_pos = constrain_square(self.start_pos, self.end_pos)
        if self.current_tool == "pen":
            self.pen_path.append(self.end_pos)
        self.update_temporary_canvas_size()
        self.update()

    def mouseReleaseEvent(self, event):
        if getattr(self, 'is_dragging_canvas', False):
            self.is_dragging_canvas = False
            self.active_canvas_handle = None
            self.update()
            self.trigger_auto_save()
            return

        if getattr(self, 'is_dragging_object', False):
            self.is_dragging_object = False
            self.has_pushed_drag_undo = False
            self.active_handle = None
            self.auto_expand_for_annotations()
            self.update()
            self.trigger_auto_save()
            return

        if not self.is_drawing or event.button() != Qt.MouseButton.LeftButton:
            return
        self.is_drawing = False
        pos = event.pos() / self.zoom_factor
        self.end_pos = QPoint(int(pos.x()), int(pos.y()))
        if self.current_tool == "shape" and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.end_pos = constrain_square(self.start_pos, self.end_pos)
        
        if self.current_tool == "arrow":
            if (self.end_pos - self.start_pos).manhattanLength() > 5:
                self.push_undo()
                obj = ArrowObject(self.start_pos, self.end_pos, self.tool_color, self.tool_width, self.arrow_type)
                self.annotations.append(obj)
                self.selected_annotation = obj
                self.auto_expand_for_annotations()
                win = self.window()
                if hasattr(win, 'props_panel'):
                    win.props_panel.sync_from_selected()
                
        elif self.current_tool == "shape":
            if (self.end_pos - self.start_pos).manhattanLength() > 5:
                self.push_undo()
                obj = ShapeObject(self.start_pos, self.end_pos, self.tool_color, self.tool_width, self.shape_type, self.line_style)
                self.annotations.append(obj)
                self.selected_annotation = obj
                self.auto_expand_for_annotations()
                win = self.window()
                if hasattr(win, 'props_panel'):
                    win.props_panel.sync_from_selected()
                
        elif self.current_tool == "pen":
            if len(self.pen_path) > 1:
                self.push_undo()
                xs = [p.x() for p in self.pen_path]
                ys = [p.y() for p in self.pen_path]
                pad = max(6, int(self.tool_width * 2))
                pen_rect = QRect(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + pad * 2, max(ys) - min(ys) + pad * 2)
                shift_x, shift_y = self.auto_expand_for_annotations(extra_rect=pen_rect)
                if shift_x > 0 or shift_y > 0:
                    self.pen_path = [QPoint(pt.x() + shift_x, pt.y() + shift_y) for pt in self.pen_path]

                painter = QPainter(self.base_image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                self.render_pen(painter, self.pen_path)
                painter.end()
                
        elif self.current_tool == "blur":
            rect = QRect(self.start_pos, self.end_pos).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self.push_undo()
                self.apply_blur_rect(rect)
                
        elif self.current_tool == "crop":
            self.crop_rect = QRect(self.start_pos, self.end_pos).normalized()
            self.apply_crop()
            
        elif self.current_tool == "text":
            rect = QRect(self.start_pos, self.end_pos).normalized()
            box_w = rect.width()
            box_h = rect.height()
            if box_w < 15 or box_h < 15:
                box_w = max(int(self.font_size * 1.5), 250)
                box_h = int(self.font_size * 1.5)
                top_left = self.start_pos
            else:
                top_left = rect.topLeft()
                calc_font_size = max(10, min(200, int(box_h * 0.75)))
                self.font_size = calc_font_size
                win = self.window()
                if hasattr(win, 'props_panel'):
                    win.props_panel.update_properties()
            fm = QFontMetrics(QFont(self.font_family, self.font_size, QFont.Weight.Bold))
            min_char_w = max(16, int(self.font_size * 0.5))
            box_w = max(min_char_w, box_w)
            self.text_box_pos = top_left
            self.editing_text_object = None
            widget_pos = QPoint(int(top_left.x() * self.zoom_factor), int(top_left.y() * self.zoom_factor))
            self.show_text_input(widget_pos, box_w, box_h)
            
        self.update()
        self.trigger_auto_save()

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.current_tool != "select":
            return
        pos = event.pos() / self.zoom_factor
        pt = QPoint(int(pos.x()), int(pos.y()))
        hit_obj = None
        for obj in reversed(self.annotations):
            if obj.hit_test(pt) and obj.obj_type == "text":
                hit_obj = obj
                break
        if not hit_obj and self.selected_annotation and self.selected_annotation.obj_type == "text":
            hit_obj = self.selected_annotation
            
        if hit_obj:
            self.selected_annotation = hit_obj
            self.editing_text_object = hit_obj
            self.font_size = hit_obj.font_size
            self.font_family = hit_obj.font_family
            self.tool_color = hit_obj.color
            win = self.window()
            if hasattr(win, 'props_panel'):
                win.props_panel.sync_from_selected()
            self.text_box_pos = hit_obj.pos
            widget_pos = QPoint(int(hit_obj.pos.x() * self.zoom_factor), int(hit_obj.pos.y() * self.zoom_factor))
            box_w = max(int(hit_obj.font_size * 0.5), getattr(hit_obj, 'box_width', 250))
            box_h = hit_obj.bounds().height()
            self.show_text_input(widget_pos, box_w, box_h, initial_text=hit_obj.text)

    # -------------------------------------------------------------------------
    # Text Input Helper
    # -------------------------------------------------------------------------
    def show_text_input(self, widget_pos, box_w=250, box_h=50, initial_text=""):
        self.active_box_w = box_w
        font = QFont(self.font_family, max(8, int(self.font_size * self.zoom_factor)), QFont.Weight.Bold)
        self.text_input.setFont(font)
        self.text_input.setStyleSheet(f"color: {self.tool_color.name()}; background: rgba(0,0,0,180); border: 1px dashed {self.tool_color.name()}; padding: 2px;")
        self.text_input.setPlaceholderText("Text")
        self.text_input.setText(initial_text)
        self.text_input.move(widget_pos)
        min_h = max(35, int(box_h * self.zoom_factor))
        self.text_input.setMinimumHeight(min_h)
        self.text_input.resize(max(40, int(box_w * self.zoom_factor)), min_h)
        self.text_input.show()
        self.text_input._auto_resize()
        self.text_input.setFocus()
        if initial_text:
            cursor = self.text_input.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.text_input.setTextCursor(cursor)

    def commit_text(self):
        text = self.text_input.toPlainText().strip()
        if self.text_input.isVisible():
            if getattr(self, 'editing_text_object', None):
                self.push_undo()
                if text:
                    self.editing_text_object.text = text
                    self.editing_text_object.color = self.tool_color
                    self.editing_text_object.font_family = self.font_family
                    self.editing_text_object.font_size = self.font_size
                    if getattr(self, 'active_box_w', 0) > 0:
                        min_char_w = max(16, int(self.font_size * 0.5))
                        self.editing_text_object.box_width = max(min_char_w, self.active_box_w)
                else:
                    if self.editing_text_object in self.annotations:
                        self.annotations.remove(self.editing_text_object)
                    if self.selected_annotation == self.editing_text_object:
                        self.selected_annotation = None
                self.editing_text_object = None
            elif text:
                self.push_undo()
                pos = getattr(self, 'text_box_pos', self.start_pos)
                min_char_w = max(16, int(self.font_size * 0.5))
                eff_w = max(min_char_w, getattr(self, 'active_box_w', 250))
                obj = TextObject(pos, text, self.tool_color, self.font_family, self.font_size, eff_w)
                self.annotations.append(obj)
                self.selected_annotation = obj
                self.auto_expand_for_annotations()
            win = self.window()
            if hasattr(win, 'props_panel'):
                win.props_panel.sync_from_selected()
        self.text_input.hide()
        self.update()
        self.trigger_auto_save()

    # -------------------------------------------------------------------------
    # Drawing & Render Logic
    # -------------------------------------------------------------------------
    def draw_step_sticker(self, pt: QPoint):
        painter = QPainter(self.base_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        radius = max(14, int(self.tool_width * 2.5))
        rect = QRect(pt.x() - radius, pt.y() - radius, radius * 2, radius * 2)
        
        # Circle background
        painter.setBrush(QBrush(self.tool_color))
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawEllipse(rect)
        
        # Number text
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont("Arial", int(radius * 0.9), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self.step_counter))
        painter.end()
        
        self.step_counter += 1
        self.step_changed.emit(self.step_counter)

    def render_arrow(self, painter: QPainter, start: QPoint, end: QPoint):
        pen = QPen(self.tool_color, self.tool_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QBrush(self.tool_color))
        
        # Main line
        painter.drawLine(start, end)
        
        if self.arrow_type == "Plain Line":
            return
            
        # Arrow head at end
        self._draw_arrow_head(painter, start, end)
        
        if self.arrow_type == "Double Arrow":
            self._draw_arrow_head(painter, end, start)

    def _draw_arrow_head(self, painter: QPainter, p1: QPoint, p2: QPoint):
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        arrow_len = max(12.0, float(self.tool_width * 3.5))
        arrow_rad = math.radians(28)
        
        pt1 = QPoint(int(p2.x() - arrow_len * math.cos(angle - arrow_rad)),
                     int(p2.y() - arrow_len * math.sin(angle - arrow_rad)))
        pt2 = QPoint(int(p2.x() - arrow_len * math.cos(angle + arrow_rad)),
                     int(p2.y() - arrow_len * math.sin(angle + arrow_rad)))
        
        polygon = [p2, pt1, pt2]
        painter.drawPolygon(polygon)

    def render_shape(self, painter: QPainter, start: QPoint, end: QPoint):
        style = Qt.PenStyle.DashLine if self.line_style == "Dashed" else Qt.PenStyle.SolidLine
        pen = QPen(self.tool_color, self.tool_width, style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        
        if self.shape_type == "Circle":
            r = max(abs(dx), abs(dy))
            rect = QRect(start.x(), start.y(), r if dx >= 0 else -r, r if dy >= 0 else -r).normalized()
            painter.drawEllipse(rect)
        elif self.shape_type == "Ellipse":
            rect = QRect(start, end).normalized()
            painter.drawEllipse(rect)
        else: # Rectangle
            rect = QRect(start, end).normalized()
            painter.drawRect(rect)

    def render_pen(self, painter: QPainter, path: list):
        if len(path) < 2:
            return
        color = QColor(self.tool_color)
        width = self.tool_width
        
        if self.pen_style == "Highlighter":
            color.setAlpha(110)
            width = max(12, self.tool_width * 3)
            
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        for i in range(len(path) - 1):
            painter.drawLine(path[i], path[i+1])

    def apply_blur_rect(self, rect: QRect):
        # Intersect with canvas bounds
        bounds = QRect(0, 0, self.base_image.width(), self.base_image.height())
        rect = rect.intersected(bounds)
        if rect.width() <= 0 or rect.height() <= 0:
            return
            
        arr = np.array(self.base_image.bits()).reshape(self.base_image.height(), self.base_image.width(), 4)
        sub = arr[rect.top():rect.bottom()+1, rect.left():rect.right()+1].copy()
        h_sub, w_sub = sub.shape[:2]
        
        if self.blur_type == "Mosaic":
            block = max(2, int(self.blur_intensity))
            small = cv2.resize(sub, (max(1, w_sub // block), max(1, h_sub // block)), interpolation=cv2.INTER_LINEAR)
            res = cv2.resize(small, (w_sub, h_sub), interpolation=cv2.INTER_NEAREST)
            arr[rect.top():rect.bottom()+1, rect.left():rect.right()+1] = res
        else: # Gaussian Blur
            k = max(3, int(self.blur_intensity) | 1) # Must be odd
            res = cv2.GaussianBlur(sub, (k, k), 0)
            arr[rect.top():rect.bottom()+1, rect.left():rect.right()+1] = res
            
        self.base_image = QImage(arr.data, self.base_image.width(), self.base_image.height(), 
                                 self.base_image.width() * 4, QImage.Format.Format_ARGB32).copy()

    # -------------------------------------------------------------------------
    # Paint Event & Flatten
    # -------------------------------------------------------------------------
    def flatten_image(self) -> QImage:
        img = self.base_image.copy()
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for obj in self.annotations:
            obj.render(painter)
        painter.end()
        return img

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.zoom_factor, self.zoom_factor)
        
        # Draw transparent checkerboard background over the entire widget rect
        w_curr = int(self.width() / max(0.1, self.zoom_factor))
        h_curr = int(self.height() / max(0.1, self.zoom_factor))
        self._draw_checkerboard(painter, QRect(0, 0, max(self.base_image.width(), w_curr), max(self.base_image.height(), h_curr)))
        
        # Draw Base Image
        painter.drawImage(0, 0, self.base_image)
        
        # Draw saved annotations
        for obj in self.annotations:
            obj.render(painter)
            
        # Draw selection handles if selected
        if self.selected_annotation in self.annotations:
            obj = self.selected_annotation
            pen = QPen(QColor("#00a8ff"), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            b = obj.bounds().adjusted(-3, -3, 3, 3)
            if obj.obj_type != "arrow":
                painter.drawRect(b)
            
            # Handles
            painter.setBrush(QBrush(QColor("#00a8ff")))
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            hw = 8
            if obj.obj_type == "arrow":
                for pt in [obj.start_pos, obj.end_pos]:
                    painter.drawRect(QRect(pt.x() - hw//2, pt.y() - hw//2, hw, hw))
            elif obj.obj_type in ("shape", "text"):
                for corner in [b.topLeft(), b.topRight(), b.bottomLeft(), b.bottomRight()]:
                    painter.drawRect(QRect(corner.x() - hw//2, corner.y() - hw//2, hw, hw))
        
        # Draw Preview Shape while drawing
        if self.is_drawing:
            if self.current_tool == "arrow":
                temp = ArrowObject(self.start_pos, self.end_pos, self.tool_color, self.tool_width, self.arrow_type)
                temp.render(painter)
            elif self.current_tool == "shape":
                temp = ShapeObject(self.start_pos, self.end_pos, self.tool_color, self.tool_width, self.shape_type, self.line_style)
                temp.render(painter)
            elif self.current_tool == "text":
                rect = QRect(self.start_pos, self.end_pos).normalized()
                pen = QPen(self.tool_color, 1, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(QBrush(QColor(self.tool_color.red(), self.tool_color.green(), self.tool_color.blue(), 30)))
                painter.drawRect(rect)
            elif self.current_tool == "pen" and len(self.pen_path) > 1:
                self.render_pen(painter, self.pen_path)
            elif self.current_tool == "blur":
                pen = QPen(QColor("#00a8ff"), 1, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(QBrush(QColor(0, 168, 255, 40)))
                painter.drawRect(QRect(self.start_pos, self.end_pos).normalized())
            elif self.current_tool == "crop":
                rect = QRect(self.start_pos, self.end_pos).normalized()
                pen = QPen(QColor("#ff5252"), 2, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(QBrush(QColor(255, 82, 82, 40)))
                painter.drawRect(rect)
                
        # Always draw canvas border and 8 handles around the image frame
        if not getattr(self, 'is_dragging_object', False):
            W = self.base_image.width()
            H = self.base_image.height()
            is_crop = (self.current_tool == "crop")
            
            pen = QPen(QColor("#00a8ff" if is_crop else "#ffffff"), 1, Qt.PenStyle.SolidLine if is_crop else Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRect(0, 0, W - 1, H - 1))
            
            hw = 10
            handle_color = QColor("#00a8ff" if is_crop else "#ffffff")
            border_color = QColor("#ffffff" if is_crop else "#1e293b")
            painter.setBrush(QBrush(handle_color))
            painter.setPen(QPen(border_color, 1))
            
            handle_rects = [
                QRect(0, 0, hw, hw),
                QRect(W//2 - hw//2, 0, hw, hw),
                QRect(W - hw, 0, hw, hw),
                QRect(W - hw, H//2 - hw//2, hw, hw),
                QRect(W - hw, H - hw, hw, hw),
                QRect(W//2 - hw//2, H - hw, hw, hw),
                QRect(0, H - hw, hw, hw),
                QRect(0, H//2 - hw//2, hw, hw),
            ]
            for r in handle_rects:
                painter.drawRect(r)

        painter.end()

