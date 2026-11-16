@echo off
rem Builds dist\PortalHubConfig\PortalHubConfig.exe. Needs Python with PyInstaller (pip install pyinstaller).
rem One-folder on purpose: a one-file build unpacks itself at each start, which antivirus tools flag far more often.
cd /d "%~dp0"
rem The stills of the looks (previews\, CRD-046) go in too when the folder is there.
set PREVIEWS=
if exist previews\ set PREVIEWS=--add-data "previews;previews"
python -m PyInstaller --noconfirm --clean --onedir --windowed --name PortalHubConfig --add-data "icons;icons" %PREVIEWS% PortalHubConfig.py
