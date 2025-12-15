# -*- coding: utf-8 -*-
"""
Epic Games Store - Free Games Claimer (HTTP-only).

This script automates the collection of free games from the Epic Games Store
using pure HTTP requests without browser automation.
"""

import os
import json
import time
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from epic_games_logger import Logger

# Load environment variables
load_dotenv()


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class Config:
    """Application configuration from environment variables."""
    
    # Epic Games API client (launcher client - supports device auth)
    client_id: str = field(default_factory=lambda: os.getenv(
        'EPIC_CLIENT_ID', '34a02cf8f4414e29b15921876da36f9a'
    ))
    client_secret: str = field(default_factory=lambda: os.getenv(
        'EPIC_CLIENT_SECRET', 'daafbccc737745039dffe53d94fc76cf'
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
    
    # Fallback cookies from .env (optional)
    fallback_eg1: str = field(default_factory=lambda: os.getenv('EPIC_EG1', ''))
    fallback_sso: str = field(default_factory=lambda: os.getenv('EPIC_SSO', ''))
    fallback_bearer: str = field(default_factory=lambda: os.getenv('EPIC_BEARER_TOKEN', ''))
    
    # Feature flags
    use_external_freebies: bool = field(default_factory=lambda: os.getenv(
        'USE_EXTERNAL_FREEBIES', 'false'
    ).lower() == 'true')
    
    # Request settings
    timeout: int = field(default_factory=lambda: int(os.getenv('TIMEOUT', '30')))
    user_agent: str = field(default_factory=lambda: os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0'
    ))
    
    def __post_init__(self):
        """Ensure directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_base_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Session Management
# =============================================================================

@dataclass
class Session:
    """Stores authentication tokens and cookies."""
    
    access_token: str = ''
    refresh_token: str = ''
    account_id: str = ''
    display_name: str = ''
    expires_at: str = ''  # ISO format
    refresh_expires_at: str = ''  # ISO format
    
    # Cookies for web requests
    cookies: Dict[str, str] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if access token is still valid."""
        if not self.access_token or not self.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            # Add 5-minute buffer
            return datetime.now(timezone.utc) < (expires - timedelta(minutes=5))
        except:
            return False
    
    def can_refresh(self) -> bool:
        """Check if refresh token is still valid."""
        if not self.refresh_token or not self.refresh_expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.refresh_expires_at.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) < expires
        except:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create Session from dictionary."""
        return cls(
            access_token=data.get('access_token', ''),
            refresh_token=data.get('refresh_token', ''),
            account_id=data.get('account_id', ''),
            display_name=data.get('display_name', ''),
            expires_at=data.get('expires_at', ''),
            refresh_expires_at=data.get('refresh_expires_at', ''),
            cookies=data.get('cookies', {})
        )


class SessionStore:
    """Handles session persistence."""
    
    def __init__(self, session_file: Path, logger: Logger):
        self.session_file = session_file
        self._logger = logger
    
    def load(self) -> Optional[Session]:
        """Load session from file."""
        try:
            if not self.session_file.exists():
                self._logger.logger.info("ℹ️ No saved session found")
                return None
            
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle old format (Playwright cookies array)
            if 'cookies' in data and isinstance(data['cookies'], list):
                session = self._convert_from_playwright_format(data)
            else:
                session = Session.from_dict(data)
            
            self._logger.logger.info(f"💾 Session loaded for: {session.display_name}")
            return session
            
        except Exception as e:
            self._logger.logger.error(f"❌ Error loading session: {e}")
            return None
    
    def _convert_from_playwright_format(self, data: Dict[str, Any]) -> Session:
        """Convert Playwright cookie format to session format."""
        cookies_dict = {}
        access_token = ''
        
        # Extract cookies from array
        for cookie in data.get('cookies', []):
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            
            if name == 'EPIC_EG1':
                access_token = value
            
            cookies_dict[name] = value
        
        # Try to decode token to get account info
        account_id = ''
        display_name = ''
        expires_at = ''
        
        if access_token and access_token.startswith('eg1~'):
            try:
                import base64
                # Token format: eg1~<jwt>
                jwt_part = access_token[4:]  # Remove 'eg1~'
                # JWT has 3 parts: header.payload.signature
                parts = jwt_part.split('.')
                if len(parts) >= 2:
                    # Decode payload (add padding if needed)
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = base64.urlsafe_b64decode(payload)
                    payload_data = json.loads(decoded)
                    
                    account_id = payload_data.get('sub', '')
                    display_name = payload_data.get('dn', '')
                    exp_timestamp = payload_data.get('exp', 0)
                    if exp_timestamp:
                        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).isoformat()
            except Exception as e:
                self._logger.logger.debug(f"Could not decode token: {e}")
        
        return Session(
            access_token=access_token,
            account_id=account_id,
            display_name=display_name,
            expires_at=expires_at,
            cookies=cookies_dict
        )
    
    def save(self, session: Session) -> bool:
        """Save session to file."""
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            self._logger.logger.info(f"💾 Session saved to: {self.session_file}")
            return True
            
        except Exception as e:
            self._logger.logger.error(f"❌ Error saving session: {e}")
            return False
    
    def clear(self) -> None:
        """Delete saved session."""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                self._logger.logger.info("🗑️ Session cleared")
        except Exception as e:
            self._logger.logger.error(f"❌ Error clearing session: {e}")


# =============================================================================
# Epic Games API Client
# =============================================================================

class EpicAPI:
    """HTTP client for Epic Games APIs."""
    
    # API endpoints
    OAUTH_HOST = 'https://account-public-service-prod.ol.epicgames.com'
    CATALOG_HOST = 'https://catalog-public-service-prod06.ol.epicgames.com'
    STORE_HOST = 'https://store.epicgames.com'
    STORE_GQL = 'https://store.epicgames.com/graphql'
    ENTITLEMENT_HOST = 'https://entitlement-public-service-prod08.ol.epicgames.com'
    ORDER_HOST = 'https://order-processor-prod.ol.epicgames.com'
    
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self._logger = logger
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Configure default request headers."""
        self.session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://store.epicgames.com',
            'Referer': 'https://store.epicgames.com/',
        })
    
    def _basic_auth(self) -> str:
        """Generate Basic auth header from client credentials."""
        import base64
        # For public clients without secret, use just client_id
        if not self.config.client_secret:
            credentials = f"{self.config.client_id}:"
        else:
            credentials = f"{self.config.client_id}:{self.config.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    # -------------------------------------------------------------------------
    # Exchange Code Auth (Alternative to Device Auth)
    # -------------------------------------------------------------------------
    
    def exchange_code_auth(self, exchange_code: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate using an exchange code.
        
        Exchange codes can be obtained from:
        https://www.epicgames.com/id/api/exchange/generate
        (while logged in to epicgames.com)
        """
        url = f"{self.OAUTH_HOST}/account/api/oauth/token"
        
        try:
            response = self.session.post(
                url,
                headers={'Authorization': self._basic_auth()},
                data={
                    'grant_type': 'exchange_code',
                    'exchange_code': exchange_code
                },
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            self._logger.logger.info("✅ Exchange code authentication successful!")
            return response.json()
            
        except Exception as e:
            self._logger.logger.error(f"❌ Exchange code auth failed: {e}")
            return None
    
    # -------------------------------------------------------------------------
    # Device Auth Flow
    # -------------------------------------------------------------------------
    
    def start_device_auth(self) -> Optional[Dict[str, Any]]:
        """
        Start device authorization flow.
        
        Returns device_code, user_code, verification_uri, etc.
        """
        url = f"{self.OAUTH_HOST}/account/api/oauth/deviceAuthorization"
        
        try:
            response = self.session.post(
                url,
                headers={'Authorization': self._basic_auth()},
                data={'prompt': 'login'},
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            self._logger.logger.info("🔑 Device authorization started")
            return data
            
        except Exception as e:
            self._logger.logger.error(f"❌ Device auth start failed: {e}")
            return None
    
    def poll_device_auth(self, device_code: str, interval: int = 5, 
                         max_attempts: int = 60) -> Optional[Dict[str, Any]]:
        """
        Poll for device authorization completion.
        
        Args:
            device_code: The device code from start_device_auth
            interval: Polling interval in seconds
            max_attempts: Maximum polling attempts
        
        Returns:
            Token response or None if failed/expired
        """
        url = f"{self.OAUTH_HOST}/account/api/oauth/token"
        
        for attempt in range(max_attempts):
            try:
                response = self.session.post(
                    url,
                    headers={'Authorization': self._basic_auth()},
                    data={
                        'grant_type': 'device_code',
                        'device_code': device_code
                    },
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    self._logger.logger.info("✅ Device authorization complete!")
                    return response.json()
                
                # Check for pending authorization
                error_data = response.json()
                error_code = error_data.get('errorCode', '')
                
                if 'authorization_pending' in error_code:
                    self._logger.logger.debug(f"⏳ Waiting for authorization... ({attempt + 1}/{max_attempts})")
                    time.sleep(interval)
                    continue
                elif 'slow_down' in error_code:
                    time.sleep(interval * 2)
                    continue
                elif 'expired' in error_code:
                    self._logger.logger.error("❌ Device code expired")
                    return None
                else:
                    self._logger.logger.error(f"❌ Auth error: {error_data}")
                    return None
                    
            except Exception as e:
                self._logger.logger.error(f"❌ Polling error: {e}")
                time.sleep(interval)
        
        self._logger.logger.error("❌ Max polling attempts reached")
        return None
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: The refresh token
        
        Returns:
            New token response or None if failed
        """
        url = f"{self.OAUTH_HOST}/account/api/oauth/token"
        
        try:
            response = self.session.post(
                url,
                headers={'Authorization': self._basic_auth()},
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token
                },
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            self._logger.logger.info("🔄 Token refreshed successfully")
            return response.json()
            
        except Exception as e:
            self._logger.logger.error(f"❌ Token refresh failed: {e}")
            return None
    
    def verify_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify access token and get account info.
        
        Returns account info if valid, None otherwise.
        """
        url = f"{self.OAUTH_HOST}/account/api/oauth/verify"
        
        try:
            response = self.session.get(
                url,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=self.config.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self._logger.logger.debug(f"Token verification failed: {e}")
            return None
    
    # -------------------------------------------------------------------------
    # Catalog / Free Games
    # -------------------------------------------------------------------------
    
    def get_free_games(self, access_token: str, cookies: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        Get current free games from Epic Store.
        
        Uses the catalog API to fetch free promotions.
        """
        # Set cookies if provided
        if cookies:
            for name, value in cookies.items():
                self.session.cookies.set(name, value, domain='.epicgames.com')
        
        # Use catalog API instead of GraphQL
        url = f"{self.CATALOG_HOST}/catalog/api/shared/namespace/epic/bulk/items"
        
        try:
            # Get promoted games
            params = {
                'id': 'freegames',
                'locale': 'pt-BR',
                'country': 'BR',
                'allowCountries': 'BR'
            }
            
            response = self.session.get(
                url,
                params=params,
                headers={
                    'User-Agent': self.config.user_agent,
                    'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3'
                },
                timeout=self.config.timeout
            )
            
            # Try alternative endpoint
            if response.status_code != 200:
                # Use store content endpoint
                store_url = f"{self.STORE_HOST}/api/content/store"
                response = self.session.get(
                    store_url,
                    headers={
                        'User-Agent': self.config.user_agent,
                        'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3'
                    },
                    timeout=self.config.timeout
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Parse free games from response
            free_games = []
            
            # The structure varies, try to extract games
            if isinstance(data, dict):
                # Try different keys that might contain game data
                for key in ['elements', 'items', 'data', 'games']:
                    if key in data and isinstance(data[key], list):
                        for item in data[key]:
                            if self._is_free_game(item):
                                free_games.append(self._parse_game_item(item))
            
            self._logger.logger.info(f"🎮 Found {len(free_games)} free games")
            return free_games
            
        except Exception as e:
            self._logger.logger.error(f"❌ Error fetching free games: {e}")
            return []
    
    def _is_free_game(self, item: Dict[str, Any]) -> bool:
        """Check if an item is a free game."""
        # Look for price information indicating free
        price = item.get('price', {})
        if isinstance(price, dict):
            total_price = price.get('totalPrice', {})
            discount_price = total_price.get('discountPrice', 999999)
            original_price = total_price.get('originalPrice', 999999)
            
            # Free if discount price is 0
            if discount_price == 0:
                return True
        
        # Check promotions
        promotions = item.get('promotions')
        if promotions and isinstance(promotions, dict):
            promo_offers = promotions.get('promotionalOffers', [])
            for promo in promo_offers:
                offers = promo.get('promotionalOffers', [])
                for offer in offers:
                    discount_pct = offer.get('discountSetting', {}).get('discountPercentage', 0)
                    if discount_pct == 0:  # 0 means 100% off
                        return True
        
        return False
    
    def _parse_game_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a game item into standard format."""
        return {
            'title': item.get('title', 'Unknown'),
            'id': item.get('id', ''),
            'namespace': item.get('namespace', ''),
            'slug': item.get('productSlug') or item.get('urlSlug', ''),
            'start_date': '',
            'end_date': ''
        }
    
    def _get_slug(self, game: Dict[str, Any]) -> str:
        """Extract the best slug for a game."""
        # Try catalogNs mappings first
        mappings = game.get('catalogNs', {}).get('mappings', [])
        if mappings:
            return mappings[0].get('pageSlug', '')
        
        # Try offerMappings
        offer_mappings = game.get('offerMappings', [])
        if offer_mappings:
            return offer_mappings[0].get('pageSlug', '')
        
        # Fallback to productSlug or urlSlug
        return game.get('productSlug') or game.get('urlSlug', '')
    
    def get_external_freebies(self) -> List[Dict[str, Any]]:
            $count: Int,
            $country: String!,
            $keywords: String,
            $locale: String,
            $namespace: String,
            $itemNs: String,
            $sortBy: String,
            $sortDir: String,
            $start: Int,
            $tag: String,
            $releaseDate: String,
            $withPrice: Boolean = true,
            $freeGame: Boolean,
            $onSale: Boolean,
            $effectiveDate: String
        ) {
            Catalog {
                searchStore(
                    allowCountries: $allowCountries
                    category: $category
                    count: $count
                    country: $country
                    keywords: $keywords
                    locale: $locale
                    namespace: $namespace
                    itemNs: $itemNs
                    sortBy: $sortBy
                    sortDir: $sortDir
                    start: $start
                    tag: $tag
                    releaseDate: $releaseDate
                    freeGame: $freeGame
                    onSale: $onSale
                    effectiveDate: $effectiveDate
                ) {
                    elements {
                        title
                        id
                        namespace
                        description
                        productSlug
                        urlSlug
                        catalogNs {
                            mappings(pageType: "productHome") {
                                pageSlug
                            }
                        }
                        offerMappings {
                            pageSlug
                        }
                        items {
                            id
                            namespace
                        }
                        promotions(category: $category) @include(if: $withPrice) {
                            promotionalOffers {
                                promotionalOffers {
                                    startDate
                                    endDate
                                    discountSetting {
                                        discountType
                                        discountPercentage
                                    }
                                }
                            }
                            upcomingPromotionalOffers {
                                promotionalOffers {
                                    startDate
                                    endDate
                                    discountSetting {
                                        discountType
                                        discountPercentage
                                    }
                                }
                            }
                        }
                        price(country: $country) @include(if: $withPrice) {
                            totalPrice {
                                discountPrice
                                originalPrice
                                discount
                                currencyCode
                                currencyInfo {
                                    decimals
                                }
                                fmtPrice(locale: $locale) {
                                    originalPrice
                                    discountPrice
                                    intermediatePrice
                                }
                            }
                            lineOffers {
                                appliedRules {
                                    id
                                    endDate
                                }
                            }
                        }
                    }
                    paging {
                        count
                        total
                    }
                }
            }
        }
        """
        
        variables = {
            "allowCountries": "BR",
            "category": "games/edition/base|bundles/games|editors|software/edition/base",
            "count": 40,
            "country": "BR",
            "locale": "pt-BR",
            "sortBy": "releaseDate",
            "sortDir": "DESC",
            "freeGame": True,
            "start": 0,
            "withPrice": True
        }
        
        try:
            response = self.session.post(
                self.STORE_GQL,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': self.config.user_agent,
                    'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3'
                },
                json={'query': query, 'variables': variables},
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
            
            # Filter for currently free games (100% discount)
            free_games = []
            now = datetime.now(timezone.utc)
            
            for game in elements:
                promotions = game.get('promotions')
                if not promotions:
                    continue
                
                # Check current promotional offers
                promo_offers = promotions.get('promotionalOffers', [])
                for promo in promo_offers:
                    for offer in promo.get('promotionalOffers', []):
                        discount = offer.get('discountSetting', {}).get('discountPercentage', 0)
                        if discount == 0:  # 0 means 100% off (free)
                            try:
                                start = datetime.fromisoformat(offer['startDate'].replace('Z', '+00:00'))
                                end = datetime.fromisoformat(offer['endDate'].replace('Z', '+00:00'))
                                if start <= now <= end:
                                    free_games.append({
                                        'title': game['title'],
                                        'id': game['id'],
                                        'namespace': game['namespace'],
                                        'slug': self._get_slug(game),
                                        'start_date': offer['startDate'],
                                        'end_date': offer['endDate']
                                    })
                            except:
                                pass
            
            self._logger.logger.info(f"🎮 Found {len(free_games)} free games")
            return free_games
            
        except Exception as e:
            self._logger.logger.error(f"❌ Error fetching free games: {e}")
            return []
    
    def _get_slug(self, game: Dict[str, Any]) -> str:
        """Extract the best slug for a game."""
        # Try catalogNs mappings first
        mappings = game.get('catalogNs', {}).get('mappings', [])
        if mappings:
            return mappings[0].get('pageSlug', '')
        
        # Try offerMappings
        offer_mappings = game.get('offerMappings', [])
        if offer_mappings:
            return offer_mappings[0].get('pageSlug', '')
        
        # Fallback to productSlug or urlSlug
        return game.get('productSlug') or game.get('urlSlug', '')
    
    def get_external_freebies(self) -> List[Dict[str, Any]]:
        """
        Fetch free games from external API (fallback).
        
        Only used if USE_EXTERNAL_FREEBIES=true.
        """
        if not self.config.use_external_freebies:
            return []
        
        try:
            response = requests.get(
                'https://freegamesepic.onrender.com/api/games',
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            self._logger.logger.info(f"🌐 External API: {len(data.get('currentGames', []))} games")
            return data.get('currentGames', [])
            
        except Exception as e:
            self._logger.logger.warning(f"⚠️ External API failed: {e}")
            return []
    
    # -------------------------------------------------------------------------
    # Entitlements / Ownership
    # -------------------------------------------------------------------------
    
    def get_owned_games(self, access_token: str, account_id: str) -> List[str]:
        """
        Get list of owned game IDs.
        
        Returns list of offer IDs the user already owns.
        """
        url = f"{self.ENTITLEMENT_HOST}/entitlement/api/account/{account_id}/entitlements"
        
        try:
            response = self.session.get(
                url,
                headers={'Authorization': f'Bearer {access_token}'},
                params={'count': 5000},
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            entitlements = response.json()
            owned_ids = [e.get('catalogItemId', '') for e in entitlements]
            
            self._logger.logger.info(f"📚 Found {len(owned_ids)} owned items")
            return owned_ids
            
        except Exception as e:
            self._logger.logger.error(f"❌ Error fetching entitlements: {e}")
            return []
    
    # -------------------------------------------------------------------------
    # Claim / Purchase
    # -------------------------------------------------------------------------
    
    def claim_game(self, access_token: str, account_id: str, 
                   offer_id: str, namespace: str) -> bool:
        """
        Claim a free game.
        
        Args:
            access_token: Valid access token
            account_id: User's account ID
            offer_id: The offer/game ID to claim
            namespace: The game's namespace
        
        Returns:
            True if claimed successfully, False otherwise
        """
        url = f"{self.ORDER_HOST}/api/v1/user/{account_id}/orders"
        
        payload = {
            "offerId": offer_id,
            "namespace": namespace,
            "country": "BR",
            "locale": "pt-BR",
            "eulaId": None,
            "useDefault": True,
            "lineOffers": [
                {
                    "offerId": offer_id,
                    "quantity": 1,
                    "namespace": namespace
                }
            ]
        }
        
        try:
            response = self.session.post(
                url,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                self._logger.logger.info(f"✅ Game claimed successfully!")
                return True
            
            # Handle specific error codes
            if response.status_code == 409:
                self._logger.logger.info("ℹ️ Already owned")
                return True  # Consider already owned as success
            
            if response.status_code == 401:
                self._logger.logger.warning("⚠️ Token expired during claim")
                return False
            
            error_data = response.json() if response.text else {}
            self._logger.logger.error(f"❌ Claim failed: {response.status_code} - {error_data}")
            return False
            
        except Exception as e:
            self._logger.logger.error(f"❌ Claim error: {e}")
            return False


# =============================================================================
# Main Claimer Class
# =============================================================================

class EpicGamesClaimer:
    """Main class for claiming free Epic Games."""
    
    def __init__(self):
        """Initialize the claimer."""
        self._logger = Logger()
        self.config = Config()
        self.api = EpicAPI(self.config, self._logger)
        self.session_store = SessionStore(self.config.session_file, self._logger)
        self.session: Optional[Session] = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Epic Games.
        
        Tries in order:
        1. Load saved session
        2. Refresh if expired
        3. Use fallback cookies from .env
        4. Start device auth flow (only for launcher client)
        """
        # 1. Try to load saved session
        self.session = self.session_store.load()
        
        if self.session and self.session.is_valid():
            self._logger.logger.info(f"🎉 Session valid for: {self.session.display_name}")
            return True
        
        # 2. Try to verify token even if expiration is unknown
        if self.session and self.session.access_token and not self.session.expires_at:
            self._logger.logger.info("🔍 Verifying token...")
            verify_data = self.api.verify_token(self.session.access_token)
            if verify_data:
                # Update session with verified data
                self.session.account_id = verify_data.get('account_id', self.session.account_id)
                self.session.display_name = verify_data.get('displayName', self.session.display_name)
                self.session.expires_at = verify_data.get('expires_at', '')
                self._logger.logger.info(f"✅ Token verified for: {self.session.display_name}")
                self.session_store.save(self.session)
                return True
        
        # 3. Try to refresh
        if self.session and self.session.can_refresh():
            self._logger.logger.info("🔄 Refreshing token...")
            token_data = self.api.refresh_token(self.session.refresh_token)
            
            if token_data:
                self._update_session(token_data)
                self.session_store.save(self.session)
                return True
        
        # 4. Try fallback cookies from .env
        if self.config.fallback_eg1:
            self._logger.logger.info("🔑 Trying fallback credentials from .env...")
            # Verify the fallback token
            verify_data = self.api.verify_token(self.config.fallback_eg1)
            if verify_data:
                self.session = Session(
                    access_token=self.config.fallback_eg1,
                    account_id=verify_data.get('account_id', ''),
                    display_name=verify_data.get('displayName', ''),
                    expires_at=verify_data.get('expires_at', ''),
                )
                self._logger.logger.info(f"✅ Fallback auth successful: {self.session.display_name}")
                return True
            else:
                self._logger.logger.warning("⚠️ Fallback credentials invalid/expired")
        
        # 5. Start device auth flow (only if using launcher client with secret)
        if self.config.client_secret:
            return self._device_auth_flow()
        else:
            self._logger.logger.error("❌ Cannot use device auth with web client. Please provide cookies via .env or browser session.")
            return False
    
    def _device_auth_flow(self) -> bool:
        """Run interactive device authorization flow."""
        self._logger.logger.info("🔐 Starting device authorization...")
        
        # Get device code
        device_data = self.api.start_device_auth()
        if not device_data:
            return False
        
        # Show instructions
        verification_uri = device_data.get('verification_uri_complete')
        user_code = device_data.get('user_code')
        device_code = device_data.get('device_code')
        expires_in = device_data.get('expires_in', 600)
        interval = device_data.get('interval', 5)
        
        print("\n" + "=" * 60)
        print("🔐 EPIC GAMES DEVICE AUTHORIZATION")
        print("=" * 60)
        print(f"\n1. Open this URL in your browser:\n   {verification_uri}")
        print(f"\n2. Enter this code if prompted: {user_code}")
        print(f"\n3. Log in with your Epic Games account")
        print(f"\nWaiting for authorization (expires in {expires_in // 60} minutes)...")
        print("=" * 60 + "\n")
        
        # Try to open browser automatically
        try:
            webbrowser.open(verification_uri)
            self._logger.logger.info("🌐 Browser opened automatically")
        except:
            pass
        
        # Poll for completion
        token_data = self.api.poll_device_auth(
            device_code,
            interval=interval,
            max_attempts=expires_in // interval
        )
        
        if not token_data:
            return False
        
        # Update and save session
        self._update_session(token_data)
        self.session_store.save(self.session)
        
        self._logger.logger.info(f"🎉 Authenticated as: {self.session.display_name}")
        return True
    
    def _update_session(self, token_data: Dict[str, Any]) -> None:
        """Update session from token response."""
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data.get('expires_in', 7200)
        )
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data.get('refresh_expires', 28800)
        )
        
        self.session = Session(
            access_token=token_data.get('access_token', ''),
            refresh_token=token_data.get('refresh_token', ''),
            account_id=token_data.get('account_id', ''),
            display_name=token_data.get('displayName', ''),
            expires_at=expires_at.isoformat(),
            refresh_expires_at=refresh_expires_at.isoformat(),
        )
    
    def get_claimable_games(self) -> List[Dict[str, Any]]:
        """
        Get list of free games that can be claimed.
        
        Filters out already owned games.
        """
        if not self.session:
            return []
        
        # Get free games
        free_games = self.api.get_free_games(
            self.session.access_token,
            self.session.cookies
        )
        
        # Optionally merge with external API
        if self.config.use_external_freebies:
            external = self.api.get_external_freebies()
            # Merge logic here if needed
        
        if not free_games:
            return []
        
        # Get owned games
        owned_ids = self.api.get_owned_games(
            self.session.access_token,
            self.session.account_id
        )
        
        # Filter out already owned
        claimable = []
        for game in free_games:
            if game['id'] not in owned_ids:
                claimable.append(game)
            else:
                self._logger.logger.info(f"ℹ️ Already owned: {game['title']}")
        
        return claimable
    
    def claim_all_games(self) -> Tuple[int, int]:
        """
        Claim all available free games.
        
        Returns:
            Tuple of (claimed_count, failed_count)
        """
        if not self.session:
            self._logger.logger.error("❌ Not authenticated")
            return (0, 0)
        
        claimable = self.get_claimable_games()
        
        if not claimable:
            self._logger.logger.info("ℹ️ No new free games to claim")
            return (0, 0)
        
        self._logger.logger.info(f"🎮 {len(claimable)} games to claim")
        
        claimed = 0
        failed = 0
        
        for game in claimable:
            self._logger.logger.info(f"🎯 Claiming: {game['title']}")
            
            success = self.api.claim_game(
                self.session.access_token,
                self.session.account_id,
                game['id'],
                game['namespace']
            )
            
            if success:
                claimed += 1
            else:
                failed += 1
                
                # Try to refresh token on failure
                if self.session.can_refresh():
                    token_data = self.api.refresh_token(self.session.refresh_token)
                    if token_data:
                        self._update_session(token_data)
                        self.session_store.save(self.session)
            
            # Small delay between claims
            time.sleep(1)
        
        return (claimed, failed)
    
    def save_next_games(self) -> None:
        """Save information about upcoming free games."""
        if not self.session:
            return
        
        # Get all games including upcoming
        # This would need a separate query for upcoming games
        # For now, we save current free games info
        
        free_games = self.api.get_free_games(
            self.session.access_token,
            self.session.cookies
        )
        
        data = {
            'current_games': free_games,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            output_path = self.config.data_dir / 'next_games.json'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self._logger.logger.info(f"📝 Games info saved to: {output_path}")
            
        except Exception as e:
            self._logger.logger.error(f"❌ Error saving games info: {e}")
    
    def run(self) -> None:
        """Main execution flow."""
        print("\n" + "=" * 60)
        print("🎮 EPIC GAMES FREE CLAIMER (HTTP-only)")
        print("=" * 60 + "\n")
        
        # Authenticate
        if not self.authenticate():
            self._logger.logger.error("❌ Authentication failed")
            return
        
        # Claim games
        claimed, failed = self.claim_all_games()
        
        # Save games info
        self.save_next_games()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"  ✅ Claimed: {claimed}")
        print(f"  ❌ Failed:  {failed}")
        print("=" * 60 + "\n")


# =============================================================================
# Entry Point
# =============================================================================

def main() -> None:
    """Main entry point."""
    claimer = EpicGamesClaimer()
    claimer.run()


if __name__ == "__main__":
    main()
