'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal, QSize

class FloatingToolbar(QWidget):
    """Floating toolbar for static image capture region selection."""
    def __init__(self, parent, on_done, on_cancel):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        from platforms import Platform
        Platform.set_window_capture_excluded(int(self.winId()))
        Platform.set_window_hides_on_deactivate(int(self.winId()), False)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        bg = QWidget()
        bg.setObjectName("bg_widget")
        bg.setStyleSheet("#bg_widget { background-color: #2b2b2b; border: 1px solid #555555; border-radius: 6px; }")
        bg_layout = QHBoxLayout(bg)
        bg_layout.setContentsMargins(10, 6, 10, 6)
        bg_layout.setSpacing(8)
        
        self.lbl_size = QLabel("0 x 0")
        self.lbl_size.setStyleSheet("color: white; font-family: monospace; font-size: 13px; margin-right: 6px;")
        bg_layout.addWidget(self.lbl_size)
        
        from resources.icon_utils import create_svg_icon, SVG_DONE, SVG_CANCEL
        from widgets.capture_buttons import create_toolbar_button
        
        btn_done = create_toolbar_button(icon=create_svg_icon(SVG_DONE), icon_size=QSize(20, 20), color_theme="blue", padding="6px 15px")
        btn_cancel = create_toolbar_button(icon=create_svg_icon(SVG_CANCEL), icon_size=QSize(20, 20), color_theme="cancel", padding="6px 15px")
            
        btn_done.clicked.connect(on_done)
        btn_cancel.clicked.connect(on_cancel)
        
        bg_layout.addWidget(btn_done)
        bg_layout.addWidget(btn_cancel)
        layout.addWidget(bg)
        self.adjustSize()
        
    def update_size(self, width, height):
        self.lbl_size.setText(f"{width} x {height}")
        self.adjustSize()


class ScrollCaptureToolbar(QWidget):
    """Control toolbar for scrolling capture manager."""
    finish_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.status_lbl = QLabel("Scroll vertically...")
        self.status_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        
        hbox_btns = QHBoxLayout()
        hbox_btns.setSpacing(8)
        
        from widgets.capture_buttons import create_toolbar_button
        self.btn_done = create_toolbar_button("Finish", color_theme="blue", padding="6px 15px")
        self.btn_done.clicked.connect(self.finish_requested.emit)
        
        self.btn_cancel = create_toolbar_button("Cancel", color_theme="cancel", padding="6px 15px")
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        
        hbox_btns.addWidget(self.btn_done)
        hbox_btns.addWidget(self.btn_cancel)
        hbox_btns.addStretch()
        
        layout.addWidget(self.status_lbl)
        layout.addLayout(hbox_btns)


