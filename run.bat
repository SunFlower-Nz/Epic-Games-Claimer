
@echo off
REM Script de execução para Windows
REM Execute com: run.bat

cd /d %~dp0

REM Ativa ambiente virtual
call venv\Scripts\activate.bat

REM Executa o script
python epic_games_claimer.py

REM Desativa ambiente virtual
deactivate

pause
