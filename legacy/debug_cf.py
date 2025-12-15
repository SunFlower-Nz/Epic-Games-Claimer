#!/usr/bin/env python3
"""Debug CF_CLEARANCE cookie handling"""

import os
from dotenv import load_dotenv
import requests

load_dotenv()

cf_clearance = os.getenv('CF_CLEARANCE')
eg1_token = os.getenv('EPIC_EG1')

print("=" * 80)
print("🔍 CF_CLEARANCE DEBUG")
print("=" * 80)
print(f"\n✓ CF_CLEARANCE value: {cf_clearance[:50]}..." if cf_clearance else "✗ CF_CLEARANCE is empty")
print(f"✓ EPIC_EG1 value: {eg1_token[:50]}..." if eg1_token else "✗ EPIC_EG1 is empty")

# Test request
session = requests.Session()
session.cookies.set('cf_clearance', cf_clearance, domain='.store.epicgames.com')

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
            }
        }
    }
}
"""

print("\n" + "=" * 80)
print("📡 Sending GraphQL Request...")
print("=" * 80)

try:
    response = session.post(
        'https://store.epicgames.com/graphql',
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0',
            'Authorization': f'Bearer {eg1_token}',
        },
        json={
            'query': query,
            'variables': {
                'country': 'BR',
                'locale': 'pt-BR',
                'count': 10,
                'freeGame': True
            }
        },
        timeout=10
    )
    
    print(f"\n🔸 Status Code: {response.status_code}")
    print(f"🔸 Response Headers:")
    for k, v in response.headers.items():
        print(f"   {k}: {v}")
    
    print(f"\n🔸 Response Body (first 500 chars):")
    print(response.text[:500])
    
    # Try to parse JSON
    try:
        data = response.json()
        print(f"\n✓ Valid JSON Response")
        if 'data' in data:
            print(f"✓ Has 'data' key")
        if 'errors' in data:
            print(f"✗ Has 'errors' key: {data['errors']}")
    except:
        print(f"\n✗ Not JSON (likely HTML error page from Cloudflare)")
        
except Exception as e:
    print(f"\n✗ Request failed: {e}")

print("\n" + "=" * 80)
