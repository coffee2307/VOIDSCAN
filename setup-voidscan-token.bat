@echo off
chcp 65001 >nul
cd /d "%~dp0"
python manage_token.py set
echo.
pause
