'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import logging
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt
from config import load_config, save_config
import soundcard as sc
from capture.capture_prefs_ui import PreferencesUI

class Preferences(PreferencesUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_hw_accel_controls()

    def init_hw_accel_controls(self):
        from core.capture_codecs import get_cached_hw_encoders, detect_available_hw_encoders
        cached = get_cached_hw_encoders()
        if cached is not None:
            self._apply_hw_encoders(cached)
        else:
            self.cb_hw_encoder.clear()
            self.cb_hw_encoder.addItem("Detecting GPU...", "")
            self.cb_hw_encoder.setEnabled(False)
            import threading
            from PySide6.QtCore import QTimer
            def _detect_bg():
                encs = detect_available_hw_encoders()
                QTimer.singleShot(0, lambda: self._apply_hw_encoders(encs))
            threading.Thread(target=_detect_bg, daemon=True).start()

    def _apply_hw_encoders(self, encoders):
        cfg = load_config()
        saved_encoder = cfg.get("hw_encoder", "")
        
        if encoders:
            try:
                self.chk_hw_accel.toggled.disconnect()
            except Exception as e:
                logging.debug("Disconnecting chk_hw_accel toggled failed: %s", e, exc_info=True)
            self.chk_hw_accel.setText("Hardware Acceleration:")
            self.chk_hw_accel.setEnabled(True)
            self.cb_hw_encoder.clear()
            for codec_id, display_name in encoders:
                self.cb_hw_encoder.addItem(display_name, codec_id)
                
            idx = -1
            if saved_encoder:
                idx = self.cb_hw_encoder.findData(saved_encoder)
            if idx >= 0:
                self.cb_hw_encoder.setCurrentIndex(idx)
            else:
                self.cb_hw_encoder.setCurrentIndex(0)
                
            self.chk_hw_accel.toggled.connect(self.cb_hw_encoder.setEnabled)
            self.cb_hw_encoder.setEnabled(self.chk_hw_accel.isChecked())
        else:
            # N/A: No hardware acceleration available
            self.chk_hw_accel.setText("Hardware Acceleration (N/A):")
            self.chk_hw_accel.setChecked(False)
            self.chk_hw_accel.setEnabled(False)
            self.cb_hw_encoder.clear()
            self.cb_hw_encoder.addItem("N/A (Software Only)", "")
            self.cb_hw_encoder.setEnabled(False)

    def load_audio_devices(self):
        self.cb_audio.clear()
        mics = []
        try:
            mics = sc.all_microphones(include_loopback=False)
        except Exception as e:
            logging.warning("Error loading sound devices: %s", e, exc_info=True)
            
        if not mics:
            self.cb_audio.addItem("No Microphone Detected")
            self.cb_audio.setEnabled(False)
            if hasattr(self, 'lbl_audio'):
                self.lbl_audio.setEnabled(False)
        else:
            for m in mics:
                self.cb_audio.addItem(m.name)
            self.cb_audio.setEnabled(True)
            if hasattr(self, 'lbl_audio'):
                self.lbl_audio.setEnabled(True)

    def save_and_close(self):
        cfg = load_config()
        cfg["video_compression"] = self.cb_compression.currentText()
        cfg["audio_source"] = self.cb_audio.currentText() if self.cb_audio.isEnabled() else ""
        cfg["limit_1080p"] = self.toggle_1080p.isChecked()
        cfg["hw_accel"] = self.chk_hw_accel.isChecked()
        cfg["hw_encoder"] = self.cb_hw_encoder.currentData() or ""
        save_config(cfg)
        self.accept()

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
