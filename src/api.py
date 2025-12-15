# -*- coding: utf-8 -*-
"""
Epic Games API Client.

HTTP client for Epic Games services:
- OAuth authentication (device auth, token refresh)
- Catalog/Store API (free games discovery)
- Entitlements API (owned games)
- Order API (claiming free games)
"""

import base64
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import requests

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    cloudscraper = None  # type: ignore
    CLOUDSCRAPER_AVAILABLE = False

from .config import Config
from .logger import Logger


class EpicAPI:
    """HTTP client for Epic Games APIs with enhanced logging."""
    
    # API endpoints
    OAUTH_HOST = 'https://account-public-service-prod.ol.epicgames.com'
    CATALOG_HOST = 'https://catalog-public-service-prod06.ol.epicgames.com'
    STORE_HOST = 'https://store.epicgames.com'
    STORE_GQL = 'https://store.epicgames.com/graphql'
    ENTITLEMENT_HOST = 'https://entitlement-public-service-prod08.ol.epicgames.com'
    ORDER_HOST = 'https://order-processor-prod.ol.epicgames.com'
    
    def __init__(self, config: Config, logger: Logger):
        """
        Initialize API client.
        
        Args:
            config: Application configuration.
            logger: Logger instance.
        """
        self.config = config
        self._logger = logger
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Configure default request headers."""
        self.session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': f'{self.config.locale},{self.config.locale.split("-")[0]};q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://store.epicgames.com',
            'Referer': 'https://store.epicgames.com/',
        })
    
    def _basic_auth(self) -> str:
        """Generate Basic auth header from client credentials."""
        if not self.config.client_secret:
            credentials = f"{self.config.client_id}:"
        else:
            credentials = f"{self.config.client_id}:{self.config.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    # =========================================================================
    # Authentication
    # =========================================================================
    
    def start_device_auth(self) -> Optional[Dict[str, Any]]:
        """
        Start device authorization flow.
        
        Returns:
            Dictionary with device_code, user_code, verification_uri, etc.
            None if failed.
        """
        url = f"{self.OAUTH_HOST}/account/api/oauth/deviceAuthorization"
        
        self._logger.debug("Starting device authorization", endpoint=url)
        
        try:
            response = self.session.post(
                url,
                headers={'Authorization': self._basic_auth()},
                data={'prompt': 'login'},
                timeout=self.config.timeout
            )
            
            self._logger.network('POST', url, status=response.status_code)
            response.raise_for_status()
            
            data = response.json()
            self._logger.auth("Device authorization initiated")
            return data
            
        except requests.RequestException as e:
            self._logger.error(
                "Device auth start failed",
                exc=e,
                status=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            )
            return None
    
    def poll_device_auth(
        self,
        device_code: str,
        interval: int = 5,
        max_attempts: int = 60
    ) -> Optional[Dict[str, Any]]:
        """
        Poll for device authorization completion.
        
        Args:
            device_code: The device code from start_device_auth.
            interval: Polling interval in seconds.
            max_attempts: Maximum polling attempts.
        
        Returns:
            Token response or None if failed/expired.
        """
        url = f"{self.OAUTH_HOST}/account/api/oauth/token"
        
        for attempt in range(1, max_attempts + 1):
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
                    self._logger.auth("Device authorization completed", attempt=attempt)
                    return response.json()
                
                # Handle pending/error states
                error_data = response.json()
                error_code = error_data.get('errorCode', '')
                
                if 'authorization_pending' in error_code:
                    self._logger.debug(
                        f"Waiting for authorization...",
                        attempt=f"{attempt}/{max_attempts}"
                    )
                    time.sleep(interval)
                    continue
                    
                elif 'slow_down' in error_code:
                    self._logger.debug("Rate limited, slowing down")
                    time.sleep(interval * 2)
                    continue
                    
                elif 'expired' in error_code:
                    self._logger.error("Device code expired")
                    return None
                    
                else:
                    self._logger.error(
                        "Device auth error",
                        error_code=error_code,
                        error_msg=error_data.get('errorMessage', '')
                    )
                    return None
                    
            except requests.RequestException as e:
                self._logger.error("Polling error", exc=e, attempt=attempt)
                time.sleep(interval)
        
        self._logger.error("Max polling attempts reached")
        return None
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: The refresh token.
        
        Returns:
            New token response or None if failed.
        """
        url = f"{self.OAUTH_HOST}/account/api/oauth/token"
        
        self._logger.debug("Refreshing access token")
        
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
            
            self._logger.network('POST', url, status=response.status_code)
            response.raise_for_status()
            
            self._logger.auth("Token refreshed successfully")
            return response.json()
            
        except requests.RequestException as e:
            self._logger.error(
                "Token refresh failed",
                exc=e,
                status=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            )
            return None
    
    def verify_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify access token and get account info.
        
        Args:
            access_token: Token to verify.
        
        Returns:
            Account info if valid, None otherwise.
        """
        url = f"{self.OAUTH_HOST}/account/api/oauth/verify"
        
        try:
            response = self.session.get(
                url,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=self.config.timeout
            )
            
            self._logger.network('GET', url, status=response.status_code)
            
            if response.status_code == 200:
                data = response.json()
                self._logger.debug(
                    "Token verified",
                    account=data.get('displayName'),
                    account_id=data.get('account_id', '')[:8] + '...'
                )
                return data
            
            return None
            
        except requests.RequestException as e:
            self._logger.debug(f"Token verification failed: {e}")
            return None
    
    # =========================================================================
    # Free Games Discovery
    # =========================================================================
    
    def get_free_games(
        self,
        access_token: str,
        cookies: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get current free games from Epic Store using GraphQL.
        
        Tenta múltiplos métodos para contornar Cloudflare:
        1. requests regular + CF_CLEARANCE cookie
        2. cloudscraper (automático)
        3. API alternativa
        
        Args:
            access_token: Valid access token.
            cookies: Optional cookies for web requests.
        
        Returns:
            List of free game dictionaries.
        """
        self._logger.info("Fetching free games from Epic Store...")
        
        # GraphQL query
        query = """
        query searchStoreQuery(
            $allowCountries: String,
            $category: String,
            $count: Int,
            $country: String!,
            $locale: String,
            $namespace: String,
            $sortBy: String,
            $sortDir: String,
            $start: Int,
            $freeGame: Boolean,
            $withPrice: Boolean = true
        ) {
            Catalog {
                searchStore(
                    allowCountries: $allowCountries
                    category: $category
                    count: $count
                    country: $country
                    locale: $locale
                    namespace: $namespace
                    sortBy: $sortBy
                    sortDir: $sortDir
                    start: $start
                    freeGame: $freeGame
                ) {
                    elements {
                        title
                        id
                        namespace
                        productSlug
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
                                        discountPercentage
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            "allowCountries": self.config.country,
            "category": "games/edition/base|bundles/games",
            "count": 40,
            "country": self.config.country,
            "locale": self.config.locale,
            "sortBy": "releaseDate",
            "sortDir": "DESC",
            "freeGame": True,
            "start": 0,
            "withPrice": True
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Authorization': f'Bearer {access_token}',
            'Origin': 'https://store.epicgames.com',
            'Referer': 'https://store.epicgames.com/',
        }
        
        # ===== MÉTODO 1: CF_CLEARANCE Cookie =====
        if self.config.cf_clearance:
            self._logger.debug("Tentando Método 1: CF_CLEARANCE cookie...")
            try:
                session = requests.Session()
                session.cookies.set('cf_clearance', self.config.cf_clearance, domain='.store.epicgames.com')
                session.headers.update(headers)
                
                response = session.post(
                    self.STORE_GQL,
                    json={'query': query, 'variables': variables},
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and 'errors' not in data:
                        self._logger.debug("✅ CF_CLEARANCE funcionou!")
                        return self._parse_free_games(data)
            except Exception as e:
                self._logger.debug(f"CF_CLEARANCE falhou: {e}")
        
        # ===== MÉTODO 2: cloudscraper =====
        if CLOUDSCRAPER_AVAILABLE:
            self._logger.debug("Tentando Método 2: cloudscraper (contorna Cloudflare)...")
            try:
                # cloudscraper is available here; hint to type checker
                assert cloudscraper is not None
                scraper = cloudscraper.create_scraper()
                scraper.headers.update(headers)
                
                response = scraper.post(
                    self.STORE_GQL,
                    json={'query': query, 'variables': variables},
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Verificar se há erros de permissão
                    if 'errors' in data and data['errors']:
                        error_msg = str(data['errors'][0].get('message', ''))
                        if 'permission' in error_msg.lower():
                            self._logger.debug("Token sem permissão para acessar promotions")
                        else:
                            self._logger.debug(f"GraphQL error: {error_msg}")
                    elif 'data' in data:
                        result = self._parse_free_games(data)
                        if result:
                            self._logger.success("✅ cloudscraper contornou Cloudflare!")
                            return result
            except Exception as e:
                self._logger.debug(f"cloudscraper falhou: {e}")
        
        # ===== MÉTODO 3: API alternativa =====
        self._logger.debug("Tentando Método 3: API alternativa...")
        return self.get_external_freebies()
    
    def _parse_free_games(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse GraphQL response and extract free games.
        
        Args:
            data: GraphQL response data
        
        Returns:
            List of free games
        """
        free_games = []
        now = datetime.now(timezone.utc)
        
        try:
            elements = (
                data.get('data', {})
                .get('Catalog', {})
                .get('searchStore', {})
                .get('elements', [])
            )
            
            for game in elements:
                promotions = game.get('promotions', {})
                if not promotions:
                    continue
                
                for promo in promotions.get('promotionalOffers', []):
                    for offer in promo.get('promotionalOffers', []):
                        discount = offer.get('discountSetting', {}).get('discountPercentage', 0)
                        
                        if discount == 0:
                            try:
                                start = datetime.fromisoformat(
                                    offer['startDate'].replace('Z', '+00:00')
                                )
                                end = datetime.fromisoformat(
                                    offer['endDate'].replace('Z', '+00:00')
                                )
                                
                                if start <= now <= end:
                                    game_info = {
                                        'title': game['title'],
                                        'id': game['id'],
                                        'namespace': game['namespace'],
                                        'slug': game.get('productSlug', ''),
                                    }
                                    free_games.append(game_info)
                                    self._logger.game("Free game found", game['title'], id=game['id'][:8])
                            except (KeyError, ValueError):
                                pass
            
            self._logger.success(f"Found {len(free_games)} free games")
            return free_games
            
        except Exception as e:
            self._logger.error("Error parsing GraphQL response", exc=e)
            return []
    
    def _get_slug(self, game: Dict[str, Any]) -> str:
        """
        Extract the best slug for a game URL.
        
        Args:
            game: Game data dictionary.
        
        Returns:
            Slug string for the game.
        """
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
        Fetch free games from external API (freegamesepic.onrender.com).
        
        Since EPIC_EG1 tokens don't have permission to access promotions,
        we use a public API that tracks free games.
        
        Returns:
            List of free game dictionaries.
        """
        self._logger.debug("Buscando jogos grátis via API externa...")
        
        try:
            # Use reliable external API with proper validation
            response = requests.get(
                'https://freegamesepic.onrender.com/api/games',
                timeout=self.config.timeout,
                verify=True  # Validate SSL certificate
            )
            
            self._logger.network(
                'GET',
                'freegamesepic.onrender.com/api/games',
                status=response.status_code
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                if not isinstance(data, dict):
                    self._logger.warning("External API returned invalid structure (not dict)")
                    return []
                
                games = data.get('currentGames', [])
                
                # Validate games list
                if not isinstance(games, list):
                    self._logger.warning("External API games list is invalid")
                    return []
                
                if games:
                    self._logger.success(f"External API returned {len(games)} games")
                    
                    free_games = []
                    for game in games:
                        # Validate game structure
                        if not isinstance(game, dict):
                            self._logger.debug("Skipping invalid game entry (not dict)")
                            continue
                        
                        game_info = {
                            'title': game.get('title', 'Unknown'),
                            'id': game.get('id', ''),
                            'namespace': game.get('namespace', ''),
                            'slug': game.get('slug', ''),
                        }
                        free_games.append(game_info)
                        self._logger.game("Free game found", game_info['title'], id=game_info['id'][:8] if game_info['id'] else 'N/A')
                    
                    return free_games
            
            return []
            
        except requests.RequestException as e:
            self._logger.warning("Erro ao buscar API externa", exc=e)
            return []
    
    # =========================================================================
    # Entitlements (Owned Games)
    # =========================================================================
    
    def get_owned_games(self, access_token: str, account_id: str) -> List[str]:
        """
        Get list of owned game IDs.
        
        Args:
            access_token: Valid access token.
            account_id: User's account ID.
        
        Returns:
            List of catalog item IDs the user owns.
        """
        url = f"{self.ENTITLEMENT_HOST}/entitlement/api/account/{account_id}/entitlements"
        
        self._logger.debug("Fetching owned games/entitlements...")
        
        try:
            response = self.session.get(
                url,
                headers={'Authorization': f'Bearer {access_token}'},
                params={'count': 5000},
                timeout=self.config.timeout
            )
            
            self._logger.network('GET', url, status=response.status_code)
            response.raise_for_status()
            
            entitlements = response.json()
            owned_ids = [e.get('catalogItemId', '') for e in entitlements if e.get('catalogItemId')]
            
            self._logger.debug(f"Found {len(owned_ids)} owned items")
            return owned_ids
            
        except requests.RequestException as e:
            self._logger.error(
                "Error fetching entitlements",
                exc=e,
                account_id=account_id[:8] + '...'
            )
            return []
    
    # =========================================================================
    # Claim / Purchase
    # =========================================================================
    
    def claim_game(
        self,
        access_token: str,
        account_id: str,
        offer_id: str,
        namespace: str,
        title: str = "Unknown"
    ) -> bool:
        """
        Claim a free game.
        
        Args:
            access_token: Valid access token.
            account_id: User's account ID.
            offer_id: The offer/game ID to claim.
            namespace: The game's namespace.
            title: Game title for logging.
        
        Returns:
            True if claimed successfully (or already owned).
        """
        url = f"{self.ORDER_HOST}/api/v1/user/{account_id}/orders"
        
        self._logger.game("Attempting to claim", title, offer_id=offer_id[:8] + '...')
        
        payload = {
            "offerId": offer_id,
            "namespace": namespace,
            "country": self.config.country,
            "locale": self.config.locale,
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
            
            self._logger.network('POST', url, status=response.status_code)
            
            if response.status_code == 200:
                self._logger.success(f"Game claimed: {title}")
                return True
            
            # Already owned (409 Conflict)
            if response.status_code == 409:
                self._logger.info(f"Already owned: {title}")
                return True  # Not a failure
            
            # Token expired
            if response.status_code == 401:
                self._logger.warning("Token expired during claim", game=title)
                return False
            
            # Other errors
            error_data = response.json() if response.text else {}
            self._logger.error(
                f"Claim failed for: {title}",
                status=response.status_code,
                error=error_data.get('errorCode', 'unknown'),
                error_msg=error_data.get('errorMessage', '')
            )
            return False
            
        except requests.RequestException as e:
            self._logger.error(f"Claim error for: {title}", exc=e)
            return False
