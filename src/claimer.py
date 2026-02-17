"""
Epic Games Claimer - Main Orchestration.

Coordinates authentication, game discovery, and claiming workflow.
"""

import json
import time
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .api import EpicAPI
from .config import Config
from .logger import Logger
from .models import ClaimStatus
from .playwright_cookies import PlaywrightCookieExtractor
from .session_store import Session, SessionStore


@dataclass
class ClaimResult:
    """Result of a claim attempt."""

    claimed: int = 0
    failed: int = 0
    already_owned: int = 0
    games_processed: list[str] = field(default_factory=list)


class EpicGamesClaimer:
    """
    Main class for claiming free Epic Games.

    Handles:
    - Authentication (device auth, token refresh, fallback cookies)
    - Free games discovery
    - Game claiming workflow
    - Result logging and persistence
    """

    def __init__(self, config: Config | None = None, logger: Logger | None = None):
        """
        Initialize the claimer.

        Args:
            config: Application configuration (uses defaults if None).
            logger: Logger instance (creates new one if None).
        """
        self.config = config or Config()
        self._logger = logger or Logger(str(self.config.log_base_dir))
        self.api = EpicAPI(self.config, self._logger)
        self.session_store = SessionStore(self.config.session_file, self._logger)
        self.session: Session | None = None

    # =========================================================================
    # Authentication
    # =========================================================================

    def authenticate(self) -> bool:
        """
        Authenticate with Epic Games.

        Tries in order:
        1. Load saved session (if valid)
        2. Verify token (if expiration unknown)
        3. Refresh token (if refresh token available)
        4. Use fallback cookies from .env
        5. Start device auth flow (interactive)

        Returns:
            True if authenticated successfully.
        """
        self._logger.subheader("🔐 AUTENTICAÇÃO")

        # 1. Try to load saved session
        self.session = self.session_store.load()

        if self.session and self.session.is_valid():
            self._logger.success(
                f"Sessão válida para: {self.session.display_name}",
                expires_in=self._format_expiry(self.session.time_until_expiry()),
            )
            return True

        # 2. Verify token if expiration is unknown
        if self.session and self.session.access_token and not self.session.expires_at:
            self._logger.info("Verificando token...")
            verify_data = self.api.verify_token(self.session.access_token)

            if verify_data:
                self.session.account_id = verify_data.get("account_id", self.session.account_id)
                self.session.display_name = verify_data.get(
                    "displayName", self.session.display_name
                )
                self.session.expires_at = verify_data.get("expires_at", "")

                self._logger.success(f"Token verificado: {self.session.display_name}")
                self.session_store.save(self.session)
                return True

        # 3. Try to refresh
        if self.session and self.session.can_refresh():
            self._logger.info("Renovando token...")
            token_data = self.api.refresh_token(self.session.refresh_token)

            if token_data:
                self._update_session(token_data)
                self.session_store.save(self.session)
                self._logger.success(f"Token renovado: {self.session.display_name}")
                return True
            else:
                self._logger.warning("Falha ao renovar token")

        # 4. Try automatic Chrome cookie extraction (Profile negao)
        self._logger.info("Tentando extrair cookies do Chrome automaticamente...")
        chrome_session = self.session_store.refresh_from_chrome(self.config)
        if chrome_session and chrome_session.is_valid():
            self.session = chrome_session
            return True

        # 5. Try fallback cookies from .env
        if self.config.fallback_eg1:
            self._logger.info("Tentando credenciais do .env...")

            # First try to create session from token
            fallback_session = Session.from_eg1_token(self.config.fallback_eg1)

            if fallback_session and fallback_session.is_valid():
                self.session = fallback_session
                self.session_store.save(self.session)
                self._logger.success(f"Autenticado via .env: {self.session.display_name}")
                return True

            # Verify if token still works
            verify_data = self.api.verify_token(self.config.fallback_eg1)
            if verify_data:
                self.session = Session(
                    access_token=self.config.fallback_eg1,
                    account_id=verify_data.get("account_id", ""),
                    display_name=verify_data.get("displayName", ""),
                    expires_at=verify_data.get("expires_at", ""),
                )
                self._logger.success(f"Autenticado: {self.session.display_name}")
                return True
            else:
                self._logger.warning("Credenciais do .env inválidas/expiradas")

        # 6. Start device auth flow (interactive) - last resort
        if self.config.client_secret:
            self._logger.warning("Iniciando device auth (interativo)...")
            if self._device_auth_flow():
                return True

        # 7. Interactive Playwright Login (GUI) - Absolute last resort
        self._logger.warning("Tentando login interativo via navegador...")
        try:
            extractor = PlaywrightCookieExtractor(logger=self._logger)
            cookies = extractor.interactive_login()

            session = None
            if cookies.has_eg1():
                session = Session.from_eg1_token(cookies.epic_eg1)
            elif cookies.has_refresh_eg1():
                session = Session(
                    refresh_token=cookies.refresh_eg1,
                    cookies={"REFRESH_EPIC_EG1": cookies.refresh_eg1},
                )
                # Set dummy refresh expiry to allow refresh
                session.refresh_expires_at = (
                    datetime.now(timezone.utc) + timedelta(days=30)
                ).isoformat()

            if session:
                if cookies.cf_clearance:
                    session.cookies["cf_clearance"] = cookies.cf_clearance

                self.session = session
                self.session_store.save(self.session)
                self._logger.success(
                    f"Autenticado via login interativo: {self.session.display_name or 'Refresh Token'}"
                )
                return True

        except Exception as e:
            self._logger.error(f"Falha no login interativo: {e}")

        self._logger.error(
            "Não foi possível autenticar. Por favor, execute 'python scripts/login.py' manualmente."
        )
        return False

    def _device_auth_flow(self) -> bool:
        """
        Run interactive device authorization flow.

        Opens browser for user to log in.

        Returns:
            True if authenticated successfully.
        """
        self._logger.auth("Iniciando autorização de dispositivo...")

        # Get device code
        device_data = self.api.start_device_auth()
        if not device_data:
            self._logger.error("Falha ao iniciar autorização")
            return False

        # Extract data
        verification_uri = device_data.get("verification_uri_complete")
        user_code = device_data.get("user_code")
        device_code = device_data.get("device_code")
        expires_in = device_data.get("expires_in", 600)
        interval = device_data.get("interval", 5)

        # Show instructions
        self._logger.subheader("AUTORIZAÇÃO EPIC GAMES")
        if verification_uri:
            self._logger.info(f"1. Abra esta URL no navegador: {verification_uri}")
        else:
            self._logger.warning("URL de verificação ausente")
        self._logger.info(f"2. Se solicitado, digite o código: {user_code}")
        self._logger.info("3. Faça login com sua conta Epic Games")
        self._logger.info(f"Aguardando autorização (expira em {expires_in // 60} minutos)...")

        # Try to open browser automatically
        try:
            if verification_uri:
                webbrowser.open(verification_uri)
            self._logger.info("Navegador aberto automaticamente")
        except Exception:
            pass

        # Poll for completion
        token_data = self.api.poll_device_auth(
            device_code or "", interval=interval, max_attempts=expires_in // interval
        )

        if not token_data:
            self._logger.error("Autorização falhou ou expirou")
            return False

        # Update and save session
        self._update_session(token_data)
        if self.session:
            self.session_store.save(self.session)
            self._logger.success(f"Autenticado como: {self.session.display_name}")
        return True

    def _update_session(self, token_data: dict[str, Any]) -> None:
        """
        Update session from token response.

        Args:
            token_data: OAuth token response dictionary.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data.get("expires_in", 7200)
        )
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data.get("refresh_expires", 28800)
        )

        self.session = Session(
            access_token=token_data.get("access_token", ""),
            refresh_token=token_data.get("refresh_token", ""),
            account_id=token_data.get("account_id", ""),
            display_name=token_data.get("displayName", ""),
            expires_at=expires_at.isoformat(),
            refresh_expires_at=refresh_expires_at.isoformat(),
        )

    def _format_expiry(self, remaining: timedelta | None) -> str:
        """Format time remaining until expiry."""
        if not remaining:
            return "unknown"
        hours = remaining.total_seconds() / 3600
        if hours >= 1:
            return f"{hours:.1f}h"
        return f"{int(remaining.total_seconds() / 60)}min"

    # =========================================================================
    # Game Discovery
    # =========================================================================

    def get_claimable_games(self) -> list[dict[str, Any]]:
        """
        Get list of free games that can be claimed.

        Filters out already owned games.

        Returns:
            List of claimable game dictionaries.
        """
        if not self.session:
            self._logger.error("Não autenticado")
            return []

        self._logger.subheader("🎮 BUSCANDO JOGOS GRÁTIS")

        # Get free games from Epic Store
        free_games = self.api.get_free_games(self.session.access_token, self.session.cookies)
        if self.config.low_cpu_mode:
            time.sleep(self.config.low_cpu_sleep_ms / 1000.0)

        # Optionally merge with external API
        if self.config.use_external_freebies:
            external = self.api.get_external_freebies()
            if external and not free_games:
                free_games = external

        if not free_games:
            self._logger.info("Nenhum jogo grátis encontrado no momento")
            return []

        # Get owned games to filter
        owned = self.api.get_owned_games(self.session.access_token, self.session.account_id)
        if self.config.low_cpu_mode:
            time.sleep(self.config.low_cpu_sleep_ms / 1000.0)

        # Filter out already owned (check by namespace since
        # offer IDs differ from entitlement catalogItemIds)
        claimable = []
        for game in free_games:
            if game["namespace"] in owned["namespaces"]:
                self._logger.info(f"Já possuído: {game['title']}")
            else:
                claimable.append(game)

        if claimable:
            self._logger.success(f"{len(claimable)} jogo(s) disponível(is) para resgate")
        else:
            self._logger.info("Todos os jogos grátis já estão na sua biblioteca!")

        return claimable

    # =========================================================================
    # Claiming
    # =========================================================================

    def claim_all_games(self) -> ClaimResult:
        """
        Claim all available free games.

        Returns:
            ClaimResult with counts and processed games.
        """
        result = ClaimResult()

        if not self.session:
            self._logger.error("Não autenticado")
            return result

        # Get claimable games
        claimable = self.get_claimable_games()

        if not claimable:
            return result

        self._logger.subheader("🎁 RESGATANDO JOGOS")

        for game in claimable:
            title = game["title"]
            result.games_processed.append(title)

            status = self.api.claim_game(
                access_token=self.session.access_token,
                account_id=self.session.account_id,
                offer_id=game["id"],
                namespace=game["namespace"],
                title=title,
                slug=game.get("slug", ""),
            )

            if status == ClaimStatus.CLAIMED:
                result.claimed += 1
            elif status == ClaimStatus.ALREADY_OWNED:
                result.already_owned += 1
            elif status == ClaimStatus.RATE_LIMITED:
                self._logger.error("Rate-limited — skipping remaining games")
                result.failed += 1
                break
            else:
                result.failed += 1

                # Try to refresh token on failure
                if self.session.can_refresh():
                    self._logger.debug("Tentando renovar token após falha...")
                    token_data = self.api.refresh_token(self.session.refresh_token)
                    if token_data:
                        self._update_session(token_data)
                        self.session_store.save(self.session)

            # Small delay between claims to avoid rate limiting
            if len(claimable) > 1:
                time.sleep(
                    1
                    if not self.config.low_cpu_mode
                    else max(1, self.config.low_cpu_sleep_ms / 1000.0)
                )
            elif self.config.low_cpu_mode:
                time.sleep(self.config.low_cpu_sleep_ms / 1000.0)

        return result

    # =========================================================================
    # Data Persistence
    # =========================================================================

    def save_games_info(self, games: list[dict[str, Any]] | None = None) -> None:
        """
        Save information about free games to JSON file.

        Args:
            games: List of games to save (fetches if None).
        """
        if games is None and self.session:
            games = self.api.get_free_games(self.session.access_token, self.session.cookies)

        data = {
            "current_games": games or [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "account": self.session.display_name if self.session else None,
        }

        try:
            output_path = self.config.data_dir / "next_games.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._logger.debug("Games info saved", path=str(output_path))

        except Exception as e:
            self._logger.error("Error saving games info", exc=e)

    # =========================================================================
    # Main Execution
    # =========================================================================

    def run(self) -> ClaimResult:
        """
        Main execution flow.

        1. Authenticate
        2. Find and claim free games
        3. Save games info
        4. Log summary

        Returns:
            ClaimResult with execution results.
        """
        self._logger.header("🎮 EPIC GAMES CLAIMER")
        self._logger.info(f"Iniciando execução: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        result = ClaimResult()

        # Authenticate
        if not self.authenticate():
            self._logger.error("Falha na autenticação - execução cancelada")
            return result

        # Claim games
        result = self.claim_all_games()

        # Save games info
        self.save_games_info()

        # Log summary
        self._logger.summary(
            claimed=result.claimed, failed=result.failed, already_owned=result.already_owned
        )

        return result

    def check_only(self) -> list[dict[str, Any]]:
        """
        Check for free games without claiming.

        Returns:
            List of available free games.
        """
        self._logger.header("🔍 VERIFICANDO JOGOS GRÁTIS")

        if not self.authenticate():
            return []

        games = self.get_claimable_games()
        self.save_games_info()

        return games
