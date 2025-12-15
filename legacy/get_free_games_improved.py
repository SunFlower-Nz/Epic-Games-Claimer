#!/usr/bin/env python3
"""
Versão melhorada de get_free_games com fallback para cloudscraper
Copie esta função para substituir a atual em src/api.py
"""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

def get_free_games_improved(
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
        self._logger.debug("Tentando Método 2: cloudscraper...")
        try:
            scraper = cloudscraper.create_scraper()
            scraper.headers.update(headers)
            
            response = scraper.post(
                self.STORE_GQL,
                json={'query': query, 'variables': variables},
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'errors' not in data:
                    self._logger.success("✅ cloudscraper contornou Cloudflare!")
                    # Extrair e salvar novo CF_CLEARANCE para próximas execuções
                    if 'cf_clearance' in scraper.cookies:
                        new_cookie = scraper.cookies.get('cf_clearance')
                        # Atualizar .env
                        self._logger.info(f"💾 Novo CF_CLEARANCE obtido: {new_cookie[:50]}...")
                    return self._parse_free_games(data)
        except Exception as e:
            self._logger.debug(f"cloudscraper falhou: {e}")
    else:
        self._logger.debug("cloudscraper não está instalado")
    
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
