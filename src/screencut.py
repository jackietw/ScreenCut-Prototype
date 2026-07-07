'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import sys
import os
import logging

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction
from capture.capture_main import Main

def get_documents_folder():
    from platforms import Platform
    return Platform.get_documents_folder()


def global_exception_handler(exc_type, exc_value, exc_tb):
    import traceback
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        from config import get_app_config_dir
        crash_log_path = os.path.join(get_app_config_dir(), "crash.log")
        with open(crash_log_path, "a", encoding="utf-8") as f:
            f.write(error_msg + "\n")
    except Exception as e:
        logging.debug("Failed to write crash log: %s", e, exc_info=True)
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
                from editor.editor_main import ImageEditor
                ImageEditor.get_instance(library_dir, current_filepath=file_path)
            return True
        return super().event(e)


def main():
    import sys
    from config import setup_logging
    setup_logging()   # Must be first - configures logging for the whole app
    sys.excepthook = global_exception_handler
    is_editor_mode = "--editor" in sys.argv or "editor" in sys.argv[0].lower() or (len(sys.argv) > 1 and sys.argv[1].lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.scut')))
    if sys.platform == 'win32':
        import ctypes
        app_id = 'screencut.editor.app.v1' if is_editor_mode else 'screencut.capture.app.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    from platforms import Platform
    Platform.init_dpi_awareness()
    app = ScreenCut(sys.argv)
    app.setStyleSheet("QToolTip { background-color: #1e293b; color: #f8fafc; border: 1px solid #475569; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }")
    
    from resources.icon_utils import get_app_icon
    app_icon = get_app_icon(is_editor_mode)
    app.setWindowIcon(app_icon)
    
    if is_editor_mode:
        app.setQuitOnLastWindowClosed(True)
        docs_dir = get_documents_folder()
        library_dir = os.path.join(docs_dir, "My ScreenCut Library")
        os.makedirs(library_dir, exist_ok=True)
        from editor.editor_main import ImageEditor
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
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    lock_path = os.path.join(QDir.tempPath(), "ScreenCut_Unique_Instance.lock")
    lock_file = QLockFile(lock_path)
    lock_file.setStaleLockTime(1000)
    if not lock_file.tryLock(100):
        sock = QLocalSocket()
        sock.connectToServer("ScreenCut_IPC_Server")
        if sock.waitForConnected(500):
            msg = "OPEN_EDITOR" if ("--editor" in sys.argv or "-e" in sys.argv) else "SHOW_NORMAL"
            sock.write(msg.encode('utf-8'))
            sock.flush()
            sock.waitForBytesWritten(500)
            sock.disconnectFromServer()
            sys.exit(0)
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
    from core.capture_codecs import detect_available_hw_encoders
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
    
    def cleanup_before_quit():
        try:
            from editor.editor_main import ImageEditor
            if ImageEditor._instance and hasattr(ImageEditor._instance, 'canvas'):
                canvas = ImageEditor._instance.canvas
                if hasattr(canvas, '_auto_save_timer') and canvas._auto_save_timer.isActive():
                    canvas._auto_save_timer.stop()
                    canvas._perform_auto_save()
        except Exception as e:
            logging.debug("Error flushing editor auto-save on quit: %s", e, exc_info=True)

        try:
            from core.capture_video import VideoCaptureManager
            from capture.capture_overlay import Overlay
            vm = VideoCaptureManager._active_instance or getattr(Overlay, 'video_manager', None)
            if vm and hasattr(vm, 'thread') and vm.thread and vm.thread.isRunning():
                vm.stop_capture()
                vm.thread.wait(3000)
        except Exception as e:
            logging.debug("Error stopping active video capture on quit: %s", e, exc_info=True)

    app.aboutToQuit.connect(cleanup_before_quit)

    def force_quit():
        tray_icon.hide()
        cleanup_before_quit()
        try:
            window.close()
        except Exception as e:
            logging.debug("Exception while closing main window: %s", e, exc_info=True)
        app.quit()
        
    quit_action = QAction("Quit", window)
    quit_action.triggered.connect(force_quit)
    tray_menu.addAction(quit_action)
    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    
    # Double click tray icon to show window
    tray_icon.activated.connect(
        lambda reason: window.showNormal() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
    )

    QLocalServer.removeServer("ScreenCut_IPC_Server")
    ipc_server = QLocalServer()
    ipc_server.listen("ScreenCut_IPC_Server")
    def handle_ipc_connection():
        sock = ipc_server.nextPendingConnection()
        if sock and sock.waitForReadyRead(500):
            msg = bytes(sock.readAll()).decode('utf-8')
            if msg == "OPEN_EDITOR":
                window.open_editor()
            elif msg == "SHOW_NORMAL":
                window.showNormal()
                window.activateWindow()
            elif msg == "START_CAPTURE":
                window.start_capture()
    ipc_server.newConnection.connect(handle_ipc_connection)
    app._ipc_server = ipc_server

    if "--editor" in sys.argv or "-e" in sys.argv:
        window.open_editor()
    else:
        window.show()
    app.exec()

if __name__ == "__main__":
    main()
