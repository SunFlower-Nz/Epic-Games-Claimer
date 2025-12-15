#!/usr/bin/env python
"""Test browser-cookie3 extraction."""

import browser_cookie3

print("Testing browser-cookie3 extraction...")

try:
    cj = browser_cookie3.chrome(domain_name='.epicgames.com')
    print(f"\nCookies found for .epicgames.com:")
    for c in cj:
        val = c.value[:40] + "..." if c.value and len(c.value) > 40 else c.value
        print(f"  {c.name}: {val}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
