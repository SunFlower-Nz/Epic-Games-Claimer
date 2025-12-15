@echo off
REM Epic Games Claimer - Windows Run Script
REM Runs the claimer once

cd /d "%~dp0"

REM Check for virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run the claimer
python main.py %*

pause
