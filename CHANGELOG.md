# 📝 CHANGELOG

## [2.0.0] - 2025-12-15 🎉

### ✨ Novidades
- **Scheduler interno** - Verifica jogos grátis automaticamente às 12:00 diariamente
- **Arquitetura modular** - Código dividido em módulos reutilizáveis (`src/`)
- **Logs aprimorados** - Contexto estruturado e detalhes em cada operação
- **CLI com comandos** - `--schedule`, `--check`, `--status`, etc.
- **Melhor segurança** - Type hints completos, validação de entrada

### 🔧 Refatoração
- Removido código duplicado (~300 linhas em `claim_game`, `_get_slug`, etc.)
- Consolidado em `src/api.py` (sem duplicações)
- Sessão salva com JWT decodificado para melhor persistência
- Logger com contexto em cada chamada

### 🗂️ Reorganização
- **Nova estrutura**:
  ```
  src/          → Código modular
  scripts/      → Helpers (get_cookies.py, run.bat, run.sh)
  docs/         → Documentação (ARCHITECTURE.md)
  _old/         → Arquivos descontinuados
  ```

### ❌ Removido
- `epic_games_claimer.py` (monolítico, 1.2k linhas)
- `epic_games_logger.py` (substituído por aprimorado)
- Arquivos `.har` (debug)
- `install.bat/sh` (substituído por pip)
- `get_cookies.py` da raiz (movido para `scripts/`)

### 📊 Estatísticas
- **Antes**: 1 arquivo de 1.2k linhas + logs simples
- **Depois**: 7 módulos focados + logs estruturados
- **Duplicação removida**: ~300 linhas
- **Cobertura de logs**: 90%+ das operações com contexto

### 🚀 Como Usar

#### Modo Uma Vez
```bash
python main.py
```

#### Modo Agendado (12:00 diariamente)
```bash
python main.py --schedule
```

#### Apenas Verificar
```bash
python main.py --check
```

#### Ver Status
```bash
python main.py --status
```

### ✅ Testes
```bash
# Verificar imports
python -c "from src import *; print('✅ OK')"

# Testar CLI
python main.py --help
python main.py --status
```

### 📚 Documentação
- `README.md` - Guia de uso principal
- `docs/ARCHITECTURE.md` - Estrutura técnica (novo!)
- `docs/http-flow.md` - Fluxo de requisições HTTP
- `.env.example` - Variáveis de configuração

### 🔒 Segurança
- Tokens nunca logados em texto completo
- `.env` e `session.json` ignorados pelo git
- Type hints para validação de entrada

### 🎯 Próximos Steps Sugeridos
1. Testar modo agendado por algumas horas
2. Verificar logs em `logs/2025/12/15.txt`
3. Deletar pasta `_old/` se não precisar mais
4. Adicionar à Task Scheduler/cron se desejar persistência

---

## [1.0.0] - 2025-12-14

### ✨ Inicial
- ✅ Autenticação via token navegador
- ✅ Device auth flow
- ✅ Busca de jogos grátis (GraphQL)
- ✅ Resgate automático
- ✅ Persistência de sessão
- ✅ Logs organizados por data
