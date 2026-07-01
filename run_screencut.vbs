Set WshShell = CreateObject("WScript.Shell")
' Launch ScreenCut capture & system tray in the background without a console window
WshShell.Run "cmd /c .\venv\Scripts\pythonw.exe src\screencut.py", 0
Set WshShell = Nothing
