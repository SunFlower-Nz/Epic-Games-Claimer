# 🔐 GUIA DE SEGURANÇA - Epic Games Claimer

## Resumo Executivo

O Epic Games Claimer foi desenvolvido com segurança em mente. Este documento descreve práticas de segurança implementadas e recomendações para os usuários.

**Status Geral:** ✅ **Relativamente Seguro**

---

## 🛡️ Práticas de Segurança Implementadas

### 1. Autenticação sem Senhas
- ✅ **Nenhuma senha é solicitada ou armazenada**
- ✅ Usa exclusivamente tokens OAuth
- ✅ Fallback para Device Auth Flow (navegador interativo)

### 2. Proteção de Dados Sensíveis
- ✅ **Credenciais não são hardcoded** (removidas de config.py)
- ✅ **session.json ignorado pelo Git** (.gitignore configurado)
- ✅ **Tokens mascarados em logs** (apenas primeiros 8 caracteres)
- ✅ **Nenhum header Authorization logado**

### 3. Endpoints Seguros
- ✅ **Apenas endpoints oficiais da Epic Games** (`*.epicgames.com`)
- ✅ **Validação de certificado SSL** em todas as requisições
- ✅ **API externa validada** (freegamesepic.onrender.com com structure checks)

### 4. Armazenamento Local
- ✅ **session.json protegido por permissões do Windows**
- ✅ **Tokens renovados automaticamente** (refresh token)
- ✅ **Logs organizados por data** (fácil auditoria)

### 5. Logging Estruturado
- ✅ **Logs em arquivo + console** para rastreabilidade
- ✅ **Nenhum token completo em logs**
- ✅ **Contexto e stacktraces detalhados** para debugging
- ✅ **Emojis para scanning visual rápido**

---

## ⚠️ Riscos Conhecidos e Mitigações

### Risco 1: API Externa (freegamesepic.onrender.com)
**Severidade:** 🟡 Média  
**Mitigação:**
- ✅ Validação de estrutura de resposta (isDict, isList)
- ✅ HTTPS obrigatório com validação de certificado
- ✅ Usado apenas como fallback (não crítico)
- ✅ Nenhum dado sensível enviado

**Recomendação:** Manter como fallback apenas. Se offline, claimer falha gracefully.

### Risco 2: session.json em Texto Claro
**Severidade:** 🟡 Média  
**Mitigação:**
- ✅ Arquivo ignorado pelo Git (não versionado)
- ✅ Permissões locais do Windows (apenas usuário atual)
- ✅ Arquivo local, não sincronizado em nuvem por padrão

**Recomendação:** Usar Windows DPAPI para encriptar (possível em versão futura).

### Risco 3: Cookies do Chrome
**Severidade:** 🟢 Baixo  
**Mitigação:**
- ✅ Extração local via DPAPI ou Playwright (sem envio para terceiros)
- ✅ Cookies lidos apenas, nunca modificados
- ✅ Chrome deve estar fechado para DPAPI (evita interferência)

**Recomendação:** Manter prática atual. DPAPI é seguro para ambiente local.

---

## 🔑 Como Gerenciar Credenciais

### Opção 1: Deixar Vazio (Recomendado)
```env
# .env
EPIC_CLIENT_ID=
EPIC_CLIENT_SECRET=
```
→ Usa credenciais públicas padrão da Epic Games (seguro)

### Opção 2: Token do Navegador
```bash
python scripts/get_cookies.py
# Será convertido em session.json
```
→ Mais seguro que hardcoding

### Opção 3: Credenciais Customizadas
Se você obteve suas próprias credenciais:
```env
EPIC_CLIENT_ID=seu_id
EPIC_CLIENT_SECRET=seu_secret
```
→ Nunca commit isso em Git. Use `.env` (ignorado).

---

## 📋 Checklist de Segurança para Usuários

- [ ] **`.env` NUNCA é versionado** (verifique `.gitignore`)
- [ ] **`session.json` NUNCA é compartilhado**
- [ ] **Permissões de pasta** restritas (apenas seu usuário)
- [ ] **Chrome fechado ao executar** (para DPAPI)
- [ ] **Logs contêm informações públicas apenas** (verifique antes de compartilhar)
- [ ] **Token do navegador não é commitado** (use `.env` ou scripts)

---

## 🔍 Auditoria e Monitoramento

### Logs para Revisar
```
logs/YYYY/MM/DD.txt
```

**O que procurar:**
- ✅ Tokens sempre mascarados (`eg1~...`)
- ✅ Nenhuma senha ou PIN
- ✅ Apenas URLs (sem query strings sensíveis)
- ✅ Status HTTP e timestamps

**Vermelho (não deve aparecer):**
- ❌ Token completo
- ❌ Bearer token decodificado
- ❌ Cookie valores completos
- ❌ Account password

### Verificar Permissões
```powershell
# Ver proprietário de session.json
(Get-Item data/session.json).Owner

# Ver permissões
icacls data/session.json
```

---

## 🚨 Reportar Vulnerabilidades

Se encontrar um problema de segurança:
1. **NÃO** abra issue pública
2. Entre em contato via email (proprietário do repositório)
3. Descreva:
   - Tipo de vulnerabilidade
   - Como reproduzir
   - Impacto potencial

---

## 📚 Referências Externas

- [OAuth 2.0 Device Authorization Grant](https://tools.ietf.org/html/draft-ietf-oauth-device-flow)
- [OWASP: Credential Storage](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Storage_Cheat_Sheet.html)
- [Windows DPAPI](https://docs.microsoft.com/en-us/windows/win32/seccng/data-protection-api)
- [Epic Games API Docs](https://docs.unrealengine.com/en-US/API/web-api/getting-started/)

---

**Última atualização:** 15 de Dezembro de 2025  
**Status:** ✅ Auditado e Seguro
