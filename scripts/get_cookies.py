#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helper script to extract Epic Games session from Chrome browser automatically.

Two modes:
1. AUTOMATIC (default): Extracts cookies directly from Chrome
   - Profile: CHROME_PROFILE env var (default: 'Profile negao', fallback: 'Default')
   - No manual steps required
   - Chrome must be closed
   
2. MANUAL: Paste EPIC_EG1 token manually (fallback)

This creates a session.json file that the claimer will use.
"""

import json
import base64
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_from_chrome() -> bool:
    """
    Automatically extract session from Chrome browser.
    
    Reads cookies from Chrome profile specified by CHROME_PROFILE env.
    Fallback to 'Default' profile if not found.
    Chrome must be closed for this to work.
    
    Returns:
        True if session was created successfully.
    """
    import os
    profile = os.getenv('CHROME_PROFILE', 'Profile negao')
    
    print("\n" + "=" * 60)
    print("🔑 EXTRAÇÃO AUTOMÁTICA DO CHROME")
    print("=" * 60)
    print(f"\nPerfil: {profile} (fallback: Default)")
    print("Extraindo cookies automaticamente...\n")
    
    try:
        from src.chrome_cookies import ChromeCookieExtractor, ExtractedCookies
        from src.session_store import Session
        
        extractor = ChromeCookieExtractor(profile_name=profile)
        cookies, success = extractor.extract_and_validate()
        
        if not success:
            print("❌ Não foi possível extrair EPIC_EG1 do Chrome")
            print("\n   Verifique se:")
            print("   1. Chrome está FECHADO")
            print("   2. Você está logado em store.epicgames.com")
            print(f"   3. O perfil '{profile}' existe (ou 'Default')")
            return False
        
        # Create session from EG1 token
        session = Session.from_eg1_token(cookies.epic_eg1)
        if not session:
            print("❌ Token extraído é inválido")
            return False
        
        # Add extra cookies
        if cookies.epic_sso:
            session.cookies['EPIC_SSO'] = cookies.epic_sso
        
        # Check expiry
        remaining = session.time_until_expiry()
        hours_left = int(remaining.total_seconds() / 3600) if remaining else 0
        
        if hours_left <= 0:
            print("❌ Token extraído já está expirado!")
            print("   Faça login novamente em store.epicgames.com")
            return False
        
        # Save session
        output_dir = Path(__file__).parent.parent / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        session_file = output_dir / "session.json"
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        
        print("✅ Sessão extraída com sucesso!")
        print(f"   👤 Conta:       {session.display_name}")
        print(f"   🆔 Account ID:  {session.account_id[:8]}...")
        print(f"   ⏰ Válido por:  {hours_left} horas")
        print(f"   📁 Arquivo:     {session_file.absolute()}")
        
        # Also show CF_CLEARANCE status
        if cookies.has_cf_clearance():
            print(f"   ✅ CF_CLEARANCE: extraído")
        else:
            print(f"   ⚠️  CF_CLEARANCE: não encontrado (cloudscraper será usado)")
        
        print("\n🎮 Agora você pode executar: python main.py")
        
        return True
        
    except ImportError as e:
        print(f"❌ Dependências não instaladas: {e}")
        print("\n   Execute: pip install pywin32 cryptography")
        return False
    except Exception as e:
        print(f"❌ Erro na extração: {e}")
        import traceback
        traceback.print_exc()
        return False


from typing import Optional


def create_session_from_token(eg1_token: str, output_dir: Optional[Path] = None) -> bool:
    """
    Create session.json from EPIC_EG1 token.
    
    Args:
        eg1_token: The eg1~ prefixed token from browser cookies.
        output_dir: Output directory (default: data/).
    
    Returns:
        True if session was created successfully.
    """
    # Validate token
    if not eg1_token or eg1_token == "eg1~YOUR_TOKEN_HERE":
        print("❌ Por favor, cole seu token EPIC_EG1 no script primeiro!")
        print("\n📋 Instruções:")
        print("   1. Abra https://store.epicgames.com e faça login")
        print("   2. Pressione F12 → Application → Cookies → store.epicgames.com")
        print("   3. Encontre o cookie EPIC_EG1 e copie seu valor")
        print("   4. Cole neste script onde diz 'YOUR_TOKEN_HERE'")
        print("   5. Execute este script novamente")
        return False
    
    if not eg1_token.startswith('eg1~'):
        print("❌ Formato de token inválido. O token deve começar com 'eg1~'")
        return False
    
    # Decode JWT to get account info
    try:
        jwt_part = eg1_token[4:]  # Remove 'eg1~' prefix
        parts = jwt_part.split('.')
        
        if len(parts) < 2:
            print("❌ Formato JWT inválido")
            return False
        
        # Decode payload (add padding if needed)
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        # Extract info
        account_id = payload_data.get('sub', '')
        display_name = payload_data.get('dn', '')
        exp_timestamp = payload_data.get('exp', 0)
        
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).isoformat()
        
        # Check if expired
        now = datetime.now(timezone.utc).timestamp()
        if exp_timestamp <= now:
            hours_ago = int((now - exp_timestamp) / 3600)
            print(f"❌ Token expirado há {hours_ago} hora(s)!")
            print("   Por favor, obtenha um novo token do seu navegador.")
            return False
        
        hours_left = int((exp_timestamp - now) / 3600)
        
        # Create session
        session = {
            "access_token": eg1_token,
            "refresh_token": "",
            "account_id": account_id,
            "display_name": display_name,
            "expires_at": expires_at,
            "refresh_expires_at": "",
            "cookies": {
                "EPIC_EG1": eg1_token
            }
        }
        
        # Save to file
        output_dir = output_dir or Path(__file__).parent.parent / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        session_file = output_dir / "session.json"
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        
        print("\n✅ Sessão criada com sucesso!")
        print(f"   👤 Conta:       {display_name}")
        print(f"   🆔 Account ID:  {account_id[:8]}...")
        print(f"   ⏰ Válido por:  {hours_left} horas")
        print(f"   📁 Arquivo:     {session_file.absolute()}")
        print("\n🎮 Agora você pode executar: python main.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar sessão: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point - tries automatic extraction first."""
    print("\n" + "=" * 60)
    print("🔑 EPIC GAMES - EXTRATOR DE COOKIES")
    print("=" * 60)
    
    # Check for --login flag (interactive browser login)
    if len(sys.argv) > 1 and sys.argv[1] == "--login":
        from scripts.login import interactive_login
        interactive_login()
        return
    
    # Check for --manual flag
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        # Manual mode: prompt for token
        print("\n[MODO MANUAL]")
        print("Cole seu token EPIC_EG1 abaixo:")
        print("(O token começa com 'eg1~...')\n")
        
        try:
            token = input("> ").strip()
            if token:
                create_session_from_token(token)
            else:
                print("❌ Token vazio")
        except EOFError:
            print("❌ Entrada cancelada")
        return
    
    # Default: Try automatic Chrome extraction
    print("\n[MODO AUTOMÁTICO]")
    print("Tentando extrair cookies do Chrome...")
    print("⚠️  Chrome 127+ usa App-Bound Encryption (pode não funcionar)\n")
    
    if extract_from_chrome():
        return  # Success!
    
    # Fallback options
    print("\n" + "-" * 60)
    print("Extração automática falhou.")
    print("\nOpções disponíveis:")
    print("  1. LOGIN INTERATIVO (recomendado):")
    print("     python scripts/login.py")
    print("     Abre navegador para você fazer login uma vez.")
    print("")
    print("  2. MANUAL (cole o cookie):")
    print("     python scripts/get_cookies.py --manual")
    print("     Você precisa copiar o cookie EPIC_EG1 do navegador.")
    print("-" * 60)


if __name__ == "__main__":
    main()
