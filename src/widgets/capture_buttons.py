'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QMenu
from PySide6.QtCore import Qt, QSize, QPoint, Signal
from PySide6.QtGui import QIcon

def create_toolbar_button(
    text: str = "",
    icon: QIcon = None,
    icon_size: QSize = QSize(22, 22),
    color_theme: str = "default",
    checkable: bool = False,
    checked: bool = False,
    radius_type: str = "all", # "all", "left", "right"
    padding: str = "8px 12px",
    fixed_width: int = None,
    fixed_height: int = None
) -> QPushButton:
    """Create a standardized toolbar QPushButton with rich 3D tactile styling.
    
    Parameters:
        text (str): Button text label.
        icon (QIcon): Optional button icon.
        icon_size (QSize): Size of the icon.
        color_theme (str): Color theme ("default", "red", "cancel", "menu_arrow").
        checkable (bool): Whether the button is checkable (toggle switch).
        checked (bool): Initial checked state.
        radius_type (str): Corner radius style ("all", "left", "right").
        padding (str): Inner padding CSS.
        fixed_width (int): Optional fixed width in pixels.
    """
    btn = QPushButton(text)
    if icon:
        btn.setIcon(icon)
        btn.setIconSize(icon_size)
        
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if checkable:
        btn.setCheckable(True)
        btn.setChecked(checked)
        
    if fixed_width is not None:
        btn.setFixedWidth(fixed_width)
    if fixed_height is not None:
        btn.setFixedHeight(fixed_height)

    # Corner radius logic for split buttons or regular buttons
    if radius_type == "left":
        radius_css = "border-top-left-radius: 6px; border-bottom-left-radius: 6px; border-top-right-radius: 0; border-bottom-right-radius: 0;"
    elif radius_type == "right":
        radius_css = "border-top-left-radius: 0; border-bottom-left-radius: 0; border-top-right-radius: 6px; border-bottom-right-radius: 6px;"
    else:
        radius_css = "border-radius: 6px;"

    border_css = "border: 1px solid rgba(255, 255, 255, 35);"

    # Generate theme-specific QSS
    if color_theme == "red":
        bg_norm = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e53935, stop:1 #b71c1c)"
        bg_hov  = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5252, stop:1 #d32f2f)"
        bg_pres = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b71c1c, stop:1 #8e0000)"
        qss = f"""
            QPushButton {{ background: {bg_norm}; padding: {padding}; {radius_css} {border_css} color: white; font-weight: bold; }}
            QPushButton:hover {{ background: {bg_hov}; border: 1px solid rgba(255, 255, 255, 60); }}
            QPushButton:pressed {{ background: {bg_pres}; }}
        """
    elif color_theme == "blue":
        bg_norm = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #42a5f5, stop:1 #1976d2)"
        bg_hov  = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #64b5f6, stop:1 #2196f3)"
        bg_pres = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1976d2, stop:1 #0d47a1)"
        qss = f"""
            QPushButton {{ background: {bg_norm}; padding: {padding}; {radius_css} {border_css} color: white; font-weight: bold; }}
            QPushButton:hover {{ background: {bg_hov}; border: 1px solid rgba(255, 255, 255, 60); }}
            QPushButton:pressed {{ background: {bg_pres}; }}
        """
    elif color_theme == "cancel":
        bg_norm = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a5a5a, stop:1 #3e3e3e)"
        bg_hov  = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6a6a6a, stop:1 #4e4e4e)"
        bg_pres = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3e3e3e, stop:1 #2a2a2a)"
        qss = f"""
            QPushButton {{ background: {bg_norm}; padding: {padding}; {radius_css} {border_css} color: #dddddd; }}
            QPushButton:hover {{ background: {bg_hov}; color: white; }}
            QPushButton:pressed {{ background: {bg_pres}; }}
        """
    elif color_theme == "menu_arrow":
        qss = f"""
            QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #505050, stop:1 #383838); color: #aaaaaa; font-size: 10px; {radius_css} border-top: 1px solid rgba(255,255,255,35); border-bottom: 1px solid rgba(255,255,255,35); border-right: 1px solid rgba(255,255,255,35); border-left: none; }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #606060, stop:1 #484848); color: white; }}
            QPushButton:pressed {{ background: #2b2b2b; }}
        """
    else:  # "default" toggle theme (grey when off, green when on)
        bg_off      = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #505050, stop:1 #383838)"
        bg_off_hov  = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #606060, stop:1 #484848)"
        bg_on       = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43a047, stop:1 #2e7d32)"
        bg_on_hov   = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4caf50, stop:1 #388e3c)"
        
        qss = f"""
            QPushButton {{ background: {bg_off}; padding: {padding}; {radius_css} {border_css} color: white; }}
            QPushButton:hover {{ background: {bg_off_hov}; }}
            QPushButton:checked {{ background: {bg_on}; border: 1px solid rgba(255, 255, 255, 50); }}
            QPushButton:checked:hover {{ background: {bg_on_hov}; }}
            QPushButton:pressed {{ background: #2b2b2b; }}
        """

    btn.setStyleSheet(qss)
    return btn


