'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QTimer, QSize

class VideoToolbar(QWidget):
    start_requested = Signal()
    stop_requested = Signal()
    cancel_requested = Signal()
    audio_toggled = Signal(bool)
    cursor_toggled = Signal(bool)

    PRE_RECORD = 0
    RECORDING = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Exclude from screen capture via platform abstraction
        from platforms import Platform
        Platform.set_window_capture_excluded(int(self.winId()))
            
        self.state = self.PRE_RECORD
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        bg = QWidget()
        bg.setObjectName("bg_widget")
        bg.setStyleSheet("#bg_widget { background-color: #2b2b2b; border: 1px solid #555555; border-radius: 8px; }")
        bg_layout = QHBoxLayout(bg)
        bg_layout.setContentsMargins(12, 8, 12, 8)
        bg_layout.setSpacing(8)
        
        from ui.icon_utils import create_svg_icon, SVG_RECORD, SVG_STOP, SVG_MOUSE, SVG_MIC, SVG_MIC_OFF, SVG_CANCEL
        
        ICON_SIZE = QSize(22, 22)
        BTN_STYLE_TOGGLE = """
            QPushButton {{ background-color: #444444; padding: 8px 12px; border-radius: 6px; border: none; }}
            QPushButton:checked {{ background-color: #388e3c; }}
        """
        
        # Action button (Record / Stop)
        self.btn_action = QPushButton()
        self.btn_action.setIcon(create_svg_icon(SVG_RECORD))
        self.btn_action.setIconSize(ICON_SIZE)
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setStyleSheet("background-color: #d32f2f; padding: 8px 18px; border-radius: 6px; border: none;")
        self.btn_action.clicked.connect(self._on_action_clicked)
        
        # Cursor Toggle button
        self.btn_cursor = QPushButton()
        self.btn_cursor.setIcon(create_svg_icon(SVG_MOUSE))
        self.btn_cursor.setIconSize(ICON_SIZE)
        self.btn_cursor.setCheckable(True)
        self.btn_cursor.setChecked(True)
        self.btn_cursor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cursor.setStyleSheet(BTN_STYLE_TOGGLE.format())
        self.btn_cursor.toggled.connect(self.cursor_toggled.emit)
        
        # Audio button
        self.btn_audio = QPushButton()
        self.btn_audio.setIcon(create_svg_icon(SVG_MIC))
        self.btn_audio.setIconSize(ICON_SIZE)
        self.btn_audio.setCheckable(True)
        self.btn_audio.setChecked(True)
        self.btn_audio.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_audio.setStyleSheet(BTN_STYLE_TOGGLE.format())
        self.btn_audio.toggled.connect(self._on_audio_toggled)
        
        # Info label (Size or Time)
        self.lbl_info = QLabel("0 x 0")
        self.lbl_info.setStyleSheet("color: white; font-family: monospace; font-size: 14px; margin: 0 10px;")
        
        # Red blinking dot - now to the RIGHT of lbl_info
        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet("background-color: transparent; border-radius: 5px;")
        
        # Cancel button
        self.btn_cancel = QPushButton()
        self.btn_cancel.setIcon(create_svg_icon(SVG_CANCEL))
        self.btn_cancel.setIconSize(ICON_SIZE)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("background-color: #4a4a4a; padding: 8px 12px; border-radius: 6px; border: none;")
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        
        # Layout: [?èRecord] [?ñ∞] [??] | [00:00:00] [?è] | [?ï]
        bg_layout.addWidget(self.btn_action)
        bg_layout.addWidget(self.btn_cursor)
        bg_layout.addWidget(self.btn_audio)
        bg_layout.addWidget(self.lbl_info)
        bg_layout.addWidget(self.dot)
        bg_layout.addWidget(self.btn_cancel)
        
        layout.addWidget(bg)
        self.adjustSize()
        
        self.dot_visible = False

    def _on_action_clicked(self):
        if self.state == self.PRE_RECORD:
            self.start_requested.emit()
            self._set_recording_state()
        else:
            self.stop_requested.emit()

    def _on_audio_toggled(self, checked):
        from ui.icon_utils import create_svg_icon, SVG_MIC, SVG_MIC_OFF
        self.btn_audio.setIcon(create_svg_icon(SVG_MIC if checked else SVG_MIC_OFF))
        self.audio_toggled.emit(checked)

    def _set_recording_state(self):
        from ui.icon_utils import create_svg_icon, SVG_STOP
        self.state = self.RECORDING
        self.btn_action.setIcon(create_svg_icon(SVG_STOP))
        self.lbl_info.setText("00:00:00")
        self.dot_visible = True
        self.dot.setStyleSheet("background-color: #ff1744; border-radius: 5px;")
        self.adjustSize()

    def update_size(self, width, height):
        if self.state == self.PRE_RECORD:
            self.lbl_info.setText(f"{width} x {height}")
            self.adjustSize()

    def update_time(self, time_str):
        if self.state == self.RECORDING:
            self.lbl_info.setText(time_str)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_pos'):
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'drag_pos'):
            del self.drag_pos
            event.accept()
