#!/usr/bin/env python3
"""
Playwright-based cookie extractor for Epic Games
Automatically logs in and extracts valid CF_CLEARANCE cookie
"""

import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

async def get_epic_cookies():
    """Extract valid cookies from Epic Games Store via browser automation"""
    from playwright.async_api import async_playwright
    
    print("=" * 80)
    print("🌐 INICIANDO AUTOMAÇÃO DO NAVEGADOR PARA OBTER COOKIES")
    print("=" * 80)
    
    async with async_playwright() as p:
        # Launch browser
        print("\n📱 Abrindo navegador Chrome...")
        browser = await p.chromium.launch(headless=False)  # headless=False para ver o progresso
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to Epic Games Store
            print("📍 Navegando para store.epicgames.com...")
            await page.goto('https://store.epicgames.com', wait_until='networkidle')
            
            # Wait for user to be logged in or handle login
            print("\n" + "=" * 80)
            print("⏳ AGUARDANDO LOGIN...")
            print("=" * 80)
            print("""
Se você ainda não está logado:
1. Clique em "Sign In" no navegador que abriu
2. Faça login com sua conta Epic Games
3. Após fazer login, será feito um desafio do Cloudflare
4. Conclua o desafio
5. O script continuará automaticamente...

Pressione Enter aqui quando terminar de fazer login no navegador:
            """)
            
            # Wait for user interaction
            input()
            
            # Wait additional time for CF challenge
            print("\n⏳ Aguardando resolução do desafio Cloudflare (30s)...")
            await asyncio.sleep(5)  # Give time for CF challenge
            
            # Check if we're on the main store page
            print("🔍 Verificando se está logado...")
            await page.wait_for_selector('[data-testid="user-avatar"]', timeout=5000)
            print("✅ Login detectado!")
            
            # Extract cookies
            print("\n🍪 Extraindo cookies...")
            cookies = await context.cookies()
            
            # Find CF_CLEARANCE
            cf_clearance = None
            epic_eg1 = None
            
            for cookie in cookies:
                if cookie['name'] == 'cf_clearance':
                    cf_clearance = cookie['value']
                    print(f"✅ CF_CLEARANCE encontrado: {cf_clearance[:50]}...")
                if cookie['name'] == 'EPIC_EG1':
                    epic_eg1 = cookie['value']
                    print(f"✅ EPIC_EG1 encontrado")
            
            if not cf_clearance:
                print("⚠️  CF_CLEARANCE não encontrado. Aguardando mais tempo...")
                await asyncio.sleep(10)
                cookies = await context.cookies()
                for cookie in cookies:
                    if cookie['name'] == 'cf_clearance':
                        cf_clearance = cookie['value']
                        print(f"✅ CF_CLEARANCE encontrado: {cf_clearance[:50]}...")
            
            # Update .env file
            if cf_clearance:
                print("\n📝 Atualizando .env...")
                env_file = Path('.env')
                if env_file.exists():
                    content = env_file.read_text()
                    # Replace CF_CLEARANCE line
                    import re
                    new_content = re.sub(
                        r'CF_CLEARANCE=.*',
                        f'CF_CLEARANCE={cf_clearance}',
                        content
                    )
                    env_file.write_text(new_content)
                    print("✅ .env atualizado com novo CF_CLEARANCE!")
                else:
                    print("⚠️  Arquivo .env não encontrado")
            
            if epic_eg1:
                print("💾 Você pode também atualizar EPIC_EG1 se necessário")
            
            print("\n" + "=" * 80)
            print("✅ PROCESSO CONCLUÍDO!")
            print("=" * 80)
            print("\nAgora você pode fechar o navegador e executar: python main.py")
            
        except Exception as e:
            print(f"\n❌ Erro: {e}")
        
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(get_epic_cookies())
