
@echo off
REM Script de instalação automática para Windows
REM Execute com: install.bat

echo ==========================================
echo Epic Games Claimer - Instalacao
echo ==========================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python nao encontrado. Por favor, instale Python 3.8 ou superior.
    pause
    exit /b 1
)

echo OK Python encontrado
python --version
echo.

REM Cria ambiente virtual
echo Criando ambiente virtual...
python -m venv venv

REM Ativa ambiente virtual
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Instala dependências
echo Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Instala browsers do Playwright
echo Instalando browsers do Playwright...
playwright install chromium

REM Cria arquivo .env se não existir
if not exist .env (
    echo Criando arquivo .env...
    copy .env.example .env
    echo.
    echo IMPORTANTE: Edite o arquivo .env com suas credenciais!
)

REM Cria diretório de dados
echo Criando diretorio de dados...
if not exist data mkdir data

echo.
echo ==========================================
echo OK Instalacao concluida com sucesso!
echo ==========================================
echo.
echo Proximos passos:
echo 1. Configure suas credenciais no arquivo .env
echo 2. Execute o script com: venv\Scripts\activate e python epic_games_claimer.py
echo.
pause
