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

from ui.icon_utils import (create_svg_icon, SVG_SELECT, SVG_ARROW, SVG_TEXT, SVG_SHAPE, 
                         SVG_STAMP, SVG_CROP, SVG_BLUR, SVG_PEN, SVG_STEP, 
                         SVG_UNDO, SVG_REDO, SVG_SAVE, SVG_COPY, SVG_ZOOM_IN, 
                         SVG_ZOOM_OUT, SVG_CLOSE, SVG_RECENT, SVG_TAG, 
                         SVG_EFFECTS, SVG_PROPERTIES)
from version import EDITOR_VERSION, PROJECT_FILE_VERSION
from ui.toast_notification import ToastNotification


class AnnotationObject:
    def __init__(self, obj_type, color, width):
        self.obj_type = obj_type
        self.color = QColor(color)
        self.width = width

    def clone(self):
        import copy
        c = copy.copy(self)
        if hasattr(self, 'start_pos'): c.start_pos = QPoint(self.start_pos)
        if hasattr(self, 'end_pos'): c.end_pos = QPoint(self.end_pos)
        if hasattr(self, 'pos'): c.pos = QPoint(self.pos)
        if hasattr(self, 'color'): c.color = QColor(self.color)
        return c

    def bounds(self):
        return QRect()

    def hit_test(self, pt, tol=8):
        return self.bounds().adjusted(-tol, -tol, tol, tol).contains(pt)

    def move_by(self, dx, dy):
        pass

    def render(self, painter):
        pass

    def to_dict(self):
        return {"obj_type": self.obj_type, "color": self.color.name(), "width": self.width}

    @staticmethod
    def from_dict(d):
        obj_type = d.get("obj_type")
        if obj_type == "arrow":
            return ArrowObject.from_dict(d)
        elif obj_type == "shape":
            return ShapeObject.from_dict(d)
        elif obj_type == "text":
            return TextObject.from_dict(d)
        elif obj_type == "step":
            return StepObject.from_dict(d)
        return None


class ArrowObject(AnnotationObject):
    def __init__(self, start_pos, end_pos, color, width, arrow_type="Single Arrow"):
        super().__init__("arrow", color, width)
        self.start_pos = QPoint(start_pos)
        self.end_pos = QPoint(end_pos)
        self.arrow_type = arrow_type

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "start_pos": [self.start_pos.x(), self.start_pos.y()],
            "end_pos": [self.end_pos.x(), self.end_pos.y()],
            "arrow_type": self.arrow_type
        })
        return d

    @classmethod
    def from_dict(cls, d):
        sp = d.get("start_pos", [0, 0])
        ep = d.get("end_pos", [0, 0])
        return cls(QPoint(sp[0], sp[1]), QPoint(ep[0], ep[1]), d.get("color", "#ff3333"), d.get("width", 4), d.get("arrow_type", "Single Arrow"))

    def bounds(self):
        return QRect(self.start_pos, self.end_pos).normalized()

    def hit_test(self, pt, tol=8):
        x0, y0 = pt.x(), pt.y()
        x1, y1 = self.start_pos.x(), self.start_pos.y()
        x2, y2 = self.end_pos.x(), self.end_pos.y()
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x0 - x1, y0 - y1) <= tol
        t = ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        px, py = x1 + t * dx, y1 + t * dy
        return math.hypot(x0 - px, y0 - py) <= max(tol, self.width + 4)

    def move_by(self, dx, dy):
        self.start_pos += QPoint(dx, dy)
        self.end_pos += QPoint(dx, dy)

    def render(self, painter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QBrush(self.color))
        painter.drawLine(self.start_pos, self.end_pos)
        if self.arrow_type == "Plain Line":
            return
        self._draw_arrow_head(painter, self.start_pos, self.end_pos)
        if self.arrow_type == "Double Arrow":
            self._draw_arrow_head(painter, self.end_pos, self.start_pos)

    def _draw_arrow_head(self, painter, p1, p2):
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        arrow_len = max(12.0, float(self.width * 3.5))
        arrow_rad = math.radians(28)
        pt1 = QPoint(int(p2.x() - arrow_len * math.cos(angle - arrow_rad)),
                     int(p2.y() - arrow_len * math.sin(angle - arrow_rad)))
        pt2 = QPoint(int(p2.x() - arrow_len * math.cos(angle + arrow_rad)),
                     int(p2.y() - arrow_len * math.sin(angle + arrow_rad)))
        painter.drawPolygon([p2, pt1, pt2])


