# ScreenCut (Archived)

**English** | [中文](README_zh.md)

[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL_v2.1-blue.svg)](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework: PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-green.svg)](https://doc.qt.io/qtforpython/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)]

> [!IMPORTANT]
> **⚠️ Project Status: Python Prototype / Archived**
> This repository represents the **Python / PySide6 Proof-of-Concept (PoC)** version of ScreenCut. It has been archived and is no longer under active development.
>
> To achieve **0ms instantaneous capture response** and **ultra-low memory footprint (~15MB)** without Python virtual machine overhead, ScreenCut is undergoing a complete native rewrite in **C++ / Qt 6 / Win32 Native**. The link to the new high-performance repository will be published here soon!

**ScreenCut** is a lightweight, high-performance, cross-platform desktop screen capture and video recording utility. Powered by **Python** and **PySide6 (Qt6)**, it combines hardware-accelerated video encoding and dual-stream synchronized audio recording with a built-in non-destructive image editor, providing developers, professionals, and daily users with an all-in-one visual productivity suite.

---

## Key Features

### Multi-Mode Screen Capture

* **Free-Form Region Capture**: Drag and select any customized rectangular area on your screen with pixel-perfect precision.
* **Intelligent Window Detection**: Automatically detects UI boundaries under the cursor to snap capture rectangles directly to application windows.
* **Long Scrolling Capture**: Automatically stitches long vertical web pages, chat transcripts, or documents into a single high-resolution panoramic image.
* **Multi-Monitor & DPI Awareness**: Full native support for multi-monitor setups, mixed scaling ratios, 4K displays, and macOS Retina screens.

### Hardware-Accelerated Video Recording & Dual Audio

* **High-Performance MP4 Recording**: Custom compression presets (`ultrafast` to `veryslow`) and configurable frame rates.
* **GPU Hardware Acceleration**: Supports ultra-low CPU overhead encoding via NVIDIA NVENC, AMD AMF, Intel QSV, Apple VideoToolbox, and Windows MediaFoundation DXVA.
* **Synchronized Dual Audio Recording**: Background multi-threaded audio capture simultaneously records both **Microphone Voice** and **Computer System Sound (WASAPI Loopback)**, muxing them at high speed via FFmpeg without video re-encoding.
* **Dynamic Mouse Effects**: Real-time cursor visualization with spotlight highlights and interactive click ripple animations.

### Professional Built-In Image Editor & Annotations

* **Rich Annotation Suite**: Arrows, Geometric Shapes (Rectangles, Ellipses), Freehand Pen/Brush, Text Boxes, and Stamp Overlays.
* **Sequential Step Markers**: Click anywhere to auto-increment numbered workflow badges (`1`, `2`, `3`...), making technical documentation and tutorials effortless.
* **Privacy Protection Tools**: Apply **Mosaic Pixelation** and **Gaussian Blur** to quickly redact passwords, API keys, and sensitive personal data.
* **Non-Destructive Editing & History**: Full Undo/Redo (`Ctrl+Z` / `Ctrl+Y`), image cropping, aspect ratio locking, and dynamic object resizing.

---

## Installation

### Prerequisites

* **Operating System**: Windows 10 / 11 or macOS 11+
* **Python**: Version 3.10 or higher

### Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/ScreenCut.git
   cd ScreenCut
   ```

2. **Create a virtual environment (Recommended)**

   ```bash
   python -m venv venv
   # Activate on Windows:
   .\venv\Scripts\activate
   # Activate on macOS / Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## Usage

### Windows VBS Shortcuts (Silent Background Execution)

The project root includes convenient VBS scripts that run without popping up command console windows:

* **`run_screencut.vbs`**: Starts the ScreenCut background tray application and global capture shortcuts.
* **`run_editor.vbs`**: Launches the standalone ScreenCut image annotation editor directly.

### Command Line Interface (CLI)

```bash
# Launch the background tray & capture engine
python src/screencut.py

# Launch the standalone image editor
python src/editor/editor_main.py
```

---

## Shortcuts & Hotkeys

| Key Combination / Action | Description |
| :--- | :--- |
| `Ctrl + Z` | Editor: Undo last annotation step |
| `Ctrl + Y` | Editor: Redo next annotation step |
| `Ctrl + C` | Editor: Copy rendered image to system clipboard |
| `Ctrl + S` | Editor: Save image to designated library directory |
| `Del` / `Backspace` | Editor: Delete selected annotation object |
| `Esc` | Cancel selection region / Close current popup dialog |

*(Note: Global hotkeys for triggering screen capture and video recording can be customized in the system tray `Preferences` menu)*

---

## Project Structure

```text
ScreenCut/
├── run_screencut.vbs         # Windows silent background launcher for capture tray
├── run_editor.vbs            # Windows silent background launcher for image editor
├── requirements.txt          # Python project dependency definitions
├── LICENSE                   # LGPL-2.1 license document
└── src/
    ├── screencut.py          # Main entry point and system tray manager
    ├── config.py             # User configuration & preferences persistence
    ├── version.py            # Centralized version definitions
    ├── capture/              # Static capture, scroll capture & recording toolbars
    ├── core/                 # Core capture engine, FFmpeg muxer, and audio recording
    ├── editor/               # Built-in non-destructive image editor UI and models
    ├── platforms/            # Cross-platform OS adapters (Windows / macOS)
    ├── resources/            # SVG vector icons and graphical assets
    └── widgets/              # Reusable Qt components, popups, and toast alerts
```

---

## License

This project is open-source and licensed under the **GNU Lesser General Public License v2.1 or later (LGPL-2.1-or-later)**.
Please see the [LICENSE](file:///d:/GitHUB/ScreenCut/LICENSE) file in the repository root for complete license details.

```text
SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
SPDX-License-Identifier: LGPL-2.0-or-later
```
