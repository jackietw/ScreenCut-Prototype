'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from version import CAPTURE_VERSION
import sys
from platforms import Platform
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from capture.capture_main_ui import MainUI

class Main(MainUI):
    def __init__(self, library_dir):
        super().__init__(library_dir)
        
        # Connect signals
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.btn_presets.clicked.connect(self.open_preferences)
        self.btn_editor.clicked.connect(self.open_editor)
        self.close_btn.clicked.connect(self.hide)
        self.about_btn.clicked.connect(self.show_about)
        
        self.overlay = None
        self.HOTKEY_VIDEO_ID = 1
        self.HOTKEY_IMAGE_ID = 2
        self.register_hotkeys()

    def open_preferences(self):
        from capture.capture_prefs import Preferences
        prefs = Preferences(self)
        prefs.exec()

    def open_editor(self, initial_image=None, current_filepath=None):
        self.hide()
        from editor.editor_main import ImageEditor
        self.editor_win = ImageEditor.get_instance(self.library_dir, initial_image=initial_image, current_filepath=current_filepath)

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
        
        info = QLabel("Version: v" + CAPTURE_VERSION + " •  LGPL-2.0 License")
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
        if hasattr(self, 'btn_editor'):
            self.btn_editor.setVisible(index == 0)

    def load_video_tab(self):
        if getattr(self, 'video_tab_loaded', False):
            return
        self.video_tab_loaded = True
        from widgets.capture_tabs import VideoTab
        tab_video = VideoTab(self)
        icon = self.tabs.tabIcon(1)
        text = self.tabs.tabText(1)
        self.tabs.blockSignals(True)
        self.tabs.removeTab(1)
        self.tabs.insertTab(1, tab_video, icon, text)
        self.tabs.setCurrentIndex(1)
        self.tabs.blockSignals(False)

    def show_cursor_settings(self):
        btn = self.sender()
        if not hasattr(self, 'cursor_popup') or self.cursor_popup is None:
            from capture.capture_cursor_dlg import CursorSettings
            self.cursor_popup = CursorSettings(self)
            
        pos = btn.mapToGlobal(btn.rect().topRight())
        self.cursor_popup.move(pos.x() + 5, pos.y() - 20)
        self.cursor_popup.show()

    def save_toggle_state(self, label_text, state):
        from config import load_config, save_config
        config_data = load_config()
        if "toggles" not in config_data:
            config_data["toggles"] = {}
        is_checked = (state == Qt.CheckState.Checked.value) if isinstance(state, int) else bool(state)
        config_data["toggles"][label_text] = is_checked
        save_config(config_data)

    def _hide_editor_before_capture(self):
        try:
            from editor.editor_main import ImageEditor
            if ImageEditor._instance and ImageEditor._instance.isVisible():
                ImageEditor._instance._hidden_by_capture = True
                ImageEditor._instance.hide()
        except Exception:
            pass

    def start_capture(self):
        self.hide()
        self._hide_editor_before_capture()
        capture_cursor = self.toggles.get("Capture Cursor", None)
        self._has_cursor = capture_cursor.isChecked() if capture_cursor else False
        
        delay_toggle = self.toggles.get("5 Second Delay", None)
        has_delay = delay_toggle.isChecked() if delay_toggle else False
        
        scroll_toggle = self.toggles.get("Scroll Capture", None)
        self._is_scroll = scroll_toggle.isChecked() if scroll_toggle else False
        
        if has_delay:
            from capture.capture_countdown import Countdown
            self.countdown = Countdown(5)
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
        self._hide_editor_before_capture()
        capture_cursor = self.toggles.get("Capture Cursor (Video)", None)
        self._has_cursor = capture_cursor.isChecked() if capture_cursor else False
        self._is_scroll = False
        
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._do_overlay(is_video=True))
        
    def _do_overlay(self, is_video=False):
        from capture.capture_overlay import Overlay
        self.overlay = Overlay(self.library_dir, self._has_cursor, self._is_scroll, is_video)
        self.overlay.capture_finished.connect(self.show_after_capture)
        self.overlay.show()
        self.overlay.activateWindow()
        self.overlay.raise_()
        self.overlay.setFocus()

    def show_after_capture(self):
        try:
            from editor.editor_main import ImageEditor
            if ImageEditor._instance and getattr(ImageEditor._instance, '_hidden_by_capture', False):
                ImageEditor._instance._hidden_by_capture = False
                ImageEditor._instance.show()
                ImageEditor._instance.raise_()
        except Exception:
            pass

        try:
            from editor.editor_main import ImageEditor
            if ImageEditor._instance and ImageEditor._instance.isVisible():
                self.hide()
                return
        except Exception:
            pass

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

        vk_video  = hotkeys.get("video_hotkey", {}).get("vk", 0x56)
        mods_video = hotkeys.get("video_hotkey", {}).get("modifiers", 6)
        if vk_video:
            Platform.register_hotkey(int(self.winId()), self.HOTKEY_VIDEO_ID, mods_video, vk_video)

        vk_image  = hotkeys.get("image_hotkey", {}).get("vk", 0x50)
        mods_image = hotkeys.get("image_hotkey", {}).get("modifiers", 6)
        if vk_image:
            Platform.register_hotkey(int(self.winId()), self.HOTKEY_IMAGE_ID, mods_image, vk_image)

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
        if sys.platform == "win32":
            import ctypes.wintypes
            if eventType in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                msg = ctypes.wintypes.MSG.from_address(message.__int__())
                if msg.message == 0x0312:
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
