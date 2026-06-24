import ctypes
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from config import load_config, save_config

# Windows Modifier Flags
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

class HotkeyLabel(QLabel):
    hotkey_changed = Signal(str, int, int) # config_key, modifiers, vk
    
    def __init__(self, default_hotkey="Hot Key", config_key=None):
        super().__init__(default_hotkey)
        self.config_key = config_key
        self.listening = False
        self.current_hotkey = default_hotkey
        self.valid = True
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Load from config if available
        if self.config_key:
            cfg = load_config()
            hotkeys = cfg.get("hotkeys", {})
            if self.config_key in hotkeys:
                hk_data = hotkeys[self.config_key]
                self.current_hotkey = hk_data.get("readable", default_hotkey)
                vk = hk_data.get("vk", 0)
                mods = hk_data.get("modifiers", 0)
                if vk:
                    # Test if it's still available upon loading
                    success = ctypes.windll.user32.RegisterHotKey(0, 9999, mods, vk)
                    if success:
                        ctypes.windll.user32.UnregisterHotKey(0, 9999)
                        self.valid = True
                    else:
                        self.valid = False
                        
        self.setText(self.current_hotkey)
        self.update_style(self.valid)
        
    def update_style(self, valid=True, listening=False):
        if listening:
            self.setStyleSheet("color: #FF0000; font-size: 13px; margin-top: 5px;")
        elif not valid:
            self.setStyleSheet("color: #FF0000; font-size: 13px; margin-top: 5px;")
        else:
            self.setStyleSheet("color: #006400; font-size: 13px; margin-top: 5px;")
            
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.listening = True
            self.setText("Input HotKey")
            self.update_style(listening=True)
            self.setFocus()
            
    def keyPressEvent(self, event):
        if not self.listening:
            super().keyPressEvent(event)
            return
            
        key = event.key()
        
        # Ignore if only modifier is pressed (waiting for actual key)
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return
            
        modifiers = event.modifiers()
        
        # Require Ctrl and (Alt or Shift) to be present
        has_ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        has_alt = bool(modifiers & Qt.KeyboardModifier.AltModifier)
        has_shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        has_meta = bool(modifiers & Qt.KeyboardModifier.MetaModifier)
        
        if not (has_ctrl and (has_alt or has_shift)):
            # Not a valid hotkey combination, just cancel listening and revert
            self.listening = False
            self.setText(self.current_hotkey)
            self.update_style(valid=self.valid)
            return
            
        # Valid combo, calculate native modifiers for RegisterHotKey
        fsModifiers = 0
        if has_alt: fsModifiers |= MOD_ALT
        if has_ctrl: fsModifiers |= MOD_CONTROL
        if modifiers & Qt.KeyboardModifier.ShiftModifier: fsModifiers |= MOD_SHIFT
        if has_meta: fsModifiers |= MOD_WIN
        
        vk = event.nativeVirtualKey()
        
        # Generate readable string (e.g. "Ctrl+Alt+S")
        key_seq = QKeySequence(key | modifiers.value)
        readable_hotkey = key_seq.toString(QKeySequence.SequenceFormat.NativeText)
        
        # Test hotkey registration
        hotkey_id = 9999 # arbitrary id for testing
        success = ctypes.windll.user32.RegisterHotKey(0, hotkey_id, fsModifiers, vk)
        
        self.current_hotkey = readable_hotkey
        self.setText(self.current_hotkey)
        
        if success:
            ctypes.windll.user32.UnregisterHotKey(0, hotkey_id)
            self.valid = True
            self.update_style(valid=True)
            
            # Save to config
            if self.config_key:
                cfg = load_config()
                if "hotkeys" not in cfg:
                    cfg["hotkeys"] = {}
                cfg["hotkeys"][self.config_key] = {
                    "readable": readable_hotkey,
                    "vk": vk,
                    "modifiers": fsModifiers
                }
                save_config(cfg)
                self.hotkey_changed.emit(self.config_key, fsModifiers, vk)
        else:
            self.valid = False
            self.update_style(valid=False)
            
        self.listening = False
