#!/usr/bin/env python3
"""
Solução Alternativa: Usar Playwright para contornar Cloudflare automaticamente
Sem necessidade de extrair CF_CLEARANCE cookie
"""

import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def check_playwright_version():
    """Check if playwright is properly installed"""
    try:
        import playwright
        from packaging import version
        print("✅ Playwright está instalado")
        return True
    except ImportError:
        print("❌ Playwright não está instalado")
        return False

def create_graphql_fetcher():
    """Create a modified api.py that uses Playwright for GraphQL requests"""
    
    content = """#!/usr/bin/env python3
\"\"\"
API Module com suporte a Playwright para contornar Cloudflare
\"\"\"

import asyncio
import json
from typing import List, Dict, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from . import logger, config

try:
    from playwright.async_api import async_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

class PlaywrightGraphQLFetcher:
    \"\"\"Fetch free games using Playwright to bypass Cloudflare\"\"\"
    
    STORE_URL = 'https://store.epicgames.com'
    STORE_GQL = f'{STORE_URL}/graphql'
    
    def __init__(self, cfg: config.Config, log: logger.Logger):
        self.config = cfg
        self._logger = log
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright não instalado. Instale com: pip install playwright")
    
    async def get_free_games(self, access_token: str) -> List[Dict]:
        \"\"\"Fetch free games using Playwright browser\"\"\"
        
        self._logger.info("Iniciando Playwright para contornar Cloudflare...")
        
        try:
            async with async_playwright() as p:
                # Launch headless browser
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 720}
                )
                page = await context.new_page()
                
                # Navigate to store
                await page.goto(self.STORE_URL, wait_until='networkidle')
                
                # Set auth header via JavaScript
                await page.evaluate(f'''
                    window.AUTH_TOKEN = '{access_token}';
                ''')
                
                # Make GraphQL request via page.evaluate
                query = \"\"\"
                query searchStoreQuery(
                    $country: String!,
                    $locale: String,
                    $count: Int,
                    $freeGame: Boolean
                ) {{
                    Catalog {{
                        searchStore(
                            country: $country
                            locale: $locale
                            count: $count
                            freeGame: $freeGame
                        ) {{
                            elements {{
                                title
                                id
                                namespace
                                productSlug
                                items {{ id namespace }}
                                promotions {{
                                    promotionalOffers {{
                                        promotionalOffers {{
                                            discountSetting {{ discountPercentage }}
                                            startDate
                                            endDate
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
                \"\"\"
                
                variables = {{
                    'country': self.config.country,
                    'locale': self.config.locale,
                    'count': 100,
                    'freeGame': True
                }}
                
                result = await page.evaluate(f'''
                    async () => {{
                        const response = await fetch('{self.STORE_GQL}', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                                'Authorization': 'Bearer ' + window.AUTH_TOKEN
                            }},
                            body: JSON.stringify({{
                                query: `{query}`,
                                variables: {json.dumps(variables)}
                            }})
                        }});
                        return await response.json();
                    }}
                ''')
                
                await browser.close()
                
                # Process result
                if 'errors' in result:
                    self._logger.error(f"GraphQL error: {result['errors']}")
                    return []
                
                elements = (
                    result.get('data', {})
                    .get('Catalog', {})
                    .get('searchStore', {})
                    .get('elements', [])
                )
                
                # Filter for free games
                free_games = []
                now = datetime.now(timezone.utc)
                
                for game in elements:
                    promos = game.get('promotions', {}).get('promotionalOffers', [])
                    for promo in promos:
                        for offer in promo.get('promotionalOffers', []):
                            discount = offer.get('discountSetting', {}).get('discountPercentage')
                            if discount == 100:  # Free
                                start = datetime.fromisoformat(offer['startDate'].replace('Z', '+00:00'))
                                end = datetime.fromisoformat(offer['endDate'].replace('Z', '+00:00'))
                                
                                if start <= now <= end:
                                    free_games.append({{
                                        'title': game['title'],
                                        'id': game['id'],
                                        'namespace': game.get('namespace', ''),
                                        'productSlug': game.get('productSlug', ''),
                                        'offerType': 'game'
                                    }})
                
                return free_games
        
        except Exception as e:
            self._logger.error(f"Erro com Playwright: {e}")
            return []
"""
    return content

def main():
    print("=" * 80)
    print("🎯 CONFIGURAR SUPORTE A PLAYWRIGHT")
    print("=" * 80)
    
    if not check_playwright_version():
        print("\n📝 Playwright será instalado automaticamente")
        import subprocess
        subprocess.run(['pip', 'install', 'playwright'], check=True)
        print("\n📥 Baixando navegadores...")
        subprocess.run(['python', '-m', 'playwright', 'install', 'chromium'], check=True)
    
    print("\n" + "=" * 80)
    print("✅ CONFIGURAÇÃO CONCLUÍDA")
    print("=" * 80)
    print("""
Próximos passos:

1. Edite src/api.py e importe PlaywrightGraphQLFetcher
2. Modifique get_free_games() para usar Playwright quando CF_CLEARANCE falhar:

    async def get_free_games(self, access_token: str):
        # Tentar com CF_CLEARANCE primeiro
        if self.config.cf_clearance:
            result = await self._get_games_with_cf(access_token)
            if result: return result
        
        # Fallback: usar Playwright
        fetcher = PlaywrightGraphQLFetcher(self.config, self._logger)
        return await fetcher.get_free_games(access_token)

3. Execute: python main.py
""")

if __name__ == '__main__':
    main()
