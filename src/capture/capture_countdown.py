'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import logging
from PySide6.QtCore import Qt, QTimer
from capture.capture_countdown_ui import CountdownUI

class Countdown(CountdownUI):
    def __init__(self, seconds=5):
        super().__init__(seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        
    def tick(self):
        self.seconds -= 1
        if self.seconds > 0:
            self.label.setText(str(self.seconds))
        else:
            self.timer.stop()
            self.close()
            self.finished.emit()
            
    def mousePressEvent(self, event):
        # Cancel the countdown if the user clicks on the timer widget
        if event.button() == Qt.MouseButton.LeftButton:
            self.timer.stop()
            self.close()
            self.cancelled.emit()
            logging.debug("Countdown cancelled by user.")
