# -*- coding: utf-8 -*-
"""
Interactive Login for Epic Games Claimer.

Opens a browser window for user to log in to Epic Games.
After login, saves cookies to session.json for future use.

This only needs to be run once - after that, the claimer will use
the saved session and refresh tokens automatically.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def interactive_login():
    """
    Open browser for user to log in to Epic Games.
    
    After successful login, saves session to data/session.json.
    """
    print("\n" + "=" * 60)
    print("🔐 EPIC GAMES - LOGIN INTERATIVO")
    print("=" * 60)
    print("""
Este script abre uma janela do navegador para você fazer login
na Epic Games. Após o login, os cookies serão salvos e você
não precisará fazer isso novamente por muito tempo.

Instruções:
1. Uma janela do navegador será aberta
2. Faça login na sua conta Epic Games
3. Após o login, feche a janela OU aguarde (auto-detecta)
4. Os cookies serão salvos automaticamente
""")
    
    input("Pressione Enter para continuar...")
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\n❌ Playwright não instalado!")
        print("   Execute: pip install playwright && python -m playwright install chromium")
        return False
    
    print("\n🌐 Abrindo navegador...")
    
    try:
        with sync_playwright() as p:
            # Launch visible browser
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = context.new_page()
            
            # Go to Epic Games login
            page.goto("https://www.epicgames.com/id/login", wait_until="domcontentloaded")
            
            print("\n⏳ Aguardando login...")
            print("   Faça login na janela do navegador.")
            print("   A janela fechará automaticamente após detectar o login.")
            
            # Wait for login success - detect by URL change or cookie presence
            max_wait = 300  # 5 minutes
            check_interval = 2
            waited = 0
            
            cookies = []
            while waited < max_wait:
                page.wait_for_timeout(check_interval * 1000)
                waited += check_interval
                
                # Check if we're logged in by looking at cookies
                cookies = context.cookies()
                epic_eg1 = next((c for c in cookies if c.get('name') == 'EPIC_EG1'), None)
                
                if epic_eg1:
                    print("\n✅ Login detectado!")
                    break
                
                # Also check if redirected to store after login
                if "store.epicgames.com" in page.url:
                    page.wait_for_timeout(3000)  # Wait for cookies to be set
                    cookies = context.cookies()
                    break
            
            if not cookies:
                print("\n❌ Timeout - login não detectado")
                browser.close()
                return False
            
            # Process and save cookies
            session_data = process_cookies(cookies)
            
            if session_data:
                # Save session
                output_dir = Path(__file__).parent.parent / "data"
                output_dir.mkdir(parents=True, exist_ok=True)
                session_file = output_dir / "session.json"
                
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                
                print(f"\n✅ Sessão salva com sucesso!")
                print(f"   👤 Conta: {session_data.get('display_name', 'N/A')}")
                print(f"   📁 Arquivo: {session_file.absolute()}")
                print(f"\n🎮 Agora você pode executar: python main.py")
                
                browser.close()
                return True
            else:
                print("\n❌ Não foi possível extrair cookies de login")
                browser.close()
                return False
                
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


from typing import Optional, Dict, Any

def process_cookies(cookies: list) -> Optional[Dict[str, Any]]:
    """
    Process Playwright cookies and create session data.
    
    Args:
        cookies: List of cookie dicts from Playwright.
    
    Returns:
        Session dict ready to save, or None if no EPIC_EG1.
    """
    import base64
    
    # Find relevant cookies
    epic_eg1 = None
    cf_clearance = None
    epic_sso = None
    cookies_dict = {}
    
    for cookie in cookies:
        domain = cookie.get('domain', '')
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        
        if 'epicgames' not in domain:
            continue
        
        cookies_dict[name] = value
        
        if name == 'EPIC_EG1':
            epic_eg1 = value
        elif name == 'cf_clearance':
            cf_clearance = value
        elif name == 'EPIC_SSO':
            epic_sso = value
    
    if not epic_eg1:
        return None
    
    # Decode JWT to get account info
    try:
        if epic_eg1.startswith('eg1~'):
            jwt_part = epic_eg1[4:]
        else:
            jwt_part = epic_eg1
        
        parts = jwt_part.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            payload_data = json.loads(decoded)
            
            account_id = payload_data.get('sub', '')
            display_name = payload_data.get('dn', '')
            exp_timestamp = payload_data.get('exp', 0)
            
            expires_at = ''
            if exp_timestamp:
                expires_at = datetime.fromtimestamp(
                    exp_timestamp, tz=timezone.utc
                ).isoformat()
        else:
            account_id = ''
            display_name = ''
            expires_at = ''
            
    except Exception:
        account_id = ''
        display_name = ''
        expires_at = ''
    
    return {
        'access_token': epic_eg1,
        'refresh_token': '',
        'account_id': account_id,
        'display_name': display_name,
        'expires_at': expires_at,
        'refresh_expires_at': '',
        'cookies': cookies_dict
    }


if __name__ == '__main__':
    success = interactive_login()
    sys.exit(0 if success else 1)
