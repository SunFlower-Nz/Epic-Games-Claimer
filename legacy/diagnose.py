#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic tool for authentication issues.
Checks .env configuration and token validity.
"""

import json
import base64
import sys
from datetime import datetime, timezone
from pathlib import Path

def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload (without verification)."""
    try:
        # Remove 'eg1~' prefix if present
        if token.startswith('eg1~'):
            token = token[4:]
        
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {'error': 'Token inválido (não é JWT)'}
        
        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        return {'error': f'Erro ao decodificar: {e}'}

def main():
    print("\n" + "=" * 70)
    print("🔧 DIAGNÓSTICO DE AUTENTICAÇÃO - Epic Games Claimer")
    print("=" * 70 + "\n")
    
    # Load .env
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ Arquivo .env não encontrado!")
        return
    
    config = {}
    with open('.env', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    print("📋 CONFIGURAÇÃO DO .env:")
    print("-" * 70)
    
    # Check EPIC_CLIENT_ID
    client_id = config.get('EPIC_CLIENT_ID', '')
    print(f"\n1. EPIC_CLIENT_ID:")
    if client_id:
        print(f"   ✅ Presente: {client_id[:20]}...")
    else:
        print(f"   ❌ FALTANDO!")
    
    # Check EPIC_CLIENT_SECRET
    client_secret = config.get('EPIC_CLIENT_SECRET', '')
    print(f"\n2. EPIC_CLIENT_SECRET:")
    if client_secret:
        print(f"   ✅ Presente: {client_secret[:20]}...")
    else:
        print(f"   ⚠️  FALTANDO (opcional para token, OBRIGATÓRIO para device auth)")
    
    # Check CF_CLEARANCE
    cf_clearance = config.get('CF_CLEARANCE', '')
    print(f"\n3. CF_CLEARANCE (Cloudflare bypass):")
    if cf_clearance:
        print(f"   ✅ Presente: {cf_clearance[:30]}...")
    else:
        print(f"   ❌ FALTANDO (necessário para buscar jogos grátis)")
    
    # Check EPIC_EG1
    eg1_token = config.get('EPIC_EG1', '')
    print(f"\n4. EPIC_EG1 (Token do navegador):")
    if eg1_token:
        print(f"   ✅ Presente")
        # Decode and check expiration
        payload = decode_jwt_payload(eg1_token)
        if 'error' not in payload:
            exp = payload.get('exp')
            if exp:
                exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                remaining = (exp_time - now).total_seconds()
                
                if remaining > 0:
                    hours = int(remaining // 3600)
                    print(f"   ✅ Token válido por {hours}h mais")
                    print(f"      Expira em: {exp_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                else:
                    print(f"   ❌ Token EXPIRADO!")
                    print(f"      Expirou em: {exp_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # Show account info
            display_name = payload.get('dn')
            account_id = payload.get('sub')
            if display_name:
                print(f"   📌 Conta: {display_name} ({account_id})")
        else:
            print(f"   ⚠️  Não é um JWT válido")
    else:
        print(f"   ⚠️  FALTANDO (usando device auth como fallback)")
    
    print("\n" + "-" * 70)
    print("\n💡 RECOMENDAÇÕES:")
    print("-" * 70)
    
    issues = []
    
    if not client_id:
        issues.append("EPIC_CLIENT_ID não configurado")
    
    if not client_secret:
        issues.append("EPIC_CLIENT_SECRET necessário para device auth")
    
    if not cf_clearance:
        issues.append("CF_CLEARANCE necessário para buscar jogos grátis")
    
    if eg1_token:
        payload = decode_jwt_payload(eg1_token)
        if 'error' not in payload:
            exp = payload.get('exp')
            if exp:
                remaining = exp - int(datetime.now(timezone.utc).timestamp())
                if remaining <= 0:
                    issues.append("EPIC_EG1 token está EXPIRADO")
    
    if not issues:
        print("✅ Tudo parece estar correto!")
        print("\nPróximos passos:")
        print("1. Execute: python main.py")
        print("2. Se error 401 continuar, tente:")
        print("   - python scripts/get_cookies.py")
        print("   - Cole seu novo eg1~ token no .env")
    else:
        print("\n⚠️  Problemas encontrados:\n")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        
        print("\n\n🔧 COMO CORRIGIR:")
        print("-" * 70)
        
        if "EPIC_EG1 token está EXPIRADO" in issues:
            print("\n❌ Token expirado - Você precisa renovar:")
            print("\n1. Execute:")
            print("   python scripts/get_cookies.py")
            print("\n2. Abra seu navegador e faça login em epicgames.com")
            print("\n3. Copie o novo token eg1~ do DevTools (Console/Storage)")
            print("\n4. Cole no .env como: EPIC_EG1=eg1~seu_novo_token")
        
        if "EPIC_CLIENT_SECRET" in issues:
            print("\n❌ EPIC_CLIENT_SECRET faltando - Você precisa de 2 opções:\n")
            print("OPÇÃO A - Usar token do navegador (recomendado):")
            print("  1. python scripts/get_cookies.py")
            print("  2. Cole seu token eg1~ no .env")
            print("  3. Pode deixar EPIC_CLIENT_SECRET vazio\n")
            print("OPÇÃO B - Usar device auth (requer client_secret):")
            print("  1. Obtenha CLIENT_SECRET do Epic Games Launcher")
            print("  2. Configure no .env: EPIC_CLIENT_SECRET=...")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == '__main__':
    main()