class ShapeObject(AnnotationObject):
    def __init__(self, start_pos, end_pos, color, width, shape_type="Rectangle", line_style="Solid"):
        super().__init__("shape", color, width)
        self.start_pos = QPoint(start_pos)
        self.end_pos = QPoint(end_pos)
        self.shape_type = shape_type
        self.line_style = line_style

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "start_pos": [self.start_pos.x(), self.start_pos.y()],
            "end_pos": [self.end_pos.x(), self.end_pos.y()],
            "shape_type": self.shape_type,
            "line_style": self.line_style
        })
        return d

    @classmethod
    def from_dict(cls, d):
        sp = d.get("start_pos", [0, 0])
        ep = d.get("end_pos", [0, 0])
        return cls(QPoint(sp[0], sp[1]), QPoint(ep[0], ep[1]), d.get("color", "#ff3333"), d.get("width", 4), d.get("shape_type", "Rectangle"), d.get("line_style", "Solid"))

    def bounds(self):
        dx = self.end_pos.x() - self.start_pos.x()
        dy = self.end_pos.y() - self.start_pos.y()
        if self.shape_type == "Circle":
            r = max(abs(dx), abs(dy))
            return QRect(self.start_pos.x(), self.start_pos.y(), r if dx >= 0 else -r, r if dy >= 0 else -r).normalized()
        return QRect(self.start_pos, self.end_pos).normalized()

    def move_by(self, dx, dy):
        self.start_pos += QPoint(dx, dy)
        self.end_pos += QPoint(dx, dy)

    def render(self, painter):
        style = Qt.PenStyle.DashLine if self.line_style == "Dashed" else Qt.PenStyle.SolidLine
        pen = QPen(self.color, self.width, style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = self.bounds()
        if self.shape_type in ("Circle", "Ellipse"):
            painter.drawEllipse(rect)
        elif self.shape_type in ("Rounded Rectangle", "Rounded Rect"):
            r = max(8.0, min(rect.width(), rect.height()) * 0.18)
            painter.drawRoundedRect(rect, r, r)
        else:
            painter.drawRect(rect)


class TextObject(AnnotationObject):
    def __init__(self, pos, text, color, font_family="Arial", font_size=24):
        super().__init__("text", color, 1)
        self.pos = QPoint(pos)
        self.text = text
        self.font_family = font_family
        self.font_size = font_size

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "pos": [self.pos.x(), self.pos.y()],
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size
        })
        return d

    @classmethod
    def from_dict(cls, d):
        p = d.get("pos", [0, 0])
        return cls(QPoint(p[0], p[1]), d.get("text", ""), d.get("color", "#ff3333"), d.get("font_family", "Arial"), d.get("font_size", 24))

    def bounds(self):
        lines = self.text.split('\n')
        w = max((len(line) for line in lines), default=1) * int(self.font_size * 0.65)
        h = len(lines) * int(self.font_size * 1.3)
        return QRect(self.pos.x(), self.pos.y(), max(40, int(w)), max(25, int(h)))

    def move_by(self, dx, dy):
        self.pos += QPoint(dx, dy)

    def render(self, painter):
        painter.setFont(QFont(self.font_family, self.font_size, QFont.Weight.Bold))
        painter.setPen(QPen(self.color))
        lines = self.text.split('\n')
        for i, line in enumerate(lines):
            y = self.pos.y() + self.font_size + i * int(self.font_size * 1.3)
            painter.drawText(self.pos.x(), y, line)


class StepObject(AnnotationObject):
    def __init__(self, pos, step_num, color, width):
        super().__init__("step", color, width)
        self.pos = QPoint(pos)
        self.step_num = step_num

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "pos": [self.pos.x(), self.pos.y()],
            "step_num": self.step_num
        })
        return d

    @classmethod
    def from_dict(cls, d):
        p = d.get("pos", [0, 0])
        return cls(QPoint(p[0], p[1]), d.get("step_num", 1), d.get("color", "#ff3333"), d.get("width", 4))

    def bounds(self):
        radius = max(14, int(self.width * 2.5))
        return QRect(self.pos.x() - radius, self.pos.y() - radius, radius * 2, radius * 2)

    def move_by(self, dx, dy):
        self.pos += QPoint(dx, dy)

    def render(self, painter):
        radius = max(14, int(self.width * 2.5))
        rect = self.bounds()
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawEllipse(rect)
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont("Arial", int(radius * 0.9), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self.step_num))


def constrain_square(start: QPoint, end: QPoint) -> QPoint:
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    r = max(abs(dx), abs(dy))
    sign_x = 1 if dx >= 0 else -1
    sign_y = 1 if dy >= 0 else -1
    return QPoint(start.x() + r * sign_x, start.y() + r * sign_y)


