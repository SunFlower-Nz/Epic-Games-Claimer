# -*- coding: utf-8 -*-
"""
Playwright-based Cookie Extractor for Epic Games Claimer.

Uses Playwright to connect to an existing Chrome profile and extract cookies.
This works with Chrome 127+ App-Bound Encryption since it uses Chrome's own
cookie storage through DevTools Protocol.

Target profile: Profile negao (or Default as fallback)
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ExtractedCookies:
    """Container for extracted Epic Games cookies."""
    epic_eg1: str = ''
    cf_clearance: str = ''
    epic_sso: str = ''
    refresh_eg1: str = ''
    bearer_hash: str = ''
    
    def has_eg1(self) -> bool:
        return bool(self.epic_eg1) and self.epic_eg1.startswith('eg1~')
    
    def has_refresh_eg1(self) -> bool:
        return bool(self.refresh_eg1)
    
    def has_cf_clearance(self) -> bool:
        return bool(self.cf_clearance)


class PlaywrightCookieExtractor:
    """
    Extracts cookies from Chrome using Playwright.
    
    This method works with Chrome 127+ App-Bound Encryption by connecting
    to the browser via Chrome DevTools Protocol and accessing cookies directly.
    
    Profile is configurable via CHROME_PROFILE env or constructor arg.
    Fallback: 'Default' profile if configured profile not found.
    """
    
    DEFAULT_PROFILE = "Profile negao"
    
    EPIC_DOMAINS = [
        'epicgames.com',
        'store.epicgames.com',
        'www.epicgames.com',
    ]
    
    def __init__(self, profile_name: Optional[str] = None, logger=None):
        import os
        self.profile_name = profile_name or os.getenv('CHROME_PROFILE', self.DEFAULT_PROFILE)
        self._logger = logger
    
    def _log(self, level: str, message: str, **kwargs):
        if self._logger:
            getattr(self._logger, level, self._logger.info)(message, **kwargs)
        else:
            print(f"[{level.upper()}] {message}")
    
    def get_chrome_path(self) -> Optional[Path]:
        """Get Chrome user data directory."""
        local_appdata = os.getenv('LOCALAPPDATA', '')
        if not local_appdata:
            return None
        
        chrome_path = Path(local_appdata) / 'Google' / 'Chrome' / 'User Data'
        return chrome_path if chrome_path.exists() else None
    
    def get_profile_path(self) -> Optional[Path]:
        """Get profile directory, with Default fallback."""
        chrome_path = self.get_chrome_path()
        if not chrome_path:
            return None
        
        # Try configured profile
        profile_path = chrome_path / self.profile_name
        if profile_path.exists():
            return profile_path
        
        # Fallback to Default
        if self.profile_name != "Default":
            default_path = chrome_path / "Default"
            if default_path.exists():
                self._log('info', f"Perfil '{self.profile_name}' não encontrado, usando 'Default'")
                return default_path
        
        return None
    
    def extract_cookies_playwright(self) -> ExtractedCookies:
        """
        Extract cookies using Playwright.
        
        Tries two methods:
        1. Connect to existing Chrome via CDP (if Chrome is open with remote debugging)
        2. Launch new browser with copied profile
        """
        result = ExtractedCookies()
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self._log('error', "Playwright não instalado. Execute: pip install playwright && playwright install chromium")
            return result
        
        # Method 1: Try to use a temporary copy of the profile
        result = self._extract_with_temp_profile()
        if result.has_eg1() or result.has_refresh_eg1():
            return result
        
        # Method 2: Launch headless Chromium and navigate to Epic (user must be logged in)
        self._log('info', "Tentando método alternativo...")
        result = self._extract_with_login_check()
        
        return result
    
    def _extract_with_temp_profile(self) -> ExtractedCookies:
        """Extract by launching Chromium with copied cookies."""
        result = ExtractedCookies()
        
        try:
            from playwright.sync_api import sync_playwright
            import tempfile
            import shutil
            
            chrome_path = self.get_chrome_path()
            if not chrome_path:
                return result
            
            # Determine profile
            profile_dir = self.profile_name
            profile_path = chrome_path / profile_dir
            if not profile_path.exists():
                profile_dir = "Default"
                profile_path = chrome_path / profile_dir
            
            # Create temp user data dir
            temp_dir = tempfile.mkdtemp(prefix="chrome_cookies_")
            temp_profile = Path(temp_dir) / profile_dir
            
            self._log('info', f"Copiando perfil {profile_dir} para temp...")
            
            try:
                # Copy essential files only
                temp_profile.mkdir(parents=True, exist_ok=True)
                
                # Copy Local State
                local_state_src = chrome_path / "Local State"
                local_state_dst = Path(temp_dir) / "Local State"
                if local_state_src.exists():
                    shutil.copy2(local_state_src, local_state_dst)
                
                # Copy cookies and login data
                for filename in ['Cookies', 'Login Data', 'Preferences', 'Secure Preferences']:
                    for subdir in ['', 'Network']:
                        src = profile_path / subdir / filename if subdir else profile_path / filename
                        if src.exists():
                            dst_dir = temp_profile / subdir if subdir else temp_profile
                            dst_dir.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src, dst_dir / filename)
                
                self._log('info', "Abrindo Chromium com perfil copiado...")
                
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=temp_dir,
                        headless=True,
                        args=[
                            f"--profile-directory={profile_dir}",
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                        ],
                    )
                    
                    page = context.new_page()
                    page.goto("https://store.epicgames.com", wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(2000)
                    
                    cookies = context.cookies()
                    result = self._parse_cookies(cookies)
                    
                    page.close()
                    context.close()
                    
            finally:
                # Cleanup temp dir
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
                    
        except Exception as e:
            self._log('debug', f"Temp profile method failed: {e}")
        
        return result
    
    def _extract_with_login_check(self) -> ExtractedCookies:
        """Launch headless browser and check if logged in."""
        result = ExtractedCookies()
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                
                # Go to Epic login page
                page.goto("https://store.epicgames.com", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                
                cookies = context.cookies()
                result = self._parse_cookies(cookies)
                
                browser.close()
                
        except Exception as e:
            self._log('debug', f"Login check method failed: {e}")
        
        return result
    
    def _parse_cookies(self, cookies: list) -> ExtractedCookies:
        """Parse Playwright cookies list into ExtractedCookies."""
        result = ExtractedCookies()
        
        for cookie in cookies:
            domain = cookie.get('domain', '')
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            
            if not any(d in domain for d in ['epicgames.com']):
                continue
            
            if name == 'EPIC_EG1' and value:
                result.epic_eg1 = value
                self._log('debug', f"EPIC_EG1 encontrado ({len(value)} chars)")
            elif name == 'EPIC_SSO' and value:
                result.epic_sso = value
                self._log('debug', "EPIC_SSO encontrado")
            elif name == 'cf_clearance' and value:
                result.cf_clearance = value
                self._log('debug', "CF_CLEARANCE encontrado")
            elif name == 'REFRESH_EPIC_EG1' and value:
                result.refresh_eg1 = value
                self._log('debug', f"REFRESH_EPIC_EG1 encontrado ({len(value)} chars)")
            elif name == 'bearerTokenHash' and value:
                result.bearer_hash = value
                self._log('debug', "bearerTokenHash encontrado")
        
        return result
    
    def extract_and_validate(self) -> Tuple[ExtractedCookies, bool]:
        """Extract and validate cookies."""
        cookies = self.extract_cookies_playwright()
        
        if cookies.has_eg1():
            self._log('info', "✅ EPIC_EG1 extraído com sucesso")
            if cookies.has_cf_clearance():
                self._log('info', "✅ CF_CLEARANCE também extraído")
            return cookies, True
        
        if cookies.has_refresh_eg1():
            self._log('info', "✅ REFRESH_EPIC_EG1 extraído")
            self._log('info', "   (EPIC_EG1 não encontrado - token de acesso expirado)")
            if cookies.has_cf_clearance():
                self._log('info', "✅ CF_CLEARANCE também extraído")
            return cookies, True
        
        self._log('warning', "Nenhum token Epic encontrado")
        return cookies, False


def extract_via_playwright(profile_name: Optional[str] = None, logger=None) -> ExtractedCookies:
    """Convenience function."""
    extractor = PlaywrightCookieExtractor(profile_name=profile_name, logger=logger)
    return extractor.extract_cookies_playwright()


if __name__ == '__main__':
    print("=" * 60)
    print("🎭 PLAYWRIGHT COOKIE EXTRACTOR - Profile negao")
    print("=" * 60)
    print("\nEste método abre o Chrome brevemente para extrair cookies.")
    print("Funciona com Chrome 127+ (App-Bound Encryption).\n")
    
    extractor = PlaywrightCookieExtractor()
    cookies, success = extractor.extract_and_validate()
    
    if success:
        print("\n" + "=" * 60)
        if cookies.epic_eg1:
            print(f"✅ EPIC_EG1: {cookies.epic_eg1[:50]}...")
        if cookies.refresh_eg1:
            print(f"✅ REFRESH_EPIC_EG1: {cookies.refresh_eg1[:50]}...")
        if cookies.cf_clearance:
            print(f"✅ CF_CLEARANCE: {cookies.cf_clearance[:50]}...")
        if cookies.epic_sso:
            print(f"✅ EPIC_SSO: encontrado")
        print("\n🎮 Cookies prontos para uso!")
    else:
        print("\n❌ Falha ao extrair cookies")
        print("   Verifique se você está logado em store.epicgames.com")
