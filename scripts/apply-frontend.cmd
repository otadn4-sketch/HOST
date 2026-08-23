@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply-frontend.ps1"
exit /b %ERRORLEVEL%
