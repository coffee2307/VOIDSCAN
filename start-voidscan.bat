@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
    echo Khong tim thay Python. Hay cai Python 3.10+.
    pause
    exit /b 1
)
python launch_voidscan.py
if errorlevel 1 pause
