#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script for GraphQL free games query.
Shows the exact error from Epic Games API.
"""

import requests
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.session_store import SessionStore
from src.logger import Logger

def debug_free_games():
    """Debug free games GraphQL query."""
    
    print("\n" + "=" * 70)
    print("🔍 DEBUG: Buscando Jogos Grátis")
    print("=" * 70 + "\n")
    
    # Load config and session
    config = Config()
    logger = Logger(config.log_base_dir)
    session_store = SessionStore(config, logger)
    session = session_store.load()
    
    if not session:
        print("❌ Sessão não carregada! Tentando token do .env...")
        # Try loading from EPIC_EG1
        import os
        eg1_token = os.getenv('EPIC_EG1', '')
        if eg1_token:
            from src.session_store import Session
            session = Session.from_eg1_token(eg1_token)
            if session:
                print(f"✅ Sessão carregada do .env: {session.display_name}")
            else:
                print("❌ Token do .env inválido!")
                return
        else:
            print("❌ Nenhum token disponível!")
            return
    
    print(f"✅ Sessão carregada: {session.display_name}")
    print(f"   Account ID: {session.account_id}")
    print(f"   Token válido\n")
    
    # GraphQL query (same as in api.py)
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
                            fmtPrice(locale: $locale) {
                                originalPrice
                                discountPrice
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
        "allowCountries": config.country,
        "category": "games/edition/base|bundles/games|editors|software/edition/base",
        "count": 40,
        "country": config.country,
        "locale": config.locale,
        "sortBy": "releaseDate",
        "sortDir": "DESC",
        "freeGame": True,
        "start": 0,
        "withPrice": True
    }
    
    print(f"📝 Configuração:")
    print(f"   Country: {config.country}")
    print(f"   Locale: {config.locale}")
    print(f"   Client ID: {config.client_id[:20]}...")
    print()
    
    # Make request
    req_session = requests.Session()
    req_session.headers.update({
        'User-Agent': config.user_agent,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': f'{config.locale},{config.locale.split("-")[0]};q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://store.epicgames.com',
        'Referer': 'https://store.epicgames.com/',
    })
    
    print("📡 Enviando requisição GraphQL...")
    print(f"   URL: https://store.epicgames.com/graphql")
    print()
    
    try:
        response = req_session.post(
            'https://store.epicgames.com/graphql',
            headers={
                'Content-Type': 'application/json',
                'User-Agent': config.user_agent,
            },
            json={'query': query, 'variables': variables},
            timeout=config.timeout
        )
        
        print(f"📥 Resposta recebida:")
        print(f"   Status: {response.status_code}")
        print()
        
        # Parse response
        try:
            data = response.json()
            
            # Check for GraphQL errors
            if 'errors' in data:
                print("❌ ERRO GraphQL:")
                for error in data['errors']:
                    print(f"   - {error.get('message', 'Unknown error')}")
                    if 'extensions' in error:
                        print(f"     Details: {error['extensions']}")
                print()
            
            # Check data
            if 'data' in data:
                catalog = data.get('data', {}).get('Catalog')
                if catalog:
                    elements = catalog.get('searchStore', {}).get('elements', [])
                    paging = catalog.get('searchStore', {}).get('paging', {})
                    
                    print(f"✅ SUCESSO:")
                    print(f"   Jogos encontrados: {len(elements)}")
                    print(f"   Total na API: {paging.get('total', '?')}")
                    print()
                    
                    if elements:
                        print("📋 Primeiros 3 jogos:")
                        for game in elements[:3]:
                            print(f"   - {game.get('title')}")
                            promos = game.get('promotions', {})
                            if promos:
                                offers = promos.get('promotionalOffers', [])
                                print(f"     Promoções: {len(offers)} encontradas")
                    else:
                        print("   (Nenhum jogo retornado)")
                else:
                    print("❌ Resposta vazia ou sem Catalog")
            
            # Pretty print full response
            print("\n" + "-" * 70)
            print("📄 RESPOSTA COMPLETA (JSON):")
            print("-" * 70)
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
            if len(json.dumps(data)) > 2000:
                print("\n... (truncado, veja acima) ...")
            
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao fazer parse JSON: {e}")
            print(f"   Conteúdo: {response.text[:500]}")
    
    except requests.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status: {e.response.status_code}")
            print(f"   Conteúdo: {e.response.text[:500]}")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == '__main__':
    debug_free_games()
