#!/usr/bin/env python
"""Debug script for Chrome cookie extraction."""

from src.chrome_cookies import ChromeCookieExtractor
import sqlite3
import shutil
import tempfile
from pathlib import Path
import os

e = ChromeCookieExtractor()
profile_path = e.get_profile_path()
print(f'1. Profile path: {profile_path}')
if not profile_path:
    print('Perfil não encontrado. Abortando teste.')
    raise SystemExit(1)

# Check Cookies DB location
cookies_db = profile_path / 'Cookies'
network_cookies = profile_path / 'Network' / 'Cookies'
print(f'2. Cookies exists: {cookies_db.exists()}')
print(f'3. Network/Cookies exists: {network_cookies.exists()}')

# Try to copy and read
db_path = network_cookies if network_cookies.exists() else cookies_db
print(f'4. Using: {db_path}')

# Copy to temp
with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
    temp_file = tmp.name
shutil.copy2(db_path, temp_file)
print(f'5. Copied to temp: {temp_file}')

# Query
conn = sqlite3.connect(temp_file)
cursor = conn.cursor()

# Get cf_clearance for testing
cursor.execute("SELECT encrypted_value FROM cookies WHERE name = 'cf_clearance' LIMIT 1")
row = cursor.fetchone()

if row:
    enc = row[0]
    print(f'\n6. Testing decryption of cf_clearance:')
    print(f'   Prefix: {enc[:3]}')
    print(f'   Total length: {len(enc)}')
    
    # Get encryption key
    key = e.get_encryption_key()
    print(f'   Key obtained: {key is not None}')
    
    if key:
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # type: ignore
            from cryptography.hazmat.backends import default_backend  # type: ignore
        except Exception:
            print('   cryptography não disponível, pulando teste de descriptografia')
            conn.close()
            os.unlink(temp_file)
            raise SystemExit(0)
        
        nonce = enc[3:15]
        ciphertext = enc[15:]
        
        print(f'   Nonce length: {len(nonce)}')
        print(f'   Ciphertext length: {len(ciphertext)}')
        
        try:
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(ciphertext[:-16])
            decryptor.finalize_with_tag(ciphertext[-16:])
            print(f'   ✅ Decrypted: {decrypted.decode("utf-8")[:60]}...')
        except Exception as ex:
            print(f'   ❌ Error: {type(ex).__name__}: {ex}')
            import traceback
            traceback.print_exc()

conn.close()
os.unlink(temp_file)
