# -*- coding: utf-8 -*-
"""
Chrome Cookie Extractor for Epic Games Claimer.

Automatically extracts EPIC_EG1 and CF_CLEARANCE cookies from Chrome
using Windows DPAPI decryption. No browser UI required.

Target profile: Profile negao
"""

import os
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

# Windows DPAPI for cookie decryption
from typing import Any
try:
    import win32crypt  # type: ignore
    HAS_WIN32CRYPT = True
except ImportError:
    win32crypt = None  # type: ignore
    HAS_WIN32CRYPT = False

# AES decryption for Chrome v80+ cookies
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # type: ignore
    from cryptography.hazmat.backends import default_backend  # type: ignore
    HAS_CRYPTOGRAPHY = True
except ImportError:
    Cipher = None  # type: ignore
    algorithms = None  # type: ignore
    modes = None  # type: ignore
    default_backend = None  # type: ignore
    HAS_CRYPTOGRAPHY = False


@dataclass
class ExtractedCookies:
    """Container for extracted Epic Games cookies."""
    epic_eg1: str = ''
    cf_clearance: str = ''
    epic_sso: str = ''
    refresh_eg1: str = ''  # REFRESH_EPIC_EG1
    bearer_hash: str = ''  # bearerTokenHash
    
    def has_eg1(self) -> bool:
        """Check if EPIC_EG1 was extracted."""
        return bool(self.epic_eg1) and self.epic_eg1.startswith('eg1~')
    
    def has_refresh_eg1(self) -> bool:
        """Check if REFRESH_EPIC_EG1 was extracted."""
        return bool(self.refresh_eg1)
    
    def has_cf_clearance(self) -> bool:
        """Check if CF_CLEARANCE was extracted."""
        return bool(self.cf_clearance)


