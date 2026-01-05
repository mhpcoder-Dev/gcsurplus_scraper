@echo off
REM Quick Start Script for FastAPI Backend
REM Handles everything automatically

echo.
echo ============================================================
echo   Starting Auction Scraper Backend
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python found

REM Navigate to the script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/update dependencies
echo.
echo Installing dependencies...
echo This may take 1-2 minutes on first run...
pip install --prefer-binary -r requirements.txt

REM Check if using PostgreSQL and install psycopg2 if needed
findstr /C:"postgresql://" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo Detected PostgreSQL - Installing database driver...
    pip install -q psycopg2-binary==2.9.9 || (
        echo [WARNING] psycopg2-binary installation failed
        echo You can continue with SQLite or manually install: pip install psycopg2-binary
    )
)

REM Create .env if it doesn't exist
if not exist ".env" (
    echo.
    echo Creating .env file with defaults...
    (
        echo DATABASE_URL=sqlite:///./auction_data.db
        echo GSA_API_KEY=rXyfDnTjMh3d0Zu56fNcMbHb5dgFBQrmzfTjZqq3
        echo DELETE_CLOSED_IMMEDIATELY=true
    ) > .env
    echo [OK] Created .env file with SQLite database
)

REM Run the quick start script
echo.
echo Starting server...
echo.
python start.py

REM Deactivate virtual environment on exit
deactivate
