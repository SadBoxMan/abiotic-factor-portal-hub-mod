@echo off
rem Cordona Tracker launcher: starts the tracker without a console window (pythonw, then pyw, then python).
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw "%~dp0CordonaTracker.py" %* & exit /b 0)
where pyw >nul 2>nul && (start "" pyw -3 "%~dp0CordonaTracker.py" %* & exit /b 0)
where python >nul 2>nul && (python "%~dp0CordonaTracker.py" %* & exit /b 0)
echo Python 3 was not found. Install it from python.org (with Tkinter), then run this again.
pause