class ChromeCookieExtractor:
    """
    Extracts cookies from Chrome browser on Windows.
    
    Supports Chrome's encrypted cookie format using DPAPI and AES-GCM.
    Target profile: configurable via CHROME_PROFILE env or constructor arg.
    Fallback: 'Default' profile if the configured profile is not found.
    """
    
    # Default Chrome profile name (can be overridden via env or arg)
    DEFAULT_PROFILE = "Profile negao"
    
    # Epic Games domains to search
    EPIC_DOMAINS = [
        '.epicgames.com',
        'epicgames.com',
        'store.epicgames.com',
        '.store.epicgames.com',
    ]
    
    # Cookies to extract
    TARGET_COOKIES = ['EPIC_EG1', 'EPIC_SSO', 'cf_clearance', 'REFRESH_EPIC_EG1', 'bearerTokenHash']
    
    def __init__(self, profile_name: Optional[str] = None, logger=None):
        """
        Initialize extractor.
        
        Args:
            profile_name: Chrome profile folder name.
                          Default: CHROME_PROFILE env or 'Profile negao'.
                          Fallback: 'Default' if profile not found.
            logger: Optional logger instance.
        """
        import os
        self.profile_name = profile_name or os.getenv('CHROME_PROFILE', self.DEFAULT_PROFILE)
        self._logger = logger
        self._encryption_key: Optional[bytes] = None
    
    def _log(self, level: str, message: str, **kwargs):
        """Log message if logger available."""
        if self._logger:
            getattr(self._logger, level, self._logger.info)(message, **kwargs)
    
    def get_chrome_path(self) -> Optional[Path]:
        """
        Get Chrome user data directory path.
        
        Returns:
            Path to Chrome User Data folder or None.
        """
        local_appdata = os.getenv('LOCALAPPDATA', '')
        if not local_appdata:
            return None
        
        chrome_path = Path(local_appdata) / 'Google' / 'Chrome' / 'User Data'
        if chrome_path.exists():
            return chrome_path
        
        return None
    
    def get_profile_path(self) -> Optional[Path]:
        """
        Get path to configured Chrome profile.
        
        Falls back to 'Default' profile if configured profile doesn't exist.
        
        Returns:
            Path to profile folder or None.
        """
        chrome_path = self.get_chrome_path()
        if not chrome_path:
            self._log('error', "Chrome não encontrado")
            return None
        
        # Try configured profile first
        profile_path = chrome_path / self.profile_name
        if profile_path.exists():
            self._log('debug', f"Usando perfil: {self.profile_name}")
            return profile_path
        
        # Fallback to Default profile
        if self.profile_name != "Default":
            default_path = chrome_path / "Default"
            if default_path.exists():
                self._log('info', f"Perfil '{self.profile_name}' não encontrado, usando 'Default'")
                return default_path
        
        self._log('error', f"Perfil não encontrado: {self.profile_name}")
        return None
    
    def get_encryption_key(self) -> Optional[bytes]:
        """
        Get Chrome's cookie encryption key.
        
        Chrome v80+ uses AES-256-GCM with a key stored in Local State.
        
        Returns:
            Decrypted AES key or None.
        """
        if self._encryption_key:
            return self._encryption_key
        
        chrome_path = self.get_chrome_path()
        if not chrome_path:
            return None
        
        local_state_path = chrome_path / 'Local State'
        if not local_state_path.exists():
            self._log('debug', "Local State não encontrado")
            return None
        
        try:
            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
            
            encrypted_key_b64 = local_state.get('os_crypt', {}).get('encrypted_key', '')
            if not encrypted_key_b64:
                return None
            
            import base64
            encrypted_key = base64.b64decode(encrypted_key_b64)
            
            # Remove 'DPAPI' prefix (5 bytes)
            if encrypted_key[:5] == b'DPAPI':
                encrypted_key = encrypted_key[5:]
            
            # Decrypt using Windows DPAPI
            if HAS_WIN32CRYPT and win32crypt:
                wc: Any = win32crypt
                self._encryption_key = wc.CryptUnprotectData(
                    encrypted_key, None, None, None, 0
                )[1]
                return self._encryption_key
            
        except Exception as e:
            self._log('debug', f"Erro ao obter chave: {e}")
        
        return None
    
    def decrypt_cookie_value(self, encrypted_value: bytes) -> str:
        """
        Decrypt a Chrome cookie value.
        
        Handles both DPAPI (old) and AES-GCM (v80+) encryption.
        Supports v10, v11, v20 prefixes.
        
        Args:
            encrypted_value: Raw encrypted cookie bytes.
        
        Returns:
            Decrypted cookie value or empty string.
        """
        if not encrypted_value:
            return ''
        
        try:
            # Chrome v80+ uses 'v10', 'v11', or 'v20' prefix with AES-GCM
            prefix = encrypted_value[:3]
            if prefix in (b'v10', b'v11', b'v20'):
                if not HAS_CRYPTOGRAPHY:
                    self._log('warning', "cryptography não instalado para AES")
                    return ''
                
                key = self.get_encryption_key()
                if not key:
                    self._log('debug', "Não foi possível obter chave de criptografia")
                    return ''
                
                # v10/v11/v20 format: prefix(3) + nonce(12) + ciphertext + tag(16)
                nonce = encrypted_value[3:15]
                ciphertext = encrypted_value[15:]
                
                if not (Cipher and algorithms and modes and default_backend):
                    return ''
                cipher = Cipher(
                    algorithms.AES(key),
                    modes.GCM(nonce),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                
                # Last 16 bytes are the authentication tag
                decrypted = decryptor.update(ciphertext[:-16])
                decryptor.finalize_with_tag(ciphertext[-16:])
                
                return decrypted.decode('utf-8')
            
            # Old DPAPI encryption (rare now)
            elif HAS_WIN32CRYPT and win32crypt:
                wc: Any = win32crypt
                return wc.CryptUnprotectData(
                    encrypted_value, None, None, None, 0
                )[1].decode('utf-8')
            
        except Exception as e:
            self._log('debug', f"Erro ao descriptografar: {e}")
        
        return ''
    
    def extract_cookies(self) -> ExtractedCookies:
        """
        Extract Epic Games cookies from Chrome.
        
        Reads the Cookies SQLite database, decrypts values, and returns
        EPIC_EG1 and CF_CLEARANCE.
        
        Returns:
            ExtractedCookies with found values.
        """
        result = ExtractedCookies()
        
        profile_path = self.get_profile_path()
        if not profile_path:
            return result
        
        cookies_db = profile_path / 'Cookies'
        if not cookies_db.exists():
            # Try Network subfolder (newer Chrome versions)
            cookies_db = profile_path / 'Network' / 'Cookies'
            if not cookies_db.exists():
                self._log('error', "Database de cookies não encontrada")
                return result
        
        # Copy database to temp to avoid lock issues
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
                temp_file = tmp.name
            
            shutil.copy2(cookies_db, temp_file)
            
            # Connect and query
            conn = sqlite3.connect(temp_file)
            cursor = conn.cursor()
            
            # Build domain filter
            domain_conditions = ' OR '.join(
                f"host_key LIKE '%{d}'" for d in self.EPIC_DOMAINS
            )
            
            # Query for target cookies
            query = f"""
                SELECT name, encrypted_value, host_key, value
                FROM cookies
                WHERE ({domain_conditions})
                AND name IN ({','.join('?' for _ in self.TARGET_COOKIES)})
            """
            
            cursor.execute(query, self.TARGET_COOKIES)
            rows = cursor.fetchall()
            conn.close()
            
            for name, encrypted_value, host, plain_value in rows:
                # Try plain value first (unencrypted)
                value = plain_value if plain_value else ''
                
                # Decrypt if needed
                if not value and encrypted_value:
                    value = self.decrypt_cookie_value(encrypted_value)
                
                if not value:
                    continue
                
                # Store by cookie name
                if name == 'EPIC_EG1':
                    result.epic_eg1 = value
                    self._log('debug', f"EPIC_EG1 encontrado ({len(value)} chars)")
                elif name == 'EPIC_SSO':
                    result.epic_sso = value
                    self._log('debug', f"EPIC_SSO encontrado")
                elif name == 'cf_clearance':
                    result.cf_clearance = value
                    self._log('debug', f"CF_CLEARANCE encontrado")
                elif name == 'REFRESH_EPIC_EG1':
                    result.refresh_eg1 = value
                    self._log('debug', f"REFRESH_EPIC_EG1 encontrado ({len(value)} chars)")
                elif name == 'bearerTokenHash':
                    result.bearer_hash = value
                    self._log('debug', f"bearerTokenHash encontrado")
            
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e).lower():
                self._log('error', "Chrome deve estar fechado para ler cookies")
            else:
                self._log('error', f"Erro SQLite: {e}")
        except Exception as e:
            self._log('error', f"Erro ao extrair cookies: {e}")
        finally:
            # Cleanup temp file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        return result
    
    def extract_and_validate(self) -> Tuple[ExtractedCookies, bool]:
        """
        Extract cookies and validate useful tokens are present.
        
        Success if EPIC_EG1 OR REFRESH_EPIC_EG1 is found.
        
        Returns:
            Tuple of (ExtractedCookies, success_bool).
        """
        cookies = self.extract_cookies()
        
        if cookies.has_eg1():
            self._log('info', "✅ EPIC_EG1 extraído do Chrome com sucesso")
            if cookies.has_cf_clearance():
                self._log('info', "✅ CF_CLEARANCE também extraído")
            return cookies, True
        
        if cookies.has_refresh_eg1():
            self._log('info', "✅ REFRESH_EPIC_EG1 extraído do Chrome")
            self._log('info', "   (EPIC_EG1 não encontrado - token de acesso expirado)")
            if cookies.has_cf_clearance():
                self._log('info', "✅ CF_CLEARANCE também extraído")
            return cookies, True
        
        # DPAPI extraction failed - try Playwright (works with Chrome 127+ App-Bound Encryption)
        self._log('info', "Extração DPAPI falhou. Tentando via Playwright...")
        try:
            from .playwright_cookies import PlaywrightCookieExtractor
            
            pw_extractor = PlaywrightCookieExtractor(
                profile_name=self.profile_name,
                logger=self._logger
            )
            pw_cookies, pw_success = pw_extractor.extract_and_validate()
            if pw_success and pw_cookies:
                # Map to local ExtractedCookies type to satisfy type checker
                mapped = ExtractedCookies(
                    epic_eg1=getattr(pw_cookies, 'epic_eg1', ''),
                    cf_clearance=getattr(pw_cookies, 'cf_clearance', ''),
                    epic_sso=getattr(pw_cookies, 'epic_sso', ''),
                    refresh_eg1=getattr(pw_cookies, 'refresh_eg1', ''),
                    bearer_hash=getattr(pw_cookies, 'bearer_hash', ''),
                )
                return mapped, True
        except ImportError:
            self._log('warning', "Playwright não disponível. Execute: pip install playwright && playwright install chromium")
        except Exception as e:
            self._log('warning', f"Playwright falhou: {e}")
        
        self._log('warning', "Nenhum token Epic encontrado no Chrome")
        return cookies, False


