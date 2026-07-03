'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QToolBar, QToolButton, QButtonGroup
from PySide6.QtCore import Qt, Signal
from resources.icon_utils import (create_svg_icon, SVG_SELECT, SVG_ARROW, SVG_TEXT, 
                         SVG_SHAPE, SVG_STAMP, SVG_CROP, SVG_BLUR, SVG_PEN, 
                         SVG_STEP, SVG_UNDO, SVG_REDO, SVG_COPY, SVG_SAVE, SVG_TAB_IMAGE)


class EditorToolBar(QToolBar):
    capture_clicked = Signal()
    tool_selected = Signal(str)
    undo_clicked = Signal()
    redo_clicked = Signal()
    copy_clicked = Signal()
    save_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__("Tools", parent)
        self.setMovable(False)
        self.setFloatable(False)
        
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_buttons = {}
        
        self._setup_capture_button()
        self.addSeparator()
        self._setup_tools()
        self.addSeparator()
        self._setup_history_buttons()
        self.addSeparator()
        self._setup_action_buttons()

    def _setup_capture_button(self):
        self.btn_capture = QToolButton()
        self.btn_capture.setText("Capture")
        self.btn_capture.setIcon(create_svg_icon(SVG_TAB_IMAGE, 24, 24))
        self.btn_capture.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.btn_capture.setToolTip("Start a new screen capture")
        self.btn_capture.clicked.connect(self.capture_clicked.emit)
        self.addWidget(self.btn_capture)

    def _setup_tools(self):
        tools = [
            ("select", "Select", SVG_SELECT),
            ("arrow", "Arrow", SVG_ARROW),
            ("text", "Text", SVG_TEXT),
            ("shape", "Shape", SVG_SHAPE),
            ("stamp", "Stamp", SVG_STAMP),
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
                btn.clicked.connect(lambda _, t=tool_id: self.tool_selected.emit(t))
            self.addWidget(btn)
            self.tool_group.addButton(btn)
            self.tool_buttons[tool_id] = btn
            if tool_id == "select":
                btn.setChecked(True)

    def _setup_history_buttons(self):
        self.btn_undo = QToolButton()
        self.btn_undo.setText("Undo")
        self.btn_undo.setIcon(create_svg_icon(SVG_UNDO, 24, 24))
        self.btn_undo.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.btn_undo.clicked.connect(self.undo_clicked.emit)
        self.addWidget(self.btn_undo)
        
        self.btn_redo = QToolButton()
        self.btn_redo.setText("Redo")
        self.btn_redo.setIcon(create_svg_icon(SVG_REDO, 24, 24))
        self.btn_redo.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.btn_redo.clicked.connect(self.redo_clicked.emit)
        self.addWidget(self.btn_redo)

    def update_history_state(self, can_undo: bool, can_redo: bool):
        if hasattr(self, 'btn_undo'):
            self.btn_undo.setEnabled(can_undo)
        if hasattr(self, 'btn_redo'):
            self.btn_redo.setEnabled(can_redo)

    def _setup_action_buttons(self):
        btn_copy = QToolButton()
        btn_copy.setText("Copy")
        btn_copy.setIcon(create_svg_icon(SVG_COPY, 24, 24))
        btn_copy.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn_copy.clicked.connect(self.copy_to_clipboard_triggered)
        self.addWidget(btn_copy)
        
        btn_save = QToolButton()
        btn_save.setText("Save As")
        btn_save.setIcon(create_svg_icon(SVG_SAVE, 24, 24))
        btn_save.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn_save.clicked.connect(self.save_image_triggered)
        self.addWidget(btn_save)

    def copy_to_clipboard_triggered(self):
        self.copy_clicked.emit()

    def save_image_triggered(self):
        self.save_clicked.emit()

    def set_active_tool(self, tool_id: str):
        if tool_id in self.tool_buttons:
            self.tool_buttons[tool_id].setChecked(True)
