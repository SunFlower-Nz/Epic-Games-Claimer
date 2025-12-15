# 📂 Estrutura do Projeto - Epic Games Claimer v2.0.0

## 🏗️ Visão Geral

```
Epic-Games-Claimer/
├── main.py                 # ⭐ Ponto de entrada (CLI)
├── requirements.txt        # Dependências Python
├── README.md              # Documentação principal
├── .env.example           # Configuração de exemplo
├── .env                   # Sua configuração (não versionada)
├── .gitignore
│
├── src/                   # 📦 Código modular (novo)
│   ├── __init__.py
│   ├── config.py          # Leitura de env vars
│   ├── logger.py          # Sistema de logs melhorado
│   ├── session_store.py   # Persistência de sessão
│   ├── api.py             # Cliente HTTP Epic Games
│   ├── claimer.py         # Orquestração do resgate
│   └── scheduler.py       # Agendador interno (12h)
│
├── scripts/               # 🔧 Scripts auxiliares
│   ├── get_cookies.py     # Extrai token do navegador
│   ├── run.bat            # Executa (Windows)
│   ├── run.sh             # Executa (Unix)
│   ├── run_scheduled.bat  # Modo agendado (Windows)
│   └── run_scheduled.sh   # Modo agendado (Unix)
│
├── data/                  # 💾 Dados persistentes
│   ├── session.json       # Sessão salva (não versionada)
│   ├── next_games.json    # Info dos jogos
│   └── .gitkeep
│
├── logs/                  # 📝 Logs organizados
│   └── YYYY/MM/DD.txt
│
├── docs/                  # 📚 Documentação
│   └── http-flow.md       # Fluxo de requisições HTTP
│
├── _old/                  # 📦 Arquivos descontinuados
│   └── README.md          # Explicação dos antigos
│
└── .venv/                 # 🐍 Ambiente virtual (não versionado)
```

## 📖 Descrição dos Módulos

### `src/config.py`
- **Responsabilidade**: Ler variáveis de ambiente
- **Exporta**: `Config` (dataclass com todas as configurações)
- **Usa**: `python-dotenv`
- **Produz**: Objeto de configuração centralizado

### `src/logger.py`
- **Responsabilidade**: Logging estruturado e contextualizado
- **Exporta**: `Logger` (wrapper do logging.Logger)
- **Recursos**:
  - Logs no console (INFO+) e arquivo (DEBUG+)
  - Organização por data: `logs/YYYY/MM/DD.txt`
  - Métodos de conveniência: `.success()`, `.game()`, `.auth()`, etc.
  - Suporte a contexto: `logger.success("Msg", account_id="xyz")`

### `src/session_store.py`
- **Responsabilidade**: Persistência de sessão de autenticação
- **Exporta**: `Session` (dataclass), `SessionStore` (gerenciador)
- **Recursos**:
  - Carregar/salvar sessão em `data/session.json`
  - Conversão de formato legado (Playwright)
  - Decodificação de JWT do token `eg1~...`
  - Validação e cálculo de expiração

### `src/api.py`
- **Responsabilidade**: Cliente HTTP para APIs Epic Games
- **Exporta**: `EpicAPI` (todas as chamadas HTTP)
- **Endpoints**:
  - OAuth (device auth, token refresh, verify)
  - Catalog (GraphQL - free games)
  - Entitlements (jogos que você já possui)
  - Order (claim/resgate)
- **Recursos**:
  - Logging detalhado de requests/responses
  - Tratamento de erros por status code
  - Retry automático com backoff

### `src/claimer.py`
- **Responsabilidade**: Orquestração do fluxo de resgate
- **Exporta**: `EpicGamesClaimer` (orquestrador), `ClaimResult` (resultado)
- **Fluxo**:
  1. Autenticar (session salva → refresh → fallback → device auth)
  2. Buscar jogos grátis disponíveis
  3. Filtrar jogos já possuídos
  4. Resgatar cada jogo
  5. Salvar informações e logs

### `src/scheduler.py`
- **Responsabilidade**: Agendamento automático (12:00 diariamente)
- **Exporta**: `Scheduler` (agendador)
- **Recursos**:
  - Calcula próximo tempo de execução
  - Loop contínuo com sleep inteligente
  - Graceful shutdown (Ctrl+C)
  - Logging de eventos de agendamento

### `main.py`
- **Responsabilidade**: Interface CLI
- **Comandos**:
  - `python main.py` - Executa uma vez
  - `python main.py --schedule` - Modo agendado
  - `python main.py --check` - Só verifica
  - `python main.py --status` - Status do agendador
  - `python main.py --help` - Ajuda

## 🔄 Fluxo de Dados

```
main.py (CLI)
    ↓
Config (ler .env)
Logger (setup logs)
    ↓
EpicGamesClaimer
    ├── EpicAPI (HTTP requests)
    ├── SessionStore (JWT decode, persist)
    └── Scheduler (se --schedule)
        ↓
    Autentica → Busca jogos → Resgata → Logs
```

## 📋 Checklist de Funções

| Função | Módulo | Status |
|--------|--------|--------|
| Autenticação device auth | `api.py` | ✅ |
| Token refresh | `api.py` | ✅ |
| Buscar jogos grátis (GraphQL) | `api.py` | ✅ |
| Verificar posse (entitlements) | `api.py` | ✅ |
| Resgatar jogo | `api.py` | ✅ |
| Persistir sessão | `session_store.py` | ✅ |
| Logs estruturados | `logger.py` | ✅ |
| Agendamento interno | `scheduler.py` | ✅ |
| CLI com comandos | `main.py` | ✅ |

## 🧹 Limpeza Realizada (v2.0)

### ❌ Removido (movido para `_old/`)
- `epic_games_claimer.py` (monolítico, 1.2k linhas)
- `epic_games_claimer_backup.py` (backup desnecessário)
- `epic_games_logger.py` (substituído por aprimorado)
- `get_cookies.py` (movido para `scripts/`)
- `run.bat` / `run.sh` (movidos para `scripts/`)
- `install.bat` / `install.sh` (obsoletos)
- `*.har` (debug files)

### ✅ Mantido
- `.env.example` (template importante)
- `requirements.txt` (dependências)
- `README.md` (documentação)
- `docs/` (fluxos técnicos)
- `.git/` (histórico)

## 🚀 Próximas Melhorias

1. **Testes unitários** em `tests/`
2. **CI/CD** (GitHub Actions)
3. **Docker** para deploy
4. **Notificações** (Discord/Telegram)
5. **Dashboard** (web UI)

## 📝 Convenções

- **Imports**: Agrupados (stdlib, 3rd party, local)
- **Type hints**: Todas as funções anotadas
- **Docstrings**: Em todas as classes e funções públicas
- **Logs**: Contexto em chave=valor
- **Erros**: Capturados com detalhes e stack trace em DEBUG
