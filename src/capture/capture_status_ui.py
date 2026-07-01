'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import threading
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush
from resources.icon_utils import SVG_MOUSE, SVG_MIC, SVG_SYS_AUDIO

# -------------------------------------------------------------------
# VU Meter bar widget
# -------------------------------------------------------------------
class VuMeterBar(QWidget):
    """A row of small squares showing audio level."""
    TOTAL_BARS = 12
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self._level = 0.0   # 0.0 1.0

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
class RecStatusUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._build_ui()
        self.adjustSize()

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

        #  Title 
        title = QLabel("Record Status")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color: white; font-size: 17px; font-weight: 700; "
            "letter-spacing: 0.5px; padding-bottom: 12px;"
        )
        card_layout.addWidget(title)

        #  Separator 
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,25);")
        card_layout.addWidget(sep)
        card_layout.addSpacing(12)

        #  Cursor Row 
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
            full_svg_xml=SVG_MOUSE,
            label_text="Cursor",
            label_extra_layout=cursor_col,
            right_widgets=[cursor_right_widget]
        )
        card_layout.addLayout(cursor_row)
        card_layout.addSpacing(14)

        #  Microphone Row 
        mic_col = QVBoxLayout()
        mic_col.setSpacing(4)
        self.lbl_mic_device = QLabel("--")
        self.lbl_mic_device.setStyleSheet("color: #888888; font-size: 11px;")
        self.vu = VuMeterBar()
        self.vu.setFixedWidth(140)

        mic_col.addWidget(self.lbl_mic_device)
        mic_col.addWidget(self.vu)

        self.lbl_audio_on  = QLabel()  # will be set by update_audio_status
        self.lbl_audio_on.setStyleSheet("color: #4caf50; font-size: 13px; font-weight: 700;")
        
        mic_row = self._make_row(
            full_svg_xml=SVG_MIC,
            label_text="Microphone",
            label_extra_layout=mic_col,
            right_widgets=[self.lbl_audio_on]
        )
        card_layout.addLayout(mic_row)
        card_layout.addSpacing(14)

        #  System Audio Row 
        sys_col = QVBoxLayout()
        sys_col.setSpacing(4)
        self.lbl_sys_device = QLabel("Default Output")
        self.lbl_sys_device.setStyleSheet("color: #888888; font-size: 11px;")
        sys_col.addWidget(self.lbl_sys_device)

        self.lbl_sys_audio_on = QLabel()
        self.lbl_sys_audio_on.setStyleSheet("color: #4caf50; font-size: 13px; font-weight: 700;")

        sys_row = self._make_row(
            full_svg_xml=SVG_SYS_AUDIO,
            label_text="System Audio",
            label_extra_layout=sys_col,
            right_widgets=[self.lbl_sys_audio_on]
        )
        card_layout.addLayout(sys_row)

        main_layout.addWidget(self.card)

        # Init display from config
        from config import load_config
        cfg = load_config()
        toggles_cfg = cfg.get("toggles", {})
        init_mic = toggles_cfg.get("Record Microphone", True)
        init_sys = toggles_cfg.get("Record System Audio", True)

        self.update_cursor_status(True)
        self.update_audio_status(init_mic)
        self.update_sys_audio_status(init_sys)

    def _make_row(self, full_svg_xml, label_text, right_widgets, label_extra_layout=None):
        """Build one status row: [svg icon] [label (+ sub-layout)] ... [right widgets]"""
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtGui import QPixmap, QPainter
        from PySide6.QtCore import QByteArray
        
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Icon
        colored_svg = full_svg_xml.replace('#FFFFFF', '#CCCCCC')
        renderer = QSvgRenderer(QByteArray(colored_svg.encode('utf-8')))
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

    #  Status Update API 

    def _update_vu(self): pass
