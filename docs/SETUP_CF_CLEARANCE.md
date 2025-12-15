╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║        📋 PASSO A PASSO - Copiar CF_CLEARANCE do Navegador                ║
║                                                                            ║
║                          (Leva 2 minutos)                                 ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

IMPORTANTE: Este cookie expira a cada 24-48 horas.
Se parar de funcionar depois, repita este processo.

════════════════════════════════════════════════════════════════════════════

GOOGLE CHROME, MICROSOFT EDGE, ou BRAVE
════════════════════════════════════════════════════════════════════════════

1️⃣  Abra o navegador → Acesse: https://store.epicgames.com

2️⃣  Faça login se não estiver logado (use sua conta)

3️⃣  Agora pressione: F12
    (Abre o DevTools/Inspector)

4️⃣  Clique na aba "Application" (no topo do DevTools)
    Se não vir, clique em >> e procure por "Application"

5️⃣  No lado ESQUERDO, expanda:
    Cookies → https://store.epicgames.com

6️⃣  Procure por "cf_clearance" na lista
    (pode estar no meio da lista, scroll se necessário)

7️⃣  Clique nele (uma vez)

8️⃣  No painel da DIREITA, você verá:
    
    Name:   cf_clearance
    Value:  [aquele string gigante que você vai copiar]
    
9️⃣  CLIQUE NO VALOR (o string gigante)
    → Selecione todo com Ctrl+A
    → Copie com Ctrl+C

🔟  Cole no arquivo .env:
    
    Abra: .env (na pasta raiz do projeto)
    
    Encontre:
    CF_CLEARANCE=
    
    E COLE o valor:
    CF_CLEARANCE=seu_valor_gigante_aqui

════════════════════════════════════════════════════════════════════════════

FIREFOX
════════════════════════════════════════════════════════════════════════════

1️⃣  Abra Firefox → Acesse: https://store.epicgames.com

2️⃣  Faça login

3️⃣  Pressione: F12

4️⃣  Clique na aba "Storage" (no topo)

5️⃣  No lado ESQUERDO:
    Expand Cookies → https://store.epicgames.com

6️⃣  Procure "cf_clearance"

7️⃣  Clique nela

8️⃣  Na coluna "Value", CLIQUE e copie o valor

9️⃣  Cole no .env (CF_CLEARANCE=...)

════════════════════════════════════════════════════════════════════════════

RESULTADO ESPERADO
════════════════════════════════════════════════════════════════════════════

O valor de CF_CLEARANCE parecerá assim:

CF_CLEARANCE=0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2a3b4c5d6e7f8g9h0i1j2k3l4m5n6o7p8q9r0s1t2u3v4w5x6y7z8a9b0c1d2e3f4g5h6i7j8k9l0m1n2o3p4q5r6s7t8u9v0w1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0a1b2c3d4e5f6

════════════════════════════════════════════════════════════════════════════

DEPOIS DE COLAR NO .env
════════════════════════════════════════════════════════════════════════════

1️⃣  Abra o terminal/prompt

2️⃣  Vá para a pasta do projeto:
    cd "c:\Users\seu_usuario\OneDrive\Documents\Project\Epic-Games-Claimer"

3️⃣  Teste o diagnóstico:
    python diagnose.py

4️⃣  Você deve ver:
    ✅ CF_CLEARANCE: Presente

5️⃣  Execute o claimer:
    python main.py

════════════════════════════════════════════════════════════════════════════

🎉 SUCESSO!

Se funcionar, você verá:
  ✅ Fetching free games from Epic Store...
  ✅ Found X free games available

════════════════════════════════════════════════════════════════════════════

❓ O que fazer se não funcionar?

Se vir status 403 novamente:
  1. O cookie pode ter expirado (tente copiar novamente)
  2. Ou o navegador pode ter um cf_clearance diferente
  3. Tente em OUTRO navegador

════════════════════════════════════════════════════════════════════════════
