@echo off
REM Epic Games Claimer - Windows Scheduled Run Script
REM Runs the claimer in scheduled mode (daily at 12:00)

cd /d "%~dp0"

REM Check for virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run in scheduled mode
python main.py --schedule

pause
