#!/usr/bin/env python
"""Test with extended wait and proper headers."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from playwright.sync_api import sync_playwright


try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None

print("Test 1: With extended wait and proper headers...")
print()

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",  # Disable security features that block automation
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )

    context = browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="pt-BR",  # Set locale
        timezone_id="America/Sao_Paulo",  # Set timezone
    )
    page = context.new_page()

    # Set extra headers
    page.set_extra_http_headers(
        {
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
    )

    if stealth_sync:
        stealth_sync(page)

    try:
        print("Navigating...")
        page.goto("https://store.epicgames.com/en-US/free-games", wait_until="load", timeout=60000)

        # Wait longer
        print("Waiting 10 seconds for Cloudflare challenge...")
        page.wait_for_timeout(10000)

        title = page.title()
        print(f"Title: {title}")

        # Check for "Just a moment"
        if "moment" in title.lower():
            print("❌ Still on Cloudflare challenge page")
        else:
            print("✅ Passed Cloudflare!")

            # Extract content
            html = page.content()
            if '"title"' in html:
                print("✅ Found JSON data")
                import re

                titles = re.findall(r'"title":"([^"]{5,100})"', html)
                print(f"Found {len(titles)} titles")
                for t in titles[:3]:
                    print(f"  • {t}")
            else:
                print("⚠️ No JSON titles found")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()

print("\n" + "=" * 60)
print("Test 2: Check if pyppeteer is available...")
print("=" * 60)

try:
    import pyppeteer  # noqa: F401

    print("✅ pyppeteer is installed!")
except ImportError:
    print("❌ pyppeteer not installed - might have better CF bypass")
