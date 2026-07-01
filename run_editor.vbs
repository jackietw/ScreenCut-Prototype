Set WshShell = CreateObject("WScript.Shell")
' Directly open ScreenCut Image Editor without a console window
WshShell.Run "cmd /c .\venv\Scripts\pythonw.exe src\screencut.py --editor", 0
Set WshShell = Nothing
