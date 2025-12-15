# 🎮 Epic Games Claimer

Automatize a coleta de jogos grátis da Epic Games Store com requisições HTTP puras - sem navegador, sem UI!

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

Este projeto automatiza completamente o processo de coleta de jogos grátis da Epic Games Store usando **apenas requisições HTTP**:

- ✅ Autentica via token do navegador ou device auth
- ✅ Detecta jogos grátis via API GraphQL oficial
- ✅ Adiciona os jogos à sua biblioteca automaticamente
- ✅ Gera logs detalhados organizados por data
- ✅ **Agendamento interno** - verifica diariamente às 12:00

## ✨ Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| 🌐 **100% HTTP** | Sem browser, sem UI, sem Playwright/Selenium |
| 🔑 **Múltiplas autenticações** | Token do browser, device auth, ou .env |
| ⏰ **Scheduler interno** | Executa automaticamente às 12:00 diariamente |
| 💾 **Persistência de sessão** | Token salvo para próximas execuções |
| 📊 **Logs detalhados** | Organizados em `logs/YYYY/MM/DD.txt` |
| 🔄 **Renovação automática** | Detecta e renova tokens expirados |
| ⚡ **Leve e rápido** | Execução em segundos, ~2MB de dependências |

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

## ⚙️ Configuração

### Opção 1: Token do Navegador (Recomendado)

1. Abra https://store.epicgames.com e faça login
2. Pressione `F12` → **Application** → **Cookies** → `store.epicgames.com`
3. Copie o valor do cookie `EPIC_EG1` (começa com `eg1~...`)
4. Execute o script helper:

```bash
python scripts/get_cookies.py
# Cole o token quando solicitado
```

### Opção 2: CF_CLEARANCE via Playwright (Automático)

Se você receber erro `GraphQL request blocked` (Cloudflare), use:

```bash
python get_cf_clearance.py
```

Este script:
- ✅ Abre um navegador automaticamente  
- ✅ Você faz login normalmente
- ✅ Aguarda resolução do desafio Cloudflare
- ✅ Extrai o cookie `cf_clearance` válido
- ✅ Atualiza automaticamente o `.env`

**Importante:** Este cookie dura apenas 24-48h. Se a execução falhar novamente, execute o script outra vez.

### Opção 3: Variáveis de Ambiente

1. Copie o arquivo de exemplo:

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

2. Edite `.env` e adicione seu token:

```env
EPIC_EG1=eg1~seu_token_aqui
```

### Opção 4: Device Auth (Automático)

Na primeira execução sem token, o script abrirá o navegador para autorização:

```bash
python main.py
# Siga as instruções na tela
```

### 📂 Perfil do Chrome

O claimer pode extrair cookies automaticamente do Chrome. Por padrão, ele usa o perfil `Profile negao`. Se esse perfil não existir, ele usa `Default`.

**Para usar um perfil diferente**, defina no `.env`:

```env
# Nome da pasta do perfil do Chrome
CHROME_PROFILE=Profile 1
```

**Para descobrir o nome do seu perfil:**
1. Abra Chrome e digite `chrome://version`
2. Procure "Caminho do perfil" (ex: `...\User Data\Profile 1`)
3. O nome do perfil é a última pasta (`Profile 1`)

**Onde os cookies/sessões são salvos:**
- A sessão é salva em `data/session.json`
- Cookies são lidos do Chrome (não modificados)
- Para renovar, basta fazer login no Chrome e reexecutar

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
ℹ️  Iniciando execução: 2025-12-15 12:00:00

──────────────────────────────────────────────────────────
  🔐 AUTENTICAÇÃO
──────────────────────────────────────────────────────────
✅ Sessão válida para: SeuNome [expires_in=5.2h]

──────────────────────────────────────────────────────────
  🎮 BUSCANDO JOGOS GRÁTIS
──────────────────────────────────────────────────────────
✅ Found 2 free games available now
🎮 Free game available: Jogo 1 [id=abc123...]
🎮 Free game available: Jogo 2 [id=def456...]
✅ 2 jogo(s) disponível(is) para resgate

