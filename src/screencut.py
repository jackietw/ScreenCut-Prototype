'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import sys
import os

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction
from ui.main import Main

def get_documents_folder():
    from platforms import Platform
    return Platform.get_documents_folder()


def global_exception_handler(exc_type, exc_value, exc_tb):
    import traceback
    import logging
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    # Always write to crash.log (legacy) and to the rotating log via logging
    with open("crash.log", "a") as f:
        f.write(error_msg + "\n")
    logging.critical(error_msg)
    # Only show dialog in debug mode
    from config import is_debug_mode
    if is_debug_mode():
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "ScreenCut Error", f"An unexpected error occurred:\n\n{error_msg}")

from PySide6.QtCore import QEvent

class ScreenCut(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self._lock_file = None

    def event(self, e):
        if e.type() == QEvent.Type.FileOpen:
            file_path = e.file()
            if file_path and os.path.exists(file_path):
                from platforms import Platform
                library_dir = os.path.join(Platform.get_documents_folder(), "My ScreenCut Library")
                from ui.image_editor import ImageEditor
                ImageEditor.get_instance(library_dir, current_filepath=file_path)
            return True
        return super().event(e)


def main():
    import sys
    from config import setup_logging
    setup_logging()   # Must be first - configures logging for the whole app
    sys.excepthook = global_exception_handler
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('screencut.capture.app.v1')
    app = ScreenCut(sys.argv)
    
    from resources.icon_utils import create_svg_icon, SVG_APP_ICON
    app_icon = create_svg_icon(SVG_APP_ICON, 64, 64)
    app.setWindowIcon(app_icon)
    
    # CLI Editor Mode / File association launch
    is_editor_mode = "--editor" in sys.argv or (len(sys.argv) > 1 and sys.argv[1].lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.scut')))
    if is_editor_mode:
        app.setQuitOnLastWindowClosed(True)
        docs_dir = get_documents_folder()
        library_dir = os.path.join(docs_dir, "My ScreenCut Library")
        os.makedirs(library_dir, exist_ok=True)
        from ui.image_editor import ImageEditor
        from PySide6.QtGui import QImage
        file_path = None
        for arg in sys.argv[1:]:
            if arg != "--editor" and os.path.isfile(arg):
                file_path = arg
                break
        if file_path and file_path.lower().endswith('.scut'):
            editor = ImageEditor.get_instance(library_dir, current_filepath=file_path)
        else:
            editor = ImageEditor.get_instance(library_dir, initial_image=QImage(file_path) if file_path else None, current_filepath=file_path)
        sys.exit(app.exec())

    # Single Instance Check via QLockFile (reliable cross-platform cleanup)
    from PySide6.QtCore import QLockFile, QDir
    lock_path = os.path.join(QDir.tempPath(), "ScreenCut_Unique_Instance.lock")
    lock_file = QLockFile(lock_path)
    lock_file.setStaleLockTime(1000)
    if not lock_file.tryLock(100):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(None, "ScreenCut", "ScreenCut is already running in the background.\nPlease check your System Tray.")
        sys.exit(0)
    app._lock_file = lock_file
    
    # Keep application running when the main window is closed
    app.setQuitOnLastWindowClosed(False)

    # Ensure library folder exists
    docs_dir = get_documents_folder()
    library_dir = os.path.join(docs_dir, "My ScreenCut Library")
    os.makedirs(library_dir, exist_ok=True)

    # Pre-warm hardware video codec detection in the background
    import threading
    from core.video_codecs import detect_available_hw_encoders
    threading.Thread(target=detect_available_hw_encoders, daemon=True).start()

    window = Main(library_dir)
    
    # Setup System Tray
    tray_icon = QSystemTrayIcon(window)
    tray_icon.setIcon(app_icon)
    tray_icon.setToolTip("ScreenCut")
    
    tray_menu = QMenu()
    
    show_action = QAction("Open ScreenCut", window)
    show_action.triggered.connect(window.showNormal)
    tray_menu.addAction(show_action)
    
    capture_action = QAction("Capture", window)
    capture_action.triggered.connect(window.start_capture)
    tray_menu.addAction(capture_action)
    
    editor_action = QAction("Open Image Editor", window)
    editor_action.triggered.connect(lambda: window.open_editor())
    tray_menu.addAction(editor_action)
    
    tray_menu.addSeparator()
    
    def force_quit():
        tray_icon.hide()
        # Forcefully terminate the application
        os._exit(0)
        
    quit_action = QAction("Quit", window)
    quit_action.triggered.connect(force_quit)
    tray_menu.addAction(quit_action)
    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    
    # Double click tray icon to show window
    tray_icon.activated.connect(
        lambda reason: window.showNormal() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
    )

    window.show()
    app.exec()

if __name__ == "__main__":
    main()
