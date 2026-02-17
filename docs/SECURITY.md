# 🔐 Guia de Segurança — Epic Games Claimer

## Resumo

O Epic Games Claimer foi desenvolvido com segurança em mente. Nenhuma senha é solicitada ou armazenada.

**Status:** ✅ Seguro para uso local

---

## 🛡️ Práticas Implementadas

### 1. Autenticação sem Senhas
- ✅ Usa exclusivamente tokens OAuth (EPIC_EG1)
- ✅ Tokens extraídos do Chrome via CDP (local, sem envio a terceiros)
- ✅ Fallback para login interativo via Playwright

### 2. Proteção de Dados Sensíveis
- ✅ Credenciais não são hardcoded no código
- ✅ `data/session.json` ignorado pelo Git
- ✅ `.env` ignorado pelo Git
- ✅ Tokens mascarados em logs (apenas primeiros 8 caracteres)
- ✅ Nenhum header Authorization logado em texto completo
- ✅ Histórico do git limpo (dados pessoais removidos via `git-filter-repo`)

### 3. Chrome CDP
- ✅ Conexão via localhost (127.0.0.1:9222) — sem exposição de rede
- ✅ Perfil do Chrome copiado para diretório temporário (original não modificado)
- ✅ Chrome fechado automaticamente após uso
- ✅ Cookies injetados no contexto do browser (não salvos em disco)

### 4. Endpoints Seguros
- ✅ Apenas endpoints oficiais da Epic Games (`*.epicgames.com`)
- ✅ Validação de certificado SSL em todas as requisições
- ✅ API externa de fallback (`freegamesepic.onrender.com`) com validação de resposta

### 5. Armazenamento Local
- ✅ `session.json` protegido por permissões do sistema
- ✅ Logs organizados por data para fácil auditoria
- ✅ Debug dumps salvos apenas em `logs/debug/` (ignorado pelo Git)

---

## ⚠️ Riscos e Mitigações

### Risco 1: session.json em Texto Claro
**Severidade:** 🟡 Média
- ✅ Arquivo ignorado pelo Git
- ✅ Permissões locais do sistema operacional
- ⚠️ Não sincronize em nuvem sem criptografia

### Risco 2: Chrome CDP Expõe Porta
**Severidade:** 🟢 Baixo
- ✅ Porta 9222 escuta apenas em localhost
- ✅ Chrome fechado após cada execução
- ✅ Perfil copiado (original intacto)

### Risco 3: API Externa
**Severidade:** 🟢 Baixo
- ✅ Usada apenas como fallback para listar jogos grátis
- ✅ Nenhum dado sensível enviado
- ✅ HTTPS com validação de certificado

---

## 📋 Checklist para Usuários

- [ ] `.env` nunca versionado (verifique `.gitignore`)
- [ ] `data/session.json` nunca compartilhado
- [ ] Permissões de pasta restritas ao seu usuário
- [ ] Logs não contêm tokens completos
- [ ] Token do navegador não commitado no Git

---

## 🔑 Gerenciamento de Credenciais

### Recomendado: Chrome Automático
```bash
# Faça login no Chrome → Feche → Execute
python main.py
```
Cookies extraídos localmente, sem configuração manual.

### Alternativa: .env
```env
EPIC_EG1=eg1~seu_token_aqui
```
Nunca faça commit deste arquivo.

---

## 🔍 Auditoria

### Logs
```
logs/YYYY/MM/DD.txt   # Operações do dia
logs/debug/           # Screenshots e dumps HTML (debug)
```

**Verificar que NÃO contêm:**
- ❌ Token completo
- ❌ Bearer token decodificado
- ❌ Valores de cookies completos

### Permissões (Windows)
```powershell
icacls data\session.json
```

---

**Última atualização:** Fevereiro 2026
