@echo off
rem Opens the Portal Hub config editor (a plain, readable PowerShell script: tools\PortalHubConfig\PortalHubConfig.ps1).
rem This window closes by itself once the editor is closed. -ExecutionPolicy Bypass only applies to this one run.
echo Opening Portal Hub Config...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\PortalHubConfig\PortalHubConfig.ps1"