class ImageCanvas(QWidget):
    zoom_changed = Signal(int)
    step_changed = Signal(int)
    image_changed = Signal()
    new_image_loaded = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_image = QImage(600, 400, QImage.Format.Format_ARGB32)
        self.base_image.fill(QColor("#333333"))
        
        self.annotations = []
        self.selected_annotation = None
        self.active_handle = None
        self.is_dragging_object = False
        
        self.undo_stack = []
        self.redo_stack = []
        
        self.zoom_factor = 1.0
        
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
        self.text_input = QLineEdit(self)
        self.text_input.hide()
        self.text_input.returnPressed.connect(self.commit_text)
        self.text_input.editingFinished.connect(self.commit_text)
        
        self.current_filepath = None
        self.setMouseTracking(True)
        self.update_canvas_size()

    def trigger_auto_save(self):
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
                "version": PROJECT_FILE_VERSION,
                "timestamp": time.strftime("%Y%m%d_%H%M%S"),
                "image_base64": img_b64,
                "thumbnail_base64": thumb_b64,
                "annotations": [obj.to_dict() for obj in self.annotations]
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            win = self.window()
            if hasattr(win, 'refresh_library_strip'):
                win.refresh_library_strip()
        except Exception as e:
            print(f"Error auto-saving scut project: {e}")

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
            self.update()
        except Exception as e:
            print(f"Error loading scut project: {e}")

    def set_image(self, img: QImage):
        self.base_image = img.convertToFormat(QImage.Format.Format_ARGB32)
        self.annotations = []
        self.selected_annotation = None
        self.undo_stack = []
        self.redo_stack = []
        self.update_canvas_size()
        self.show()
        self.image_changed.emit()
        self.new_image_loaded.emit()
        self.update()

    def clear_canvas(self):
        self.base_image = QImage(1, 1, QImage.Format.Format_ARGB32)
        self.base_image.fill(QColor("transparent"))
        self.annotations = []
        self.selected_annotation = None
        self.undo_stack = []
        self.redo_stack = []
        self.current_filepath = None
        self.update_canvas_size()
        self.hide()
        self.image_changed.emit()
        self.new_image_loaded.emit()
        self.update()

    def push_undo(self):
        self.undo_stack.append((self.base_image.copy(), [obj.clone() for obj in self.annotations]))
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append((self.base_image.copy(), [obj.clone() for obj in self.annotations]))
        base_img, annots = self.undo_stack.pop()
        self.base_image = base_img
        self.annotations = annots
        self.selected_annotation = None
        self.update_canvas_size()
        self.image_changed.emit()
        self.update()
        self.trigger_auto_save()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append((self.base_image.copy(), [obj.clone() for obj in self.annotations]))
        base_img, annots = self.redo_stack.pop()
        self.base_image = base_img
        self.annotations = annots
        self.selected_annotation = None
        self.update_canvas_size()
        self.image_changed.emit()
        self.update()
        self.trigger_auto_save()

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
        self.update_canvas_size()
        self.image_changed.emit()
        self.update()
        self.trigger_auto_save()

    def resize_image(self, new_w, new_h):
        if new_w <= 0 or new_h <= 0:
            return
        self.push_undo()
        self.base_image = self.base_image.scaled(new_w, new_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.update_canvas_size()
        self.image_changed.emit()
        self.update()
        self.trigger_auto_save()

    # -------------------------------------------------------------------------
    # Mouse Events
    # -------------------------------------------------------------------------
    def delete_selected(self):
        if self.selected_annotation in self.annotations:
            self.push_undo()
            self.annotations.remove(self.selected_annotation)
            self.selected_annotation = None
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
        elif obj.obj_type == "shape":
            b = obj.bounds()
            for name, corner in [("tl", b.topLeft()), ("tr", b.topRight()), ("bl", b.bottomLeft()), ("br", b.bottomRight())]:
                if (pt - corner).manhattanLength() <= 12:
                    return name
        return None

    def mousePressEvent(self, event):
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
        
        if self.current_tool == "text":
            self.show_text_input(event.pos())
            return
            
        if self.current_tool == "step":
            self.push_undo()
            step_obj = StepObject(self.start_pos, self.step_counter, self.tool_color, self.tool_width)
            self.annotations.append(step_obj)
            self.selected_annotation = step_obj
            self.step_counter += 1
            self.step_changed.emit(self.step_counter)
            self.is_drawing = False
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
        
        if getattr(self, 'is_dragging_object', False) and self.selected_annotation:
            dx = pt.x() - self.drag_last_pos.x()
            dy = pt.y() - self.drag_last_pos.y()
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
            self.drag_last_pos = pt
            self.update()
            return

        if not self.is_drawing:
            return
        self.end_pos = pt
        if self.current_tool == "shape" and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.end_pos = constrain_square(self.start_pos, self.end_pos)
        if self.current_tool == "pen":
            self.pen_path.append(self.end_pos)
        self.update()

    def mouseReleaseEvent(self, event):
        if getattr(self, 'is_dragging_object', False):
            self.is_dragging_object = False
            self.active_handle = None
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
                win = self.window()
                if hasattr(win, 'props_panel'):
                    win.props_panel.sync_from_selected()
                
        elif self.current_tool == "shape":
            if (self.end_pos - self.start_pos).manhattanLength() > 5:
                self.push_undo()
                obj = ShapeObject(self.start_pos, self.end_pos, self.tool_color, self.tool_width, self.shape_type, self.line_style)
                self.annotations.append(obj)
                self.selected_annotation = obj
                win = self.window()
                if hasattr(win, 'props_panel'):
                    win.props_panel.sync_from_selected()
                
        elif self.current_tool == "pen":
            if len(self.pen_path) > 1:
                self.push_undo()
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
            
        self.update()
        self.trigger_auto_save()

    # -------------------------------------------------------------------------
    # Text Input Helper
    # -------------------------------------------------------------------------
    def show_text_input(self, widget_pos):
        self.text_input.setFont(QFont(self.font_family, int(self.font_size * self.zoom_factor)))
        self.text_input.setStyleSheet(f"color: {self.tool_color.name()}; background: rgba(0,0,0,150); border: 1px solid white; padding: 2px;")
        self.text_input.setText("")
        self.text_input.move(widget_pos)
        self.text_input.resize(200, int(self.font_size * self.zoom_factor * 1.8))
        self.text_input.show()
        self.text_input.setFocus()

    def commit_text(self):
        text = self.text_input.text().strip()
        if text and self.text_input.isVisible():
            self.push_undo()
            obj = TextObject(self.start_pos, text, self.tool_color, self.font_family, self.font_size)
            self.annotations.append(obj)
            self.selected_annotation = obj
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
            elif obj.obj_type == "shape":
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
                
        painter.end()


class ToolPropertiesPanel(QFrame):
    def __init__(self, canvas: ImageCanvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setFixedWidth(240)
        self.setStyleSheet("""
            QFrame { background-color: #252525; border-left: 1px solid #3c3c3c; color: #ffffff; }
            QLabel { color: #dddddd; font-size: 13px; font-weight: bold; }
            QSlider::groove:horizontal { height: 6px; background: #3c3c3c; border-radius: 3px; }
            QSlider::handle:horizontal { width: 14px; margin: -4px 0; background: #246bb2; border-radius: 7px; }
            QComboBox, QFontComboBox, QSpinBox { background: #333333; border: 1px solid #555555; border-radius: 4px; padding: 4px; color: white; }
            QPushButton { background: #333333; border: 1px solid #555555; border-radius: 4px; padding: 6px; color: white; font-weight: bold; }
            QPushButton:hover { background: #444444; border-color: #246bb2; }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 20, 15, 20)
        self.layout.setSpacing(15)
        
        self.lbl_title = QLabel("Tool Properties")
        self.lbl_title.setStyleSheet("font-size: 16px; color: #246bb2; border-bottom: 1px solid #3c3c3c; padding-bottom: 8px;")
        self.layout.addWidget(self.lbl_title)
        
        # Dynamic property container
        self.prop_container = QVBoxLayout()
        self.prop_container.setSpacing(12)
        self.layout.addLayout(self.prop_container)
        
        # Quick Styles Section
        self.layout.addSpacing(10)
        lbl_quick = QLabel("Quick Styles")
        self.layout.addWidget(lbl_quick)
        
        quick_grid = QHBoxLayout()
        presets = [("#ff3333", 4), ("#ffcc00", 6), ("#33cc33", 4), ("#3399ff", 4), ("#ffffff", 3)]
        for color_hex, w in presets:
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            btn.setStyleSheet(f"background-color: {color_hex}; border-radius: 16px; border: 2px solid #555;")
            btn.clicked.connect(lambda _, c=color_hex, width=w: self.apply_quick_style(c, width))
            quick_grid.addWidget(btn)
        self.layout.addLayout(quick_grid)
        
        self.layout.addStretch()
        self.update_properties()

    def apply_quick_style(self, color_hex, width):
        self.set_tool_color(QColor(color_hex))
        self.set_tool_width(width)

    def set_tool_color(self, c: QColor):
        self.canvas.tool_color = c
        if self.canvas.selected_annotation:
            self.canvas.push_undo()
            self.canvas.selected_annotation.color = c
            self.canvas.update()
            self.canvas.trigger_auto_save()
        self.update_properties()

    def set_tool_width(self, w: int):
        self.canvas.tool_width = w
        if self.canvas.selected_annotation:
            self.canvas.push_undo()
            self.canvas.selected_annotation.width = w
            self.canvas.update()
            self.canvas.trigger_auto_save()

    def set_attr(self, name, val):
        setattr(self.canvas, name, val)
        if self.canvas.selected_annotation and hasattr(self.canvas.selected_annotation, name):
            self.canvas.push_undo()
            setattr(self.canvas.selected_annotation, name, val)
            self.canvas.update()
            self.canvas.trigger_auto_save()

    def sync_from_selected(self):
        obj = getattr(self.canvas, 'selected_annotation', None)
        if obj:
            if hasattr(obj, 'color'): self.canvas.tool_color = QColor(obj.color)
            if hasattr(obj, 'width'): self.canvas.tool_width = obj.width
            if hasattr(obj, 'arrow_type'): self.canvas.arrow_type = obj.arrow_type
            if hasattr(obj, 'shape_type'): self.canvas.shape_type = obj.shape_type
            if hasattr(obj, 'line_style'): self.canvas.line_style = obj.line_style
            if hasattr(obj, 'font_family'): self.canvas.font_family = obj.font_family
            if hasattr(obj, 'font_size'): self.canvas.font_size = obj.font_size
        self.update_properties()

    def clear_container(self):
        while self.prop_container.count():
            item = self.prop_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def update_properties(self):
        self.clear_container()
        tool = self.canvas.current_tool
        obj = getattr(self.canvas, 'selected_annotation', None)
        active_tool = obj.obj_type if (tool == "select" and obj) else tool
        
        self.lbl_title.setText(f"{active_tool.capitalize()} Properties")
        
        if active_tool not in ["crop", "blur", "select"]:
            row_color = QHBoxLayout()
            lbl_c = QLabel("Color:")
            btn_color = QPushButton()
            btn_color.setFixedSize(40, 24)
            btn_color.setStyleSheet(f"background-color: {self.canvas.tool_color.name()}; border: 1px solid white;")
            btn_color.clicked.connect(self.pick_color)
            row_color.addWidget(lbl_c)
            row_color.addWidget(btn_color)
            row_color.addStretch()
            self.prop_container.addLayout(row_color)
            
        if active_tool == "arrow":
            lbl_type = QLabel("Arrow Type:")
            cb_type = QComboBox()
            cb_type.addItems(["Single Arrow", "Double Arrow", "Plain Line"])
            cb_type.setCurrentText(self.canvas.arrow_type)
            cb_type.currentTextChanged.connect(lambda t: self.set_attr('arrow_type', t))
            self.prop_container.addWidget(lbl_type)
            self.prop_container.addWidget(cb_type)
            self._add_width_slider("Line Thickness:", 1, 24, self.canvas.tool_width, lambda v: self.set_tool_width(v))
            
        elif active_tool == "text":
            lbl_font = QLabel("Font Family:")
            cb_font = QFontComboBox()
            cb_font.setCurrentFont(QFont(self.canvas.font_family))
            cb_font.currentFontChanged.connect(lambda f: self.set_attr('font_family', f.family()))
            self.prop_container.addWidget(lbl_font)
            self.prop_container.addWidget(cb_font)
            self._add_width_slider("Font Size:", 12, 72, self.canvas.font_size, lambda v: self.set_attr('font_size', v))
            
        elif active_tool == "shape":
            lbl_stype = QLabel("Shape Type:")
            cb_stype = QComboBox()
            cb_stype.addItems(["Rectangle", "Rounded Rectangle", "Ellipse"])
            cb_stype.setCurrentText(self.canvas.shape_type)
            cb_stype.currentTextChanged.connect(lambda t: self.set_attr('shape_type', t))
            self.prop_container.addWidget(lbl_stype)
            self.prop_container.addWidget(cb_stype)
            
            lbl_lstyle = QLabel("Line Style:")
            cb_lstyle = QComboBox()
            cb_lstyle.addItems(["Solid", "Dashed"])
            cb_lstyle.setCurrentText(self.canvas.line_style)
            cb_lstyle.currentTextChanged.connect(lambda t: self.set_attr('line_style', t))
            self.prop_container.addWidget(lbl_lstyle)
            self.prop_container.addWidget(cb_lstyle)
            self._add_width_slider("Border Width:", 1, 20, self.canvas.tool_width, lambda v: self.set_tool_width(v))
            
        elif active_tool == "blur":
            lbl_btype = QLabel("Blur Effect:")
            cb_btype = QComboBox()
            cb_btype.addItems(["Mosaic", "Gaussian Blur"])
            cb_btype.setCurrentText(self.canvas.blur_type)
            cb_btype.currentTextChanged.connect(lambda t: self.set_attr('blur_type', t))
            self.prop_container.addWidget(lbl_btype)
            self.prop_container.addWidget(cb_btype)
            self._add_width_slider("Intensity / Block Size:", 3, 51, self.canvas.blur_intensity, lambda v: self.set_attr('blur_intensity', v))
            
        elif active_tool == "pen":
            lbl_pstyle = QLabel("Pen Mode:")
            cb_pstyle = QComboBox()
            cb_pstyle.addItems(["Solid Pen", "Highlighter"])
            cb_pstyle.setCurrentText(self.canvas.pen_style)
            cb_pstyle.currentTextChanged.connect(lambda t: self.set_attr('pen_style', t))
            self.prop_container.addWidget(lbl_pstyle)
            self.prop_container.addWidget(cb_pstyle)
            self._add_width_slider("Pen Thickness:", 2, 30, self.canvas.tool_width, lambda v: self.set_tool_width(v))
            
        elif active_tool == "step":
            self._add_width_slider("Sticker Size:", 3, 12, self.canvas.tool_width, lambda v: self.set_tool_width(v))
            btn_reset = QPushButton("Reset Step Counter (①)")
            btn_reset.clicked.connect(self.canvas.reset_step)
            self.prop_container.addWidget(btn_reset)

    def _add_width_slider(self, label_text, min_val, max_val, current_val, callback):
        lbl = QLabel(f"{label_text} ({current_val})")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(current_val)
        def on_change(val):
            lbl.setText(f"{label_text} ({val})")
            callback(val)
        slider.valueChanged.connect(on_change)
        self.prop_container.addWidget(lbl)
        self.prop_container.addWidget(slider)

    def pick_color(self):
        c = QColorDialog.getColor(self.canvas.tool_color, self, "Select Tool Color")
        if c.isValid():
            self.set_tool_color(c)


class ResizePopup(QWidget):
    def __init__(self, editor_window, parent=None):
        super().__init__(parent)
        self.editor_win = editor_window
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        bg = QWidget()
        bg.setStyleSheet("""
            QWidget {
                background-color: #1e293b; 
                border: 1px solid #475569; 
                border-radius: 6px;
            }
            QLabel { color: #f1f5f9; font-size: 13px; font-weight: bold; border: none; }
            QSpinBox { background-color: #334155; border: 1px solid #64748b; border-radius: 4px; padding: 4px 6px; color: white; font-size: 13px; }
            QCheckBox { color: #cbd5e1; font-size: 13px; border: none; }
            QPushButton { background-color: #3b82f6; border: none; border-radius: 4px; padding: 6px 14px; color: white; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #2563eb; }
        """)
        bg_layout = QVBoxLayout(bg)
        bg_layout.setContentsMargins(12, 12, 12, 12)
        bg_layout.setSpacing(10)
        
        # Title
        title_lbl = QLabel("Resize Image")
        title_lbl.setStyleSheet("font-size: 14px; color: #38bdf8; margin-bottom: 2px; border: none;")
        bg_layout.addWidget(title_lbl)
        
        # Width Row
        w_row = QHBoxLayout()
        w_row.addWidget(QLabel("Width:"))
        from PySide6.QtWidgets import QSpinBox, QCheckBox
        self.w_spin = QSpinBox()
        self.w_spin.setRange(10, 10000)
        self.w_spin.setValue(self.editor_win.canvas.base_image.width())
        self.w_spin.setFixedWidth(90)
        w_row.addStretch()
        w_row.addWidget(self.w_spin)
        bg_layout.addLayout(w_row)
        
        # Height Row
        h_row = QHBoxLayout()
        h_row.addWidget(QLabel("Height:"))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(10, 10000)
        self.h_spin.setValue(self.editor_win.canvas.base_image.height())
        self.h_spin.setFixedWidth(90)
        h_row.addStretch()
        h_row.addWidget(self.h_spin)
        bg_layout.addLayout(h_row)
        
        # Aspect Ratio Checkbox
        self.ratio = self.editor_win.canvas.base_image.width() / max(1, self.editor_win.canvas.base_image.height())
        self.chk_ratio = QCheckBox("Keep Aspect Ratio")
        self.chk_ratio.setChecked(True)
        bg_layout.addWidget(self.chk_ratio)
        
        def on_w_change(val):
            if self.chk_ratio.isChecked():
                self.h_spin.blockSignals(True)
                self.h_spin.setValue(max(1, int(val / self.ratio)))
                self.h_spin.blockSignals(False)
                
        def on_h_change(val):
            if self.chk_ratio.isChecked():
                self.w_spin.blockSignals(True)
                self.w_spin.setValue(max(1, int(val * self.ratio)))
                self.w_spin.blockSignals(False)
                
        self.w_spin.valueChanged.connect(on_w_change)
        self.h_spin.valueChanged.connect(on_h_change)
        
        # Apply Button
        btn_apply = QPushButton("Apply Resize")
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.clicked.connect(self.apply_and_close)
        bg_layout.addWidget(btn_apply)
        
        layout.addWidget(bg)
        self.setFixedSize(210, 200)
        
    def apply_and_close(self):
        self.editor_win.canvas.resize_image(self.w_spin.value(), self.h_spin.value())
        self.close()


class DeleteConfirmPopup(QWidget):
    def __init__(self, editor_window, filepath, target_widget=None, parent=None):
        super().__init__(parent)
        self.editor_win = editor_window
        self.filepath = filepath
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        bg = QWidget()
        bg.setStyleSheet("""
            QWidget {
                background-color: #1e293b; 
                border: 1px solid #ef4444; 
                border-radius: 6px;
            }
            QLabel { color: #f1f5f9; font-size: 13px; font-weight: bold; border: none; }
            QPushButton { border: none; border-radius: 4px; padding: 5px 12px; font-weight: bold; font-size: 12px; }
        """)
        bg_layout = QVBoxLayout(bg)
        bg_layout.setContentsMargins(12, 12, 12, 12)
        bg_layout.setSpacing(10)
        
        # Title
        title_lbl = QLabel("Delete Project?")
        title_lbl.setStyleSheet("font-size: 14px; color: #ef4444; margin-bottom: 2px; border: none;")
        bg_layout.addWidget(title_lbl)
        
        # Filename
        fname_lbl = QLabel(os.path.basename(filepath))
        fname_lbl.setStyleSheet("font-size: 12px; color: #cbd5e1; font-weight: normal; border: none;")
        bg_layout.addWidget(fname_lbl)
        
        # Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("QPushButton { background-color: #334155; color: white; } QPushButton:hover { background-color: #475569; }")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.close)
        
        btn_delete = QPushButton("Delete")
        btn_delete.setStyleSheet("QPushButton { background-color: #ef4444; color: white; } QPushButton:hover { background-color: #dc2626; }")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.clicked.connect(self.confirm_delete)
        
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_delete)
        bg_layout.addLayout(btn_row)
        
        layout.addWidget(bg)
        self.setFixedSize(180, 115)
        
        if target_widget:
            pos = target_widget.mapToGlobal(target_widget.rect().topLeft())
            self.move(pos.x() - 80, pos.y() - self.height() - 6)
            
    def confirm_delete(self):
        is_current = (self.editor_win.current_image_path == self.filepath)
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
        except Exception:
            pass
        if is_current:
            self.editor_win.current_image_path = None
        self.close()
        self.editor_win.refresh_library_strip()
        if is_current and self.editor_win.thumb_buttons:
            latest_fp, _ = self.editor_win.thumb_buttons[0]
            self.editor_win.load_image_from_path(latest_fp)


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
        
        from PySide6.QtWidgets import QToolButton
        self.btn = QToolButton(self)
        self.btn.setGeometry(0, 0, 100, 62)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setToolTip(os.path.basename(filepath))
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


class ImageEditorWindow(QMainWindow):
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
        from ui.icon_utils import apply_dark_titlebar
        apply_dark_titlebar(self)
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
        super().__init__(parent)
        from ui.icon_utils import apply_dark_titlebar
        apply_dark_titlebar(self)
        self.library_dir = library_dir
        self.setWindowTitle(f"ScreenCut Image Editor v{EDITOR_VERSION}")
        self.resize(1080, 720)
        self.is_auto_fit = True
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QToolBar { background-color: #2b2b2b; border-bottom: 1px solid #3c3c3c; spacing: 6px; padding: 4px; }
            QToolButton { background: transparent; color: #cccccc; border-radius: 6px; padding: 4px 8px; font-weight: 600; font-size: 12px; }
            QToolButton:hover { background: #3d3d3d; color: white; }
            QToolButton:checked { background: #246bb2; color: white; }
            QToolButton:disabled { color: #666666; }
            QScrollArea { background-color: #141414; border: none; }
        """)
        
        self.current_image_path = current_filepath
        self.thumb_buttons = []
        
        # Central Canvas Area inside ScrollArea
        self.canvas = ImageCanvas()
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
            
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.scroll_area)
        
        # Right Dock Panel
        self.props_panel = ToolPropertiesPanel(self.canvas)
        from PySide6.QtWidgets import QDockWidget
        self.props_dock = QDockWidget("Properties", self)
        self.props_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.props_dock.setTitleBarWidget(QWidget()) # Hide dock titlebar
        self.props_dock.setWidget(self.props_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.props_dock)
        
        # Setup Top Toolbar
        self._setup_toolbar()
        
        # Setup Bottom Bar
        self._setup_bottom_bar()
        self.canvas.image_changed.connect(self.update_resolution_label)
        
        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Z"), self, self.canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.canvas.redo)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_to_clipboard)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_image)
        QShortcut(QKeySequence("Del"), self, self.canvas.delete_selected)
        QShortcut(QKeySequence("Backspace"), self, self.canvas.delete_selected)
        QShortcut(QKeySequence("Esc"), self, self.close)

    def _setup_toolbar(self):
        toolbar = self.addToolBar("Tools")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        
        tools = [
            ("select", "Select", SVG_SELECT),
            ("arrow", "Arrow", SVG_ARROW),
            ("text", "Text", SVG_TEXT),
            ("shape", "Shape", SVG_SHAPE),
            ("stamp", "Stamp (TBD)", SVG_STAMP),
            ("crop", "Crop", SVG_CROP),
            ("blur", "Blur", SVG_BLUR),
            ("pen", "Pen", SVG_PEN),
            ("step", "Step", SVG_STEP),
        ]
        
        for tool_id, label, svg in tools:
            btn = QToolButton()
            btn.setText(label)
            btn.setIcon(create_svg_icon(svg, 24, 24))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setCheckable(True)
            if tool_id == "stamp":
                btn.setEnabled(False)
                btn.setToolTip("Stamp tool coming soon")
            else:
                btn.clicked.connect(lambda _, t=tool_id: self.select_tool(t))
            toolbar.addWidget(btn)
            self.tool_group.addButton(btn)
            if tool_id == "select":
                btn.setChecked(True)
                
        toolbar.addSeparator()
        
        # Undo / Redo buttons
        btn_undo = QToolButton()
        btn_undo.setText("Undo")
        btn_undo.setIcon(create_svg_icon(SVG_UNDO, 24, 24))
        btn_undo.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn_undo.clicked.connect(self.canvas.undo)
        toolbar.addWidget(btn_undo)
        
        btn_redo = QToolButton()
        btn_redo.setText("Redo")
        btn_redo.setIcon(create_svg_icon(SVG_REDO, 24, 24))
        btn_redo.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn_redo.clicked.connect(self.canvas.redo)
        toolbar.addWidget(btn_redo)
        
        toolbar.addSeparator()
        
        # Save & Copy buttons
        btn_copy = QToolButton()
        btn_copy.setText("Copy")
        btn_copy.setIcon(create_svg_icon(SVG_COPY, 24, 24))
        btn_copy.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn_copy.clicked.connect(self.copy_to_clipboard)
        toolbar.addWidget(btn_copy)
        
        btn_save = QToolButton()
        btn_save.setText("Save As")
        btn_save.setIcon(create_svg_icon(SVG_SAVE, 24, 24))
        btn_save.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn_save.clicked.connect(self.save_image)
        toolbar.addWidget(btn_save)

    def _setup_bottom_bar(self):
        bottom_container = QFrame()
        bottom_container.setStyleSheet("QFrame { background-color: #0f172a; border-top: 1px solid #1e293b; color: white; }")
        main_bottom_layout = QVBoxLayout(bottom_container)
        main_bottom_layout.setContentsMargins(0, 0, 0, 0)
        main_bottom_layout.setSpacing(0)
        
        # Row 1: Upper Control Bar
        upper_bar = QFrame()
        upper_bar.setFixedHeight(32)
        upper_bar.setStyleSheet("QFrame { background-color: #1a202c; border-bottom: 1px solid #111827; }")
        row1 = QHBoxLayout(upper_bar)
        row1.setContentsMargins(16, 0, 16, 0)
        row1.setSpacing(10)
        
        self.btn_toggle_recent = QPushButton(" Hide Recent")
        self.btn_toggle_recent.setIcon(create_svg_icon(SVG_RECENT, 16, 16))
        self.btn_toggle_recent.setStyleSheet("QPushButton { background: transparent; border: none; color: #cbd5e1; font-size: 13px; font-weight: 600; } QPushButton:hover { color: #60a5fa; }")
        self.btn_toggle_recent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_recent.clicked.connect(self.toggle_recent_strip)
        row1.addWidget(self.btn_toggle_recent)
        
        row1.addStretch()
        
        # Zoom Menu Button
        self.btn_zoom = QPushButton()
        self.update_zoom_label()
        self.btn_zoom.setStyleSheet("QPushButton { background: #2d3748; border: 1px solid #4a5568; border-radius: 4px; padding: 2px 10px; color: #f7fafc; font-size: 12px; font-weight: bold; } QPushButton:hover { border-color: #60a5fa; }")
        self.btn_zoom.setCursor(Qt.CursorShape.PointingHandCursor)
        from PySide6.QtWidgets import QMenu
        zoom_menu = QMenu(self)
        zoom_menu.setStyleSheet("QMenu { background-color: #2d3748; color: white; border: 1px solid #4a5568; } QMenu::item:selected { background-color: #3b82f6; }")
        auto_action = zoom_menu.addAction("Auto Fit")
        auto_action.triggered.connect(self.auto_fit_image)
        zoom_menu.addSeparator()
        for z_val in [0.5, 0.8, 1.0, 1.5, 2.0]:
            action = zoom_menu.addAction(f"{int(z_val*100)}%")
            action.triggered.connect(lambda _, z=z_val: self.manual_set_zoom(z))
        self.btn_zoom.setMenu(zoom_menu)
        self.canvas.zoom_changed.connect(lambda _: self.update_zoom_label())
        row1.addWidget(self.btn_zoom)
        
        # Resolution Button
        self.btn_resize = QPushButton()
        self.update_resolution_label()
        self.btn_resize.setStyleSheet("QPushButton { background: #2d3748; border: 1px solid #4a5568; border-radius: 4px; padding: 2px 10px; color: #f7fafc; font-size: 12px; font-weight: bold; } QPushButton:hover { border-color: #60a5fa; }")
        self.btn_resize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_resize.clicked.connect(self.show_resize_dialog)
        row1.addWidget(self.btn_resize)
        
        main_bottom_layout.addWidget(upper_bar)
        
        # Row 2: Lower Thumbnail Strip
        self.recent_strip_container = QFrame()
        self.recent_strip_container.setFixedHeight(72)
        self.recent_strip_container.setStyleSheet("QFrame { background-color: #0f172a; }")
        row2 = QHBoxLayout(self.recent_strip_container)
        row2.setContentsMargins(12, 4, 12, 4)
        row2.setSpacing(8)
        
        self.lib_scroll = HorizontalScrollArea()
        self.lib_scroll.setWidgetResizable(True)
        self.lib_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lib_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.lib_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:horizontal { height: 6px; background: #1e293b; } QScrollBar::handle:horizontal { background: #475569; border-radius: 3px; }")
        
        lib_widget = QWidget()
        lib_widget.setStyleSheet("background: transparent;")
        self.lib_layout = QHBoxLayout(lib_widget)
        self.lib_layout.setContentsMargins(0, 0, 0, 0)
        self.lib_layout.setSpacing(8)
        self.lib_scroll.setWidget(lib_widget)
        row2.addWidget(self.lib_scroll, stretch=1)
        
        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedSize(28, 62)
        btn_refresh.setToolTip("Refresh Recent Thumbnails")
        btn_refresh.setStyleSheet("QPushButton { background: #1e293b; border: 1px solid #334155; border-radius: 4px; font-size: 13px; } QPushButton:hover { border-color: #3b82f6; }")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_library_strip)
        row2.addWidget(btn_refresh)
        
        main_bottom_layout.addWidget(self.recent_strip_container)
        
        self.setStatusBar(None)
        
        from PySide6.QtWidgets import QDockWidget
        self.bottom_dock = QDockWidget("BottomBar", self)
        self.bottom_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.bottom_dock.setTitleBarWidget(QWidget())
        self.bottom_dock.setWidget(bottom_container)
        
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_dock)
        
        # Populate library thumbnails
        self.refresh_library_strip()

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
            except Exception:
                pass
                
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
        toast = ToastNotification("Image copied to clipboard!", self)
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
            toast = ToastNotification(f"Saved & copied:\n{os.path.basename(path)}", self)
            toast.show_toast()
            self.refresh_library_strip()
