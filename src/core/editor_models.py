'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import math
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QFontMetrics


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
    def __init__(self, pos, text, color, font_family="Arial", font_size=24, box_width=0):
        super().__init__("text", color, 1)
        self.pos = QPoint(pos)
        self.text = text
        self.font_family = font_family
        self.font_size = font_size
        self.box_width = box_width

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "pos": [self.pos.x(), self.pos.y()],
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "box_width": getattr(self, 'box_width', 0)
        })
        return d

    @classmethod
    def from_dict(cls, d):
        p = d.get("pos", [0, 0])
        return cls(QPoint(p[0], p[1]), d.get("text", ""), d.get("color", "#ff3333"), d.get("font_family", "Arial"), d.get("font_size", 24), d.get("box_width", 0))

    def bounds(self):
        if getattr(self, 'box_width', 0) > 0:
            fm = QFontMetrics(QFont(self.font_family, self.font_size, QFont.Weight.Bold))
            flags = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap | Qt.TextFlag.TextWrapAnywhere)
            min_char_w = max(16, fm.horizontalAdvance(self.text[0]) if self.text else int(self.font_size * 0.5))
            eff_w = max(min_char_w, self.box_width)
            b = fm.boundingRect(QRect(0, 0, eff_w, 100000), flags, self.text)
            return QRect(self.pos.x(), self.pos.y(), max(min_char_w, eff_w), max(25, b.height() + 10))
        else:
            lines = self.text.split('\n')
            w = max((len(line) for line in lines), default=1) * int(self.font_size * 0.65)
            h = len(lines) * int(self.font_size * 1.3)
            return QRect(self.pos.x(), self.pos.y(), max(40, int(w)), max(25, int(h)))

    def move_by(self, dx, dy):
        self.pos += QPoint(dx, dy)

    def render(self, painter):
        painter.setFont(QFont(self.font_family, self.font_size, QFont.Weight.Bold))
        painter.setPen(QPen(self.color))
        if getattr(self, 'box_width', 0) > 0:
            fm = QFontMetrics(QFont(self.font_family, self.font_size, QFont.Weight.Bold))
            flags = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap | Qt.TextFlag.TextWrapAnywhere)
            min_char_w = max(16, fm.horizontalAdvance(self.text[0]) if self.text else int(self.font_size * 0.5))
            eff_w = max(min_char_w, self.box_width)
            rect = QRect(self.pos.x(), self.pos.y(), eff_w, 100000)
            painter.drawText(rect, flags, self.text)
        else:
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
