@echo off
rem Opens the Portal Hub config editor. Uses the packaged program if it is here, then Python (with Tkinter).
rem This window closes by itself once the editor has opened.
setlocal
set "HERE=%~dp0"
for %%E in ("%HERE%PortalHubConfig\PortalHubConfig.exe" "%HERE%tools\PortalHubConfig\dist\PortalHubConfig\PortalHubConfig.exe") do (
    if exist %%E ( start "" %%E & exit /b 0 )
)
for %%P in (pyw pythonw) do (
    %%P -c "import tkinter" >nul 2>&1 && ( start "" %%P "%HERE%tools\PortalHubConfig\PortalHubConfig.py" & exit /b 0 )
)
echo Could not find PortalHubConfig\PortalHubConfig.exe next to this file, or Python with Tkinter.
echo Keep the PortalHubConfig folder beside PortalHubConfig.bat, or install Python from python.org.
pause
