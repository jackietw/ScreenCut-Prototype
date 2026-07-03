'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import os
import sys
import time
import threading
import subprocess
import logging
import numpy as np

# Prevent imageio_ffmpeg from flashing terminal windows on Windows when launching ffmpeg
if sys.platform == "win32":
    try:
        import imageio_ffmpeg._utils as _iio_utils
        _orig_popen_kwargs = _iio_utils._popen_kwargs
        def _patched_popen_kwargs(prevent_sigint=False):
            kwargs = _orig_popen_kwargs(prevent_sigint)
            flags = kwargs.get("creationflags", 0) or 0
            flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            kwargs["creationflags"] = flags
            return kwargs
        _iio_utils._popen_kwargs = _patched_popen_kwargs
    except Exception:
        pass

_cached_hw_encoders: list = None

def get_cached_hw_encoders():
    return _cached_hw_encoders

def detect_available_hw_encoders(force_refresh: bool = False) -> list:
    """Detect functional hardware video encoders on the current machine.
    
    Returns a list of tuples: [(codec_id, display_name), ...]
    If no hardware encoder works, returns an empty list [].
    """
    global _cached_hw_encoders
    if _cached_hw_encoders is not None and not force_refresh:
        return _cached_hw_encoders

    try:
        import imageio_ffmpeg as ffmpeg
        exe = ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logging.warning("Could not obtain ffmpeg binary for hardware detection: %s", e)
        _cached_hw_encoders = []
        return _cached_hw_encoders

    candidates = []
    if sys.platform == "win32":
        candidates = [
            ("h264_nvenc", "NVIDIA NVENC (GPU)"),
            ("h264_amf", "AMD Radeon AMF (GPU)"),
            ("h264_qsv", "Intel QuickSync (GPU)"),
            ("h264_mf", "Windows MediaFoundation (DXVA)"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            ("h264_videotoolbox", "Apple VideoToolbox (GPU)"),
        ]
    else:
        candidates = [
            ("h264_vaapi", "VAAPI Hardware Acceleration (GPU)"),
        ]

    working_encoders = []
    from concurrent.futures import ThreadPoolExecutor

    def _test_codec(item):
        codec_id, display_name = item
        try:
            cmd = [
                exe,
                "-f", "lavfi",
                "-i", "nullsrc=s=1280x720:d=0.05",
                "-pix_fmt", "yuv420p",
            ]
            if codec_id == "h264_videotoolbox":
                cmd.extend(["-c:v", codec_id, "-allow_sw", "1", "-f", "null", "-"])
            else:
                cmd.extend(["-c:v", codec_id, "-f", "null", "-"])
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            res = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3.0,
                creationflags=creationflags
            )
            if res.returncode == 0:
                logging.info("Detected active hardware encoder: %s (%s)", codec_id, display_name)
                return (codec_id, display_name)
        except Exception as e:
            logging.debug("Hardware encoder test failed for %s: %s", codec_id, e)
        return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(_test_codec, candidates)
        for r in results:
            if r is not None:
                working_encoders.append(r)

    _cached_hw_encoders = working_encoders
    return _cached_hw_encoders


def get_video_writer_params(hw_enabled: bool, preferred_codec: str, compression: str) -> tuple:
    """Return (codec, ffmpeg_params) suitable for imageio.get_writer.
    
    Ensures safe compatibility across software and hardware encoders.
    """
    if not hw_enabled or not preferred_codec or preferred_codec == "libx264":
        # Standard software CPU encoding
        preset = compression if compression in ["ultrafast", "superfast", "fast", "medium", "slow", "veryslow"] else "medium"
        return ("libx264", ["-preset", preset, "-crf", "23", "-pix_fmt", "yuv420p"])

    # For GPU hardware encoders, standard preset/crf syntax may vary; ensure standard pixel format
    if preferred_codec == "h264_videotoolbox":
        return (preferred_codec, ["-pix_fmt", "yuv420p", "-allow_sw", "1"])
    return (preferred_codec, ["-pix_fmt", "yuv420p"])


