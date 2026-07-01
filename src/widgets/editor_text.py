'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Qt, Signal


class CanvasTextEdit(QTextEdit):
    commit_requested = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textChanged.connect(self._auto_resize)

    def _auto_resize(self):
        doc_height = int(self.document().size().height())
        margins = self.contentsMargins()
        needed_height = max(self.minimumHeight(), doc_height + margins.top() + margins.bottom() + 14)
        if needed_height != self.height():
            self.resize(self.width(), needed_height)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.commit_requested.emit()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self.commit_requested.emit()
            return
        super().keyPressEvent(event)
