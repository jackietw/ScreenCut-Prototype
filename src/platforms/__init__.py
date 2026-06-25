'''
* SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
* SPDX-License-Identifier: LGPL-2.0-or-later
'''

import sys

if sys.platform == "win32":
    from platforms._windows import WindowsPlatform as Platform
elif sys.platform == "darwin":
    from platforms._macos import MacOSPlatform as Platform
else:
    # Linux / unsupported: use a graceful no-op fallback
    from platforms._base import PlatformBase as Platform

__all__ = ["Platform"]
