@echo off
rem Builds dist\PortalHubConfig\PortalHubConfig.exe. Needs Python with PyInstaller (pip install pyinstaller).
rem One-folder on purpose: a one-file build unpacks itself at each start, which antivirus tools flag far more often.
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onedir --windowed --name PortalHubConfig --add-data "icons;icons" PortalHubConfig.py
