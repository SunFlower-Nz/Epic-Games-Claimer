"""
Shared data models and constants for Epic Games Claimer.

Contains:
- ExtractedCookies dataclass (used by chrome_cookies and playwright_cookies)
- ClaimStatus enum (used by api and claimer)
- Shared constants (domains, cookie names, selectors)
"""

from dataclasses import dataclass
from enum import Enum


# =============================================================================
# Enums
# =============================================================================


class ClaimStatus(str, Enum):
    """Result status of a game claim attempt."""

    CLAIMED = "claimed"
    ALREADY_OWNED = "already_owned"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class ExtractedCookies:
    """Container for extracted Epic Games cookies."""

    epic_eg1: str = ""
    cf_clearance: str = ""
    epic_sso: str = ""
    refresh_eg1: str = ""  # REFRESH_EPIC_EG1
    bearer_hash: str = ""  # bearerTokenHash

    def has_eg1(self) -> bool:
        """Check if EPIC_EG1 was extracted."""
        return bool(self.epic_eg1) and self.epic_eg1.startswith("eg1~")

    def has_refresh_eg1(self) -> bool:
        """Check if REFRESH_EPIC_EG1 was extracted."""
        return bool(self.refresh_eg1)

    def has_cf_clearance(self) -> bool:
        """Check if CF_CLEARANCE was extracted."""
        return bool(self.cf_clearance)


# =============================================================================
# Constants
# =============================================================================

# Epic Games domains for cookie extraction
EPIC_DOMAINS = [
    ".epicgames.com",
    "epicgames.com",
    "store.epicgames.com",
    ".store.epicgames.com",
]

# Cookie names to extract
COOKIE_NAMES = {
    "EG1": "EPIC_EG1",
    "SSO": "EPIC_SSO",
    "CF": "cf_clearance",
    "REFRESH": "REFRESH_EPIC_EG1",
    "BEARER": "bearerTokenHash",
}

# Button selectors for the "Get" / "Obter" action on product pages
CLAIM_BUTTON_SELECTORS = [
    'button:has-text("Obter")',
    'button:has-text("Get")',
    'a:has-text("Obter")',
    '[data-testid="purchase-cta-button"]',
    'button:has-text("Fazer pedido")',
    'button:has-text("Place Order")',
    'button:has-text("Confirm")',
    'button:has-text("Confirmar")',
    'button[data-testid="purchase-app-confirm-order-button"]',
    '#purchase-app button[type="submit"]',
]

# Checkout / confirm order selectors
CHECKOUT_SELECTORS = [
    'button:has-text("Fazer pedido")',
    'button:has-text("Place Order")',
    'button:has-text("Confirm")',
    'button:has-text("Confirmar")',
    'button[data-testid="purchase-app-confirm-order-button"]',
]

# Keywords that indicate a CAPTCHA is present on the page
CAPTCHA_KEYWORDS = [
    "verificação de segurança",
    "security check",
    "mais uma etapa",
    "complete a security",
    "hcaptcha",
    "selecione o item",
    "select the item",
]

# CSS selectors for hCaptcha elements
CAPTCHA_SELECTORS = [
    'iframe[src*="hcaptcha.com"]',
    "#h_captcha_challenge_checkout_free_prod",
]

# Patterns indicating the game was already owned
ALREADY_OWNED_PATTERNS = [
    "you already own this",
    "already in your library",
    "já está na sua biblioteca",
    "você já possui",
    "item already owned",
    "you own this item",
    "na biblioteca",
]

# Patterns indicating a successful purchase
SUCCESS_PATTERNS = [
    "thank you",
    "order complete",
    "purchase complete",
    "successfully",
    "compra concluída",
    "your order",
    "order confirmed",
]

# Patterns indicating CAPTCHA rate-limit (account blocked for 24h)
RATE_LIMIT_PATTERNS = [
    "aguarde 24 horas",
    "captcha.decline",
    "wait 24 hours",
    "não pode mais fazer download",
    "can no longer download",
]
