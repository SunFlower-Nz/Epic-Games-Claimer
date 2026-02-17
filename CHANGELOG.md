# 📝 CHANGELOG

## [3.0.0] - 2026-02-17 🎉

### ✨ Novidades
- **Chrome CDP** — Usa Chrome real via DevTools Protocol (porta 9222) para bypass de Cloudflare
- **Cookie injection** — Injeta EPIC_EG1 no contexto do browser (bypass App-Bound Encryption)
- **BrowserManager** — Novo módulo `src/browser.py` unifica Chrome CDP e Playwright Chromium
- **Models** — Novo módulo `src/models.py` com constantes, seletores e enums centralizados
- **Age Gate automático** — Preenche data de nascimento para jogos 18+
- **Direct purchase fallback** — URL direta de compra quando botão checkout não encontrado
- **Verificação por namespace** — Entitlements verificados por namespace (offer ID ≠ catalogItemId)

### 🔧 Melhorias
- Checkout flow: clica "Place Order" primeiro, depois verifica CAPTCHA
- Detecção de CAPTCHA mais estrita (verifica visibilidade do iframe + keywords fortes)
- Detecção de resultado: verifica sucesso antes de "já possuído"
- Chrome lançado com perfil copiado para diretório temporário
- Click strategy: tenta click normal primeiro (preserva event handlers)

### ❌ Removido
- Diretório `legacy/` inteiro (substituído por `src/`)
- Documentação obsoleta sobre Cloudflare workarounds
- Dados sensíveis removidos do histórico do git

### 🔐 Segurança
- Dados pessoais removidos de toda a documentação
- Histórico do git reescrito com `git-filter-repo`

---

## [2.0.0] - 2025-12-15

### ✨ Novidades
- **Scheduler interno** — Verifica jogos grátis automaticamente às 12:00 diariamente
- **Arquitetura modular** — Código dividido em módulos reutilizáveis (`src/`)
- **Logs aprimorados** — Contexto estruturado e detalhes em cada operação
- **CLI com comandos** — `--schedule`, `--check`, `--status`, etc.

### 🔧 Refatoração
- Removido código duplicado (~300 linhas em `claim_game`, `_get_slug`, etc.)
- Consolidado em `src/api.py` (sem duplicações)
- Sessão salva com JWT decodificado para melhor persistência
- Logger com contexto em cada chamada

### ❌ Removido
- `epic_games_claimer.py` (monolítico, 1.2k linhas)
- `epic_games_logger.py` (substituído por aprimorado)
- Arquivos `.har` (debug)
- `install.bat/sh` (substituído por pip)

---

## [1.0.0] - 2025-12-14

### ✨ Inicial
- ✅ Autenticação via token navegador
- ✅ Device auth flow
- ✅ Busca de jogos grátis (GraphQL)
- ✅ Resgate automático
- ✅ Persistência de sessão
- ✅ Logs organizados por data
