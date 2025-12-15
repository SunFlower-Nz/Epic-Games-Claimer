# -*- coding: utf-8 -*-
"""
Helper script to extract Epic Games cookies from browser.

Instructions:
1. Open https://store.epicgames.com in your browser
2. Log in to your Epic Games account
3. Press F12 to open Developer Tools
4. Go to Application tab (Chrome) or Storage tab (Firefox)
5. Click on Cookies > https://store.epicgames.com
6. Find EPIC_EG1 cookie and copy its value
7. Paste the value below and run this script

This will create a session.json file that the claimer can use.
"""

import json
import base64
from datetime import datetime, timezone
from pathlib import Path

# =============================================================================
# PASTE YOUR EPIC_EG1 TOKEN HERE:
# =============================================================================
EPIC_EG1_TOKEN = """
eg1~YOUR_TOKEN_HERE
""".strip()

# =============================================================================

def create_session_from_token(eg1_token: str) -> None:
    """Create session.json from EG1 token."""
    
    if not eg1_token or eg1_token == "eg1~YOUR_TOKEN_HERE":
        print("❌ Please paste your EPIC_EG1 token in the script first!")
        print("\nInstructions:")
        print("1. Open https://store.epicgames.com and log in")
        print("2. Press F12 → Application → Cookies → store.epicgames.com")
        print("3. Find EPIC_EG1 cookie and copy its value")
        print("4. Paste it in this script where it says 'YOUR_TOKEN_HERE'")
        print("5. Run this script again")
        return
    
    # Decode JWT to get account info
    try:
        if not eg1_token.startswith('eg1~'):
            print("❌ Invalid token format. Token should start with 'eg1~'")
            return
        
        jwt_part = eg1_token[4:]
        parts = jwt_part.split('.')
        
        if len(parts) < 2:
            print("❌ Invalid JWT format")
            return
        
        # Decode payload
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        account_id = payload_data.get('sub', '')
        display_name = payload_data.get('dn', '')
        exp_timestamp = payload_data.get('exp', 0)
        
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).isoformat()
        
        # Check if expired
        now = datetime.now(timezone.utc).timestamp()
        if exp_timestamp <= now:
            hours_ago = int((now - exp_timestamp) / 3600)
            print(f"❌ Token expired {hours_ago} hours ago!")
            print("Please get a fresh token from your browser.")
            return
        
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
        Path("data").mkdir(exist_ok=True)
        session_file = Path("data/session.json")
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        
        print("✅ Session created successfully!")
        print(f"   Account: {display_name}")
        print(f"   Account ID: {account_id}")
        print(f"   Valid for: {hours_left} hours")
        print(f"   File: {session_file.absolute()}")
        print("\nYou can now run: python epic_games_claimer.py")
        
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_session_from_token(EPIC_EG1_TOKEN)
