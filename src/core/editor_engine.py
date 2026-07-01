'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtCore import QRect, QPoint
from PySide6.QtGui import QImage, QPainter, QColor


def calculate_expansion(base_w: int, base_h: int, default_w: int, default_h: int, annotations: list, extra_rect: QRect = None, extra_left: int = 0, extra_top: int = 0):
    """
    Calculates required shift, shrink, and new target dimensions for the canvas based on annotations and bounds.
    Returns:
        tuple: (shift_x, shift_y, shrink_x, shrink_y, target_w, target_h, needs_expand, needs_crop)
    """
    min_x = 0
    min_y = 0
    max_x = default_w
    max_y = default_h
    
    min_ann_x = float('inf')
    min_ann_y = float('inf')
    
    if not annotations and not (extra_rect and extra_rect.isValid()):
        min_ann_x = extra_left
        min_ann_y = extra_top
    else:
        for obj in annotations:
            b = obj.bounds()
            pad = max(4, int(getattr(obj, 'width', 4) * 1.5))
            b = b.adjusted(-pad, -pad, pad, pad)
            if b.left() < min_x:
                min_x = b.left()
            if b.top() < min_y:
                min_y = b.top()
            if b.right() > max_x:
                max_x = b.right()
            if b.bottom() > max_y:
                max_y = b.bottom()
                
            if b.left() < min_ann_x:
                min_ann_x = b.left()
            if b.top() < min_ann_y:
                min_ann_y = b.top()
                
        if extra_rect and extra_rect.isValid():
            if extra_rect.left() < min_x:
                min_x = extra_rect.left()
            if extra_rect.top() < min_y:
                min_y = extra_rect.top()
            if extra_rect.right() > max_x:
                max_x = extra_rect.right()
            if extra_rect.bottom() > max_y:
                max_y = extra_rect.bottom()
            if extra_rect.left() < min_ann_x:
                min_ann_x = extra_rect.left()
            if extra_rect.top() < min_ann_y:
                min_ann_y = extra_rect.top()
            
    if min_ann_x == float('inf'): min_ann_x = 0
    if min_ann_y == float('inf'): min_ann_y = 0
    
    shift_x = -min_x if min_x < 0 else 0
    shift_y = -min_y if min_y < 0 else 0
    
    needs_expand = (shift_x > 0 or shift_y > 0 or max(default_w + shift_x, max_x + shift_x) > base_w or max(default_h + shift_y, max_y + shift_y) > base_h)
    
    if needs_expand:
        target_w = max(default_w + shift_x, max_x + shift_x)
        target_h = max(default_h + shift_y, max_y + shift_y)
        return shift_x, shift_y, 0, 0, target_w, target_h, True, False
    else:
        shrink_x = min(extra_left, max(0, int(min_ann_x))) if extra_left > 0 else 0
        shrink_y = min(extra_top, max(0, int(min_ann_y))) if extra_top > 0 else 0
        
        target_w = max(default_w - shrink_x, max_x - shrink_x)
        target_h = max(default_h - shrink_y, max_y - shrink_y)
        
        needs_crop = (shrink_x > 0 or shrink_y > 0 or target_w < base_w or target_h < base_h)
        return 0, 0, shrink_x, shrink_y, target_w, target_h, False, needs_crop


def apply_canvas_expansion(base_image: QImage, target_w: int, target_h: int, shift_x: int, shift_y: int) -> QImage:
    """
    Creates a new transparent QImage of target dimensions and draws base_image shifted by (shift_x, shift_y).
    """
    new_img = QImage(target_w, target_h, QImage.Format.Format_ARGB32)
    new_img.fill(QColor("transparent"))
    p = QPainter(new_img)
    p.drawImage(shift_x, shift_y, base_image)
    p.end()
    return new_img


def calculate_temporary_size(base_w: int, base_h: int, annotations: list, is_drawing: bool = False, end_pos = None):
    """
    Calculates the temporary widget size needed during live drawing or object dragging.
    """
    w = base_w
    h = base_h
    for obj in annotations:
        b = obj.bounds()
        pad = max(6, int(getattr(obj, 'width', 4) * 2))
        if b.right() + pad > w:
            w = b.right() + pad
        if b.bottom() + pad > h:
            h = b.bottom() + pad
            
    if is_drawing and end_pos:
        if end_pos.x() + 20 > w:
            w = end_pos.x() + 20
        if end_pos.y() + 20 > h:
            h = end_pos.y() + 20
            
    return w, h


def constrain_square(start: QPoint, end: QPoint) -> QPoint:
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    r = max(abs(dx), abs(dy))
    sign_x = 1 if dx >= 0 else -1
    sign_y = 1 if dy >= 0 else -1
    return QPoint(start.x() + r * sign_x, start.y() + r * sign_y)