def extract_chrome_cookies(profile_name: Optional[str] = None, logger=None) -> ExtractedCookies:
    """
    Convenience function to extract Epic Games cookies from Chrome.
    
    Args:
        profile_name: Chrome profile name (default: Profile negao).
        logger: Optional logger instance.
    
    Returns:
        ExtractedCookies with EPIC_EG1, CF_CLEARANCE, etc.
    """
    extractor = ChromeCookieExtractor(profile_name=profile_name, logger=logger)
    return extractor.extract_cookies()


def refresh_session_from_chrome(session_store, config, logger=None) -> bool:
    """
    Refresh session.json from Chrome cookies.
    
    Extracts EPIC_EG1 from Chrome and creates/updates session.
    Also updates CF_CLEARANCE in config if found.
    
    Args:
        session_store: SessionStore instance.
        config: Config instance (to update CF_CLEARANCE).
        logger: Optional logger instance.
    
    Returns:
        True if session was refreshed successfully.
    """
    from .session_store import Session
    
    extractor = ChromeCookieExtractor(logger=logger)
    cookies, success = extractor.extract_and_validate()
    
    if not success:
        return False
    
    # Create session from EG1 token
    session = Session.from_eg1_token(cookies.epic_eg1)
    if not session:
        if logger:
            logger.error("Falha ao criar sessão do token extraído")
        return False
    
    # Add extra cookies
    if cookies.epic_sso:
        session.cookies['EPIC_SSO'] = cookies.epic_sso
    
    # Save session
    if session_store.save(session):
        if logger:
            logger.success(f"Sessão atualizada do Chrome: {session.display_name}")
        
        # Update CF_CLEARANCE in config if found
        if cookies.has_cf_clearance():
            config.cf_clearance = cookies.cf_clearance
            if logger:
                logger.info("CF_CLEARANCE atualizado do Chrome")
        
        return True
    
    return False


# Direct execution for testing
if __name__ == '__main__':
    print("=" * 60)
    print("🍪 CHROME COOKIE EXTRACTOR - Profile negao")
    print("=" * 60)
    print("\nExtraindo cookies do Chrome (feche o navegador primeiro)...\n")
    
    extractor = ChromeCookieExtractor()
    cookies, success = extractor.extract_and_validate()
    
    if success:
        if cookies.epic_eg1:
            print(f"✅ EPIC_EG1: {cookies.epic_eg1[:50]}...")
        if cookies.refresh_eg1:
            print(f"✅ REFRESH_EPIC_EG1: {cookies.refresh_eg1[:50]}...")
        if cookies.cf_clearance:
            print(f"✅ CF_CLEARANCE: {cookies.cf_clearance[:50]}...")
        if cookies.epic_sso:
            print(f"✅ EPIC_SSO: encontrado")
        if cookies.bearer_hash:
            print(f"✅ bearerTokenHash: encontrado")
        print("\n🎮 Cookies prontos para uso!")
    else:
        print("\n❌ Falha ao extrair cookies")
        print("   Verifique se:")
        print("   1. Chrome está fechado")
        print("   2. Você está logado em store.epicgames.com no perfil 'Profile negao'")