class AudioRecorder:
    def __init__(self, mic_device_name, sys_audio_enabled, is_mic_muted=False, is_sys_muted=False):
        self.mic_device_name = mic_device_name
        self.sys_audio_enabled = sys_audio_enabled
        self.mic_muted = is_mic_muted
        self.sys_muted = is_sys_muted
        self.is_running = False
        self.samplerate = 44100
        self.chunk_frames = 2205  # 50ms per chunk
        self.mic_chunks = []
        self.sys_chunks = []
        self.mic_thread = None
        self.sys_thread = None

    def start(self):
        self.is_running = True
        try:
            import soundcard as sc
        except ImportError:
            return

        # Start microphone loop
        if self.mic_device_name and self.mic_device_name != "None (Muted)":
            self.mic_thread = threading.Thread(target=self._mic_loop, daemon=True)
            self.mic_thread.start()

        # Start system speaker loopback
        if self.sys_audio_enabled:
            self.sys_thread = threading.Thread(target=self._sys_loop, daemon=True)
            self.sys_thread.start()

    def _mic_loop(self):
        try:
            import soundcard as sc
            mic_obj = None
            for m in sc.all_microphones(include_loopback=False):
                if m.name == self.mic_device_name:
                    mic_obj = m
                    break
            if not mic_obj:
                mic_obj = sc.default_microphone()

            with mic_obj.recorder(samplerate=self.samplerate, channels=2) as rec:
                while self.is_running:
                    data = rec.record(numframes=self.chunk_frames)
                    if self.mic_muted:
                        data = np.zeros_like(data)
                    self.mic_chunks.append(data.copy())
        except Exception as e:
            logging.warning("Error recording microphone audio: %s", e)

    def _sys_loop(self):
        try:
            import soundcard as sc
            spk = sc.default_speaker()
            sys_obj = sc.get_microphone(id=spk.id, include_loopback=True)

            with sys_obj.recorder(samplerate=self.samplerate, channels=2) as rec:
                while self.is_running:
                    data = rec.record(numframes=self.chunk_frames)
                    if self.sys_muted:
                        data = np.zeros_like(data)
                    self.sys_chunks.append(data.copy())
        except Exception as e:
            logging.warning("Error recording system audio loopback: %s", e)

    def stop_and_get_audio(self):
        self.is_running = False
        if self.mic_thread and self.mic_thread.is_alive():
            self.mic_thread.join(timeout=2.0)
        if self.sys_thread and self.sys_thread.is_alive():
            self.sys_thread.join(timeout=2.0)

        mic_audio = np.concatenate(self.mic_chunks, axis=0) if self.mic_chunks else None
        sys_audio = np.concatenate(self.sys_chunks, axis=0) if self.sys_chunks else None

        if mic_audio is None and sys_audio is None:
            return None

        if mic_audio is not None and sys_audio is not None:
            max_len = max(len(mic_audio), len(sys_audio))
            if len(mic_audio) < max_len:
                mic_audio = np.pad(mic_audio, ((0, max_len - len(mic_audio)), (0, 0)), mode='constant')
            if len(sys_audio) < max_len:
                sys_audio = np.pad(sys_audio, ((0, max_len - len(sys_audio)), (0, 0)), mode='constant')
            combined = mic_audio + sys_audio
            return np.clip(combined, -1.0, 1.0)
        elif mic_audio is not None:
            return np.clip(mic_audio, -1.0, 1.0)
        else:
            return np.clip(sys_audio, -1.0, 1.0)


def mux_audio_into_video(video_path: str, audio_data: np.ndarray, samplerate: int = 44100) -> bool:
    if audio_data is None or len(audio_data) == 0:
        return False
    library_dir = os.path.dirname(video_path)
    temp_wav = None
    temp_mp4 = None
    try:
        import soundfile as sf
        import imageio_ffmpeg
        temp_wav = os.path.join(library_dir, f"temp_aud_{int(time.time()*1000)}.wav")
        temp_mp4 = os.path.join(library_dir, f"temp_vid_{int(time.time()*1000)}.mp4")
        sf.write(temp_wav, audio_data, samplerate)
        if os.path.exists(video_path):
            os.rename(video_path, temp_mp4)
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe, "-y",
                "-i", temp_mp4,
                "-i", temp_wav,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                video_path
            ]
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
            if res.returncode == 0 and os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                if os.path.exists(temp_mp4):
                    try: os.remove(temp_mp4)
                    except Exception: pass
                return True
            else:
                logging.error("FFmpeg audio muxing failed. Restoring original un-muxed video.")
                if os.path.exists(video_path):
                    try: os.remove(video_path)
                    except Exception: pass
                if os.path.exists(temp_mp4):
                    os.rename(temp_mp4, video_path)
    except Exception as e:
        logging.warning("Failed to mux audio into video: %s", e)
        if temp_mp4 and os.path.exists(temp_mp4) and not os.path.exists(video_path):
            try:
                os.rename(temp_mp4, video_path)
            except Exception:
                pass
    finally:
        if temp_wav and os.path.exists(temp_wav):
            try: os.remove(temp_wav)
            except Exception: pass
    return False