class VideoToolbar(QWidget):
    """Floating toolbar for video recording management."""
    start_requested = Signal()
    stop_requested = Signal()
    cancel_requested = Signal()
    audio_toggled = Signal(bool)
    sys_audio_toggled = Signal(bool)
    cursor_toggled = Signal(bool)
    cursor_settings_changed = Signal(bool, bool)

    PRE_RECORD = 0
    RECORDING = 1

    def __init__(self, parent=None, init_cursor: bool = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        from platforms import Platform
        Platform.set_window_capture_excluded(int(self.winId()))
        Platform.set_window_hides_on_deactivate(int(self.winId()), False)
            
        self.state = self.PRE_RECORD
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        bg = QWidget()
        bg.setObjectName("bg_widget")
        bg.setStyleSheet("#bg_widget { background-color: #2b2b2b; border: 1px solid #555555; border-radius: 8px; }")
        bg_layout = QHBoxLayout(bg)
        bg_layout.setContentsMargins(12, 8, 12, 8)
        bg_layout.setSpacing(8)
        
        from resources.icon_utils import create_svg_icon, SVG_RECORD, SVG_STOP, SVG_MOUSE, SVG_MIC, SVG_MIC_OFF, SVG_SYS_AUDIO, SVG_SYS_AUDIO_OFF, SVG_CANCEL
        from widgets.capture_buttons import create_toolbar_button, SplitMenuButton
        from config import load_config
        cfg = load_config()
        toggles_cfg = cfg.get("toggles", {})
        if init_cursor is None:
            init_cursor = toggles_cfg.get("Record Cursor", True)
        init_mic = toggles_cfg.get("Record Microphone", True)
        init_sys = toggles_cfg.get("Record System Audio", True)
        
        ICON_SIZE = QSize(22, 22)
        
        # Action button (Record / Stop)
        self.btn_action = create_toolbar_button(
            icon=create_svg_icon(SVG_RECORD),
            icon_size=ICON_SIZE,
            color_theme="red",
            padding="8px 18px"
        )
        self.btn_action.clicked.connect(self._on_action_clicked)
        self.btn_action.setFixedHeight(40)
        
        # Cursor Group (Split button: Toggle + Dropdown Arrow)
        self.cursor_split = SplitMenuButton(
            icon=create_svg_icon(SVG_MOUSE),
            icon_size=ICON_SIZE,
            color_theme="default",
            checkable=True,
            checked=init_cursor,
            padding="8px 8px",
            fixed_height=40,
            parent=self
        )
        self.btn_cursor = self.cursor_split.main_btn
        self.btn_cursor_menu = self.cursor_split.arrow_btn
        self.cursor_menu = self.cursor_split.menu

        self.btn_cursor.toggled.connect(self.cursor_toggled.emit)

        from PySide6.QtGui import QAction

        c_cfg = cfg.get("cursor_settings", {})
        self.act_hl = QAction("Highlight Cursor", self, checkable=True)
        self.act_hl.setChecked(c_cfg.get("highlight", True))
        self.act_hl.toggled.connect(self._on_cursor_setting_changed)

        self.act_anim = QAction("Click Animation", self, checkable=True)
        self.act_anim.setChecked(c_cfg.get("click", True))
        self.act_anim.toggled.connect(self._on_cursor_setting_changed)

        self.cursor_split.addAction(self.act_hl)
        self.cursor_split.addAction(self.act_anim)
        
        # Audio button (Split button: Toggle + Dropdown Arrow for Mic selection)
        self.audio_split = SplitMenuButton(
            icon=create_svg_icon(SVG_MIC if init_mic else SVG_MIC_OFF),
            icon_size=ICON_SIZE,
            color_theme="default",
            checkable=True,
            checked=init_mic,
            padding="8px 8px",
            fixed_height=40,
            parent=self
        )
        self.btn_audio = self.audio_split.main_btn
        self.btn_audio_menu = self.audio_split.arrow_btn
        self.audio_menu = self.audio_split.menu
        self.btn_audio.toggled.connect(self._on_audio_toggled)

        from PySide6.QtGui import QActionGroup
        self.audio_action_group = QActionGroup(self)
        self.audio_action_group.setExclusive(True)
        curr_aud = cfg.get("audio_source", "")

        try:
            import soundcard as sc
            mics = sc.all_microphones(include_loopback=False)
            found_checked = False

            if not mics:
                no_act = QAction("No Microphone Detected", self)
                no_act.setEnabled(False)
                self.audio_split.addAction(no_act)
                self.audio_split.setEnabled(False)
                self.btn_audio.setChecked(False)
            else:
                for m in mics:
                    dev_name = m.name
                    act = QAction(dev_name, self, checkable=True)
                    if dev_name == curr_aud:
                        act.setChecked(True)
                        found_checked = True
                    act.triggered.connect(lambda checked=False, name=dev_name: self._on_audio_device_selected(name))
                    self.audio_action_group.addAction(act)
                    self.audio_split.addAction(act)
                if not found_checked and len(self.audio_action_group.actions()) > 0:
                    self.audio_action_group.actions()[0].setChecked(True)
        except Exception as e:
            import logging
            logging.warning("Error enumerating sound devices in toolbar: %s", e, exc_info=True)

        # System Audio button
        self.btn_sys_audio = create_toolbar_button(
            icon=create_svg_icon(SVG_SYS_AUDIO if init_sys else SVG_SYS_AUDIO_OFF),
            icon_size=ICON_SIZE,
            color_theme="default",
            checkable=True,
            checked=init_sys,
            padding="8px 12px"
        )
        self.btn_sys_audio.setFixedHeight(40)
        self.btn_sys_audio.toggled.connect(self._on_sys_audio_toggled)
        try:
            import soundcard as sc
            if not sc.all_speakers():
                self.btn_sys_audio.setChecked(False)
                self.btn_sys_audio.setEnabled(False)
        except Exception:
            pass
        
        # Info label (Size or Time)
        self.lbl_info = QLabel("0 x 0")
        self.lbl_info.setStyleSheet("color: white; font-family: monospace; font-size: 14px; margin: 0 10px;")
        
        # Red blinking dot - now to the RIGHT of lbl_info
        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet("background-color: transparent; border-radius: 5px;")
        
        # Cancel button
        self.btn_cancel = create_toolbar_button(
            icon=create_svg_icon(SVG_CANCEL),
            icon_size=ICON_SIZE,
            color_theme="cancel",
            padding="8px 12px"
        )
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        
        bg_layout.addWidget(self.btn_action)
        bg_layout.addWidget(self.cursor_split)
        bg_layout.addWidget(self.audio_split)
        bg_layout.addWidget(self.btn_sys_audio)
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
        from resources.icon_utils import create_svg_icon, SVG_MIC, SVG_MIC_OFF
        self.btn_audio.setIcon(create_svg_icon(SVG_MIC if checked else SVG_MIC_OFF))
        if checked and hasattr(self, 'audio_action_group'):
            checked_act = self.audio_action_group.checkedAction()
            if not checked_act:
                actions = self.audio_action_group.actions()
                if actions:
                    actions[0].setChecked(True)
                    self._on_audio_device_selected(actions[0].text())
        self.audio_toggled.emit(checked)

    def _on_audio_device_selected(self, name):
        from config import load_config, save_config
        cfg = load_config()
        cfg["audio_source"] = name
        save_config(cfg)
        if not self.btn_audio.isChecked():
            self.btn_audio.setChecked(True)
        if hasattr(self.parent(), "ready_panel") and self.parent().ready_panel:
            self.parent().ready_panel.set_audio_device_name(name)
            self.parent().ready_panel.update_audio_status(True)

    def _on_sys_audio_toggled(self, checked):
        from resources.icon_utils import create_svg_icon, SVG_SYS_AUDIO, SVG_SYS_AUDIO_OFF
        self.btn_sys_audio.setIcon(create_svg_icon(SVG_SYS_AUDIO if checked else SVG_SYS_AUDIO_OFF))
        self.sys_audio_toggled.emit(checked)

    def _on_cursor_setting_changed(self):
        from config import load_config, save_config
        cfg = load_config()
        if "cursor_settings" not in cfg:
            cfg["cursor_settings"] = {}
        cfg["cursor_settings"]["highlight"] = self.act_hl.isChecked()
        cfg["cursor_settings"]["click"] = self.act_anim.isChecked()
        save_config(cfg)
        
        self.cursor_settings_changed.emit(self.act_hl.isChecked(), self.act_anim.isChecked())
        
        if hasattr(self.parent(), "ready_panel") and self.parent().ready_panel:
            self.parent().ready_panel.update_cursor_status(self.btn_cursor.isChecked())

    def _set_recording_state(self):
        from resources.icon_utils import create_svg_icon, SVG_STOP
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
