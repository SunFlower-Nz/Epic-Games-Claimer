# -*- coding: utf-8 -*-
"""
Session management for Epic Games Claimer.

Handles:
- Authentication token storage
- Session persistence to JSON
- Token validation and expiration checks
- Conversion from legacy formats
"""

import json
import base64
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, TYPE_CHECKING

from .logger import Logger

if TYPE_CHECKING:
    from .config import Config


@dataclass
class Session:
    """Stores authentication tokens and account information."""
    
    access_token: str = ''
    refresh_token: str = ''
    account_id: str = ''
    display_name: str = ''
    expires_at: str = ''  # ISO format timestamp
    refresh_expires_at: str = ''  # ISO format timestamp
    cookies: Dict[str, str] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """
        Check if access token is still valid.
        
        Returns:
            True if token exists and hasn't expired (with 5-min buffer).
        """
        if not self.access_token or not self.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            # 5-minute buffer before expiration
            return datetime.now(timezone.utc) < (expires - timedelta(minutes=5))
        except (ValueError, TypeError):
            return False
    
    def can_refresh(self) -> bool:
        """
        Check if refresh token can be used.
        
        Returns:
            True if refresh token exists and hasn't expired.
        """
        if not self.refresh_token or not self.refresh_expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.refresh_expires_at.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) < expires
        except (ValueError, TypeError):
            return False
    
    def time_until_expiry(self) -> Optional[timedelta]:
        """Get time remaining until token expires."""
        if not self.expires_at:
            return None
        try:
            expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            remaining = expires - datetime.now(timezone.utc)
            return remaining if remaining.total_seconds() > 0 else timedelta(0)
        except (ValueError, TypeError):
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """
        Create Session from dictionary.
        
        Args:
            data: Dictionary with session fields.
        
        Returns:
            Session instance.
        """
        return cls(
            access_token=data.get('access_token', ''),
            refresh_token=data.get('refresh_token', ''),
            account_id=data.get('account_id', ''),
            display_name=data.get('display_name', ''),
            expires_at=data.get('expires_at', ''),
            refresh_expires_at=data.get('refresh_expires_at', ''),
            cookies=data.get('cookies', {})
        )
    
    @classmethod
    def from_eg1_token(cls, eg1_token: str) -> Optional['Session']:
        """
        Create Session from EPIC_EG1 cookie token.
        
        Decodes the JWT to extract account info and expiration.
        
        Args:
            eg1_token: The eg1~ prefixed token from browser cookies.
        
        Returns:
            Session instance or None if invalid.
        """
        if not eg1_token or not eg1_token.startswith('eg1~'):
            return None
        
        try:
            jwt_part = eg1_token[4:]  # Remove 'eg1~' prefix
            parts = jwt_part.split('.')
            
            if len(parts) < 2:
                return None
            
            # Decode JWT payload (add padding if needed)
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            payload_data = json.loads(decoded)
            
            # Extract fields from JWT
            account_id = payload_data.get('sub', '')
            display_name = payload_data.get('dn', '')
            exp_timestamp = payload_data.get('exp', 0)
            
            expires_at = ''
            if exp_timestamp:
                expires_at = datetime.fromtimestamp(
                    exp_timestamp, tz=timezone.utc
                ).isoformat()
            
            return cls(
                access_token=eg1_token,
                account_id=account_id,
                display_name=display_name,
                expires_at=expires_at,
                cookies={'EPIC_EG1': eg1_token}
            )
            
        except Exception:
            return None


