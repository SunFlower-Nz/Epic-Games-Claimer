"""
Epic Games API Client.

HTTP client for Epic Games services:
- OAuth authentication (device auth, token refresh)
- Catalog/Store API (free games discovery)
- Entitlements API (owned games)
- Browser-based claiming (via BrowserManager)
"""

import base64
import contextlib
import time
from datetime import datetime, timezone
from typing import Any

import requests

from .browser import BrowserManager
from .config import Config
from .logger import Logger
from .models import (
    ALREADY_OWNED_PATTERNS,
    CAPTCHA_KEYWORDS,
    CAPTCHA_SELECTORS,
    CHECKOUT_SELECTORS,
    CLAIM_BUTTON_SELECTORS,
    RATE_LIMIT_PATTERNS,
    SUCCESS_PATTERNS,
    ClaimStatus,
)


class EpicAPI:
    """HTTP client for Epic Games APIs with enhanced logging."""

    # API endpoints
    OAUTH_HOST = "https://account-public-service-prod.ol.epicgames.com"
    CATALOG_HOST = "https://catalog-public-service-prod06.ol.epicgames.com"
    ENTITLEMENT_HOST = "https://entitlement-public-service-prod08.ol.epicgames.com"
    FREE_GAMES_API = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
    EXTERNAL_FREE_GAMES_API = "https://freegamesepic.onrender.com/api/games"

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
        self.session.headers.update(
            {
                "User-Agent": self.config.user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": f"{self.config.locale},{self.config.locale.split('-')[0]};q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://store.epicgames.com",
                "Referer": "https://store.epicgames.com/",
            }
        )

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

    def start_device_auth(self) -> dict[str, Any] | None:
        """
        Start device authorization flow.

        First obtains a client_credentials token, then uses it to
        initiate device authorization.

        Returns:
            Dictionary with device_code, user_code, verification_uri, etc.
            None if failed.
        """
        # Step 1: Get client_credentials token
        token_url = f"{self.OAUTH_HOST}/account/api/oauth/token"
        device_url = f"{self.OAUTH_HOST}/account/api/oauth/deviceAuthorization"

        self._logger.debug("Obtaining client_credentials token...")

        try:
            token_resp = self.session.post(
                token_url,
                headers={"Authorization": self._basic_auth()},
                data={"grant_type": "client_credentials"},
                timeout=self.config.timeout,
            )
            self._logger.network("POST", token_url, status=token_resp.status_code)
            token_resp.raise_for_status()

            client_token = token_resp.json().get("access_token", "")
            if not client_token:
                self._logger.error("No access_token in client_credentials response")
                return None

            # Step 2: Start device authorization with Bearer token
            self._logger.debug("Starting device authorization", endpoint=device_url)

            response = self.session.post(
                device_url,
                headers={"Authorization": f"Bearer {client_token}"},
                data={"prompt": "login"},
                timeout=self.config.timeout,
            )

            self._logger.network("POST", device_url, status=response.status_code)
            response.raise_for_status()

            data = response.json()
            self._logger.auth("Device authorization initiated")
            return data

        except requests.RequestException as e:
            self._logger.error(
                "Device auth start failed",
                exc=e,
                status=getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None,
            )
            return None

    def poll_device_auth(
        self, device_code: str, interval: int = 5, max_attempts: int = 60
    ) -> dict[str, Any] | None:
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
                    headers={"Authorization": self._basic_auth()},
                    data={"grant_type": "device_code", "device_code": device_code},
                    timeout=self.config.timeout,
                )

                if response.status_code == 200:
                    self._logger.auth("Device authorization completed", attempt=attempt)
                    return response.json()

                # Handle pending/error states
                error_data = response.json()
                error_code = error_data.get("errorCode", "")

                if "authorization_pending" in error_code:
                    self._logger.debug(
                        "Waiting for authorization...", attempt=f"{attempt}/{max_attempts}"
                    )
                    time.sleep(interval)
                    continue

                elif "slow_down" in error_code:
                    self._logger.debug("Rate limited, slowing down")
                    time.sleep(interval * 2)
                    continue

                elif "expired" in error_code:
                    self._logger.error("Device code expired")
                    return None

                else:
                    self._logger.error(
                        "Device auth error",
                        error_code=error_code,
                        error_msg=error_data.get("errorMessage", ""),
                    )
                    return None

            except requests.RequestException as e:
                self._logger.error("Polling error", exc=e, attempt=attempt)
                time.sleep(interval)

        self._logger.error("Max polling attempts reached")
        return None

    def refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
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
                headers={"Authorization": self._basic_auth()},
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                timeout=self.config.timeout,
            )

            self._logger.network("POST", url, status=response.status_code)
            response.raise_for_status()

            self._logger.auth("Token refreshed successfully")
            return response.json()

        except requests.RequestException as e:
            self._logger.error(
                "Token refresh failed",
                exc=e,
                status=getattr(e.response, "status_code", None) if hasattr(e, "response") else None,
            )
            return None

    def verify_token(self, access_token: str) -> dict[str, Any] | None:
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
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=self.config.timeout,
            )

            self._logger.network("GET", url, status=response.status_code)

            if response.status_code == 200:
                data = response.json()
                self._logger.debug(
                    "Token verified",
                    account=data.get("displayName"),
                    account_id=data.get("account_id", "")[:8] + "...",
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
        self, access_token: str, cookies: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Get current weekly free games from Epic Store.

        Uses the dedicated freeGamesPromotions API which returns
        real offer IDs and namespaces needed for claiming.

        Args:
            access_token: Valid access token.
            cookies: Optional cookies (unused, kept for compatibility).

        Returns:
            List of free game dictionaries with id, namespace, title, slug.
        """
        self._logger.info("Fetching free games from Epic Store...")

        # Try the dedicated Free Games Promotions API first (most reliable)
        free_games = self._get_weekly_free_games()
        if free_games:
            return free_games

        # Fallback: Try external API
        self._logger.debug("Free Games API failed, trying external API...")
        external_games = self.get_external_freebies()
        if external_games:
            return external_games

        # Last resort: no games found
        self._logger.warning("All APIs failed. No free games detected.")
        return []

    def _get_weekly_free_games(self) -> list[dict[str, Any]]:
        """
        Get weekly free games from Epic's freeGamesPromotions API.

        This API returns all current and upcoming free game promotions
        with real offer IDs that can be used for claiming.

        Returns:
            List of currently active free games.
        """
        self._logger.debug("Querying freeGamesPromotions API...")

        params = {
            "locale": self.config.locale,
            "country": self.config.country,
            "allowCountries": self.config.country,
        }

        try:
            response = self.session.get(
                self.FREE_GAMES_API,
                params=params,
                timeout=self.config.timeout,
            )

            self._logger.network("GET", self.FREE_GAMES_API, status=response.status_code)

            if response.status_code != 200:
                self._logger.warning(f"Free Games API returned {response.status_code}")
                return []

            data = response.json()
            return self._parse_promotions_response(data)

        except requests.RequestException as e:
            self._logger.warning("Free Games API request failed", exc=e)
            return []

    def _parse_promotions_response(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse the freeGamesPromotions API response.

        Filters games where:
        - discountPercentage = 0 (100% off = free)
        - startDate <= now <= endDate (currently active)

        Args:
            data: Raw API response

        Returns:
            List of active free games
        """
        free_games = []
        now = datetime.now(timezone.utc)

        try:
            elements = (
                data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
            )

            self._logger.debug(f"Found {len(elements)} elements in promotions response")

            for game in elements:
                promotions = game.get("promotions")
                if not promotions:
                    continue

                # Check promotional offers (current free games)
                promo_offers = promotions.get("promotionalOffers", [])
                for promo_group in promo_offers:
                    for offer in promo_group.get("promotionalOffers", []):
                        discount = offer.get("discountSetting", {}).get("discountPercentage", 100)

                        if discount == 0:  # 0% = 100% discount = FREE
                            try:
                                start = datetime.fromisoformat(
                                    offer["startDate"].replace("Z", "+00:00")
                                )
                                end = datetime.fromisoformat(
                                    offer["endDate"].replace("Z", "+00:00")
                                )

                                if start <= now <= end:
                                    # Get the best slug for the game
                                    slug = self._extract_slug(game)

                                    game_info = {
                                        "title": game["title"],
                                        "id": game["id"],
                                        "namespace": game["namespace"],
                                        "slug": slug,
                                    }
                                    free_games.append(game_info)
                                    self._logger.game(
                                        "Free game found",
                                        game["title"],
                                        id=game["id"][:8] + "...",
                                        namespace=game["namespace"][:12] + "...",
                                    )
                            except (KeyError, ValueError) as e:
                                self._logger.debug(f"Error parsing offer dates: {e}")

            self._logger.success(f"Found {len(free_games)} free games")
            return free_games

        except Exception as e:
            self._logger.error("Error parsing promotions response", exc=e)
            return []

    def _extract_slug(self, game: dict[str, Any]) -> str:
        """
        Extract the best URL slug for a game.

        Tries multiple sources in order of preference:
        1. catalogNs.mappings[].pageSlug
        2. offerMappings[].pageSlug
        3. productSlug
        4. urlSlug

        Args:
            game: Game data from API

        Returns:
            Best available slug
        """
        # Try catalogNs mappings first (most reliable)
        mappings = game.get("catalogNs", {}).get("mappings", [])
        if mappings:
            for mapping in mappings:
                if mapping.get("pageType") == "productHome":
                    return mapping.get("pageSlug", "")
            # Fallback to first mapping
            return mappings[0].get("pageSlug", "")

        # Try offerMappings
        offer_mappings = game.get("offerMappings", [])
        if offer_mappings:
            return offer_mappings[0].get("pageSlug", "")

        # Fallback to productSlug or urlSlug
        return game.get("productSlug") or game.get("urlSlug", "")

    def get_external_freebies(self) -> list[dict[str, Any]]:
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
                self.EXTERNAL_FREE_GAMES_API,
                timeout=self.config.timeout,
                verify=True,
            )

            self._logger.network("GET", self.EXTERNAL_FREE_GAMES_API, status=response.status_code)

            if response.status_code == 200:
                data = response.json()

                # Validate response structure
                if not isinstance(data, dict):
                    self._logger.warning("External API returned invalid structure (not dict)")
                    return []

                games = data.get("currentGames", [])

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
                            "title": game.get("title", "Unknown"),
                            "id": game.get("id", ""),
                            "namespace": game.get("namespace", ""),
                            "slug": game.get("slug", ""),
                        }
                        free_games.append(game_info)
                        self._logger.game(
                            "Free game found",
                            game_info["title"],
                            id=game_info["id"][:8] if game_info["id"] else "N/A",
                        )

                    return free_games

            return []

        except requests.RequestException as e:
            self._logger.warning("Erro ao buscar API externa", exc=e)
            return []

    # =========================================================================
    # Entitlements (Owned Games)
    # =========================================================================

    def get_owned_games(
        self, access_token: str, account_id: str
    ) -> dict[str, set[str]]:
        """
        Get owned games data for verification.

        Returns a dict with two sets:
        - ``"ids"``:  set of ``catalogItemId`` values
        - ``"namespaces"``: set of ``namespace`` values

        The free games API uses an *offer* catalog ID that differs from
        the entitlement's ``catalogItemId``, so callers should verify
        ownership by **namespace** rather than by ID.
        """
        url = f"{self.ENTITLEMENT_HOST}/entitlement/api/account/{account_id}/entitlements"

        self._logger.debug("Fetching owned games/entitlements...")

        result: dict[str, set[str]] = {"ids": set(), "namespaces": set()}
        try:
            response = self.session.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"count": 5000},
                timeout=self.config.timeout,
            )

            self._logger.network("GET", url, status=response.status_code)
            response.raise_for_status()

            entitlements = response.json()
            for e in entitlements:
                cid = e.get("catalogItemId", "")
                ns = e.get("namespace", "")
                if cid:
                    result["ids"].add(cid)
                if ns:
                    result["namespaces"].add(ns)

            self._logger.debug(f"Found {len(result['ids'])} owned items")
            return result

        except requests.RequestException as e:
            self._logger.error(
                "Error fetching entitlements", exc=e, account_id=account_id[:8] + "..."
            )
            return result

    # =========================================================================
    # Claim / Purchase
    # =========================================================================

    def claim_game(
        self,
        access_token: str,
        account_id: str,
        offer_id: str,
        namespace: str,
        title: str = "Unknown",
        slug: str = "",
    ) -> str:
        """
        Claim a free game via browser-based purchase flow.

        After the browser flow reports success, verifies ownership via
        the entitlements API to avoid false positives.

        Returns:
            ClaimStatus value string.
        """
        self._logger.game("Attempting to claim", title, offer_id=offer_id[:8] + "...")

        status = self._claim_via_playwright(namespace, offer_id, access_token, title, slug)

        if status == ClaimStatus.CLAIMED:
            try:
                self._logger.info("Verifying claim via entitlements...")
                for attempt in range(1, 11):
                    owned = self.get_owned_games(access_token, account_id)
                    if namespace in owned["namespaces"]:
                        self._logger.success(f"Claim verified: {title}")
                        return ClaimStatus.CLAIMED
                    time.sleep(3)
                    if attempt in {3, 6, 9}:
                        self._logger.info(
                            "Still waiting for entitlement propagation...",
                            attempt=f"{attempt}/10",
                        )

                self._logger.error(
                    "Claim flow completed but entitlement NOT found.",
                    title=title,
                )
                return ClaimStatus.FAILED
            except Exception as e:
                self._logger.error("Claim verification failed", exc=e)
                return ClaimStatus.FAILED

        return status

    # =========================================================================
    # Browser-based claim helpers
    # =========================================================================

    # Age gate keywords (lowercased)
    _AGE_GATE_KEYWORDS = [
        "data de nascimento",
        "date of birth",
        "age gate",
        "não ser adequado para todas as idades",
        "may not be appropriate for all ages",
        "forneça sua data de nascimento",
        "provide your date of birth",
        "enter your date of birth",
    ]

    def _handle_age_gate(self, page) -> None:
        """
        Detect and dismiss the Epic Store age-gate overlay.

        Mature-rated games (18+) show a date-of-birth form before the
        product page becomes interactive.  The Epic age gate uses custom
        dropdown buttons (``#day_toggle``, ``#month_toggle``,
        ``#year_toggle``) — **not** native ``<select>`` elements.
        """
        text = self._get_page_text(page)
        if not any(kw in text for kw in self._AGE_GATE_KEYWORDS):
            return

        self._logger.info("Age gate detected — filling birth date...")

        # The Epic age gate uses custom dropdown buttons:
        #   #day_toggle   → aria-controls="day_menu"
        #   #month_toggle → aria-controls="month_menu"
        #   #year_toggle  → aria-controls="year_menu"
        for field_id, menu_id, value in [
            ("day_toggle", "day_menu", "01"),
            ("month_toggle", "month_menu", "01"),
            ("year_toggle", "year_menu", "1990"),
        ]:
            try:
                toggle = page.locator(f"#{field_id}")
                if not toggle.is_visible(timeout=3000):
                    self._logger.warning(f"Age gate dropdown #{field_id} not found")
                    continue

                toggle.click(timeout=3000)
                page.wait_for_timeout(500)

                # Click the menu item matching the value
                menu = page.locator(f"#{menu_id}")
                # Try exact text match first, then contains
                item = menu.locator(f'[role="menuitem"]:has-text("{value}")').first
                try:
                    if item.is_visible(timeout=2000):
                        item.click(timeout=3000)
                        page.wait_for_timeout(300)
                        continue
                except Exception:
                    pass

                # Fallback: try any clickable item with the value text
                item = menu.locator(f'li:has-text("{value}"), '
                                    f'div:has-text("{value}"), '
                                    f'button:has-text("{value}")').first
                try:
                    if item.is_visible(timeout=1500):
                        item.click(timeout=3000)
                        page.wait_for_timeout(300)
                except Exception:
                    self._logger.warning(
                        f"Could not select value '{value}' in #{menu_id}"
                    )

            except Exception as e:
                self._logger.warning(f"Age gate field {field_id} error: {e}")

        page.wait_for_timeout(500)

        # Click Continue button (should now be enabled)
        try:
            continue_btn = page.locator("#btn_age_continue")
            if continue_btn.is_visible(timeout=2000):
                continue_btn.click(timeout=10000)
                self._logger.info("Age gate dismissed")
                page.wait_for_timeout(3000)
                return
        except Exception as e:
            self._logger.warning(f"Age gate continue click failed: {e}")

        # Last resort: reload with JS bypass
        self._logger.warning("Age gate not dismissed — attempting JS bypass")
        try:
            page.evaluate("""
                try {
                    localStorage.setItem('ageGatePassed', 'true');
                    localStorage.setItem('diesel_age_gate', '1990-01-01');
                } catch(e) {}
            """)
            page.reload(wait_until="load", timeout=30000)
            page.wait_for_timeout(3000)
        except Exception:
            pass

    def _find_button(
        self,
        page,
        selectors: list[str],
        *,
        timeout: int = 2000,
    ):
        """
        Find the first visible button matching any of *selectors*.

        Searches both the top-level page and any embedded iframes.

        Returns:
            A Playwright Locator, or ``None``.
        """
        for selector in selectors:
            try:
                loc = page.locator(selector).first
                if loc.is_visible(timeout=timeout):
                    return loc
            except Exception:
                continue

        # Search inside iframes (purchase flows often use them)
        for frame in page.frames:
            for selector in selectors:
                try:
                    loc = frame.locator(selector).first
                    if loc.is_visible(timeout=min(timeout, 1000)):
                        return loc
                except Exception:
                    continue
        return None

    def _get_page_text(self, page) -> str:
        """
        Get combined visible text from all frames (lowercased).
        """
        parts: list[str] = []
        for frame in page.frames:
            with contextlib.suppress(Exception):
                parts.append(frame.locator("body").inner_text())
        return "\n".join(parts).lower()

    def _has_captcha(self, page) -> bool:
        """Detect whether a CAPTCHA challenge is currently visible on the page."""
        # Check for visible hCaptcha challenge iframe (most reliable signal)
        for selector in CAPTCHA_SELECTORS:
            try:
                loc = page.locator(selector)
                if loc.count() > 0 and loc.first.is_visible(timeout=1000):
                    return True
            except Exception:
                pass

        # Check iframes for visible challenge
        for frame in page.frames:
            if "hcaptcha" in frame.url:
                try:
                    # The challenge frame is the one with "frame=challenge"
                    if "challenge" in frame.url:
                        return True
                except Exception:
                    pass

        # Fall back to keyword detection in visible text
        text = self._get_page_text(page)
        # Only trigger on strong CAPTCHA signals (not just "hcaptcha" in source)
        strong_keywords = [
            "verificação de segurança",
            "security check",
            "mais uma etapa",
            "complete a security",
            "selecione o item",
            "select the item",
        ]
        return any(kw in text for kw in strong_keywords)

    def _wait_for_captcha_resolution(self, page) -> bool:
        """
        Auto-wait for CAPTCHA resolution by polling.

        Three detection strategies:
        1. ``textarea[name="h-captcha-response"]`` has a value -> solved.
        2. Challenge iframe becomes hidden -> solved.
        3. CAPTCHA keywords disappear from page text -> solved.

        Returns:
            True if CAPTCHA was resolved, False if timed out or rate-limited.
        """
        timeout = self.config.captcha_timeout
        self._logger.warning(f"CAPTCHA detected -- waiting up to {timeout}s for resolution...")

        start = time.time()
        poll_interval = 3

        while time.time() - start < timeout:
            # Strategy 1: h-captcha-response textarea has value
            try:
                textarea = page.locator('textarea[name="h-captcha-response"]')
                if textarea.count() > 0:
                    value = textarea.input_value(timeout=1000)
                    if value:
                        self._logger.info("CAPTCHA resolved (response token detected)")
                        return True
            except Exception:
                pass

            # Strategy 2: challenge iframe is now hidden
            try:
                challenge = page.locator('iframe[src*="hcaptcha.com"][src*="frame=challenge"]')
                if challenge.count() > 0 and not challenge.is_visible(timeout=500):
                    self._logger.info("CAPTCHA resolved (challenge iframe hidden)")
                    return True
            except Exception:
                pass

            # Strategy 3: CAPTCHA keywords gone from page
            text = self._get_page_text(page)
            if not any(kw in text for kw in CAPTCHA_KEYWORDS):
                self._logger.info("CAPTCHA resolved (keywords no longer present)")
                return True

            # Check for rate-limit (24h block)
            if any(pat in text for pat in RATE_LIMIT_PATTERNS):
                self._logger.error("CAPTCHA rate-limit detected -- account blocked for ~24h")
                return False

            elapsed = int(time.time() - start)
            if elapsed % 15 == 0 and elapsed > 0:
                self._logger.info(f"Still waiting for CAPTCHA... ({elapsed}s)")

            page.wait_for_timeout(poll_interval * 1000)

        self._logger.error(f"CAPTCHA timed out after {timeout}s")
        return False

    def _check_page_result(self, page) -> str:
        """
        Inspect the current page to decide the claim result.

        Returns:
            A ClaimStatus value string.
        """
        final_url = page.url
        text = self._get_page_text(page)

        if any(pat in text for pat in RATE_LIMIT_PATTERNS):
            return ClaimStatus.RATE_LIMITED

        # URL-based detection is the most reliable signal
        if (
            "receipt" in final_url
            or "confirmation" in final_url
            or "#/purchase/success" in final_url
        ):
            return ClaimStatus.CLAIMED

        # Check success BEFORE already-owned: post-purchase pages
        # contain phrases like "na biblioteca" which match both,
        # but "agradecemos" / "order complete" only match success.
        has_success = any(pat in text for pat in SUCCESS_PATTERNS)
        has_already_owned = any(pat in text for pat in ALREADY_OWNED_PATTERNS)

        if has_success and has_already_owned:
            # Both signals — likely a successful purchase confirmation
            # ("your order is now in your library")
            return ClaimStatus.CLAIMED

        if has_success:
            return ClaimStatus.CLAIMED

        if has_already_owned:
            return ClaimStatus.ALREADY_OWNED

        if "invalid_offers_code_redemption_only" in text:
            return ClaimStatus.FAILED

        # No clear signal — return FAILED (caller can verify via entitlements)
        self._logger.debug("No clear success/failure signal on page")
        return ClaimStatus.FAILED

    def _save_debug_artifact(self, page, name: str) -> None:
        """Save a screenshot to the configured debug directory."""
        import os

        debug_dir = self.config.debug_dir
        os.makedirs(debug_dir, exist_ok=True)
        with contextlib.suppress(Exception):
            page.screenshot(path=os.path.join(debug_dir, f"{name}.png"))

    def _claim_via_playwright(
        self,
        namespace: str,
        offer_id: str,
        access_token: str,
        title: str,
        slug: str = "",
    ) -> str:
        """
        Claim a free game using a browser-based purchase flow.

        Flow:
        1. Open the product page (or fallback payment page).
        2. Click the "Get" / "Obter" button.
        3. If a checkout step appears, click "Place Order".
        4. If CAPTCHA appears, auto-wait for user to solve it.
        5. After CAPTCHA, wait for Talon SDK auto-submit (~5s),
           then fallback re-click if needed.
        6. Inspect the page to determine result.

        Returns:
            A ClaimStatus value string.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            self._logger.error(f"Playwright not installed: {e}")
            return ClaimStatus.FAILED

        # Build the product URL
        locale = self.config.locale.replace("_", "-")  # pt_BR -> pt-BR
        if slug:
            product_url = f"https://store.epicgames.com/{locale}/p/{slug}"
            self._logger.info(f"Opening product page: {product_url}")
        else:
            product_url = (
                f"https://www.epicgames.com/store/purchase?offers=1-{namespace}-{offer_id}"
            )
            self._logger.info(f"Opening purchase page: {product_url}")

        browser_mgr = BrowserManager(self.config, self._logger)

        try:
            with sync_playwright() as p:
                page = browser_mgr.get_page(
                    p,
                    access_token=access_token,
                    headless=False,
                )

                # Navigate to store root first — establishes cookie domain
                # and activates the injected EPIC_EG1 session cookie.
                self._logger.info("Navigating to Epic Store to establish session...")
                page.goto(
                    "https://store.epicgames.com/",
                    wait_until="load",
                    timeout=60000,
                )
                page.wait_for_timeout(3000)

                # Verify login succeeded (look for account menu indicator)
                store_url = page.url
                if "login" in store_url.lower() or "id/login" in store_url.lower():
                    self._logger.warning(
                        "Store redirected to login — waiting for manual login..."
                    )
                    # Wait up to 120s for user to log in manually
                    for _wait in range(40):
                        page.wait_for_timeout(3000)
                        if "login" not in page.url.lower():
                            self._logger.info("Login completed!")
                            page.wait_for_timeout(2000)
                            break
                    else:
                        self._logger.error("Login timeout — aborting")
                        return ClaimStatus.FAILED

                # Navigate to the product/purchase page
                self._logger.info(f"Navigating to: {product_url}")
                page.goto(product_url, wait_until="load", timeout=60000)
                page.wait_for_timeout(5000)

                current_url = page.url
                self._logger.info(f"Current URL: {current_url}")

                # Login redirect check
                if "login" in current_url.lower():
                    self._logger.warning("Redirected to login -- session invalid")
                    return ClaimStatus.FAILED

                # Read page text once
                visible_text = self._get_page_text(page)

                if "invalid_offers_code_redemption_only" in visible_text:
                    self._logger.error("Offer is code-redemption only", title=title)
                    return ClaimStatus.FAILED

                if any(pat in visible_text for pat in ALREADY_OWNED_PATTERNS):
                    self._logger.info(f"Already owned: {title}")
                    return ClaimStatus.ALREADY_OWNED

                # Handle age gate if present (mature content games)
                self._handle_age_gate(page)

                # --- Step 1: Find and click the "Get" / "Obter" button ---
                order_button = self._find_button(page, CLAIM_BUTTON_SELECTORS)

                if not order_button:
                    self._logger.error("Claim/Get button not found")
                    self._save_debug_artifact(page, "no_button")
                    return ClaimStatus.FAILED

                self._logger.info("Found claim button -- clicking...")
                with contextlib.suppress(Exception):
                    order_button.scroll_into_view_if_needed()

                page.wait_for_timeout(2000)

                # Try normal click first (preserves event handlers),
                # then force click if that fails
                try:
                    order_button.click(timeout=10000)
                except Exception:
                    try:
                        order_button.click(force=True, timeout=10000)
                    except Exception:
                        try:
                            order_button.evaluate("el => el.click()")
                        except Exception:
                            try:
                                order_button.dispatch_event("click")
                            except Exception:
                                self._logger.error("All click strategies failed")
                                return ClaimStatus.FAILED

                self._logger.info("Waiting for checkout step...")
                page.wait_for_timeout(3000)

                # --- Step 2: Checkout / confirm order ---
                # The checkout overlay can take several seconds to load,
                # especially on real Chrome.  Retry several times.
                # For 18+ games, an age-gate popup may appear after clicking
                # "Obter" — handle it here too.
                checkout_button = None
                original_url = page.url  # to detect navigation
                for retry in range(10):
                    # Handle age gate that may appear AFTER clicking "Obter"
                    # (common for 18+ rated games)
                    self._handle_age_gate(page)

                    checkout_button = self._find_button(
                        page, CHECKOUT_SELECTORS, timeout=3000
                    )
                    if checkout_button:
                        break

                    # Check for strong success/already-owned signals only
                    # (no optimistic fallback — checkout may still be loading)
                    text = self._get_page_text(page)
                    url = page.url

                    if any(pat in text for pat in ALREADY_OWNED_PATTERNS):
                        self._logger.info(f"Already owned: {title}")
                        return ClaimStatus.ALREADY_OWNED

                    # Only trust success patterns if URL changed from
                    # product page (avoids matching game descriptions
                    # or localization strings embedded in page text)
                    url_changed = url != original_url
                    purchase_url = any(
                        kw in url
                        for kw in ("receipt", "confirmation", "purchase/success")
                    )
                    if purchase_url or (
                        url_changed and any(pat in text for pat in SUCCESS_PATTERNS)
                    ):
                        self._logger.info(
                            "Order completed automatically (no checkout needed)"
                        )
                        return ClaimStatus.CLAIMED

                    # Detect login redirect after clicking claim
                    if "login" in url.lower() or "id/login" in url.lower():
                        self._logger.warning(
                            "Redirected to login after click — waiting for login..."
                        )
                        for _w in range(40):
                            page.wait_for_timeout(3000)
                            if "login" not in page.url.lower():
                                self._logger.info("Login completed — retrying claim")
                                page.wait_for_timeout(3000)
                                break
                        else:
                            self._logger.error("Login timeout")
                            return ClaimStatus.FAILED
                        # After login, the redirect should land on the purchase
                        # page — restart checkout detection
                        continue

                    if retry < 9:
                        self._logger.debug(
                            f"Checkout button not found yet... (attempt {retry + 1}/10)"
                        )
                        page.wait_for_timeout(2000)

                if not checkout_button:
                    self._logger.warning(
                        "Checkout button not found -- trying direct purchase URL..."
                    )
                    self._save_debug_artifact(page, "no_checkout_button")

                    # Fallback: navigate to the direct purchase page
                    purchase_url = (
                        f"https://www.epicgames.com/store/purchase"
                        f"?offers=1-{namespace}-{offer_id}"
                    )
                    self._logger.info(f"Navigating to: {purchase_url}")
                    page.goto(purchase_url, wait_until="load", timeout=60000)
                    page.wait_for_timeout(5000)

                    # Handle age gate on direct purchase page
                    self._handle_age_gate(page)

                    # Look for checkout button on Direct purchase page
                    for retry2 in range(8):
                        checkout_button = self._find_button(
                            page, CHECKOUT_SELECTORS, timeout=3000
                        )
                        if checkout_button:
                            break

                        text = self._get_page_text(page)
                        if any(pat in text for pat in ALREADY_OWNED_PATTERNS):
                            self._logger.info(f"Already owned: {title}")
                            return ClaimStatus.ALREADY_OWNED
                        if any(pat in text for pat in SUCCESS_PATTERNS):
                            return ClaimStatus.CLAIMED

                        # Handle age gate in purchase flow too
                        self._handle_age_gate(page)

                        if retry2 < 7:
                            self._logger.debug(
                                f"Direct purchase: waiting... ({retry2 + 1}/8)"
                            )
                            page.wait_for_timeout(2000)

                    if not checkout_button:
                        # Save final debug info
                        import os as _os
                        _os.makedirs(self.config.debug_dir, exist_ok=True)
                        with contextlib.suppress(Exception):
                            html_path = _os.path.join(
                                self.config.debug_dir, "no_checkout_page.html"
                            )
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(page.content())
                        with contextlib.suppress(Exception):
                            text_path = _os.path.join(
                                self.config.debug_dir, "no_checkout_text.txt"
                            )
                            text_content = self._get_page_text(page)
                            with open(text_path, "w", encoding="utf-8") as f:
                                f.write(f"URL: {page.url}\n\n{text_content}")
                        with contextlib.suppress(Exception):
                            self._logger.debug(f"Page URL: {page.url}")
                            self._logger.debug(
                                f"Frames: {[f.url for f in page.frames]}"
                            )

                if checkout_button:
                    self._logger.info("Checkout step detected -- clicking 'Place Order'...")

                    # Click checkout FIRST, then handle CAPTCHA if it appears.
                    # Epic's Talon SDK runs invisible hCaptcha automatically;
                    # clicking the button triggers it.
                    refreshed = self._find_button(
                        page,
                        CHECKOUT_SELECTORS,
                        timeout=1500,
                    )
                    btn = refreshed or checkout_button
                    try:
                        btn.click(timeout=15000)
                    except Exception:
                        try:
                            btn.click(force=True, timeout=15000)
                        except Exception as e:
                            self._logger.warning(f"Checkout click failed: {e}")

                    page.wait_for_timeout(5000)

                    # Check if order already completed (invisible CAPTCHA auto-passed)
                    result = self._check_page_result(page)
                    if result in (ClaimStatus.CLAIMED, ClaimStatus.ALREADY_OWNED):
                        self._logger.info("Order completed (no visible CAPTCHA)")
                        self._save_debug_artifact(page, "final_state")
                        return result

                    # If CAPTCHA is visible, wait for user to solve it
                    if self._has_captcha(page):
                        self._save_debug_artifact(page, "captcha_detected")
                        resolved = self._wait_for_captcha_resolution(page)

                        if not resolved:
                            text = self._get_page_text(page)
                            if any(pat in text for pat in RATE_LIMIT_PATTERNS):
                                return ClaimStatus.RATE_LIMITED
                            return ClaimStatus.FAILED

                        # Post-CAPTCHA: Talon SDK often auto-submits the order.
                        self._logger.info("CAPTCHA resolved -- waiting for Talon auto-submit...")
                        page.wait_for_timeout(5000)

                        result = self._check_page_result(page)
                        if result in (ClaimStatus.CLAIMED, ClaimStatus.ALREADY_OWNED):
                            self._logger.info("Order completed via Talon auto-submit")
                            self._save_debug_artifact(page, "final_state")
                            return result

                        # Talon didn't auto-submit: try clicking checkout again
                        self._logger.info("Auto-submit didn't fire -- clicking checkout manually")
                        refreshed = self._find_button(
                            page,
                            CHECKOUT_SELECTORS,
                            timeout=1500,
                        )
                        if refreshed:
                            try:
                                refreshed.click(force=True, timeout=15000)
                                page.wait_for_timeout(5000)
                            except Exception as e:
                                self._logger.warning(f"Retry checkout click failed: {e}")
                    else:
                        # No CAPTCHA but order not confirmed — wait a bit more
                        self._logger.debug("No CAPTCHA detected, waiting for page to settle...")
                        page.wait_for_timeout(5000)

                # --- Step 3: Determine result ---
                self._save_debug_artifact(page, "final_state")
                return self._check_page_result(page)

        except Exception as e:
            self._logger.error(f"Browser claim error: {e}")
            return ClaimStatus.FAILED
        finally:
            browser_mgr.close()
