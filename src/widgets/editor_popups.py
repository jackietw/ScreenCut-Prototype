'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QCheckBox
from PySide6.QtCore import Qt


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
                from PySide6.QtCore import QFile
                if not QFile.moveToTrash(self.filepath):
                    try:
                        import send2trash
                        send2trash.send2trash(self.filepath)
                    except ImportError:
                        os.remove(self.filepath)
        except Exception as e:
            import logging
            logging.warning("Error deleting project file: %s", e, exc_info=True)
        if is_current:
            self.editor_win.current_image_path = None
        self.close()
        self.editor_win.refresh_library_strip()
