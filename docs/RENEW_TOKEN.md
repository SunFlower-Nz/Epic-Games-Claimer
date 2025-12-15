╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║        🔐 RENOVAR TOKEN EXPIRADO - Guia Passo a Passo                      ║
║                                                                            ║
║                   Epic Games Claimer - Autenticação                        ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

STATUS: ❌ SEU TOKEN EXPIROU EM 15/12 ÀS 02:59 UTC

Seu token atual:
  Conta: REDACTED_USERNAME
  ID: REDACTED_ACCOUNT_ID
  Status: EXPIRADO (precisa renovar)

════════════════════════════════════════════════════════════════════════════

PASSO 1️⃣  - Abra seu navegador e faça login
════════════════════════════════════════════════════════════════════════════

1. Abra: https://store.epicgames.com
2. Se não estiver logado, clique em LOGIN
3. Digite suas credenciais (email/senha)
4. Deixe carregando completamente

════════════════════════════════════════════════════════════════════════════

PASSO 2️⃣  - Copie o novo token do navegador
════════════════════════════════════════════════════════════════════════════

▶️ No Chrome/Edge:

  1. Pressione F12 (abre DevTools)
  2. Clique na aba "Application" (topo)
  3. No lado esquerdo, expanda "Cookies"
  4. Clique em "https://store.epicgames.com"
  5. Procure por "EPIC_EG1" na lista
  6. Clique nela
  7. Você verá o valor no painel abaixo
  8. Copie todo o valor (começando com eg1~...)

▶️ No Firefox:

  1. Pressione F12 (abre DevTools)
  2. Clique na aba "Storage" (topo)
  3. Expanda "Cookies"
  4. Clique em "https://store.epicgames.com"
  5. Procure por "EPIC_EG1"
  6. Copie o valor (começando com eg1~...)

▶️ No Safari:

  1. Pressione Command+Option+I
  2. Clique em "Storage" → "Cookies"
  3. Selecione "store.epicgames.com"
  4. Procure "EPIC_EG1"
  5. Copie o valor

════════════════════════════════════════════════════════════════════════════

PASSO 3️⃣  - Cole o token no .env
════════════════════════════════════════════════════════════════════════════

Arquivo: .env (na pasta raiz do projeto)

Encontre a linha:
  EPIC_EG1=eg1~eyJraWQiOi...

E SUBSTITUA por:
  EPIC_EG1=eg1~COLE_SEU_NOVO_TOKEN_AQUI

Exemplo (com token fictício):
  EPIC_EG1=eg1~eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

════════════════════════════════════════════════════════════════════════════

PASSO 4️⃣  - Teste a autenticação
════════════════════════════════════════════════════════════════════════════

No terminal/prompt (pasta do projeto):

  $ python diagnose.py

Você deve ver:
  ✅ Token válido por XXh mais

════════════════════════════════════════════════════════════════════════════

PASSO 5️⃣  - Rode o claimer
════════════════════════════════════════════════════════════════════════════

  $ python main.py

Ou para rodar automaticamente (12h diariamente):

  $ python main.py --schedule

════════════════════════════════════════════════════════════════════════════

❓ DÚVIDAS?

❌ "Não vejo EPIC_EG1 nos cookies"
   → Você realmente fez login? Tente sair e entrar novamente
   → Tente outro navegador
   → Verifique se os cookies estão habilitados

❌ "Copiei errado"
   → Certifique-se que começa com eg1~
   → O token é muito longo (centenas de caracteres)
   → Não adicione espaços extras

❌ "Ainda dá erro 401 depois de renovar"
   → Execute: python diagnose.py
   → Veja se o token realmente está válido
   → Tente fazer logout e login novamente no navegador
   → Copie o token NOVAMENTE (pode ter mudado)

════════════════════════════════════════════════════════════════════════════

⏰ QUANDO RENOVAR NOVAMENTE?

Tokens Epic Games duram ~24 horas.
Se você rodar o claimer todos os dias, o token pode expirar depois.

Solução: Execute antes de dormir ou quando ver erro 401:
  $ python diagnose.py

Ele te dirá se o token está vencendo em breve.

════════════════════════════════════════════════════════════════════════════

💡 DICA PROFISSIONAL

Para evitar renovar manualmente toda semana:
1. Configure o scheduler: python main.py --schedule
2. Deixe rodando 24/7
3. Renove o token toda semana (quando receber o aviso)

Isso garante que seus jogos grátis serão resgatados automaticamente!

════════════════════════════════════════════════════════════════════════════