──────────────────────────────────────────────────────────
  🎁 RESGATANDO JOGOS
──────────────────────────────────────────────────────────
🎮 Attempting to claim: Jogo 1 [offer_id=abc123...]
✅ Game claimed: Jogo 1
🎮 Attempting to claim: Jogo 2 [offer_id=def456...]
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

O projeto inclui um scheduler que roda continuamente:

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

### Variáveis de Ambiente

Configure no `.env`:

```env
# Horário do agendamento (padrão: 12:00)
SCHEDULE_HOUR=12
SCHEDULE_MINUTE=0
```

### Task Scheduler (Windows) - Alternativa

Se preferir agendamento externo:

```powershell
# Criar tarefa agendada
schtasks /create /tn "Epic Games Claimer" /tr "C:\caminho\scripts\run.bat" /sc daily /st 12:00
```

### Cron (Linux/macOS) - Alternativa

```bash
# Abrir crontab
crontab -e

# Adicionar linha (executa às 12:00 diariamente)
0 12 * * * cd /caminho/Epic-Games-Claimer && .venv/bin/python main.py
```

## 📁 Estrutura do Projeto

```
Epic-Games-Claimer/
├── main.py                 # CLI principal
├── requirements.txt        # Dependências Python
├── .env.example           # Exemplo de configuração
├── .env                   # Suas configurações (não versionado)
│
├── src/                   # Código fonte modular
│   ├── __init__.py
│   ├── config.py          # Configuração via ambiente
│   ├── logger.py          # Sistema de logs
│   ├── session_store.py   # Persistência de sessão
│   ├── api.py             # Cliente HTTP Epic Games
│   ├── claimer.py         # Lógica de resgate
│   └── scheduler.py       # Agendador interno
│
├── scripts/               # Scripts auxiliares
│   ├── get_cookies.py     # Extrai token do navegador
│   ├── run.bat            # Executa uma vez (Windows)
│   ├── run.sh             # Executa uma vez (Unix)
│   ├── run_scheduled.bat  # Modo agendado (Windows)
│   └── run_scheduled.sh   # Modo agendado (Unix)
│
├── data/                  # Dados persistentes
│   ├── session.json       # Sessão salva
│   └── next_games.json    # Info dos jogos
│
├── logs/                  # Logs organizados por data
│   └── 2025/
│       └── 12/
│           └── 15.txt
│
├── legacy/                # Scripts de debug e arquivos antigos
│   └── (debug_*.py, scripts antigos, HARs)
│
└── docs/                  # Documentação adicional
    └── http-flow.md
```

## 🔐 Segurança

- ⚠️ **Nunca compartilhe** seu arquivo `.env` ou `session.json`
- ✅ Adicione ao `.gitignore`:
  ```
  .env
  data/session.json
  ```
- 🔑 Tokens do navegador expiram em ~8 horas
- 🔄 Device auth tokens são renovados automaticamente

## 🔧 Troubleshooting

### ❌ "Token expirado"

```bash
# Gerar novo token
python scripts/get_cookies.py
```

### ❌ "Não foi possível autenticar"

1. Verifique se `.env` existe e tem credenciais válidas
2. Delete `data/session.json` para forçar novo login
3. Execute sem token para usar device auth interativo

### ❌ "Erro de conexão"

- Aumente o timeout no `.env`: `TIMEOUT=60`
- Verifique sua conexão com internet

### ❌ Logs não aparecem

- Verifique se a pasta `logs/` tem permissão de escrita
- Configure `LOG_BASE_DIR` no `.env` se necessário

## 📝 Changelog

### v2.0.0 (2025-12-15)
- ✨ Estrutura modular (`src/`)
- ⏰ Scheduler interno para verificação diária
- 📊 Logs aprimorados com contexto
- 🧹 Removido código duplicado
- 📚 Documentação atualizada

### v1.0.0
- 🎮 Versão inicial HTTP-only

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.
