#!/usr/bin/env python3
"""
Extrator de CF_CLEARANCE do navegador Chrome/Edge do seu sistema
Lê os cookies diretamente do perfil Chrome/Edge
"""

import os
import json
import sqlite3
from pathlib import Path
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

load_dotenv()

def get_chrome_cookies(profile_path):
    """Extract CF_CLEARANCE from Chrome/Edge cookies database"""
    
    print("=" * 80)
    print("🍪 EXTRATOR DE COOKIES - Chrome/Edge")
    print("=" * 80)
    
    cookies_db = profile_path / "Cookies"
    
    if not cookies_db.exists():
        print(f"❌ Database não encontrada: {cookies_db}")
        return None
    
    try:
        # Connect to Chrome cookies database
        conn = sqlite3.connect(cookies_db)
        cursor = conn.cursor()
        
        # Query for cf_clearance
        cursor.execute("""
            SELECT name, value, domain 
            FROM cookies 
            WHERE name='cf_clearance' AND domain LIKE '%epicgames%'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            name, value, domain = result
            print(f"✅ Cookie encontrado: {name} no domínio {domain}")
            print(f"✅ Valor: {value[:50]}...")
            return value
        else:
            print("❌ Cookie cf_clearance não encontrado em epicgames.com")
            return None
            
    except sqlite3.OperationalError as e:
        print(f"❌ Chrome deve estar fechado para ler os cookies")
        print(f"   Feche o Chrome/Edge completamente e tente novamente")
        return None

def find_chrome_profile():
    """Find Chrome/Edge profile path"""
    
    # Windows paths
    appdata = Path(os.getenv('APPDATA', ''))
    local_appdata = Path(os.getenv('LOCALAPPDATA', ''))
    
    possible_paths = [
        # Chrome
        local_appdata / 'Google' / 'Chrome' / 'User Data' / 'Default',
        # Edge
        local_appdata / 'Microsoft' / 'Edge' / 'User Data' / 'Default',
        # Brave
        local_appdata / 'BraveSoftware' / 'Brave-Browser' / 'User Data' / 'Default',
        # Chromium
        local_appdata / 'Chromium' / 'User Data' / 'Default',
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"✅ Perfil encontrado: {path}")
            return path
    
    print("❌ Nenhum perfil Chrome/Edge encontrado")
    return None

def main():
    print("\n" + "=" * 80)
    print("🔍 PROCURANDO CF_CLEARANCE NO SEU NAVEGADOR")
    print("=" * 80)
    print("""
IMPORTANTE:
1. Feche o Chrome/Edge completamente (todas as abas)
2. Aguarde 3-5 segundos
3. Então execute este script

Isto é necessário porque Chrome bloqueia o acesso ao banco de cookies enquanto está aberto.
    """)
    
    input("Pressione Enter quando o navegador estiver fechado...")
    
    profile_path = find_chrome_profile()
    if not profile_path:
        print("\n❌ Não consegui encontrar seu navegador. Opções:")
        print("   1. Tente método alternativo: python scripts/get_cookies.py")
        print("   2. Copie manualmente: F12 → Application → Cookies → cf_clearance")
        return
    
    cf_clearance = get_chrome_cookies(profile_path)
    
    if cf_clearance:
        print("\n" + "=" * 80)
        print("✅ CF_CLEARANCE EXTRAÍDO COM SUCESSO!")
        print("=" * 80)
        
        # Update .env
        env_file = Path('.env')
        if env_file.exists():
            content = env_file.read_text()
            import re
            new_content = re.sub(
                r'CF_CLEARANCE=.*',
                f'CF_CLEARANCE={cf_clearance}',
                content
            )
            env_file.write_text(new_content)
            print("📝 Arquivo .env atualizado!")
        else:
            print(f"\n📝 Adicione ao seu .env:")
            print(f"CF_CLEARANCE={cf_clearance}")
        
        print("\n✅ Próximo passo: python main.py")
    else:
        print("\n❌ Não consegui extrair o cookie")
        print("   Alternativa: Use scripts/get_cookies.py ou copie manualmente")

if __name__ == '__main__':
    main()
