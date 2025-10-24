
#!/bin/bash
# Script de instalação automática para Linux/macOS
# Execute com: bash install.sh

echo "=========================================="
echo "Epic Games Claimer - Instalação"
echo "=========================================="
echo ""

# Verifica se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.8 ou superior."
    exit 1
fi

echo "✓ Python encontrado: $(python3 --version)"
echo ""

# Cria ambiente virtual
echo "📦 Criando ambiente virtual..."
python3 -m venv venv

# Ativa ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source venv/bin/activate

# Instala dependências
echo "📥 Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# Instala browsers do Playwright
echo "🌐 Instalando browsers do Playwright..."
playwright install chromium

# Cria arquivo .env se não existir
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANTE: Edite o arquivo .env com suas credenciais!"
    echo "   Use: nano .env ou vim .env"
fi

# Cria diretório de dados
echo "📂 Criando diretório de dados..."
mkdir -p data

echo ""
echo "=========================================="
echo "✅ Instalação concluída com sucesso!"
echo "=========================================="
echo ""
echo "Próximos passos:"
echo "1. Configure suas credenciais no arquivo .env"
echo "2. Execute o script com: source venv/bin/activate && python epic_games_claimer.py"
echo ""
