@echo off
REM Windows helper: bypasses PowerShell ExecutionPolicy for this run only.
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply-source.ps1"
exit /b %ERRORLEVEL%
