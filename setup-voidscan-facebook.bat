@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Cannot find Python on this Windows computer.
        pause
        exit /b 1
    )
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create VOIDSCAN browser virtual environment.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import playwright.sync_api" >nul 2>&1
if errorlevel 1 (
    echo Installing Playwright in VOIDSCAN's isolated environment...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-browser.txt
    if errorlevel 1 (
        echo Playwright installation failed. Check your Internet connection.
        pause
        exit /b 1
    )
)
echo Opening a separate Chrome window for Facebook.
echo Sign in yourself. Do not share your password or verification code.
echo Close the Chrome window to stop this browser session.
".venv\Scripts\python.exe" -u facebook_browser.py launch --url "https://www.facebook.com/tuoitretruongthptdian/posts/pfbid027NL9w2QaKQ3gf7vPztXfczuaaaHi1w6PZUzbSfn8V2w27xMAi6HVJS5LtLumdNkYl"
if errorlevel 1 (
    echo VOIDSCAN Facebook browser could not start.
    pause
)
endlocal
