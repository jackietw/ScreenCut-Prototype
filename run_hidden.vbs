Set WshShell = CreateObject("WScript.Shell")
' Run the pythonw.exe inside the venv to suppress the console window
WshShell.Run "cmd /c .\venv\Scripts\pythonw.exe src\capture_main.py", 0
Set WshShell = Nothing
