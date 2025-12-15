#!/usr/bin/env python3
"""Debug CloudScraper response"""

import json
import os
from dotenv import load_dotenv

load_dotenv()

try:
    import cloudscraper
    print("✅ cloudscraper está disponível")
except ImportError:
    print("❌ cloudscraper não instalado")
    exit(1)

eg1 = os.getenv('EPIC_EG1')
if not eg1:
    print("❌ EPIC_EG1 não definido")
    exit(1)

print("=" * 80)
print("🔍 DEBUG CLOUDFLARE + GraphQL COM CLOUDSCRAPER")
print("=" * 80)

scraper = cloudscraper.create_scraper()

query = """
query searchStoreQuery(
    $country: String!,
    $locale: String,
    $count: Int,
    $freeGame: Boolean
) {
    Catalog {
        searchStore(
            country: $country
            locale: $locale
            count: $count
            freeGame: $freeGame
        ) {
            elements {
                title
                id
                namespace
                productSlug
                promotions {
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
    'country': 'BR',
    'locale': 'pt-BR',
    'count': 100,
    'freeGame': True
}

print("\n📡 Enviando requisição com cloudscraper...")

try:
    response = scraper.post(
        'https://store.epicgames.com/graphql',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {eg1}',
            'Origin': 'https://store.epicgames.com',
            'Referer': 'https://store.epicgames.com/',
        },
        json={'query': query, 'variables': variables},
        timeout=15
    )
    
    print(f"\n🔸 Status Code: {response.status_code}")
    print(f"🔸 Content-Type: {response.headers.get('Content-Type')}")
    
    if response.status_code == 200:
        data = response.json()
        
        if 'errors' in data:
            print(f"\n❌ GraphQL Errors:")
            print(json.dumps(data['errors'], indent=2))
        
        if 'data' in data:
            catalog = data['data'].get('Catalog', {})
            search = catalog.get('searchStore', {})
            elements = search.get('elements', [])
            
            print(f"\n✅ Found {len(elements)} games")
            
            if elements:
                print("\n📋 Games list:")
                for game in elements[:5]:  # Show first 5
                    print(f"  - {game['title']} (id={game['id'][:8]}...)")
                    
                    # Check promotions
                    promos = game.get('promotions', {}).get('promotionalOffers', [])
                    if promos:
                        for promo in promos:
                            for offer in promo.get('promotionalOffers', []):
                                discount = offer.get('discountSetting', {}).get('discountPercentage')
                                start = offer.get('startDate')
                                end = offer.get('endDate')
                                print(f"      Promo: {discount}% off [{start} → {end}]")
            else:
                print("\n⚠️  No games in response!")
                print(f"\nFull response (first 1000 chars):")
                print(json.dumps(data, indent=2)[:1000])
    else:
        print(f"\n❌ Status {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
