@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restart-ui.ps1"
if errorlevel 1 (
    pause
    exit /b 1
)
