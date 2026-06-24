'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import threading
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer, QRect, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient

# -------------------------------------------------------------------
# VU Meter bar widget
# -------------------------------------------------------------------
class VuMeterBar(QWidget):
    """A row of small squares showing audio level."""
    TOTAL_BARS = 12
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self._level = 0.0   # 0.0 – 1.0

    def set_level(self, level: float):
        self._level = max(0.0, min(1.0, level))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        n = self.TOTAL_BARS
        gap = 3
        bar_w = max(4, (w - gap * (n - 1)) // n)
        total_w = bar_w * n + gap * (n - 1)
        x_start = (w - total_w) // 2
        
        lit = round(self._level * n)
        
        for i in range(n):
            x = x_start + i * (bar_w + gap)
            rect = QRectF(x, 1, bar_w, h - 2)
            
            if i < lit:
                # Green gradient for lit bars
                if i < n * 0.6:
                    color = QColor("#4caf50")
                elif i < n * 0.85:
                    color = QColor("#ffeb3b")
                else:
                    color = QColor("#f44336")
            else:
                color = QColor(70, 70, 70)
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 2, 2)
        
        painter.end()


# -------------------------------------------------------------------
# Record Status Panel
# -------------------------------------------------------------------
class ReadyToRecordPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # ── Audio level polling (sounddevice) ──────────────────────
        self._audio_level = 0.0
        self._audio_thread = None
        self._audio_running = False
        self._vu_timer = QTimer(self)
        self._vu_timer.timeout.connect(self._update_vu)
        self._vu_timer.start(60)  # ~16 fps refresh

        self._build_ui()
        self.adjustSize()

    # ── UI Construction ───────────────────────────────────────────
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.card = QWidget()
        self.card.setObjectName("record_card")
        self.card.setStyleSheet("""
            #record_card {
                background-color: rgba(40, 40, 44, 220);
                border: 1px solid rgba(255,255,255,18);
                border-radius: 14px;
            }
        """)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 18)
        card_layout.setSpacing(0)

        # ── Title ──
        title = QLabel("Record Status")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color: white; font-size: 17px; font-weight: 700; "
            "letter-spacing: 0.5px; padding-bottom: 12px;"
        )
        card_layout.addWidget(title)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,25);")
        card_layout.addWidget(sep)
        card_layout.addSpacing(12)

        # ── Cursor Row ──
        cursor_col = QVBoxLayout()
        cursor_col.setSpacing(2)
        
        lbl_hl = QLabel("Highlight")
        lbl_hl.setStyleSheet("color: #888888; font-size: 11px;")
        lbl_anim = QLabel("Cursor Animation")
        lbl_anim.setStyleSheet("color: #888888; font-size: 11px;")
        cursor_col.addWidget(lbl_hl)
        cursor_col.addWidget(lbl_anim)
        
        cursor_right_col = QVBoxLayout()
        cursor_right_col.setSpacing(2)
        cursor_right_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.lbl_cursor_main = QLabel()
        self.lbl_cursor_main.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.lbl_cursor_hl = QLabel("ON")
        self.lbl_cursor_hl.setStyleSheet("color: #cccccc; font-size: 11px;")
        self.lbl_cursor_hl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.lbl_cursor_anim = QLabel("OFF")
        self.lbl_cursor_anim.setStyleSheet("color: #cccccc; font-size: 11px;")
        self.lbl_cursor_anim.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        cursor_right_col.addWidget(self.lbl_cursor_main)
        cursor_right_col.addWidget(self.lbl_cursor_hl)
        cursor_right_col.addWidget(self.lbl_cursor_anim)
        
        cursor_right_widget = QWidget()
        cursor_right_widget.setMinimumWidth(40)
        cursor_right_widget.setLayout(cursor_right_col)
        cursor_right_col.setContentsMargins(0, 0, 0, 0)
        
        cursor_row = self._make_row(
            svg_path="M13 1.07V9h7c0-4.08-3.05-7.44-7-7.93zM4 15c0 4.42 3.58 8 8 8s8-3.58 8-8v-4H4v4zm7-13.93C7.05 1.56 4 4.92 4 9h7V1.07z",
            label_text="Cursor",
            label_extra_layout=cursor_col,
            right_widgets=[cursor_right_widget]
        )
        card_layout.addLayout(cursor_row)
        card_layout.addSpacing(14)

        # ── Microphone Row ──
        mic_col = QVBoxLayout()
        mic_col.setSpacing(4)
        self.lbl_mic_device = QLabel("—")
        self.lbl_mic_device.setStyleSheet("color: #888888; font-size: 11px;")
        self.vu = VuMeterBar()
        self.vu.setFixedWidth(140)

        mic_col.addWidget(self.lbl_mic_device)
        mic_col.addWidget(self.vu)

        self.lbl_audio_on  = QLabel()  # will be set by update_audio_status
        self.lbl_audio_on.setStyleSheet("color: #4caf50; font-size: 13px; font-weight: 700;")
        
        mic_row = self._make_row(
            svg_path="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5-3c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z",
            label_text="Microphone",
            label_extra_layout=mic_col,
            right_widgets=[self.lbl_audio_on]
        )
        card_layout.addLayout(mic_row)

        main_layout.addWidget(self.card)

        # Init display
        self.update_cursor_status(True)
        self.update_audio_status(True)

    def _make_row(self, svg_path, label_text, right_widgets, label_extra_layout=None):
        """Build one status row: [svg icon] [label (+ sub-layout)] ... [right widgets]"""
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtGui import QPixmap, QPainter
        from PySide6.QtCore import QByteArray
        
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Icon
        svg_xml = (
            f'<svg xmlns="http://www.w3.org/2000/svg" height="24px" '
            f'viewBox="0 0 24 24" width="24px" fill="#CCCCCC">'
            f'<path d="M0 0h24v24H0z" fill="none"/>'
            f'<path d="{svg_path}"/></svg>'
        )
        renderer = QSvgRenderer(QByteArray(svg_xml.encode()))
        pix = QPixmap(24, 24)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        renderer.render(p)
        p.end()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(pix)
        icon_lbl.setFixedSize(24, 24)
        row.addWidget(icon_lbl)

        # Label column
        lbl_col = QVBoxLayout()
        lbl_col.setSpacing(2)
        main_lbl = QLabel(label_text)
        main_lbl.setStyleSheet("color: #dddddd; font-size: 14px; font-weight: 500;")
        lbl_col.addWidget(main_lbl)
        if label_extra_layout:
            lbl_col.addLayout(label_extra_layout)
        row.addLayout(lbl_col)

        row.addStretch()

        # Right status widgets
        for w in right_widgets:
            row.addWidget(w)

        return row

    # ── Status Update API ──────────────────────────────────────────
    def update_cursor_status(self, is_on: bool):
        if is_on:
            self.lbl_cursor_main.setText("● ON")
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
        self._is_audio_on = is_audio_on
        if is_audio_on:
            self.lbl_audio_on.setText("● ON")
            self.lbl_audio_on.setStyleSheet("color: #4caf50; font-size: 13px; font-weight: 700;")
            self._start_audio_monitor()
        else:
            self.lbl_audio_on.setText("OFF")
            self.lbl_audio_on.setStyleSheet("color: #cccccc; font-size: 13px; font-weight: 500;")
            self._stop_audio_monitor()
            self.vu.set_level(0)

    def set_audio_device_name(self, name: str):
        self.lbl_mic_device.setText(name[:30] if name else "System Default")

    # ── Audio Level Monitoring ─────────────────────────────────────
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
            import sounddevice as sd
            import numpy as np
            
            def callback(indata, frames, time, status):
                if self._audio_running:
                    rms = float(np.sqrt(np.mean(indata ** 2)))
                    # Map to 0-1 with some headroom (typical speech ~0.01-0.1 RMS)
                    self._audio_level = min(1.0, rms * 12)
            
            with sd.InputStream(channels=1, samplerate=16000, blocksize=512, callback=callback):
                while self._audio_running:
                    threading.Event().wait(0.05)
        except Exception:
            # sounddevice not available or no input device
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
