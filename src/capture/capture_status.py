'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import threading
import numpy as np
from PySide6.QtCore import QTimer
from capture.capture_status_ui import RecStatusUI

class RecStatus(RecStatusUI):
    def __init__(self, parent=None):
        self._audio_level = 0.0
        self._audio_thread = None
        self._audio_running = False
        super().__init__(parent)
        self._vu_timer = QTimer(self)
        self._vu_timer.timeout.connect(self._update_vu)
        self._vu_timer.start(60)

    def update_cursor_status(self, is_on: bool):
        if is_on:
            self.lbl_cursor_main.setText("ON")
            self.lbl_cursor_main.setStyleSheet("color: #4caf50; font-size: 13px; font-weight: 700;")
        else:
            self.lbl_cursor_main.setText("OFF")
            self.lbl_cursor_main.setStyleSheet("color: #cccccc; font-size: 13px; font-weight: 500;")

        from config import load_config
        cfg = load_config()
        c_settings = cfg.get("cursor_settings", {})
        hl_on = c_settings.get("highlight", True) and is_on
        anim_on = c_settings.get("click", True) and is_on
        
        self.lbl_cursor_hl.setText("ON" if hl_on else "OFF")
        self.lbl_cursor_anim.setText("ON" if anim_on else "OFF")

    def update_audio_status(self, is_audio_on: bool):
        try:
            import soundcard as sc
            if not sc.all_microphones(include_loopback=False):
                self._is_audio_on = False
                self.lbl_audio_on.setText("N/A")
                self.lbl_audio_on.setStyleSheet("color: #888888; font-size: 13px; font-weight: 500;")
                self.set_audio_device_name("No Microphone Detected")
                self._stop_audio_monitor()
                self.vu.set_level(0)
                return
        except Exception:
            pass
        self._is_audio_on = is_audio_on
        from config import load_config
        cfg = load_config()
        if is_audio_on:
            self.lbl_audio_on.setText("ON")
            self.lbl_audio_on.setStyleSheet("color: #4caf50; font-size: 13px; font-weight: 700;")
            dev_name = cfg.get("audio_source", "Default Microphone")
            if not dev_name or dev_name == "None (Muted)":
                dev_name = "Default Microphone"
            self.set_audio_device_name(dev_name)
            self._start_audio_monitor()
        else:
            self.lbl_audio_on.setText("OFF")
            self.lbl_audio_on.setStyleSheet("color: #cccccc; font-size: 13px; font-weight: 500;")
            self.set_audio_device_name("None (Muted)")
            self._stop_audio_monitor()
            self.vu.set_level(0)

    def update_sys_audio_status(self, is_on: bool):
        try:
            import soundcard as sc
            if not sc.all_speakers():
                self._is_sys_audio_on = False
                self.lbl_sys_audio_on.setText("N/A")
                self.lbl_sys_audio_on.setStyleSheet("color: #888888; font-size: 13px; font-weight: 500;")
                return
        except Exception:
            pass
        self._is_sys_audio_on = is_on
        if is_on:
            self.lbl_sys_audio_on.setText("ON")
            self.lbl_sys_audio_on.setStyleSheet("color: #4caf50; font-size: 13px; font-weight: 700;")
        else:
            self.lbl_sys_audio_on.setText("OFF")
            self.lbl_sys_audio_on.setStyleSheet("color: #cccccc; font-size: 13px; font-weight: 500;")

    def set_audio_device_name(self, name: str):
        self.lbl_mic_device.setText(name[:30] if name else "System Default")

    #  Audio Level Monitoring 
    def _start_audio_monitor(self):
        if self._audio_running:
            return
        self._audio_running = True
        self._audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self._audio_thread.start()

    def _stop_audio_monitor(self):
        self._audio_running = False

    def _audio_loop(self):
        try:
            import soundcard as sc
            import numpy as np
            from config import load_config
            
            cfg = load_config()
            curr_aud = cfg.get("audio_source", "")
            mic_obj = None
            if curr_aud and curr_aud != "None (Muted)":
                for m in sc.all_microphones(include_loopback=False):
                    if m.name == curr_aud:
                        mic_obj = m
                        break
            if not mic_obj:
                mic_obj = sc.default_microphone()

            with mic_obj.recorder(samplerate=16000, channels=1) as rec:
                while self._audio_running:
                    data = rec.record(numframes=512)
                    rms = float(np.sqrt(np.mean(data ** 2)))
                    self._audio_level = min(1.0, rms * 12)
        except Exception as e:
            import logging
            logging.debug("VU meter audio monitor loop terminated: %s", e, exc_info=True)
            self._audio_running = False

    def _update_vu(self):
        if self._audio_running:
            self.vu.set_level(self._audio_level)
        elif hasattr(self, '_is_audio_on') and not self._is_audio_on:
            self.vu.set_level(0)

    def closeEvent(self, event):
        self._stop_audio_monitor()
        super().closeEvent(event)

    def hideEvent(self, event):
        self._stop_audio_monitor()
        super().hideEvent(event)

    def showEvent(self, event):
        if hasattr(self, '_is_audio_on') and self._is_audio_on:
            self._start_audio_monitor()
        super().showEvent(event)
