@echo off
REM Windows helper: bypasses PowerShell ExecutionPolicy for this run only.
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0reset-data.ps1" %*
exit /b %ERRORLEVEL%
