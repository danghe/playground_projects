@echo off
setlocal

REM M&A Forecast "Smart Runner" for Windows
REM 1. Checks for Python
REM 2. Creates virtual environment (.venv) if missing
REM 3. Installs dependencies
REM 4. Runs the app

cd /d "%~dp0"

echo ===================================================
echo    Intralinks M&A Health Forecast - Launcher
echo ===================================================

REM 1. Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python could not be found.
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM 2. Check/Create Virtual Environment
if exist ".venv" (
    if not exist ".venv\Scripts\activate.bat" (
        echo [INFO] Detected invalid virtual environment. Recreating...
        rmdir /s /q .venv
    )
)

if not exist ".venv" (
    echo [INFO] First run detected. Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Virtual environment created.
)

REM 3. Install/Update Dependencies
echo [INFO] Checking and installing dependencies (including yfinance/deal-radar)...
call .venv\Scripts\activate.bat

if exist "requirements.txt" (
    REM Removed >nul to allow users to see download progress for new tools
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [INFO] Dependencies are ready.
) else (
    echo WARNING: requirements.txt not found.
)

REM 4. Run App
echo [INFO] Starting application...
echo ---------------------------------------------------
echo Open your browser to: http://127.0.0.1:5000
echo ---------------------------------------------------
REM Force unbuffered Python output (ensure logs appear immediately)
set PYTHONUNBUFFERED=1

python app.py

pause
endlocal