class SessionStore:
    """Handles session persistence to/from JSON file."""
    
    def __init__(self, session_file: Path, logger: Logger):
        """
        Initialize session store.
        
        Args:
            session_file: Path to session JSON file.
            logger: Logger instance for output.
        """
        self.session_file = session_file
        self._logger = logger
    
    def load(self) -> Optional[Session]:
        """
        Load session from file.
        
        Returns:
            Session instance or None if not found/invalid.
        """
        try:
            if not self.session_file.exists():
                self._logger.debug("No saved session found", path=str(self.session_file))
                return None
            
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle legacy Playwright cookie format
            if 'cookies' in data and isinstance(data['cookies'], list):
                session = self._convert_from_playwright_format(data)
                self._logger.debug("Converted legacy session format")
            else:
                session = Session.from_dict(data)
            
            if session.display_name:
                self._logger.info(
                    f"Session loaded for: {session.display_name}",
                    account_id=session.account_id[:8] + '...' if session.account_id else None
                )
                
                # Log expiry info
                remaining = session.time_until_expiry()
                if remaining:
                    hours = remaining.total_seconds() / 3600
                    self._logger.debug(f"Token expires in {hours:.1f} hours")
            
            return session
            
        except json.JSONDecodeError as e:
            self._logger.error("Invalid session file format", exc=e)
            return None
        except Exception as e:
            self._logger.error("Error loading session", exc=e)
            return None
    
    def _convert_from_playwright_format(self, data: Dict[str, Any]) -> Session:
        """
        Convert legacy Playwright cookie array format to Session.
        
        Args:
            data: Dictionary with 'cookies' as array of cookie objects.
        
        Returns:
            Session instance.
        """
        cookies_dict = {}
        eg1_token = ''
        
        # Extract cookies from array format
        for cookie in data.get('cookies', []):
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            cookies_dict[name] = value
            
            if name == 'EPIC_EG1':
                eg1_token = value
        
        # Try to create session from EG1 token
        if eg1_token:
            session = Session.from_eg1_token(eg1_token)
            if session:
                session.cookies = cookies_dict
                return session
        
        # Fallback: return session with just cookies
        return Session(cookies=cookies_dict)
    
    def save(self, session: Session) -> bool:
        """
        Save session to file.
        
        Args:
            session: Session instance to save.
        
        Returns:
            True if saved successfully.
        """
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            self._logger.debug(
                "Session saved",
                path=str(self.session_file),
                account=session.display_name
            )
            return True
            
        except Exception as e:
            self._logger.error("Error saving session", exc=e, path=str(self.session_file))
            return False
    
    def clear(self) -> bool:
        """
        Delete saved session file.
        
        Returns:
            True if cleared successfully.
        """
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                self._logger.info("Session cleared", path=str(self.session_file))
            return True
        except Exception as e:
            self._logger.error("Error clearing session", exc=e)
            return False
    
    def refresh_from_chrome(self, config: Optional['Config'] = None) -> Optional[Session]:
        """
        Refresh session by extracting cookies from Chrome browser.
        
        Reads EPIC_EG1/REFRESH_EPIC_EG1 and CF_CLEARANCE from Chrome,
        creates a new session, and saves it.
        
        Args:
            config: Optional Config instance to update CF_CLEARANCE.
        
        Returns:
            New Session if successful, None otherwise.
        """
        try:
            from .chrome_cookies import ChromeCookieExtractor
            
            self._logger.info("Extraindo cookies do Chrome (Profile negao)...")
            
            extractor = ChromeCookieExtractor(logger=self._logger)
            cookies, success = extractor.extract_and_validate()
            
            if not success:
                self._logger.warning("Não foi possível extrair tokens do Chrome")
                return None
            
            session = None
            
            # Try EPIC_EG1 first (access token)
            if cookies.has_eg1():
                session = Session.from_eg1_token(cookies.epic_eg1)
                if session:
                    self._logger.debug("Sessão criada a partir de EPIC_EG1")
            
            # If no EPIC_EG1, use REFRESH_EPIC_EG1 to create a session with refresh capability
            if not session and cookies.has_refresh_eg1():
                # Create a minimal session that will trigger refresh
                session = Session(
                    refresh_token=cookies.refresh_eg1,
                    cookies={
                        'REFRESH_EPIC_EG1': cookies.refresh_eg1,
                    }
                )
                # Set refresh_expires_at to far future so can_refresh() returns True
                from datetime import datetime, timedelta, timezone
                session.refresh_expires_at = (
                    datetime.now(timezone.utc) + timedelta(days=30)
                ).isoformat()
                self._logger.info("Sessão criada com REFRESH_EPIC_EG1 (precisará renovar token)")
            
            if not session:
                self._logger.error("Nenhum token válido extraído")
                return None
            
            # Add extra cookies if found
            if cookies.epic_sso:
                session.cookies['EPIC_SSO'] = cookies.epic_sso
            if cookies.cf_clearance:
                session.cookies['cf_clearance'] = cookies.cf_clearance
            if cookies.bearer_hash:
                session.cookies['bearerTokenHash'] = cookies.bearer_hash
            
            # Save session
            if self.save(session):
                self._logger.success(
                    f"Sessão atualizada do Chrome: {session.display_name}"
                )
                
                # Update CF_CLEARANCE in config if found
                if config and cookies.has_cf_clearance():
                    config.cf_clearance = cookies.cf_clearance
                    self._logger.info("CF_CLEARANCE atualizado do Chrome")
                
                return session
            
            return None
            
        except ImportError as e:
            self._logger.error(
                "Dependências não instaladas para extração Chrome",
                exc=e,
                hint="pip install pywin32 cryptography"
            )
            return None
        except Exception as e:
            self._logger.error("Erro ao extrair cookies do Chrome", exc=e)
            return None
