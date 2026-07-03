# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2026.1.6] - 2026-07-03

### Added

- **Automated CI/CD Release Pipeline**: Configured GitHub Actions workflow (`.github/workflows/release.yml`) using `Nuitka/Nuitka-Action` for standalone GUI (Mode 2, `--windows-disable-console`) builds across Windows x86/x64 and macOS Intel/Apple Silicon.
- **Intelligent Audio Hardware Detection**: Automatically detects physical microphone and speaker endpoints (`soundcard`). When audio devices are missing (e.g. servers or headless workstations), corresponding UI controls (Preferences, Video Capture Tab, Video Toolbar) are safely disabled and fallback statuses (`No Microphone Detected` / `N/A`) are displayed.

### Changed

- **SCUT Project File Optimization**: Removed redundant duplicate `image` and `thumbnail` base64 fields from `.scut` serialization in `capture_engine.py` and `editor_canvas.py`, reducing project file sizes by approximately 50%.
- **Log Management**: Upgraded logging infrastructure in `config.py` to use `RotatingFileHandler` (max 2 MB per file, up to 2 backups) to prevent log inflation.

### Fixed

- **Hotkey Collision Prevention**: Refined `check_hotkey_conflict` in Windows and macOS platform adapters to accurately intercept cross-feature conflicts within the application before OS registration.
- **Graceful Application Exit (`force_quit`)**: Ensured active video recording threads wait to finish MP4 writing/muxing and editor auto-save debounce timers immediately flush pending edits when quitting via the system tray or application close events.
- **Accurate Video Capture Feedback**: Updated `on_finished` to strictly verify actual output file existence and non-zero byte size before emitting success toast notifications.
- **Exception Safety**: Replaced overly permissive silent exception blocks across the codebase with detailed logging (`exc_info=True`) to capture stack traces for diagnostic debugging without degrading GUI runtime performance.
