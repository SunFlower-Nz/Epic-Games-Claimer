╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║        🚨 LIMITAÇÃO: Cloudflare Bot Management                             ║
║                                                                            ║
║                   Epic Games GraphQL está protegido                        ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

PROBLEMA
════════════════════════════════════════════════════════════════════════════

A API GraphQL de jogos grátis do Epic Games está protegida por **Cloudflare Bot
Management**, que bloqueia requisições HTTP simples, mesmo com token JWT válido.

Status: 403 Forbidden (Cloudflare Challenge)
Requisição: POST https://store.epicgames.com/graphql
Solução: Requer navegador real ou bypass especial


POSSÍVEIS SOLUÇÕES
════════════════════════════════════════════════════════════════════════════

Option 1: ✅ USAR PLAYWRIGHT (Recomendado)
──────────────────────────────────────────

Implementar busca de jogos com Playwright:

  $ pip install playwright
  $ playwright install chromium
  $ python -c "from src import api; api.use_playwright = True"

Vantagens:
  ✓ Funciona 100% com Cloudflare
  ✓ Consegue fazer login automaticamente
  ✓ Mais confiável

Desvantagens:
  ✗ Requer navegador (mais memória)
  ✗ Mais lento


Option 2: ⚠️  USAR cf_clearance COOKIE
────────────────────────────────────

Pega o Cloudflare verification cookie do navegador:

  1. Abra https://store.epicgames.com em Chrome
  2. Pressione F12 → Application → Cookies
  3. Copie o valor de "cf_clearance"
  4. Adicione ao .env: CF_CLEARANCE=seu_valor_aqui
  5. Código tentará usar na requisição GraphQL

Vantagens:
  ✓ Sem necessidade de navegador real
  ✓ Rápido

Desvantagens:
  ✗ Cookie expira a cada 24-48 horas
  ✗ Precisa renovar manualmente
  ✗ Pode não funcionar se Cloudflare muda proteção


Option 3: ❌ USAR PROXY COM CLOUDFLARE BYPASS
─────────────────────────────────────────

Services como:
  - cloudflare-scraper
  - python-cloudflare
  - bright.com proxy

Vantagens:
  ✓ Sem necessidade de navegador
  ✓ Cookies gerenciados automaticamente

Desvantagens:
  ✗ Requer serviço pago
  ✗ Rate limits


IMPLEMENTAÇÃO RÁPIDA (Option 2)
════════════════════════════════════════════════════════════════════════════

1️⃣  Abra seu navegador (Chrome/Edge/Firefox)
   → Acesse: https://store.epicgames.com
   → Pressione F12

2️⃣  Copie o cookie cf_clearance
   → Application → Cookies → store.epicgames.com
   → Procure "cf_clearance"
   → Clique nele e copie o VALOR (aquele string gigante)

3️⃣  Adicione ao .env
   Arquivo: .env

   Adicione a linha:
   CF_CLEARANCE=seu_valor_gigante_aqui

   Exemplo:
   CF_CLEARANCE=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6...

4️⃣  Teste
   $ python diagnose.py
   
   Deve mostrar:
   ✅ CF_CLEARANCE: Presente

5️⃣  Execute
   $ python main.py


IMPLEMENTAÇÃO COMPLETA (Option 1 - Playwright)
════════════════════════════════════════════════════════════════════════════

Para uma solução de longo prazo, seria adicionar suporte a Playwright:

  $ pip install playwright
  $ playwright install chromium

Então modificar src/api.py para usar:

```python
from playwright.sync_api import sync_playwright

async def get_free_games_playwright(self, access_token: str):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Set auth header
        page.set_extra_http_headers({'Authorization': f'Bearer {access_token}'})
        
        # Go to graphQL endpoint
        response = page.request.post(
            'https://store.epicgames.com/graphql',
            data=json.dumps({...graphql query...})
        )
        
        return response.json()
```

Isso seria mais robusto mas requer mais desenvolvimento.


WORKAROUND ATUAL
════════════════════════════════════════════════════════════════════════════

Como alternativa enquanto Cloudflare está bloqueando:

1️⃣  Use --check para verificar jogos específicos
   $ python main.py --check

2️⃣  Pegue IDs de jogos de sites como:
   - https://www.epicgames.com/store/pt-BR/free-games
   - Communities/Discord

3️⃣  Configure manualmente em next_games.json

4️⃣  Execute claim quando quiser


MONITORAMENTO
════════════════════════════════════════════════════════════════════════════

Verifique se Cloudflare permanece um problema:

  $ python debug_free_games.py

Se vir:
  ❌ Error fetching free games [status=403, content_preview=<html>..cf_challenge

→ Cloudflare está bloqueando. Tente Option 2 acima.


PRÓXIMAS AÇÕES RECOMENDADAS
════════════════════════════════════════════════════════════════════════════

1. Tente CF_CLEARANCE (5 min de setup)
2. Se não funcionar, implemente Playwright (30 min de setup)
3. Ou use --check com IDs conhecidos (manual)


PERGUNTAS?
════════════════════════════════════════════════════════════════════════════

Veja:
- STATUS.md      (status geral do projeto)
- QUICKSTART.md  (comando rápido)
- README.md      (documentação completa)

════════════════════════════════════════════════════════════════════════════
