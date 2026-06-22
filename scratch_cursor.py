'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

app = QApplication(sys.argv)
cursor = QCursor(Qt.CursorShape.ArrowCursor)
pixmap = cursor.pixmap()
print("ArrowCursor pixmap isNull:", pixmap.isNull())

# Try to get active cursor
pixmap = app.overrideCursor()
if pixmap:
    print("Override cursor isNull:", pixmap.pixmap().isNull())
else:
    print("No override cursor")
