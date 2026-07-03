'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import os
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QScrollArea, QDockWidget, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from resources.icon_utils import create_svg_icon, SVG_RECENT, apply_dark_titlebar
from version import EDITOR_VERSION
from widgets.editor_toolbar import EditorToolBar

# Re-export core annotation models and canvas engines for backward compatibility
from core.editor_models import (
    AnnotationObject, ArrowObject, ShapeObject, TextObject, StepObject
)
from core.editor_engine import constrain_square

# Re-export extracted widgets for backward compatibility
from widgets.editor_text import CanvasTextEdit
from widgets.editor_canvas import ImageCanvas, CanvasScrollArea
from widgets.editor_props import ToolPropertiesPanel
from widgets.editor_thumbs import HorizontalScrollArea, ThumbnailWidget
from widgets.editor_popups import ResizePopup, DeleteConfirmPopup


class ImageEditorUI(QMainWindow):
    def __init__(self, library_dir: str, initial_image: QImage = None, current_filepath: str = None, parent=None):
        super().__init__(parent)
        apply_dark_titlebar(self)
        self.library_dir = library_dir
        self.setWindowTitle(f"ScreenCut Image Editor v{EDITOR_VERSION}")
        self.resize(1080, 720)
        self.is_auto_fit = True
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QToolTip { background-color: #1e293b; color: #f8fafc; border: 1px solid #475569; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
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
        self.scroll_area = CanvasScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.scroll_area)
        
        # Right Dock Panel
        self.props_panel = ToolPropertiesPanel(self.canvas)
        self.props_dock = QDockWidget("Properties", self)
        self.props_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.props_dock.setTitleBarWidget(QWidget()) # Hide dock titlebar
        self.props_dock.setWidget(self.props_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.props_dock)
        
        # Setup Top Toolbar
        self._setup_toolbar()
        
        # Setup Bottom Bar
        self._setup_bottom_bar()

    def _setup_toolbar(self):
        self.toolbar = EditorToolBar(self)
        self.addToolBar(self.toolbar)
        self.tool_group = self.toolbar.tool_group
        self.toolbar.capture_clicked.connect(self.start_new_capture)
        self.toolbar.tool_selected.connect(self.select_tool)
        self.toolbar.undo_clicked.connect(self.canvas.undo)
        self.toolbar.redo_clicked.connect(self.canvas.redo)
        self.canvas.undo_state_changed.connect(self.toolbar.update_history_state)
        self.toolbar.copy_clicked.connect(self.copy_to_clipboard)
        self.toolbar.save_clicked.connect(self.save_image)
        self.canvas._emit_undo_state()

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
        
        self.bottom_dock = QDockWidget("BottomBar", self)
        self.bottom_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.bottom_dock.setTitleBarWidget(QWidget())
        self.bottom_dock.setWidget(bottom_container)
        
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_dock)
        
        # Populate library thumbnails
        self.refresh_library_strip()

    def auto_fit_image(self): pass
    def manual_set_zoom(self, z): pass
    def update_zoom_label(self): pass
    def update_resolution_label(self): pass
    def copy_to_clipboard(self): pass
    def save_image(self): pass
    def select_tool(self, tool_id): pass
    def toggle_recent_strip(self): pass
    def show_resize_dialog(self): pass
    def delete_library_file(self, filepath, target_btn=None): pass
    def load_image_from_path(self, filepath): pass
    def refresh_library_strip(self): pass
    def start_new_capture(self): pass