class SplitMenuButton(QWidget):
    """Standardized independent split button component supporting QMenu and custom QWidget popups."""
    arrow_clicked = Signal()

    def __init__(
        self,
        text: str = "",
        icon: QIcon = None,
        icon_size: QSize = QSize(22, 22),
        color_theme: str = "default",
        checkable: bool = False,
        checked: bool = False,
        padding: str = "8px 12px",
        fixed_height: int = 40,
        arrow_width: int = 20,
        parent: QWidget = None
    ):
        super().__init__(parent)
        self.color_theme = color_theme
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main action/toggle button
        self.main_btn = create_toolbar_button(
            text=text,
            icon=icon,
            icon_size=icon_size,
            color_theme=color_theme,
            checkable=checkable,
            checked=checked,
            radius_type="left",
            padding=padding,
            fixed_height=fixed_height
        )
        
        # Dropdown arrow button
        self.arrow_btn = create_toolbar_button(
            text="▼",
            color_theme="menu_arrow",
            radius_type="right",
            fixed_width=arrow_width,
            fixed_height=fixed_height
        )
        
        # Attached default popup menu
        self.menu = QMenu(self)
        self.menu.setStyleSheet("""
            QMenu { background-color: #2b2b2b; color: #dddddd; border: 1px solid #555; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 24px 6px 24px; border-radius: 4px; }
            QMenu::item:selected { background-color: #388e3c; color: white; }
        """)
        self.popup_widget = self.menu
        
        # Connect popup action
        self.arrow_btn.clicked.connect(self._show_menu)
        
        # Connect style sync if checkable
        if checkable:
            self.main_btn.toggled.connect(self._update_arrow_style)
            self._update_arrow_style(self.main_btn.isChecked())
            
        layout.addWidget(self.main_btn)
        layout.addWidget(self.arrow_btn)
        
    def _show_menu(self):
        self.arrow_clicked.emit()
        if self.popup_widget:
            pos = self.arrow_btn.mapToGlobal(QPoint(0, self.arrow_btn.height() + 4))
            if isinstance(self.popup_widget, QMenu):
                self.popup_widget.exec(pos)
            elif isinstance(self.popup_widget, QWidget):
                self.popup_widget.move(pos)
                self.popup_widget.show()
                self.popup_widget.raise_()
        
    def _update_arrow_style(self, checked: bool):
        radius_css = "border-top-left-radius: 0; border-bottom-left-radius: 0; border-top-right-radius: 6px; border-bottom-right-radius: 6px;"
        if self.color_theme == "default":
            if checked:
                bg_norm = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43a047, stop:1 #2e7d32)"
                bg_hov  = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4caf50, stop:1 #388e3c)"
                border_css = "border-top: 1px solid rgba(255,255,255,50); border-bottom: 1px solid rgba(255,255,255,50); border-right: 1px solid rgba(255,255,255,50); border-left: none;"
                color = "white"
            else:
                bg_norm = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #505050, stop:1 #383838)"
                bg_hov  = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #606060, stop:1 #484848)"
                border_css = "border-top: 1px solid rgba(255,255,255,35); border-bottom: 1px solid rgba(255,255,255,35); border-right: 1px solid rgba(255,255,255,35); border-left: none;"
                color = "#aaaaaa"
        else:
            bg_norm = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #505050, stop:1 #383838)"
            bg_hov  = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #606060, stop:1 #484848)"
            border_css = "border-top: 1px solid rgba(255,255,255,35); border-bottom: 1px solid rgba(255,255,255,35); border-right: 1px solid rgba(255,255,255,35); border-left: none;"
            color = "#aaaaaa"

        dis_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #505050, stop:1 #383838)"
        dis_border = "border-top: 1px solid rgba(255,255,255,35); border-bottom: 1px solid rgba(255,255,255,35); border-right: 1px solid rgba(255,255,255,35); border-left: none;"

        qss = (
            f"QPushButton {{ background: {bg_norm}; color: {color}; font-size: 10px; {radius_css} {border_css} }}\n"
            f"QPushButton:hover {{ background: {bg_hov}; color: white; }}\n"
            "QPushButton:pressed { background: #2b2b2b; }\n"
            f"QPushButton:disabled {{ background: {dis_bg}; color: #666666; {radius_css} {dis_border} }}"
        )
        self.arrow_btn.setStyleSheet(qss)
        self.arrow_btn.setEnabled(checked)
        if self.popup_widget:
            self.popup_widget.setEnabled(checked)
        
    def addAction(self, action):
        return self.menu.addAction(action)

    def setPopup(self, popup: QWidget):
        """Attach any custom QWidget or QMenu as the dropdown popup."""
        self.popup_widget = popup

    @property
    def clicked(self):
        return self.main_btn.clicked

    @property
    def toggled(self):
        return self.main_btn.toggled

    def isChecked(self) -> bool:
        return self.main_btn.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.main_btn.setChecked(checked)

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self.main_btn.setEnabled(enabled)
        if not enabled:
            self.arrow_btn.setEnabled(False)
            if self.popup_widget:
                self.popup_widget.setEnabled(False)
        else:
            is_active = self.main_btn.isChecked() if self.main_btn.isCheckable() else True
            self.arrow_btn.setEnabled(is_active)
            if self.popup_widget:
                self.popup_widget.setEnabled(is_active)

