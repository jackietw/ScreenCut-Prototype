'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import sys
import os

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Keep application running when the main window is closed
    app.setQuitOnLastWindowClosed(False)

    # Ensure library folder exists
    library_dir = os.path.join(os.path.expanduser("~"), "Documents", "CutScreenLibrary")
    os.makedirs(library_dir, exist_ok=True)

    window = MainWindow(library_dir)
    
    # Setup System Tray
    tray_icon = QSystemTrayIcon(window)
    # Using a standard system icon as placeholder
    icon = window.style().standardIcon(window.style().StandardPixmap.SP_ComputerIcon)
    tray_icon.setIcon(icon)
    
    tray_menu = QMenu()
    
    show_action = QAction("Open CutScreen", window)
    show_action.triggered.connect(window.showNormal)
    tray_menu.addAction(show_action)
    
    capture_action = QAction("Capture", window)
    capture_action.triggered.connect(window.start_capture)
    tray_menu.addAction(capture_action)
    
    tray_menu.addSeparator()
    
    quit_action = QAction("Quit", window)
    quit_action.triggered.connect(app.quit)
    tray_menu.addAction(quit_action)
    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    
    # Double click tray icon to show window
    tray_icon.activated.connect(
        lambda reason: window.showNormal() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
    )

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
