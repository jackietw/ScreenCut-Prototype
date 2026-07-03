'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import os
import sys
import time
import threading
import numpy as np
import mss
import imageio
import cv2
from platforms import Platform
from PySide6.QtCore import QThread, Signal, QObject, QTimer
from PySide6.QtWidgets import QApplication
from widgets.capture_toolbar import VideoToolbar
from config import load_config
from core.capture_codecs import AudioRecorder, mux_audio_into_video


class VideoCaptureThread(QThread):
    finished_signal = Signal(str)
    
    def __init__(self, rect, output_path, capture_cursor, compression, audio_device, sys_audio_enabled=True):
        super().__init__()
        self.rect = rect
        self.output_path = output_path
        self.library_dir = os.path.dirname(output_path)
        self.capture_cursor = capture_cursor
        self.compression = compression
        self.audio_device = audio_device
        self.sys_audio_enabled = sys_audio_enabled
        self.is_running = True
        self.is_muted = (audio_device == "None (Muted)" or not audio_device)
        self.is_sys_muted = not sys_audio_enabled
        self.audio_recorder = None
        
    def set_muted(self, muted):
        self.is_muted = muted
        if self.audio_recorder:
            self.audio_recorder.mic_muted = muted

    def set_sys_muted(self, muted):
        self.is_sys_muted = muted
        if self.audio_recorder:
            self.audio_recorder.sys_muted = muted
        
    def stop(self):
        self.is_running = False
        
    def run(self):
        fps = 30
        
        # In a complete implementation, audio recording would use sounddevice to capture
        # into a temporary WAV file, and then muxed with the MP4 via ffmpeg at the end.
        # For MVP, we are setting up the structure and recording video.
        
        config_data = load_config()
        self.cursor_settings = config_data.get("cursor_settings", {})
        self.hl_enabled = self.cursor_settings.get("highlight", False)
        self.cl_enabled = self.cursor_settings.get("click", False)
        self.limit_1080p = config_data.get("limit_1080p", True)
        
        def hex_to_rgb(hex_str):
            hex_str = hex_str.lstrip('#')
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
            
        self.hl_color = hex_to_rgb(self.cursor_settings.get("highlight_color", "#ffff00"))
        self.cl_color = hex_to_rgb(self.cursor_settings.get("click_color", "#ff0000"))
        
        click_animations = []
        prev_clicked = False
        
        from core.capture_codecs import get_video_writer_params
        hw_enabled = config_data.get("hw_accel", True)
        hw_encoder = config_data.get("hw_encoder", "")
        
        codec, ffmpeg_params = get_video_writer_params(hw_enabled, hw_encoder, self.compression)
        writer = None
        audio_recorder = None
        try:
            try:
                writer = imageio.get_writer(self.output_path, fps=fps, codec=codec, macro_block_size=2, ffmpeg_params=ffmpeg_params)
            except Exception as e:
                import logging
                logging.warning("Video writer initialization failed for codec %s (%s). Falling back to software libx264.", codec, e, exc_info=True)
                codec, ffmpeg_params = get_video_writer_params(False, "", self.compression)
                writer = imageio.get_writer(self.output_path, fps=fps, codec=codec, macro_block_size=2, ffmpeg_params=ffmpeg_params)
            
            monitor = {
                "top": self.rect.top(),
                "left": self.rect.left(),
                "width": self.rect.width(),
                "height": self.rect.height()
            }
            
            audio_recorder = AudioRecorder(self.audio_device, self.sys_audio_enabled, self.is_muted, self.is_sys_muted)
            audio_recorder.start()
            self.audio_recorder = audio_recorder

            with mss.mss() as sct:
                frame_duration = 1.0 / fps
                next_frame_time = time.time()
                
                while self.is_running:
                    now = time.time()
                    if now < next_frame_time:
                        time.sleep(next_frame_time - now)
                        
                    # Grab frame (with autorelease pool on macOS to flush CoreGraphics IPC buffers)
                    if sys.platform == 'darwin':
                        try:
                            import objc
                            with objc.autorelease_pool():
                                sct_img = sct.grab(monitor)
                                frame = np.array(sct_img)
                        except Exception as e:
                            import logging
                            logging.debug("autorelease_pool grab failed: %s", e, exc_info=True)
                            sct_img = sct.grab(monitor)
                            frame = np.array(sct_img)
                    else:
                        sct_img = sct.grab(monitor)
                        frame = np.array(sct_img)
                    # Convert BGRA to RGB for imageio (and make it contiguous for cv2)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                    
                    # Check Cursor State
                    if self.capture_cursor:
                        try:
                            cx, cy = Platform.get_cursor_pos()
                            # Translate to frame coordinates
                            fx = cx - monitor["left"]
                            fy = cy - monitor["top"]

                            # Draw Highlight
                            if self.hl_enabled:
                                cv2.circle(frame, (fx, fy), 24, self.hl_color, -1, cv2.LINE_AA)
                            
                            # Trigger Click Animation on state change
                            if self.cl_enabled:
                                is_clicking = Platform.get_left_button_down()
                                if is_clicking and not prev_clicked:
                                    click_animations.append({"pos": (fx, fy), "radius": 4.0})
                                prev_clicked = is_clicking

                            # Draw Vector Cursor
                            cursor_poly = np.array([
                                [fx, fy], [fx, fy+20], [fx+5, fy+15],
                                [fx+10, fy+25], [fx+12, fy+24],
                                [fx+7, fy+14], [fx+15, fy+14]
                            ], np.int32)
                            cv2.fillPoly(frame, [cursor_poly], (0, 0, 0))
                            cv2.polylines(frame, [cursor_poly], True, (255, 255, 255), 1, cv2.LINE_AA)
                        except Exception as e:
                            import logging
                            logging.debug("Failed drawing cursor fallback: %s", e, exc_info=True)
                    
                    # Draw Click Animations
                    if self.cl_enabled and click_animations:
                        new_anims = []
                        overlay = frame.copy()
                        for anim in click_animations:
                            cv2.circle(overlay, anim["pos"], int(anim["radius"]), self.cl_color, 2, cv2.LINE_AA)
                            anim["radius"] += 4
                            if anim["radius"] < 40:
                                new_anims.append(anim)
                        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                        click_animations = new_anims
                    
                    # 1080p limit scale down
                    if self.limit_1080p and (frame.shape[1] > 1920 or frame.shape[0] > 1080):
                        scale = min(1920 / frame.shape[1], 1080 / frame.shape[0])
                        new_w = int(frame.shape[1] * scale)
                        new_h = int(frame.shape[0] * scale)
                        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

                    # Ensure even dimensions for yuv420p hardware/software video encoders
                    if frame.shape[1] % 2 != 0 or frame.shape[0] % 2 != 0:
                        ew = frame.shape[1] - (frame.shape[1] % 2)
                        eh = frame.shape[0] - (frame.shape[0] % 2)
                        frame = frame[:eh, :ew]

                    writer.append_data(frame)
                    next_frame_time += frame_duration
                    
                    now = time.time()
                    if next_frame_time < now:
                        # Prevent infinite catch-up death spirals on macOS Retina screens
                        if now - next_frame_time > frame_duration:
                            next_frame_time = now
                        else:
                            # Duplicate frame once to maintain CFR timeline sync when rendering falls behind
                            writer.append_data(frame)
                            next_frame_time += frame_duration
                        
            if writer:
                writer.close()

            if audio_recorder:
                audio_data = audio_recorder.stop_and_get_audio()
                mux_audio_into_video(self.output_path, audio_data, audio_recorder.samplerate)
        except Exception as e:
            import logging
            logging.error(f"Error during video recording: {e}", exc_info=True)
            if writer:
                try:
                    writer.close()
                except Exception as e:
                    logging.debug("Error closing video writer in exception handler: %s", e, exc_info=True)
        finally:
            self.finished_signal.emit(self.output_path)


