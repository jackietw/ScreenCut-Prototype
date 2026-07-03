# ScreenCut

[English](README.md) | **中文**

[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL_v2.1-blue.svg)](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework: PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-green.svg)](https://doc.qt.io/qtforpython/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)]

**ScreenCut** 是一款輕量、效能卓越且跨平台的桌面螢幕截圖與錄影工具。採用 **Python** 與 **PySide6 (Qt6)** 打造，結合硬體加速影像編碼與雙軌同步收音技術，並內建強大的非破壞性圖片標註編輯器，為開發者、工作專業人士與日常用戶提供一站式的畫面捕捉解決方案。

---

## 核心功能特色 (Key Features)

### 多模式靜態截圖與長截圖 (Screen Capture)

* **區域框選截圖 (Region Capture)**：自由框選任意大小與長寬比的畫面區域。
* **智慧視窗偵測 (Window Detection)**：自動感應游標所在視窗邊界，一鍵精確捕捉應用程式畫面。
* **滾動長截圖 (Scrolling Capture)**：自動翻頁與影像特徵縫合，輕鬆將長網頁、聊天紀錄或長篇文件輸出為單張超高畫質長圖。
* **多螢幕與 DPI 支援**：完美適應多螢幕拼接、高解析度 4K 螢幕及 macOS Retina 顯示器。

### 硬體加速錄影與雙軌錄音 (Video & Audio Recording)

* **高效能 MP4 錄影**：支援自訂壓縮品質 (`ultrafast` 至 `veryslow`) 與 FPS 設定。
* **GPU 硬體加速編碼**：支援 NVIDIA NVENC、AMD AMF、Intel QSV、Apple VideoToolbox 以及 Windows MediaFoundation，極低 CPU 占用。
* **雙軌同步收音 (Microphone + System Audio)**：採用背景多執行緒同步收錄 **麥克風語音** 與 **電腦內部系統音效 (WASAPI Loopback)**，並利用 FFmpeg 進行極速零損失封裝。
* **動態滑鼠特效**：錄影期間自動提示滑鼠軌跡、亮點標註 (Highlight Spotlight) 以及點擊波紋特效 (Click Ripples)。

### 專業級內建圖片編輯器 (Image Editor & Annotations)

* **豐富標註物件**：箭頭、幾何圖形 (矩形、圓形)、自由畫筆、文字方塊與印章標示。
* **步驟次序標籤 (Step Markers)**：點擊畫面自動產生數字順序標籤 (1, 2, 3...)，製作教學流程圖輕而易舉。
* **隱私防護工具**：提供 **馬賽克像素化 (Mosaic)** 與 **高斯模糊 (Gaussian Blur)** 工具，輕鬆遮蔽敏感機密資訊。
* **非破壞性編輯與歷史紀錄**：支援無限次復原/重做 (`Ctrl+Z` / `Ctrl+Y`)、縮放裁剪與裁切比例鎖定。

---

## 安裝指南 (Installation)

### 系統環境需求

* **作業系統**：Windows 10 / 11 或 macOS 11+
* **Python**：3.10 或以上版本

### 快速設定步驟

1. **複製專案庫**

   ```bash
   git clone https://github.com/yourusername/ScreenCut.git
   cd ScreenCut
   ```

2. **建立虛擬環境 (建議)**

   ```bash
   python -m venv venv
   # Windows 啟動虛擬環境:
   .\venv\Scripts\activate
   # macOS / Linux 啟動虛擬環境:
   source venv/bin/activate
   ```

3. **安裝套件相依性**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 使用方式 (Usage)

### 透過捷徑腳本快速啟動 (Windows)

專案根目錄提供了便捷的 VBS 無黑框後台執行腳本：

* 雙擊 **`run_screencut.vbs`**：常駐啟動 ScreenCut 截圖與錄影常駐服務（可在系統托盤設定捷徑與參數）。
* 雙擊 **`run_editor.vbs`**：直接開啟獨立的 ScreenCut 圖片編輯器。

### 透過命令列執行 (CLI)

```bash
# 啟動主截圖常駐程式
python src/screencut.py

# 獨立啟動圖片編輯器
python src/editor/editor_main.py
```

---

## 常用快捷鍵操作 (Shortcuts)

| 快捷鍵 / 操作 | 功能說明 |
| :--- | :--- |
| `Ctrl + Z` | 編輯器內：復原上一步 (Undo) |
| `Ctrl + Y` | 編輯器內：重做下一步 (Redo) |
| `Ctrl + C` | 將當前編輯結果複製至系統剪貼簿 |
| `Ctrl + S` | 儲存圖片至指定的輸出庫目錄 |
| `Del` / `Backspace` | 刪除當前選中的標註物件 |
| `Esc` | 取消截圖框選 / 關閉當前彈出視窗 |

*(註：全域截圖與錄影快捷鍵可在系統偏好設定 `Preferences` 中自訂綁定)*

---

## 專案架構 (Project Structure)

```text
ScreenCut/
├── run_screencut.vbs         # Windows 無黑框截圖錄影啟動器
├── run_editor.vbs            # Windows 無黑框圖片編輯器啟動器
├── requirements.txt          # 核心套件相依性設定檔案
├── LICENSE                   # LGPL-2.1 授權文件
└── src/
    ├── screencut.py          # 程式進入點與系統托盤管理器
    ├── config.py             # 使用者設定檔與偏好讀寫模組
    ├── version.py            # 版本號定義
    ├── capture/              # 靜態截圖、長截圖與錄影控制列 UI
    ├── core/                 # 核心影像處理、FFmpeg 封裝、音訊錄製與編解碼引擎
    ├── editor/               # 內建非破壞性圖片編輯器主體模組
    ├── platforms/            # Windows / macOS 跨平台底層 API 適配器
    ├── resources/            # 向量 SVG 圖標與介面資源
    └── widgets/              # 自訂 Qt 元件、懸浮通知視窗與通用元件
```

---

## 授權條款 (License)

本專案採用 **GNU Lesser General Public License v2.1 or later (LGPL-2.1-or-later)** 授權開源。
詳細授權條款請參閱專案根目錄中的 [LICENSE](file:///d:/GitHUB/ScreenCut/LICENSE) 檔案。

```text
SPDX-FileCopyrightText: 2026 Jackie <jackie.github@outlook.com>
SPDX-License-Identifier: LGPL-2.0-or-later
```
