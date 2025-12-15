@echo off
:: ============================================================================
:: Epic Games Claimer - AutoStart
:: Executa automaticamente ao iniciar o Windows
:: ============================================================================

cd /d "%~dp0.."
call .venv\Scripts\activate.bat

:: Executa uma vez ao iniciar e depois fica em modo agendado
python main.py --schedule

pause
