'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QTabWidget, QLabel
from PySide6.QtCore import Qt, QTimer
from ui.overlay_window import OverlayWindow
from ui.toggle_switch import ToggleSwitch
from ui.countdown_window import CountdownWindow

class MainWindow(QMainWindow):
    def __init__(self, library_dir):
        super().__init__()
        self.library_dir = library_dir
        self.setWindowTitle("CutScreen Capture")
        self.setFixedSize(420, 250)
        
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
                border-bottom: 2px solid #1976d2; 
            }
            #CaptureButton { 
                background-color: #d32f2f; 
                color: white; 
                font-weight: bold; 
                font-size: 18px; 
                border-radius: 45px; /* Perfect circle for 90x90 */
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
        tab_video_layout = QVBoxLayout(tab_video)
        tab_video_layout.addWidget(QLabel("Video Recording coming soon."))
        self.tabs.addTab(tab_video, "Video")
        
        self.tabs.setCurrentIndex(0)
        main_layout.addWidget(self.tabs)
        
        # Bottom Bar
        bottom_bar = QWidget()
        bottom_bar.setObjectName("BottomBar")
        bottom_bar.setFixedHeight(35)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(15, 0, 15, 0)
        
        lbl_presets = QLabel("⚙ Preference(X)")
        lbl_editor = QLabel("📝 Open Editor(X)")
        lbl_presets.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl_editor.setCursor(Qt.CursorShape.PointingHandCursor)
        
        bottom_layout.addWidget(lbl_presets)
        bottom_layout.addStretch()
        bottom_layout.addWidget(lbl_editor)
        
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

    def setup_image_tab(self, tab):
        from config import load_config
        config_data = load_config()
        toggles_config = config_data.get("toggles", {})
        
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Left side: Settings with Toggles
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(15)
        
        self.add_setting_row(settings_layout, "Preview in Editor(X)", toggles_config.get("Preview in Editor(X)", True))
        self.add_setting_row(settings_layout, "Copy to Clipboard", toggles_config.get("Copy to Clipboard", True))
        self.add_setting_row(settings_layout, "Capture Cursor", toggles_config.get("Capture Cursor", False))
        self.add_setting_row(settings_layout, "5 Second Delay", toggles_config.get("5 Second Delay", False))
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout, stretch=2)
        
        # Right side: Capture Button
        capture_layout = QVBoxLayout()
        
        self.capture_btn = QPushButton("Capture")
        self.capture_btn.setObjectName("CaptureButton")
        self.capture_btn.setFixedSize(90, 90)
        self.capture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.capture_btn.clicked.connect(self.start_capture)
        
        lbl_hotkey = QLabel("Quick Capture")
        lbl_hotkey.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hotkey.setStyleSheet("color: #888888; font-size: 13px; margin-top: 5px;")
        
        capture_layout.addStretch()
        capture_layout.addWidget(self.capture_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addWidget(lbl_hotkey, alignment=Qt.AlignmentFlag.AlignCenter)
        capture_layout.addStretch()
        
        layout.addLayout(capture_layout, stretch=1)

    def add_setting_row(self, layout, label_text, is_checked=False):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        from ui.toggle_switch import ToggleSwitch
        toggle = ToggleSwitch()
        toggle.setChecked(is_checked)
        self.toggles[label_text] = toggle
        
        toggle.stateChanged.connect(lambda state, text=label_text: self.save_toggle_state(text, state))
        
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(toggle)
        layout.addLayout(row)

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
        
        if has_delay:
            self.countdown = CountdownWindow(5)
            self.countdown.finished.connect(self._do_overlay)
            self.countdown.show()
        else:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, self._do_overlay)
        
    def _do_overlay(self):
        self.overlay = OverlayWindow(self.library_dir, self._has_cursor)
        self.overlay.show()
        self.overlay.activateWindow()
        self.overlay.raise_()
        self.overlay.setFocus()

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
