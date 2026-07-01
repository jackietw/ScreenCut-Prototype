'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import sys
import subprocess
import logging

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
