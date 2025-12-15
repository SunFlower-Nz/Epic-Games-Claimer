
#!/bin/bash
# Script de execução para Linux/macOS
# Execute com: bash run.sh

cd "$(dirname "$0")"

# Ativa ambiente virtual
source venv/bin/activate

# Executa o script
python epic_games_claimer.py

# Desativa ambiente virtual
deactivate
