# 📂 Arquitetura — Epic Games Claimer v3.0.0

## 🏗️ Visão Geral

O claimer usa **Chrome real via CDP** (Chrome DevTools Protocol) para acessar a Epic Games Store, injetar cookies de autenticação e resgatar jogos grátis. Quando Chrome real não está disponível, faz fallback para Playwright Chromium.

## 📁 Estrutura

```
Epic-Games-Claimer/
├── main.py                     # ⭐ Ponto de entrada (CLI)
├── pyproject.toml              # Configuração do projeto (Ruff, pytest)
├── requirements.txt            # Dependências Python
├── .env.example                # Template de configuração
│
├── src/                        # 📦 Código modular
│   ├── __init__.py
│   ├── api.py                  # Cliente HTTP + browser claiming
│   ├── browser.py              # BrowserManager (Chrome CDP + Playwright)
│   ├── claimer.py              # Orquestração do resgate
│   ├── models.py               # Constantes, seletores, enums
│   ├── config.py               # Configuração via variáveis de ambiente
│   ├── logger.py               # Sistema de logs estruturado
│   ├── session_store.py        # Persistência de sessão (JWT)
│   ├── scheduler.py            # Agendador interno
│   ├── chrome_cookies.py       # Extração de cookies (DPAPI/legacy)
│   └── playwright_cookies.py   # Login interativo via Playwright
│
├── scripts/                    # 🔧 Scripts auxiliares
│   ├── get_cookies.py          # Extrai token do navegador
│   ├── login.py                # Login interativo
│   ├── benchmark.py            # Benchmarks de performance
│   ├── run.bat / run.sh        # Executa uma vez
│   └── run_scheduled.*         # Modo agendado
│
├── tests/                      # 🧪 Suite de testes
│   ├── conftest.py             # Fixtures do pytest
│   └── test_*.py               # Arquivos de teste
│
├── data/                       # 💾 Dados persistentes (não versionado)
│   ├── session.json            # Sessão salva
│   └── next_games.json         # Info dos jogos
│
├── logs/                       # 📝 Logs organizados
│   ├── YYYY/MM/DD.txt          # Logs por data
│   └── debug/                  # Screenshots e dumps HTML
│
└── docs/                       # 📚 Documentação
    ├── ARCHITECTURE.md
    ├── SECURITY.md
    ├── RENEW_TOKEN.md
    └── http-flow.md
```

## 📖 Descrição dos Módulos

### `src/browser.py` — BrowserManager
- **Responsabilidade**: Gerenciar conexão com browser (Chrome CDP ou Playwright Chromium)
- **Fluxo Chrome CDP**:
  1. Fecha Chrome existente (`taskkill`)
  2. Copia perfil do Chrome para diretório temporário (Chrome recusa CDP no diretório padrão)
  3. Lança Chrome com `--remote-debugging-port=9222`
  4. Conecta via Playwright `connect_over_cdp()`
  5. Injeta cookies (EPIC_EG1, cf_clearance) no contexto via `context.add_cookies()`
- **Fallback**: Se Chrome real não disponível, usa Playwright Chromium com `playwright-stealth`

### `src/api.py` — EpicAPI
- **Responsabilidade**: Cliente HTTP para APIs Epic Games + automação de browser para claiming
- **Endpoints HTTP**: OAuth, GraphQL (catálogo), Entitlements, Order
- **Browser Claiming** (`_claim_via_playwright`):
  1. Navega para a página do produto
  2. Trata age gate (jogos 18+)
  3. Clica no botão de claim ("Obter" / "Get")
  4. Clica "Place Order" no checkout
  5. Monitora CAPTCHA e resultado
- **Verificação**: Usa namespace matching (offer ID ≠ catalogItemId nos entitlements)

### `src/claimer.py` — EpicGamesClaimer
- **Responsabilidade**: Orquestração do fluxo completo
- **Fluxo**:
  1. Autenticar (session salva → cookie do Chrome → Playwright login)
  2. Buscar jogos grátis disponíveis
  3. Filtrar jogos já possuídos (por namespace)
  4. Resgatar cada jogo via browser
  5. Salvar resultados e logs

### `src/models.py` — Modelos e Constantes
- **Exporta**: `ClaimStatus` (enum), `EpicCookies` (dataclass)
- **Constantes**: `CLAIM_BUTTON_SELECTORS`, `CHECKOUT_SELECTORS`, `CAPTCHA_KEYWORDS`, `SUCCESS_PATTERNS`, `ALREADY_OWNED_PATTERNS`
- **IDs**: Client IDs da Epic (EGL, Diesel Web)

### `src/config.py` — Config
- **Responsabilidade**: Ler variáveis de ambiente via `python-dotenv`
- **Configurações**: Paths, auth, scheduler, browser (CDP port, Chrome profile), locale, timeouts

### `src/session_store.py` — SessionStore
- **Responsabilidade**: Persistência de sessão de autenticação
- **Recursos**: Decodificação JWT de tokens `eg1~`, cálculo de expiração, conversão de formatos

### `src/logger.py` — Logger
- **Responsabilidade**: Logging estruturado (console + arquivo)
- **Organização**: `logs/YYYY/MM/DD.txt`
- **Métodos**: `.success()`, `.game()`, `.auth()`, `.separator()`

### `src/scheduler.py` — Scheduler
- **Responsabilidade**: Execução periódica (padrão: 12:00 diariamente)
- **Recursos**: Loop contínuo, graceful shutdown (Ctrl+C), cálculo de próxima execução

### `src/chrome_cookies.py` — ChromeCookieExtractor
- **Responsabilidade**: Extrair cookies do Chrome via DPAPI (Windows, Chrome < 127)
- **Status**: Legacy — Chrome 127+ usa App-Bound Encryption, tornando DPAPI insuficiente

### `src/playwright_cookies.py` — PlaywrightCookieExtractor
- **Responsabilidade**: Login interativo via Playwright para obter cookies frescos
- **Uso**: Fallback quando sessão inválida e Chrome cookies não disponíveis

## 🔄 Fluxo de Dados

```
main.py (CLI)
    ↓
Config (.env) + Logger (setup)
    ↓
EpicGamesClaimer
    ├── SessionStore (carregar sessão)
    ├── EpicAPI
    │   ├── HTTP: verificar token, buscar jogos, entitlements
    │   └── Browser: BrowserManager → Chrome CDP → claim
    └── Scheduler (se --schedule)
        ↓
    Autenticar → Buscar jogos → Filtrar → Resgatar → Verificar → Logs
```

## 🧪 Qualidade de Código

| Ferramenta | Uso |
|------------|-----|
| **Ruff** | Linting + Formatação |
| **pytest** | Testes automatizados |
| **pytest-cov** | Cobertura de código |

```bash
pip install -e ".[dev]"
ruff check src/ tests/
ruff format src/ tests/
pytest --cov=src
```
