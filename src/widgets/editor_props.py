'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from typing import TYPE_CHECKING
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QComboBox, QFontComboBox, QColorDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

if TYPE_CHECKING:
    from widgets.editor_canvas import ImageCanvas


class ToolPropertiesPanel(QFrame):
    def __init__(self, canvas: 'ImageCanvas', parent=None):
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

    def _apply_live_changes(self):
        text_input = getattr(self.canvas, 'text_input', None)
        if text_input and text_input.isVisible():
            font = QFont(self.canvas.font_family, max(8, int(self.canvas.font_size * self.canvas.zoom_factor)), QFont.Weight.Bold)
            text_input.setFont(font)
            text_input.setStyleSheet(f"color: {self.canvas.tool_color.name()}; background: rgba(0,0,0,180); border: 1px dashed {self.canvas.tool_color.name()}; padding: 2px;")
            text_input._auto_resize()
            
        target_objs = set()
        if getattr(self.canvas, 'selected_annotation', None):
            target_objs.add(self.canvas.selected_annotation)
        if getattr(self.canvas, 'editing_text_object', None):
            target_objs.add(self.canvas.editing_text_object)
            
        if target_objs:
            for obj in target_objs:
                if hasattr(obj, 'color'): obj.color = self.canvas.tool_color
                if hasattr(obj, 'width'): obj.width = self.canvas.tool_width
                if hasattr(obj, 'font_family'): obj.font_family = self.canvas.font_family
                if hasattr(obj, 'font_size'): obj.font_size = self.canvas.font_size
            self.canvas.update()
            self.canvas.trigger_auto_save()

    def set_tool_color(self, c: QColor):
        self.canvas.tool_color = c
        self._apply_live_changes()
        self.update_properties()

    def set_tool_width(self, w: int):
        self.canvas.tool_width = w
        self._apply_live_changes()

    def set_attr(self, name, val):
        setattr(self.canvas, name, val)
        self._apply_live_changes()

    def sync_from_selected(self):
        obj = getattr(self.canvas, 'selected_annotation', None) or getattr(self.canvas, 'editing_text_object', None)
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
        obj = getattr(self.canvas, 'selected_annotation', None) or getattr(self.canvas, 'editing_text_object', None)
        active_tool = obj.obj_type if (tool == "select" and obj) else tool
        if getattr(self.canvas, 'text_input', None) and self.canvas.text_input.isVisible():
            active_tool = "text"
        
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
            
        elif active_tool in ("crop", "select"):
            lbl_info = QLabel("Canvas Resize / Crop\n\n• Drag any of the 8 handles around the image border to crop or expand.\n• Expanding beyond image bounds adds a transparent checkerboard background.\n• When an object is moved or placed outside the image boundary, the canvas automatically expands.")
            lbl_info.setWordWrap(True)
            lbl_info.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: normal; line-height: 1.4;")
            self.prop_container.addWidget(lbl_info)

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