class VideoCaptureManager(QObject):
    def __init__(self, rect, library_dir, cw_x=None, cw_y=None, override_settings=None, existing_toolbar=None, logical_rect=None):
        super().__init__()
        self.rect = rect
        self.logical_rect = logical_rect if logical_rect else rect
        self.library_dir = library_dir
        
        config_data = load_config()
        self.compression = config_data.get("video_compression", "medium")
        self.audio_device = config_data.get("audio_source", "None (Muted)")
        
        toggles = config_data.get("toggles", {})
        self.capture_cursor = toggles.get("Capture Cursor (Video)", False)
        
        self.cursor_settings = config_data.get("cursor_settings", {})
        self.hl_enabled = self.cursor_settings.get("highlight", False)
        self.cl_enabled = self.cursor_settings.get("click", False)
        
        if override_settings:
            self.capture_cursor = override_settings.get("capture_cursor", self.capture_cursor)
            self.hl_enabled = override_settings.get("highlight", self.hl_enabled)
            self.cl_enabled = override_settings.get("click", self.cl_enabled)
            if not override_settings.get("audio", True):
                self.audio_device = "None (Muted)"
        
        if self.hl_enabled or self.cl_enabled:
            from widgets.capture_cursor import CursorOverlay
            hl_color = self.cursor_settings.get("highlight_color", "#ffff00")
            cl_color = self.cursor_settings.get("click_color", "#ff0000")
            self.live_overlay = CursorOverlay(self.hl_enabled, hl_color, self.cl_enabled, cl_color, capture_rect=self.logical_rect)
            if self.capture_cursor:
                self.live_overlay.show()
        else:
            self.live_overlay = None
            
        timestamp = time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time()*1000)%1000:03d}"
        self.output_path = os.path.join(self.library_dir, f"Video_{timestamp}.mp4")
        
        self.is_cancelled = False
        if existing_toolbar:
            self.toolbar = existing_toolbar
            # Note: start_requested is already connected by OverlayWindow
            self.toolbar.stop_requested.connect(self.stop_capture)
            self.toolbar.cancel_requested.connect(self.cancel_capture)
            self.toolbar.audio_toggled.connect(self.toggle_audio)
            self.toolbar.sys_audio_toggled.connect(self.toggle_sys_audio)
            self.toolbar.cursor_toggled.connect(self.toggle_cursor)
        else:
            self.toolbar = VideoToolbar()
            self.toolbar.stop_requested.connect(self.stop_capture)
            self.toolbar.cancel_requested.connect(self.cancel_capture)
            self.toolbar.audio_toggled.connect(self.toggle_audio)
            self.toolbar.sys_audio_toggled.connect(self.toggle_sys_audio)
            self.toolbar.cursor_toggled.connect(self.toggle_cursor)
            
            # Position toolbar if created newly
            if cw_x is not None and cw_y is not None:
                self.toolbar.move(cw_x, cw_y)
            else:
                screen = QApplication.screenAt(rect.center())
                if screen:
                    sg = screen.geometry()
                    x = rect.center().x() - self.toolbar.width() // 2
                    y = rect.bottom() + 20
                    if y + self.toolbar.height() > sg.bottom():
                        y = rect.top() - self.toolbar.height() - 20
                    self.toolbar.move(x, y)
                else:
                    self.toolbar.move(rect.left(), rect.bottom() + 10)
                
            self.toolbar.show()
        
        # Determine initial toggles from toolbar state if available
        self.sys_audio_enabled = toggles.get("Record System Audio", True)
        if existing_toolbar:
            self.capture_cursor = existing_toolbar.btn_cursor.isChecked()
            self.sys_audio_enabled = existing_toolbar.btn_sys_audio.isChecked()
            if not existing_toolbar.btn_audio.isChecked():
                self.audio_device = "None (Muted)"
        
        self.thread = VideoCaptureThread(self.rect, self.output_path, self.capture_cursor, self.compression, self.audio_device, self.sys_audio_enabled)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()
        
        self.start_time = time.time()
        self._last_displayed_sec = -1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(100)  # Poll every 100ms to avoid skipping seconds

    def update_timer(self):
        elapsed = int(time.time() - self.start_time)
        if elapsed == self._last_displayed_sec:
            return  # Same second, no need to update
        self._last_displayed_sec = elapsed
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.toolbar.update_time(f"{hrs:02d}:{mins:02d}:{secs:02d}")

    def toggle_audio(self, is_audio_on):
        self.audio_enabled = is_audio_on
        if hasattr(self, 'thread') and self.thread:
            self.thread.set_muted(not is_audio_on)

    def toggle_sys_audio(self, is_sys_on):
        self.sys_audio_enabled = is_sys_on
        if hasattr(self, 'thread') and self.thread:
            self.thread.set_sys_muted(not is_sys_on)

    def toggle_cursor(self, show_cursor):
        self.capture_cursor = show_cursor
        if hasattr(self, 'thread') and self.thread:
            self.thread.capture_cursor = show_cursor
        if hasattr(self, 'live_overlay') and self.live_overlay:
            if show_cursor:
                self.live_overlay.show()
            else:
                self.live_overlay.hide()

    def stop_capture(self):
        self.toolbar.hide()
        self.timer.stop()
        self.thread.stop()
        if hasattr(self, 'live_overlay') and self.live_overlay:
            self.live_overlay.close()

    def cancel_capture(self):
        self.is_cancelled = True
        self.stop_capture()

    def on_finished(self, path):
        if self.is_cancelled:
            if os.path.exists(path):
                os.remove(path)
        else:
            from widgets.common_notification import Notification
            # Save reference to prevent GC
            self.__class__._active_toast = Notification(f"Video saved successfully:\n{os.path.basename(path)}")
            self.__class__._active_toast.show_toast()
        self.deleteLater()
