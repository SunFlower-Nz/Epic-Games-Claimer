# 🎮 Epic Games Claimer

Automatize a coleta de jogos grátis da Epic Games Store usando Chrome real via CDP + Playwright.

## 📋 Índice

- [Descrição](#-descrição)
- [Funcionalidades](#-funcionalidades)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Como Usar](#-como-usar)
- [Agendamento Automático](#-agendamento-automático)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Troubleshooting](#-troubleshooting)

## 🎯 Descrição

Este projeto automatiza completamente o processo de coleta de jogos grátis da Epic Games Store:

- ✅ Usa **Chrome real** via CDP (Chrome DevTools Protocol) para bypass de Cloudflare
- ✅ Injeta cookies de autenticação automaticamente no browser
- ✅ Detecta jogos grátis via API oficial da Epic
- ✅ Adiciona os jogos à sua biblioteca automaticamente (inclusive 18+)
- ✅ Gera logs detalhados organizados por data
- ✅ **Agendamento interno** — verifica diariamente às 12:00

## ✨ Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| 🌐 **Chrome CDP** | Usa seu Chrome real com perfil copiado via DevTools Protocol |
| 🔑 **Cookie injection** | Injeta EPIC_EG1 automaticamente (bypass App-Bound Encryption) |
| 🛡️ **Bypass Cloudflare** | Chrome real evita bloqueios de bot |
| 🎂 **Age Gate** | Preenche data de nascimento automaticamente para jogos 18+ |
| ⏰ **Scheduler interno** | Executa automaticamente às 12:00 diariamente |
| 💾 **Persistência de sessão** | Token salvo para próximas execuções |
| 📊 **Logs detalhados** | Organizados em `logs/YYYY/MM/DD.txt` |
| 🔄 **Renovação automática** | Detecta e renova tokens expirados |
| 🧩 **Fallback Chromium** | Se Chrome real não disponível, usa Playwright Chromium |

## 🔧 Instalação

### 1. Clone o Repositório

```bash
git clone https://github.com/SunFlower-Nz/Epic-Games-Claimer.git
cd Epic-Games-Claimer
```

### 2. Crie um Ambiente Virtual

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Instale o Playwright

```bash
playwright install chromium
```

## ⚙️ Configuração

### Opção 1: Automática via Chrome (Recomendado)

O claimer extrai cookies automaticamente do seu Chrome instalado:

1. Abra https://store.epicgames.com no Chrome e faça login
2. Execute o claimer — ele copiará seu perfil para automação via CDP

```bash
python main.py
```

> **Nota:** O Chrome precisa estar **fechado** antes de executar, pois o claimer lança uma instância com CDP.

### Opção 2: Token Manual via Script

```bash
python scripts/get_cookies.py
# Cole o token EPIC_EG1 quando solicitado
```

Para obter o token:
1. Abra https://store.epicgames.com e faça login
2. Pressione `F12` → **Application** → **Cookies** → `store.epicgames.com`
3. Copie o valor do cookie `EPIC_EG1` (começa com `eg1~...`)

### Opção 3: Variáveis de Ambiente

```bash
# Copie o template
cp .env.example .env  # Linux/macOS
copy .env.example .env  # Windows

# Edite e adicione seu token
EPIC_EG1=eg1~seu_token_aqui
```

### 📂 Perfil do Chrome

O claimer copia o perfil do Chrome para um diretório temporário e lança com CDP. Por padrão usa o perfil `Default`.

**Para usar um perfil diferente**, defina no `.env`:

```env
CHROME_PROFILE=Profile 1
```

**Para descobrir o nome do seu perfil:**
1. Abra Chrome e digite `chrome://version`
2. Procure "Caminho do perfil" (ex: `...\User Data\Profile 1`)
3. O nome do perfil é a última pasta (`Profile 1`)

## 🚀 Como Usar

### Comandos Disponíveis

```bash
# Executar uma vez (resgatar jogos grátis)
python main.py

# Modo agendado (verifica às 12:00 diariamente)
python main.py --schedule

# Apenas verificar jogos disponíveis (sem resgatar)
python main.py --check

# Ver status do agendamento
python main.py --status

# Configurar horário personalizado
python main.py --schedule --hour 18 --minute 30

# Ajuda
python main.py --help
```

### Exemplo de Saída

```
======================================================================
  🎮 EPIC GAMES CLAIMER
======================================================================
ℹ️  Iniciando execução

──────────────────────────────────────────────────────────
  🔐 AUTENTICAÇÃO
──────────────────────────────────────────────────────────
✅ Sessão válida [expires_in=5.2h]

──────────────────────────────────────────────────────────
  🎮 BUSCANDO JOGOS GRÁTIS
──────────────────────────────────────────────────────────
✅ 2 jogo(s) disponível(is) para resgate

──────────────────────────────────────────────────────────
  🎁 RESGATANDO JOGOS
──────────────────────────────────────────────────────────
🌐 Conectado ao Chrome real via CDP
✅ Game claimed: Jogo 1
✅ Game claimed: Jogo 2

──────────────────────────────────────────────────────────
  📊 RESUMO DA EXECUÇÃO
──────────────────────────────────────────────────────────
   ✅ Resgatados:   2
   📦 Já possuídos: 0
   ❌ Falhas:       0
──────────────────────────────────────────────────────────
```

## ⏰ Agendamento Automático

### Scheduler Interno (Recomendado)

```bash
# Inicia o scheduler (roda às 12:00 por padrão)
python main.py --schedule

# Personalizar horário (exemplo: 18:30)
python main.py --schedule --hour 18 --minute 30
```

O scheduler:
- ✅ Executa imediatamente ao iniciar
- ✅ Calcula próxima execução às 12:00 (ou horário configurado)
- ✅ Roda em loop até ser interrompido (Ctrl+C)
- ✅ Logs detalhados de cada execução

### Task Scheduler (Windows) — Alternativa

```powershell
schtasks /create /tn "Epic Games Claimer" /tr "C:\caminho\scripts\run.bat" /sc daily /st 12:00
```

### Cron (Linux/macOS) — Alternativa

```bash
crontab -e
# Adicionar linha:
0 12 * * * cd /caminho/Epic-Games-Claimer && .venv/bin/python main.py
```

## 📁 Estrutura do Projeto

```
Epic-Games-Claimer/
├── main.py                 # CLI principal
├── pyproject.toml          # Configuração do projeto (Ruff, pytest)
├── requirements.txt        # Dependências Python
├── .env.example            # Exemplo de configuração
│
├── src/                    # Código fonte modular
│   ├── api.py              # Cliente HTTP + browser claiming
│   ├── browser.py          # BrowserManager (Chrome CDP + Playwright)
│   ├── claimer.py          # Orquestração do resgate
│   ├── models.py           # Constantes, seletores, enums
│   ├── config.py           # Configuração via ambiente
│   ├── logger.py           # Sistema de logs
│   ├── session_store.py    # Persistência de sessão
│   ├── scheduler.py        # Agendador interno
│   ├── chrome_cookies.py   # Extração de cookies (DPAPI/legacy)
│   └── playwright_cookies.py # Login interativo via Playwright
│
├── scripts/                # Scripts auxiliares
│   ├── get_cookies.py      # Extrai token do navegador
│   ├── login.py            # Login interativo
│   ├── benchmark.py        # Benchmarks de performance
│   ├── run.bat / run.sh    # Executa uma vez
│   └── run_scheduled.*     # Modo agendado
│
├── tests/                  # Suite de testes
│   ├── conftest.py         # Fixtures do pytest
│   └── test_*.py           # Arquivos de teste
│
├── data/                   # Dados persistentes (não versionado)
│   ├── session.json        # Sessão salva
│   └── next_games.json     # Info dos jogos
│
├── logs/                   # Logs organizados por data
│   └── YYYY/MM/DD.txt
│
└── docs/                   # Documentação técnica
    ├── ARCHITECTURE.md     # Estrutura e módulos
    ├── SECURITY.md         # Práticas de segurança
    ├── RENEW_TOKEN.md      # Guia de renovação de token
    └── http-flow.md        # Referência de endpoints HTTP
```

## 🧪 Desenvolvimento

### Ferramentas de Qualidade

O projeto usa [Ruff](https://docs.astral.sh/ruff/) para linting e formatação:

```bash
# Instalar dependências de desenvolvimento
pip install -e ".[dev]"

# Verificar código
ruff check src/ tests/

# Formatar código
ruff format src/ tests/

# Corrigir problemas automaticamente
ruff check --fix src/ tests/
```

### Executar Testes

```bash
pytest
pytest --cov=src
```

## 🔐 Segurança

- ⚠️ **Nunca compartilhe** seu `.env` ou `data/session.json`
- ✅ Ambos estão no `.gitignore`
- 🔑 Tokens do navegador expiram em ~8 horas
- 🔄 Sessão renovada automaticamente quando possível
- 🔒 Nenhuma senha é solicitada ou armazenada

## 🔧 Troubleshooting

### ❌ "Token expirado"

```bash
python scripts/get_cookies.py
```

Ou simplesmente faça login no Chrome e execute novamente — o claimer extrairá os cookies automaticamente.

### ❌ "Chrome não conecta via CDP"

- Feche todas as instâncias do Chrome antes de executar
- Verifique se a porta 9222 não está em uso: `netstat -ano | findstr 9222`

### ❌ "CAPTCHA apareceu"

O claimer aguarda até 5 minutos para resolução manual de CAPTCHA (hCaptcha). Se aparecer, resolva manualmente na janela do Chrome que abrir.

### ❌ "Erro de conexão"

- Aumente o timeout no `.env`: `TIMEOUT=60`
- Verifique sua conexão com internet

### ❌ "Jogo não foi resgatado"

- Verifique os logs em `logs/debug/` para screenshots e dumps HTML
- O jogo pode requerer verificação de idade (age gate) — o claimer tenta automaticamente
- Alguns jogos podem ter CAPTCHA que precisa de resolução manual

## 📝 Changelog

Veja [CHANGELOG.md](CHANGELOG.md) para histórico completo.

## 📄 Licença

MIT License
