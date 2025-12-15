# -*- coding: utf-8 -*-
"""
Configuration management for Epic Games Claimer.

Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Application configuration from environment variables."""
    
    # Epic Games API client credentials (launcher client - supports device auth)
    client_id: str = field(default_factory=lambda: os.getenv(
        'EPIC_CLIENT_ID', ''
    ))
    client_secret: str = field(default_factory=lambda: os.getenv(
        'EPIC_CLIENT_SECRET', ''
    ))
    
    # Session and data paths
    session_file: Path = field(default_factory=lambda: Path(
        os.getenv('SESSION_FILE', 'data/session.json')
    ))
    data_dir: Path = field(default_factory=lambda: Path(
        os.getenv('DATA_DIR', 'data')
    ))
    log_base_dir: Path = field(default_factory=lambda: Path(
        os.getenv('LOG_BASE_DIR', 'logs')
    ))
    
    # Fallback cookies from .env (optional - for browser token auth)
    fallback_eg1: str = field(default_factory=lambda: os.getenv('EPIC_EG1', ''))
    fallback_sso: str = field(default_factory=lambda: os.getenv('EPIC_SSO', ''))
    fallback_bearer: str = field(default_factory=lambda: os.getenv('EPIC_BEARER_TOKEN', ''))
    
    # Cloudflare Bot Challenge bypass cookie
    cf_clearance: str = field(default_factory=lambda: os.getenv('CF_CLEARANCE', ''))
    
    # Feature flags
    use_external_freebies: bool = field(default_factory=lambda: os.getenv(
        'USE_EXTERNAL_FREEBIES', 'false'
    ).lower() == 'true')
    
    # Scheduler settings
    schedule_hour: int = field(default_factory=lambda: int(os.getenv('SCHEDULE_HOUR', '12')))
    schedule_minute: int = field(default_factory=lambda: int(os.getenv('SCHEDULE_MINUTE', '0')))
    
    # Request settings
    timeout: int = field(default_factory=lambda: int(os.getenv('TIMEOUT', '30')))
    user_agent: str = field(default_factory=lambda: os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0'
    ))
    
    # Locale settings
    country: str = field(default_factory=lambda: os.getenv('COUNTRY', 'BR'))
    locale: str = field(default_factory=lambda: os.getenv('LOCALE', 'pt-BR'))
    
    # Chrome profile for cookie extraction (fallback to 'Default' if not found)
    chrome_profile: str = field(default_factory=lambda: os.getenv('CHROME_PROFILE', 'Profile negao'))
    
    def __post_init__(self):
        """Ensure directories exist after initialization."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_base_dir.mkdir(parents=True, exist_ok=True)
        # Ensure session file directory exists
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
    
    def update_cf_clearance(self, value: str) -> None:
        """
        Update CF_CLEARANCE cookie value.
        
        Called by Chrome cookie extractor to set fresh CF_CLEARANCE.
        
        Args:
            value: New CF_CLEARANCE cookie value.
        """
        if value:
            self.cf_clearance = value
    
    def refresh_cf_from_chrome(self) -> bool:
        """
        Refresh CF_CLEARANCE by extracting from Chrome browser.
        
        Returns:
            True if CF_CLEARANCE was updated.
        """
        try:
            from .chrome_cookies import ChromeCookieExtractor
            
            extractor = ChromeCookieExtractor(profile_name=self.chrome_profile)
            cookies = extractor.extract_cookies()
            
            if cookies.has_cf_clearance():
                self.cf_clearance = cookies.cf_clearance
                return True
            
        except Exception:
            pass
        
        return False
    
    def __repr__(self) -> str:
        """Safe representation without exposing secrets."""
        return (
            f"Config(client_id='{self.client_id[:8]}...', "
            f"session_file='{self.session_file}', "
            f"log_base_dir='{self.log_base_dir}', "
            f"schedule={self.schedule_hour:02d}:{self.schedule_minute:02d}, "
            f"timeout={self.timeout}s)"
        )
