@echo off
REM Windows helper: bypasses PowerShell ExecutionPolicy for this run only.
cd /d "%~dp0\.."
echo Running create-admin in PowerShell. Do not edit the script; answer the prompts.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create-admin.ps1" %*
exit /b %ERRORLEVEL%
