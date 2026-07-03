'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QTabWidget, QLabel
from PySide6.QtCore import Qt, QSize
from widgets.capture_switch import Switch
from version import CAPTURE_VERSION
from resources.icon_utils import create_svg_icon, SVG_TAB_IMAGE, SVG_TAB_VIDEO, SVG_PREF, SVG_EDITOR, SVG_CLOSE, SVG_ABOUT, SVG_MORE

class MainUI(QMainWindow):
    def __init__(self, library_dir):
        super().__init__()
        self.library_dir = library_dir
        self.setWindowTitle(f"ScreenCut Capture v{CAPTURE_VERSION}")
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
        
        # Tabs at the top
        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        self.tabs.tabBar().setExpanding(False)
        
        self.toggles = {}
        
        # Image Tab (Default loaded)
        from widgets.capture_tabs import ImageTab
        tab_image = ImageTab(self)
        self.tabs.addTab(tab_image, create_svg_icon(SVG_TAB_IMAGE), "Image")
        
        # Video Tab (Lazy loaded placeholder)
        self.video_tab_loaded = False
        tab_video_placeholder = QWidget()
        self.tabs.addTab(tab_video_placeholder, create_svg_icon(SVG_TAB_VIDEO), "Video")
        
        self.tabs.setCurrentIndex(0)
        main_layout.addWidget(self.tabs)
        
        # Bottom Bar
        bottom_bar = QWidget()
        bottom_bar.setObjectName("BottomBar")
        bottom_bar.setFixedHeight(35)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(15, 0, 15, 0)
        
        self.btn_presets = QPushButton("Preference")
        self.btn_presets.setIcon(create_svg_icon(SVG_PREF))
        self.btn_presets.setIconSize(QSize(18, 18))
        self.btn_presets.setStyleSheet("color: #aaaaaa; font-size: 14px; background: transparent; border: none; text-align: left;")
        self.btn_presets.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_editor = QPushButton("Open Editor")
        self.btn_editor.setIcon(create_svg_icon(SVG_EDITOR))
        self.btn_editor.setIconSize(QSize(18, 18))
        self.btn_editor.setStyleSheet("color: #aaaaaa; font-size: 14px; background: transparent; border: none; text-align: left;")
        self.btn_editor.setCursor(Qt.CursorShape.PointingHandCursor)
        
        bottom_layout.addWidget(self.btn_presets)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_editor)
        
        main_layout.addWidget(bottom_bar)
        
        # Absolute positioned close button
        self.close_btn = QPushButton("", central_widget)
        self.close_btn.setIcon(create_svg_icon(SVG_CLOSE))
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.move(self.width() - 31, 1)
        self.close_btn.raise_()
        
        self.about_btn = QPushButton("", central_widget)
        self.about_btn.setIcon(create_svg_icon(SVG_ABOUT))
        self.about_btn.setObjectName("AboutButton")
        self.about_btn.setFixedSize(30, 30)
        self.about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.about_btn.move(self.width() - 61, 1)
        self.about_btn.raise_()

    def add_setting_row(self, layout, label_text, is_checked=False, has_details=False, key_name=None):
        if key_name is None:
            key_name = label_text
            
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        toggle = Switch()
        if key_name == "Record Microphone":
            try:
                import soundcard as sc
                mics = sc.all_microphones(include_loopback=False)
                if not mics:
                    is_checked = False
                    toggle.setEnabled(False)
                    lbl.setEnabled(False)
            except Exception:
                pass
        elif key_name == "Record System Audio":
            try:
                import soundcard as sc
                speakers = sc.all_speakers()
                if not speakers:
                    is_checked = False
                    toggle.setEnabled(False)
                    lbl.setEnabled(False)
            except Exception:
                pass
        toggle.setChecked(is_checked)
        self.toggles[key_name] = toggle
        
        if hasattr(self, 'save_toggle_state'):
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
            btn_details = QPushButton()
            btn_details.setIcon(create_svg_icon(SVG_MORE))
            btn_details.setIconSize(QSize(20, 20))
            btn_details.setFixedSize(24, 24)
            btn_details.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_details.setStyleSheet("background: transparent; border: none;")
            if hasattr(self, 'show_cursor_settings'):
                btn_details.clicked.connect(self.show_cursor_settings)
            rc_layout.addWidget(btn_details)
        else:
            spacer = QWidget()
            spacer.setFixedSize(20, 20)
            rc_layout.addWidget(spacer)
            
        row.addWidget(right_container)
        layout.addLayout(row)
