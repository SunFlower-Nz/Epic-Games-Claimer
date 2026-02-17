# 🔐 Renovar Token — Epic Games Claimer

## Quando Renovar?

O token EPIC_EG1 expira em **~8 horas**. Quando expirar, o claimer tentará automaticamente:
1. Usar a sessão salva em `data/session.json`
2. Extrair cookies do Chrome via CDP
3. Solicitar login interativo via Playwright

Na maioria dos casos, basta **fazer login no Chrome** e reexecutar o claimer.

---

## Método 1: Automático via Chrome (Recomendado)

1. Abra https://store.epicgames.com no Chrome
2. Faça login normalmente
3. Feche o Chrome
4. Execute:

```bash
python main.py
```

O claimer copiará o perfil do Chrome e extrairá os cookies automaticamente.

---

## Método 2: Token Manual

Se o método automático não funcionar:

### Copie o token do navegador

**Chrome/Edge:**
1. Pressione F12 (DevTools)
2. Aba **Application** → **Cookies** → `https://store.epicgames.com`
3. Procure `EPIC_EG1`
4. Copie todo o valor (começa com `eg1~...`)

**Firefox:**
1. Pressione F12 (DevTools)
2. Aba **Storage** → **Cookies** → `https://store.epicgames.com`
3. Procure `EPIC_EG1`
4. Copie o valor

### Cole no script

```bash
python scripts/get_cookies.py
# Cole o token quando solicitado
```

Ou adicione ao `.env`:

```env
EPIC_EG1=eg1~seu_token_aqui
```

---

## Método 3: Login Interativo

Se nenhum token válido for encontrado, o claimer abrirá uma janela do Playwright para login manual:

```bash
python main.py
# Uma janela do browser abrirá
# Faça login na Epic Games
# O token será extraído automaticamente
```

---

## ❓ FAQ

**"Não vejo EPIC_EG1 nos cookies"**
→ Verifique se está realmente logado na Epic Games Store
→ Tente sair e entrar novamente

**"Token muito curto"**
→ O token real é muito longo (centenas de caracteres), começa com `eg1~`
→ Copie o valor completo

**"Ainda dá erro 401 depois de renovar"**
→ Delete `data/session.json` e tente novamente
→ Faça logout e login novamente no Chrome

---

## ⏰ Dica

Para evitar renovar manualmente:
1. Configure o scheduler: `python main.py --schedule`
2. Faça login no Chrome antes de cada execução
3. O claimer extrairá os cookies frescos automaticamente
