'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import ctypes
import ctypes.wintypes
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QTabWidget, QLabel
from PySide6.QtCore import Qt, QTimer
from ui.overlay_window import OverlayWindow
from ui.toggle_switch import ToggleSwitch
from ui.countdown_window import CountdownWindow
from ui.hotkey_label import HotkeyLabel

class MainWindow(QMainWindow):
    def __init__(self, library_dir):
        super().__init__()
        self.library_dir = library_dir
        self.setWindowTitle("ScreenCut Capture")
        self.resize(450, 270)
        self.setMinimumSize(450, 270)
        
        # Make window frameless
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            QMainWindow { background-color: transparent; }
            #CentralWidget { 
                background-color: #1e1e1e; 
                border: 1px solid #444444;
                border-radius: 8px;
            }
            QLabel { color: #ffffff; font-size: 13px; }
            QTabWidget, QTabWidget::pane { background: transparent; border: 0; }
            QTabBar::tab { 
                background: #2d2d2d; 
                color: #aaaaaa; 
                padding: 12px 25px; 
                font-size: 12px;
                border: None;
                border-bottom: 2px solid #2d2d2d;
            }
            QTabBar::tab:first {
                border-top-left-radius: 8px;
            }
            QTabBar::tab:selected { 
                color: #ffffff; 
                border-bottom: 2px solid #246bb2; 
            }
            #CaptureButton { 
                background-color: #d32f2f; 
                color: white; 
                font-weight: bold; 
                font-size: 18px; 
                border-radius: 50px; /* Perfect circle for 100x100 */
            }
            #CaptureButton:hover { background-color: #f44336; }
            #BottomBar {
                background-color: #141414;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            #BottomBar QLabel {
                font-size: 12px;
                color: #aaaaaa;
            }
            #CloseButton {
                background: transparent;
                color: #aaaaaa;
                font-weight: bold;
                font-size: 16px;
                border: none;
                border-top-right-radius: 8px;
            }
            #CloseButton:hover {
                background: #d32f2f;
                color: white;
            }
        """)

        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(1, 1, 1, 1) # Small margin for border
        main_layout.setSpacing(0)
        
        # Tabs at the top
        self.tabs = QTabWidget()
        
        # Auto Tab (TBD)
        # tab_auto = QWidget()
        # tab_auto_layout = QVBoxLayout(tab_auto)
        # tab_auto_layout.addWidget(QLabel("Auto Mode detects content intelligently."))
        # self.tabs.addTab(tab_auto, "Auto")
        
        # Image Tab
        tab_image = QWidget()
        self.toggles = {}
        self.setup_image_tab(tab_image)
        self.tabs.addTab(tab_image, "Image")
        
        # Video Tab
        tab_video = QWidget()
        self.setup_video_tab(tab_video)
        self.tabs.addTab(tab_video, "Video")
        
        self.tabs.setCurrentIndex(0)
        main_layout.addWidget(self.tabs)
        
        # Bottom Bar
        bottom_bar = QWidget()
        bottom_bar.setObjectName("BottomBar")
        bottom_bar.setFixedHeight(35)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(15, 0, 15, 0)
        
        from ui.icon_utils import create_svg_icon, SVG_PREF, SVG_EDITOR
        from PySide6.QtCore import QSize
        
        btn_presets = QPushButton("Preference")
        btn_presets.setIcon(create_svg_icon(SVG_PREF))
        btn_presets.setIconSize(QSize(18, 18))
        btn_presets.setStyleSheet("color: #aaaaaa; font-size: 14px; background: transparent; border: none; text-align: left;")
        btn_presets.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_presets.clicked.connect(self.open_preferences)
        
        btn_editor = QPushButton("Open Editor(X)")
        btn_editor.setIcon(create_svg_icon(SVG_EDITOR))
        btn_editor.setIconSize(QSize(18, 18))
        btn_editor.setStyleSheet("color: #aaaaaa; font-size: 14px; background: transparent; border: none; text-align: left;")
        btn_editor.setCursor(Qt.CursorShape.PointingHandCursor)
        # TODO: Implement editor functionality
        
        bottom_layout.addWidget(btn_presets)
        bottom_layout.addStretch()
        bottom_layout.addWidget(btn_editor)
        
        main_layout.addWidget(bottom_bar)
        
        # Absolute positioned close button
        self.close_btn = QPushButton("✕", central_widget)
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)
        self.close_btn.move(self.width() - 31, 1)
        self.close_btn.raise_()
        
        self.overlay = None
        self.HOTKEY_VIDEO_ID = 1
        self.HOTKEY_IMAGE_ID = 2
        self.register_hotkeys()

    def open_preferences(self):
        from ui.preferences_window import PreferencesWindow
        prefs = PreferencesWindow(self)
        prefs.exec()

    def setup_video_tab(self, tab):
        from config import load_config
        config_data = load_config()
        toggles_config = config_data.get("toggles", {})
        
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 15, 20, 15)
        
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(15)
        
        self.add_setting_row(settings_layout, "Capture Cursor (Video)", toggles_config.get("Capture Cursor (Video)", False), has_details=True)
        self.add_setting_row(settings_layout, "5 Second Delay (Video)", toggles_config.get("5 Second Delay (Video)", False))
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout, stretch=2)
        
        capture_layout = QVBoxLayout()
        
        self.record_btn = QPushButton("Record")
        self.record_btn.setObjectName("CaptureButton")
        self.record_btn.setFixedSize(100, 100)
        self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_btn.clicked.connect(self.start_video_capture)
        
        lbl_hotkey = HotkeyLabel("Ctrl+Shift+V", "video_hotkey")
        lbl_hotkey.hotkey_changed.connect(self.update_hotkey)

        capture_layout.addStretch()
        capture_layout.addWidget(self.record_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addWidget(lbl_hotkey, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addStretch()
        
        layout.addLayout(capture_layout, stretch=1)

    def setup_image_tab(self, tab):
        from config import load_config
        config_data = load_config()
        toggles_config = config_data.get("toggles", {})
        
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Left side: Settings with Toggles
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(15)
        
        self.add_setting_row(settings_layout, "Preview in Editor(X)", toggles_config.get("Preview in Editor(X)", True))
        self.add_setting_row(settings_layout, "Copy to Clipboard", toggles_config.get("Copy to Clipboard", True))
        self.add_setting_row(settings_layout, "Capture Cursor", toggles_config.get("Capture Cursor", False))
        self.add_setting_row(settings_layout, "5 Second Delay", toggles_config.get("5 Second Delay", False))
        self.add_setting_row(settings_layout, "Scroll Capture", toggles_config.get("Scroll Capture", False))
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout, stretch=2)
        
        # Right side: Capture Button
        capture_layout = QVBoxLayout()
        
        self.capture_btn = QPushButton("Capture")
        self.capture_btn.setObjectName("CaptureButton")
        self.capture_btn.setFixedSize(100, 100)
        self.capture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.capture_btn.clicked.connect(self.start_capture)
        
        lbl_hotkey = HotkeyLabel("Ctrl+Shift+P", "image_hotkey")
        lbl_hotkey.hotkey_changed.connect(self.update_hotkey)
        
        capture_layout.addStretch()
        capture_layout.addWidget(self.capture_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addWidget(lbl_hotkey, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addStretch()
        
        layout.addLayout(capture_layout, stretch=1)

    def add_setting_row(self, layout, label_text, is_checked=False, has_details=False):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        from ui.toggle_switch import ToggleSwitch
        toggle = ToggleSwitch()
        toggle.setChecked(is_checked)
        self.toggles[label_text] = toggle
        
        toggle.stateChanged.connect(lambda state, text=label_text: self.save_toggle_state(text, state))
        
        row.addWidget(lbl)
        row.addStretch()
        
        right_container = QWidget()
        right_container.setFixedWidth(70)
        rc_layout = QHBoxLayout(right_container)
        rc_layout.setContentsMargins(0, 0, 0, 0)
        rc_layout.setSpacing(5)
        
        rc_layout.addWidget(toggle)
        
        if has_details:
            from ui.icon_utils import create_svg_icon, SVG_MORE
            from PySide6.QtCore import QSize
            btn_details = QPushButton()
            btn_details.setIcon(create_svg_icon(SVG_MORE))
            btn_details.setIconSize(QSize(20, 20))
            btn_details.setFixedSize(24, 24)
            btn_details.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_details.setStyleSheet("background: transparent; border: none;")
            btn_details.clicked.connect(self.show_cursor_settings)
            rc_layout.addWidget(btn_details)
        else:
            spacer = QWidget()
            spacer.setFixedSize(20, 20)
            rc_layout.addWidget(spacer)
            
        row.addWidget(right_container)
        layout.addLayout(row)

    def show_cursor_settings(self):
        btn = self.sender()
        if not hasattr(self, 'cursor_popup') or self.cursor_popup is None:
            from ui.cursor_settings_popup import CursorSettingsPopup
            self.cursor_popup = CursorSettingsPopup(self)
            
        pos = btn.mapToGlobal(btn.rect().topRight())
        self.cursor_popup.move(pos.x() + 5, pos.y() - 20)
        self.cursor_popup.show()

    def save_toggle_state(self, label_text, state):
        from config import load_config, save_config
        from PySide6.QtCore import Qt
        config_data = load_config()
        if "toggles" not in config_data:
            config_data["toggles"] = {}
        # ToggleSwitch stateChanged might emit int or bool depending on implementation
        # Let's check if it's int or bool
        is_checked = (state == Qt.CheckState.Checked.value) if isinstance(state, int) else bool(state)
        config_data["toggles"][label_text] = is_checked
        save_config(config_data)

    def start_capture(self):
        self.hide()
        capture_cursor = self.toggles.get("Capture Cursor", None)
        self._has_cursor = capture_cursor.isChecked() if capture_cursor else False
        
        delay_toggle = self.toggles.get("5 Second Delay", None)
        has_delay = delay_toggle.isChecked() if delay_toggle else False
        
        scroll_toggle = self.toggles.get("Scroll Capture", None)
        self._is_scroll = scroll_toggle.isChecked() if scroll_toggle else False
        
        if has_delay:
            self.countdown = CountdownWindow(5)
            self.countdown.finished.connect(lambda: self._do_overlay(is_video=False))
            self.countdown.show()
        else:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self._do_overlay(is_video=False))
            
    def start_video_capture(self):
        self.hide()
        capture_cursor = self.toggles.get("Capture Cursor (Video)", None)
        self._has_cursor = capture_cursor.isChecked() if capture_cursor else False
        
        delay_toggle = self.toggles.get("5 Second Delay (Video)", None)
        has_delay = delay_toggle.isChecked() if delay_toggle else False
        
        self._is_scroll = False
        
        if has_delay:
            self.countdown = CountdownWindow(5)
            self.countdown.finished.connect(lambda: self._do_overlay(is_video=True))
            self.countdown.show()
        else:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self._do_overlay(is_video=True))
        
    def _do_overlay(self, is_video=False):
        self.overlay = OverlayWindow(self.library_dir, self._has_cursor, self._is_scroll, is_video)
        self.overlay.capture_finished.connect(self.show_after_capture)
        self.overlay.show()
        self.overlay.activateWindow()
        self.overlay.raise_()
        self.overlay.setFocus()

    def show_after_capture(self):
        self.show()
        self.activateWindow()
        self.raise_()

    # --- Window Dragging Logic ---
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

    def register_hotkeys(self):
        from config import load_config
        cfg = load_config()
        hotkeys = cfg.get("hotkeys", {})
        
        # Default for Video: Ctrl+Shift+V
        vk_video = hotkeys.get("video_hotkey", {}).get("vk", 0x56)  # 'V'
        mods_video = hotkeys.get("video_hotkey", {}).get("modifiers", 6)  # MOD_SHIFT(4) | MOD_CONTROL(2)
        if vk_video: ctypes.windll.user32.RegisterHotKey(int(self.winId()), self.HOTKEY_VIDEO_ID, mods_video, vk_video)
            
        # Default for Image: Ctrl+Shift+P
        vk_image = hotkeys.get("image_hotkey", {}).get("vk", 0x50)  # 'P'
        mods_image = hotkeys.get("image_hotkey", {}).get("modifiers", 6)  # MOD_SHIFT(4) | MOD_CONTROL(2)
        if vk_image: ctypes.windll.user32.RegisterHotKey(int(self.winId()), self.HOTKEY_IMAGE_ID, mods_image, vk_image)

    def update_hotkey(self, config_key, mods, vk):
        hotkey_id = self.HOTKEY_VIDEO_ID if config_key == "video_hotkey" else self.HOTKEY_IMAGE_ID
        ctypes.windll.user32.UnregisterHotKey(int(self.winId()), hotkey_id)
        if vk:
            ctypes.windll.user32.RegisterHotKey(int(self.winId()), hotkey_id, mods, vk)

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG" or eventType == b"windows_dispatcher_MSG":
            msg = ctypes.wintypes.MSG.from_address(message.__int__())
            if msg.message == 0x0312: # WM_HOTKEY
                if msg.wParam == self.HOTKEY_VIDEO_ID:
                    self.start_video_capture()
                    return True, 0
                elif msg.wParam == self.HOTKEY_IMAGE_ID:
                    self.start_capture()
                    return True, 0
        return super().nativeEvent(eventType, message)
        
    def closeEvent(self, event):
        ctypes.windll.user32.UnregisterHotKey(int(self.winId()), self.HOTKEY_VIDEO_ID)
        ctypes.windll.user32.UnregisterHotKey(int(self.winId()), self.HOTKEY_IMAGE_ID)
        super().closeEvent(event)
