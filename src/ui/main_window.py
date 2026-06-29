'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import sys
from platforms import Platform
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QTabWidget, QLabel
from PySide6.QtCore import Qt, QTimer
from ui.toggle_switch import ToggleSwitch

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
            QTabWidget::tab-bar { alignment: left; left: 0px; }
            QTabBar { qproperty-expanding: 0; }
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
            #AboutButton {
                background: transparent;
                color: #aaaaaa;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            #AboutButton:hover {
                background: #555555;
                color: white;
            }
        """)

        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(1, 1, 1, 1) # Small margin for border
        main_layout.setSpacing(0)
        
        from ui.icon_utils import create_svg_icon, SVG_TAB_IMAGE, SVG_TAB_VIDEO
        
        # Tabs at the top
        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        self.tabs.tabBar().setExpanding(False)
        
        self.toggles = {}
        
        # Image Tab (Default loaded)
        from ui.tab_utils import ImageTab
        tab_image = ImageTab(self)
        self.tabs.addTab(tab_image, create_svg_icon(SVG_TAB_IMAGE), "Image")
        
        # Video Tab (Lazy loaded placeholder)
        self.video_tab_loaded = False
        tab_video_placeholder = QWidget()
        self.tabs.addTab(tab_video_placeholder, create_svg_icon(SVG_TAB_VIDEO), "Video")
        
        self.tabs.setCurrentIndex(0)
        self.tabs.currentChanged.connect(self.on_tab_changed)
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
        
        from ui.icon_utils import SVG_CLOSE, SVG_ABOUT
        # Absolute positioned close button
        self.close_btn = QPushButton("", central_widget)
        self.close_btn.setIcon(create_svg_icon(SVG_CLOSE))
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)
        self.close_btn.move(self.width() - 31, 1)
        self.close_btn.raise_()
        
        self.about_btn = QPushButton("", central_widget)
        self.about_btn.setIcon(create_svg_icon(SVG_ABOUT))
        self.about_btn.setObjectName("AboutButton")
        self.about_btn.setFixedSize(30, 30)
        self.about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.about_btn.clicked.connect(self.show_about)
        self.about_btn.move(self.width() - 61, 1)
        self.about_btn.raise_()
        
        self.overlay = None
        self.HOTKEY_VIDEO_ID = 1
        self.HOTKEY_IMAGE_ID = 2
        self.register_hotkeys()

    def open_preferences(self):
        from ui.preferences_window import PreferencesWindow
        prefs = PreferencesWindow(self)
        prefs.exec()

    def show_about(self):
        if hasattr(self, '_about_overlay') and self._about_overlay:
            self._about_overlay.close()
            return

        overlay = QWidget(self.centralWidget())
        self._about_overlay = overlay
        overlay.setObjectName("AboutOverlay")
        overlay.setGeometry(self.centralWidget().rect())
        overlay.setCursor(Qt.CursorShape.PointingHandCursor)
        overlay.setStyleSheet("""
            #AboutOverlay {
                background-color: rgba(18, 18, 18, 230);
                border-radius: 8px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        
        layout = QVBoxLayout(overlay)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        
        title = QLabel("ScreenCut")
        title.setStyleSheet("color: #e0e0e0; font-size: 22px; font-weight: bold; letter-spacing: 1px;")
        
        subtitle = QLabel("A simple and fast screen capture tool.")
        subtitle.setStyleSheet("color: #c0c0c0; font-size: 14px;")
        
        info = QLabel("Version: 1.0.0  •  LGPL-2.0 License")
        info.setStyleSheet("color: #888888; font-size: 12px; margin-top: 5px;")
        
        tip = QLabel("(Press any key or click anywhere to close)")
        tip.setStyleSheet("color: #666666; font-size: 11px; font-style: italic; margin-top: 15px;")
        
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip, alignment=Qt.AlignmentFlag.AlignCenter)
        
        def close_overlay(event):
            overlay.hide()
            overlay.deleteLater()
            self._about_overlay = None
            
        overlay.mousePressEvent = close_overlay
        overlay.show()
        overlay.raise_()

    def on_tab_changed(self, index):
        if index == 1 and not self.video_tab_loaded:
            self.load_video_tab()

    def load_video_tab(self):
        if getattr(self, 'video_tab_loaded', False):
            return
        self.video_tab_loaded = True
        from ui.tab_utils import VideoTab
        tab_video = VideoTab(self)
        icon = self.tabs.tabIcon(1)
        text = self.tabs.tabText(1)
        self.tabs.blockSignals(True)
        self.tabs.removeTab(1)
        self.tabs.insertTab(1, tab_video, icon, text)
        self.tabs.setCurrentIndex(1)
        self.tabs.blockSignals(False)

    def add_setting_row(self, layout, label_text, is_checked=False, has_details=False, key_name=None):
        if key_name is None:
            key_name = label_text
            
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        from ui.toggle_switch import ToggleSwitch
        toggle = ToggleSwitch()
        toggle.setChecked(is_checked)
        self.toggles[key_name] = toggle
        
        toggle.stateChanged.connect(lambda state, text=key_name: self.save_toggle_state(text, state))
        
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
            from ui.countdown_window import CountdownWindow
            self.countdown = CountdownWindow(5)
            self.countdown.finished.connect(lambda: self._do_overlay(is_video=False))
            self.countdown.cancelled.connect(self.show_after_capture)
            self.countdown.show()
        else:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self._do_overlay(is_video=False))
            
    def start_video_capture(self):
        if not getattr(self, 'video_tab_loaded', False):
            self.load_video_tab()
        self.hide()
        capture_cursor = self.toggles.get("Capture Cursor (Video)", None)
        self._has_cursor = capture_cursor.isChecked() if capture_cursor else False
        self._is_scroll = False
        
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._do_overlay(is_video=True))
        
    def _do_overlay(self, is_video=False):
        from ui.overlay_window import OverlayWindow
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
        vk_video  = hotkeys.get("video_hotkey", {}).get("vk", 0x56)   # 'V'
        mods_video = hotkeys.get("video_hotkey", {}).get("modifiers", 6)  # Shift|Ctrl
        if vk_video:
            Platform.register_hotkey(int(self.winId()), self.HOTKEY_VIDEO_ID, mods_video, vk_video)

        # Default for Image: Ctrl+Shift+P
        vk_image  = hotkeys.get("image_hotkey", {}).get("vk", 0x50)   # 'P'
        mods_image = hotkeys.get("image_hotkey", {}).get("modifiers", 6)  # Shift|Ctrl
        if vk_image:
            Platform.register_hotkey(int(self.winId()), self.HOTKEY_IMAGE_ID, mods_image, vk_image)

        # On macOS, wire up callbacks via pynput (no WM_HOTKEY)
        if sys.platform == "darwin" and hasattr(Platform, 'set_hotkey_callback'):
            Platform.set_hotkey_callback(self.HOTKEY_VIDEO_ID, self.start_video_capture)
            Platform.set_hotkey_callback(self.HOTKEY_IMAGE_ID, self.start_capture)

    def update_hotkey(self, config_key, mods, vk):
        hotkey_id = self.HOTKEY_VIDEO_ID if config_key == "video_hotkey" else self.HOTKEY_IMAGE_ID
        Platform.unregister_hotkey(int(self.winId()), hotkey_id)
        if vk:
            Platform.register_hotkey(int(self.winId()), hotkey_id, mods, vk)
            if sys.platform == "darwin" and hasattr(Platform, 'set_hotkey_callback'):
                cb = self.start_video_capture if hotkey_id == self.HOTKEY_VIDEO_ID else self.start_capture
                Platform.set_hotkey_callback(hotkey_id, cb)

    def nativeEvent(self, eventType, message):
        # WM_HOTKEY interception is Windows-only
        if sys.platform == "win32":
            import ctypes.wintypes
            if eventType in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                msg = ctypes.wintypes.MSG.from_address(message.__int__())
                if msg.message == 0x0312:  # WM_HOTKEY
                    if msg.wParam == self.HOTKEY_VIDEO_ID:
                        self.start_video_capture()
                        return True, 0
                    elif msg.wParam == self.HOTKEY_IMAGE_ID:
                        self.start_capture()
                        return True, 0
        return super().nativeEvent(eventType, message)
        
    def closeEvent(self, event):
        Platform.unregister_hotkey(int(self.winId()), self.HOTKEY_VIDEO_ID)
        Platform.unregister_hotkey(int(self.winId()), self.HOTKEY_IMAGE_ID)
        super().closeEvent(event)
